import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import GanttStage from "./GanttStage";
import { api, connectEvents } from "./api";
import type { Discovery, Plan, Wiki } from "./types";

const ACCENT: Record<string, string> = {
  researcher: "#6d4cc8", planner: "#c8870f", observer: "#0a85aa", brain: "#1f9159",
};
const ROSTER = [
  { id: "researcher", role: "Researcher", tag: "discovers strategy" },
  { id: "planner", role: "Planner", tag: "builds the Gantt" },
  { id: "observer", role: "Observer", tag: "detects chaos" },
  { id: "brain", role: "Brain · Wiki", tag: "distills + learns" },
];

interface LogRow { agent: string; message: string; id: number; }
interface ChatRow { who: "you" | "bot"; text: string; id: number; }

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [disc, setDisc] = useState<Discovery | null>(null);
  const [wiki, setWiki] = useState<Wiki>({ timeline: [], index: {} });
  const [log, setLog] = useState<LogRow[]>([]);
  const [active, setActive] = useState<Record<string, boolean>>({});
  const [chat, setChat] = useState<ChatRow[]>([
    { who: "bot", text: "CogneeMind online. Try: ‘delay AB104 by 1 hr’, ‘close G3’, ‘reopen G3’, ‘add flight 09:15 to G2’, ‘storm’, ‘new day’, or ‘what is the best strategy?’", id: 0 },
  ]);
  const [stageTag, setStageTag] = useState("base schedule");
  const [busy, setBusy] = useState(false);
  const [compound, setCompound] = useState<any>(null);
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const idc = useRef(1);
  const wired = useRef(false);

  function poke(agent: string) {
    setActive((a) => ({ ...a, [agent]: true }));
    clearTimeout(timers.current[agent]);
    timers.current[agent] = setTimeout(() => setActive((a) => ({ ...a, [agent]: false })), 1200);
  }

  useEffect(() => {
    // Guard against React StrictMode double-mount in dev so the WS subscriber
    // (and welcome state) don't get wired twice.
    if (wired.current) return;
    wired.current = true;
    api.state().then((s) => { if (s.plan) setPlan(s.plan); if (s.wiki) setWiki(s.wiki); });
    const unsub = connectEvents((m) => {
      if (m.type === "agent") {
        poke(m.agent);
        setLog((l) => [...l.slice(-40), { agent: m.agent, message: m.message, id: idc.current++ }]);
      } else if (m.type === "plan") {
        if (m.plan) setPlan(m.plan);
        if (m.discovery) setDisc(m.discovery);
      } else if (m.type === "wiki") {
        setWiki({ timeline: m.timeline, index: m.index });
      }
    });
    return () => { unsub(); wired.current = false; };
  }, []);

  async function scenario(stage: string, label: string) {
    setBusy(true); setStageTag(label); setLog([]);
    try { await api.scenario(stage); } finally { setTimeout(() => setBusy(false), 1400); }
  }

  async function send(text: string) {
    const youId = idc.current++;
    const typingId = idc.current++;
    setChat((c) => [...c,
      { who: "you", text, id: youId },
      { who: "bot", text: "…", id: typingId },
    ]);
    setBusy(true);
    try {
      const r = await api.chat(text);
      if (r.plan) setPlan(r.plan);
      if (r.discovery) setDisc(r.discovery);
      if (r.wiki) setWiki(r.wiki);
      setChat((c) => c.map((row) =>
        row.id === typingId ? { ...row, text: r.reply ?? "done." } : row));
    } catch (e: any) {
      setChat((c) => c.map((row) =>
        row.id === typingId ? { ...row, text: `error: ${e?.message ?? e}` } : row));
    } finally { setTimeout(() => setBusy(false), 1200); }
  }

  async function runCompounding() {
    setBusy(true);
    try { setCompound(await api.compounding()); } finally { setBusy(false); }
  }

  const sc = plan?.score;
  return (
    <div className="app">
      {/* ── header ── */}
      <header className="head">
        <div className="brand">
          <h1><span className="beacon" />CogneeMind</h1>
          <span className="sub">Gate-Ops Brain</span>
        </div>
        <div className="readout">
          <Cell k="strategy" v={plan?.strategy?.name ?? "—"} wide />
          <Cell k="no-gate" v={sc?.U ?? 0} bad={(sc?.U ?? 0) > 0} />
          <Cell k="conflict" v={sc?.C ?? 0} bad={(sc?.C ?? 0) > 0} />
          <Cell k="walk" v={sc?.W ?? 0} />
          <Cell k="moves" v={sc?.R ?? 0} />
          <Cell k="score" v={sc?.total ?? 0} total />
        </div>
      </header>

      {/* ── stage ── */}
      <main className="stage">
        <div className="stage-tag">scenario · <b>{stageTag}</b>{busy && <> · recomputing…</>}</div>
        {plan && <GanttStage plan={plan} />}
        <div className="legend">
          <span><i style={{ background: "#36e08a" }} />domestic ok</span>
          <span><i style={{ background: "#38d6ff" }} />international</span>
          <span><i style={{ background: "#ff4d57" }} />conflict</span>
          <span><i style={{ background: "#4a525e" }} />remote stand</span>
        </div>
      </main>

      {/* ── rail ── */}
      <aside className="rail">
        <AgentDeck active={active} disc={disc} log={log} />
        <WikiPanel wiki={wiki} compound={compound} onRun={runCompounding} busy={busy} />
        <ChatConsole chat={chat} onSend={send} busy={busy} />
      </aside>

      {/* ── dock ── */}
      <footer className="dock">
        <div className="grp">
          <Trig n="01" label="Base" onClick={() => scenario("base", "base schedule")} />
          <Trig n="02" label="+ Flight" onClick={() => scenario("new_flight", "new flight inserted")} />
          <Trig n="03" label="Close G3" alarm onClick={() => scenario("gate_closed", "gate G3 closed")} />
          <Trig n="04" label="Storm" alarm onClick={() => scenario("storm", "cascading delays")} />
        </div>
        <div className="sep" />
        <button className="trig ghost" onClick={() => api.lint()}>lint wiki</button>
        <button className="trig ghost" onClick={() => send("new day")}>new day</button>
        <button className="trig ghost" onClick={() => { api.reset(); setLog([]); setDisc(null); setStageTag("base schedule"); api.state().then(s => setPlan(s.plan)); }}>reset</button>
      </footer>
    </div>
  );
}

function Cell({ k, v, total, bad, wide }: { k: string; v: any; total?: boolean; bad?: boolean; wide?: boolean }) {
  return (
    <div className={`cell ${total ? "total" : ""} ${bad ? "bad" : ""}`} style={wide ? { minWidth: 132 } : undefined}>
      <div className="k">{k}</div>
      <motion.div className="v" key={String(v)} initial={{ opacity: 0.3, y: -3 }} animate={{ opacity: 1, y: 0 }}>
        {v}
      </motion.div>
    </div>
  );
}

function AgentDeck({ active, disc, log }: { active: Record<string, boolean>; disc: Discovery | null; log: LogRow[] }) {
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => { logRef.current?.scrollTo(0, 1e9); }, [log]);
  return (
    <section className="section">
      <div className="title">Agent Deck {disc && <span className="badge mono">{disc.source.toUpperCase()} · {disc.evals} evals</span>}</div>
      <div className="agents">
        {ROSTER.map((a) => (
          <div key={a.id} className={`agent ${active[a.id] ? "active" : ""}`} style={{ ["--accent" as any]: ACCENT[a.id] }}>
            <div className="role"><span className="dot" />{a.role}</div>
            <div className="what">{a.tag}</div>
          </div>
        ))}
      </div>
      <div className="log" ref={logRef}>
        <AnimatePresence initial={false}>
          {log.map((r) => (
            <div className="row" key={r.id} style={{ ["--accent" as any]: ACCENT[r.agent] ?? "#8b95a3" }}>
              <span className="who">{r.agent}</span>
              <span className="msg">{r.message}</span>
            </div>
          ))}
        </AnimatePresence>
      </div>
    </section>
  );
}

function WikiPanel({ wiki, compound, onRun, busy }: { wiki: Wiki; compound: any; onRun: () => void; busy: boolean }) {
  const t = [...wiki.timeline].reverse().slice(0, 6);
  return (
    <section className="section">
      <div className="title">LLM Wiki · learned strategies <span className="badge mono">v{wiki.timeline.length}</span></div>
      <div className="timeline">
        {t.length === 0 && <div className="mono faint" style={{ fontSize: 11 }}>empty — run a scenario to teach the brain.</div>}
        {t.map((v) => (
          <motion.div className="ver" key={v.version} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}>
            <span className="v">v{v.version}</span>
            <div className="body">
              <div className="strat">{v.strategy}</div>
              <div className="meta">{v.signature} · {v.note}</div>
            </div>
            <span className="score">{v.score}</span>
          </motion.div>
        ))}
      </div>

      <div className="compound" style={{ marginTop: 13 }}>
        <div className="title" style={{ marginBottom: 0 }}>
          Compounding proof
          <button className="trig ghost" style={{ padding: "5px 10px", fontSize: 11 }} onClick={onRun} disabled={busy}>
            {busy ? <span className="spin" /> : "run cold vs warm"}
          </button>
        </div>
        {compound && (
          <div className="ab">
            <div className="b cold">
              <div className="lab">cold wiki</div>
              <div className="big">{compound.cold.score}</div>
              <div className="small">{compound.cold.evals} evals · no memory</div>
            </div>
            <div className="b warm">
              <div className="lab">warm wiki</div>
              <div className="big">{compound.warm.score}</div>
              <div className="small">{compound.warm.evals} evals · recalled</div>
            </div>
          </div>
        )}
        {compound && (
          <div className="small mono" style={{ marginTop: 9, color: "var(--ink-dim)" }}>
            same storm, same {compound.budget}-try budget — memory finds a {Math.round(compound.cold.score / compound.warm.score)}× better plan.
          </div>
        )}
      </div>
    </section>
  );
}

function ChatConsole({ chat, onSend, busy }: { chat: ChatRow[]; onSend: (t: string) => void; busy: boolean }) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo(0, 1e9); }, [chat]);
  return (
    <section className="section chat" style={{ marginTop: "auto" }}>
      <div className="title">Ops Console</div>
      <div className="stream" ref={ref}>
        {chat.map((c) => <div key={c.id} className={`bubble ${c.who}`}>{c.text}</div>)}
      </div>
      <form onSubmit={(e) => { e.preventDefault(); if (text.trim() && !busy) { onSend(text.trim()); setText(""); } }}>
        <input value={text} onChange={(e) => setText(e.target.value)}
               placeholder="delay AB104 30 min · close G3 · reopen G3 · add flight 09:15 G2 · new day · what's best?" />
        <button type="submit" disabled={busy}>{busy ? "…" : "send"}</button>
      </form>
    </section>
  );
}

function Trig({ n, label, onClick, alarm }: { n: string; label: string; onClick: () => void; alarm?: boolean }) {
  return (
    <button className={`trig ${alarm ? "alarm" : ""}`} onClick={onClick}>
      <span className="n">{n}</span>{label}
    </button>
  );
}
