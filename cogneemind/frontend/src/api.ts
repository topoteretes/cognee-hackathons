const BASE = (import.meta as any).env?.VITE_API ?? "http://localhost:8077";
const WS = BASE.replace(/^http/, "ws") + "/events";

async function j(path: string, opts?: RequestInit) {
  const r = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return r.json();
}

export const api = {
  state: () => j("/state"),
  scenario: (stage: string) => j(`/scenario/${stage}`, { method: "POST" }),
  chat: (text: string) => j("/chat", { method: "POST", body: JSON.stringify({ text }) }),
  reset: () => j("/reset", { method: "POST" }),
  lint: () => j("/lint", { method: "POST" }),
  compounding: () => j("/compounding"),
};

export function connectEvents(onMessage: (m: any) => void): () => void {
  let ws: WebSocket | null = null;
  let alive = true;
  const open = () => {
    ws = new WebSocket(WS);
    ws.onmessage = (e) => onMessage(JSON.parse(e.data));
    ws.onclose = () => { if (alive) setTimeout(open, 1000); };
  };
  open();
  return () => { alive = false; ws?.close(); };
}
