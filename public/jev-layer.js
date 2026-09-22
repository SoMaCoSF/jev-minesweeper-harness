/** Browser Jev layer: typed questions in, policy out. Mock unless window.TYPESAFE_API_KEY. */
export function encodeHold(G, tiles, pathKeys) {
  const questions = {
    tool: { type: "choice", prompt: "wall, tower, or wave?", criteria: { wall: "maze", tower: "dps", wave: "commit" } },
    path_value: { type: "score", prompt: "path quality" },
  };
  const legal = [...tiles.values()].filter(t => t.kind === "empty").slice(0, 40);
  for (const t of legal) {
    const k = t.q + "," + t.r + "," + t.s;
    questions["wall_" + k] = { type: "noul", prompt: "wall " + k };
    questions["tower_" + k] = { type: "noul", prompt: "tower " + k };
  }
  const state = { radius: G.R, gold: G.gold, lives: G.lives, wave: G.wave, path: pathKeys, lattice: "hex-map-wfc" };
  return { state, questions };
}

export function mockDecide(state, questions, pathSet) {
  const answers = {};
  for (const [name, q] of Object.entries(questions)) {
    if (q.type === "choice") answers[name] = { type: "choice", choice: "wall", confidence: 0.6 };
    else if (q.type === "score") answers[name] = { type: "score", score: (state.path || []).length, confidence: 0.7 };
    else {
      const k = name.split("_").slice(1).join("_");
      const near = pathSet.has(k) ? 0.75 : 0.25;
      answers[name] = { type: "noul", noul: name.startsWith("tower_") ? near * 0.9 : near, confidence: 0.55 };
    }
  }
  return { answers, mocked: true, model: "mock" };
}

export function policy(answers) {
  const tool = answers.tool?.choice || "wall";
  if (tool === "wave") return { kind: "wave", target: "" };
  let best = null, v = -1;
  const prefix = tool + "_";
  for (const [name, ans] of Object.entries(answers)) {
    if (!name.startsWith(prefix)) continue;
    const n = ans.noul ?? 0;
    if (n > v) { v = n; best = name.slice(prefix.length); }
  }
  return { kind: tool, target: best, noul: v };
}
