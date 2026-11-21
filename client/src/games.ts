/** The games listed on the home page. Each has a design doc in docs/games/. */
export interface Game {
  id: string;
  name: string;
  description: string;
}

export const GAMES: readonly Game[] = [
  {
    id: "graph-artillery",
    name: "Graph artillery",
    description: "Take turns firing shots that follow the graph of a function you type.",
  },
];
