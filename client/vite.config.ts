import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

import { passwordGate } from "./dev/passwordGate";

// In development, Vite serves the client with hot reload and forwards these
// paths to the Python server. In production the Python server serves the
// built client itself, so none of this applies there.
const PYTHON_SERVER = "http://127.0.0.1:8000";
const SERVER_PATHS = ["/login", "/logout", "/healthz", "/api"];

export default defineConfig({
  plugins: [react(), passwordGate({ server: PYTHON_SERVER, serverPaths: SERVER_PATHS })],
  server: {
    proxy: Object.fromEntries(
      // ws: also forward WebSocket connections, such as a room's live connection.
      SERVER_PATHS.map((path) => [path, { target: PYTHON_SERVER, ws: true }]),
    ),
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
