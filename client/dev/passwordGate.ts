import type { Plugin } from "vite";

// What the server's gate (server/src/games_server/auth/gate.py) answers when a
// request has no valid session: a redirect to the login page for GET and
// HEAD, and 401 for anything else.
const GATE_REFUSALS = new Set([303, 401]);

interface Refusal {
  status: number;
  location: string | null;
  body: string;
}

/**
 * Puts the Python server's password gate in front of Vite's dev server.
 *
 * In production the Python server serves the client, so every request passes
 * its gate. In development Vite serves the client, so without this the pages
 * would be open. Rather than copy the gate's logic, this asks the gate itself:
 * each request Vite would serve is first sent to the Python server with the
 * same method, path and cookie, and if the gate refuses it, the gate's answer
 * goes back to the browser instead.
 *
 * `serverPaths` are the paths Vite forwards to the Python server anyway, which
 * applies its gate there itself.
 */
export function passwordGate(options: { server: string; serverPaths: readonly string[] }): Plugin {
  const { server, serverPaths } = options;
  return {
    name: "password-gate",
    apply: "serve", // the dev server only; built files are served by Python
    configureServer(vite) {
      // Added here, rather than in a returned function, so it runs before
      // Vite's own handlers, which would otherwise serve the page first.
      vite.middlewares.use((request, response, next) => {
        const url = request.url ?? "/";
        // Matched the way Vite's proxy matches them: by prefix.
        if (serverPaths.some((path) => url.startsWith(path))) {
          next();
          return;
        }
        askTheGate(server, url, request.method ?? "GET", request.headers.cookie).then(
          (refusal) => {
            if (refusal === null) {
              next();
              return;
            }
            response.statusCode = refusal.status;
            if (refusal.location !== null) {
              response.setHeader("Location", refusal.location);
            }
            response.end(refusal.body);
          },
          () => {
            response.statusCode = 502;
            response.end(
              `Couldn't reach the Python server at ${server} to check the password gate. ` +
                "Is it running? See server/README.md.",
            );
          },
        );
      });
    },
  };
}

/** The gate's answer if it refuses this request, or null if it lets it through. */
async function askTheGate(
  server: string,
  url: string,
  method: string,
  cookie: string | undefined,
): Promise<Refusal | null> {
  const answer = await fetch(new URL(url, server), {
    method,
    headers: cookie === undefined ? {} : { cookie },
    // The gate's redirect is the answer; following it would hide it.
    redirect: "manual",
  });
  if (!GATE_REFUSALS.has(answer.status)) {
    // Past the gate. The Python server has nothing at this path in
    // development, so whatever it answered next doesn't matter.
    return null;
  }
  return {
    status: answer.status,
    location: answer.headers.get("location"),
    body: await answer.text(),
  };
}
