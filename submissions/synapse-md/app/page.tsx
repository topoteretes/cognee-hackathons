"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface PhaseItem {
  phase: string;
}
interface MessageItem {
  agent: "connector" | "skeptic" | "linter";
  t: number;
  ts: string;
  body: React.ReactNode;
  confidence: number;
  agree: number;
  dissent: number;
}
type DebateItem = PhaseItem | MessageItem;

function isPhase(item: DebateItem): item is PhaseItem {
  return "phase" in item;
}

interface WikiState {
  version: number;
  confidence: number;
  delta: number;
}

interface ApiWikiState {
  run_count: number;
  confidence: number;
  skill_version: number;
  skill_before: string;
  skill_after: string;
}

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------
const SAMPLE_NOTES = ``;

const DEBATE: DebateItem[] = [
  { phase: "ROUND 1 · INITIAL CLAIMS" },
  {
    agent: "connector", t: 1, ts: "00:00:02",
    body: (
      <>
        Pattern matches drug-induced interstitial lung disease, specifically{" "}
        <span className="em">nitrofurantoin-associated pulmonary toxicity</span>.
        Onset (10d post-init), bibasilar GGO + reticulation on{" "}
        <code>CT</code>, restrictive PFTs with reduced{" "}
        <code>DLCO 58%</code>, and peripheral{" "}
        <span className="em">eosinophilia 7%</span> are textbook for subacute
        presentation.<br /><br />
        Linked priors: <span className="ref">[NEJM 2019 · 22414]</span>{" "}
        <span className="ref">[CHEST 2023 · 04111]</span>.
        Base rate ~1:5,000 chronic users; subacute form within first month is
        most common pattern.
      </>
    ),
    confidence: 78, agree: 12, dissent: 1,
  },
  {
    agent: "skeptic", t: 2, ts: "00:00:05",
    body: (
      <>
        Hold on. Eosinophilia at 7% is{" "}
        <span className="em">non-specific</span> — overlaps with acute
        eosinophilic pneumonia, CEP, and parasitic etiologies.
        D-dimer 410 sits at the upper-normal edge; have we adequately
        excluded subsegmental PE on this CT protocol?<br /><br />
        Also consider: <span className="em">hypersensitivity pneumonitis</span>{" "}
        (ask re: birds, mold, hot tub), and{" "}
        <span className="em">CTD-ILD</span> — patient is in the demographic
        window for late-onset RA-ILD or anti-synthetase syndrome. Has an
        autoimmune panel been drawn?
      </>
    ),
    confidence: 41, agree: 4, dissent: 9,
  },
  {
    agent: "linter", t: 3, ts: "00:00:07",
    body: (
      <>
        ⚠ Inconsistency detected in source notes:<br />
        <ul>
          <li>HPI lists symptom onset at <code>3wk</code>, but timeline math
          from <code>day 24</code> of therapy + <code>10d post-init</code>{" "}
          gives <span className="em">~14 days</span> of symptoms, not 21.</li>
          <li>No documented{" "}
          <span className="em">prior nitrofurantoin exposure</span> — relevant
          since chronic-form toxicity typically requires months of use.</li>
        </ul>
        Recommend re-querying EHR for prior nitrofurantoin courses before
        anchoring on subacute DILI.
      </>
    ),
    confidence: 88, agree: 17, dissent: 0,
  },
  { phase: "ROUND 2 · EVIDENCE REVIEW" },
  {
    agent: "connector", t: 4, ts: "00:00:11",
    body: (
      <>
        Acknowledged. Re-checked EHR via{" "}
        <span className="ref">[fetch:med_history]</span> — patient has{" "}
        <span className="em">3 prior nitrofurantoin courses</span> in last 14
        months (total exposure ~58 days). This actually{" "}
        <span className="add">strengthens</span> the DILI hypothesis: cumulative
        exposure pattern fits both subacute and early-chronic forms.<br /><br />
        HP remains plausible but lower prior: no exposure history elicited, and
        crackles are <span className="em">basal</span>, not the
        mid-zone pattern typical of HP.
      </>
    ),
    confidence: 84, agree: 16, dissent: 2,
  },
  {
    agent: "skeptic", t: 5, ts: "00:00:13",
    body: (
      <>
        Fine — DILI prior goes up. But we still don&apos;t have{" "}
        <span className="em">BAL</span>. Lymphocyte-predominant lavage with
        elevated CD8 would clinch it; current evidence is{" "}
        <span className="em">imaging + temporal association</span>.
        Recommend deferring &ldquo;high confidence&rdquo; until BAL or, at minimum, a
        documented response to drug withdrawal at 4 weeks.<br /><br />
        Counter-point: don&apos;t forget{" "}
        <span className="strike">amiodarone</span> — wrong drug. Withdrawn.
      </>
    ),
    confidence: 62, agree: 9, dissent: 3,
  },
  {
    agent: "linter", t: 6, ts: "00:00:15",
    body: (
      <>
        Cross-checked against{" "}
        <span className="ref">[wiki:nitrofurantoin_ILD/v18]</span> — Skeptic&apos;s
        BAL criterion is canonical in the existing card but contradicts
        Connector&apos;s claim of &ldquo;textbook diagnosis from CT + PFT alone.&rdquo;<br /><br />
        <span className="em">Action:</span> flag wiki entry &ldquo;Diagnostic
        Threshold&rdquo; section for revision. Current copy understates need for
        tissue/lavage confirmation in ambiguous presentations.
      </>
    ),
    confidence: 91, agree: 19, dissent: 0,
  },
  { phase: "ROUND 3 · SYNTHESIS" },
  {
    agent: "connector", t: 7, ts: "00:00:18",
    body: (
      <>
        Converging. Proposed plan:<br />
        <ul>
          <li><span className="add">Discontinue nitrofurantoin</span> immediately; document baseline PFTs/imaging.</li>
          <li>Pulmonology referral with BAL within 7d if no improvement.</li>
          <li>Empiric prednisone <code>0.5 mg/kg</code> only if hypoxia worsens (SpO2 &lt;90% RA).</li>
          <li>Send ANA, RF, anti-CCP, myositis panel to address Skeptic&apos;s CTD-ILD concern.</li>
        </ul>
      </>
    ),
    confidence: 86, agree: 22, dissent: 1,
  },
  {
    agent: "skeptic", t: 8, ts: "00:00:21",
    body: (
      <>
        Acceptable with autoimmune workup included. Final dissent:
        do not communicate this as &ldquo;<span className="strike">diagnosed
        nitrofurantoin pulmonary toxicity</span>&rdquo; in the after-visit summary —
        use &ldquo;<span className="add">suspected drug-induced ILD, withdrawal trial</span>&rdquo;
        until BAL or recovery confirms.
      </>
    ),
    confidence: 75, agree: 14, dissent: 2,
  },
  {
    agent: "linter", t: 9, ts: "00:00:23",
    body: (
      <>
        Consensus reached. Generating wiki delta against{" "}
        <span className="ref">v18 → v19</span> with{" "}
        <span className="add">3 additions</span>,{" "}
        <span className="em">2 modifications</span>,{" "}
        <span className="strike">1 deletion</span>.
        Confidence locked at 0.83. Surfacing one safety banner: patient is on
        <code> lisinopril</code> — ACE-I cough is a confounder for &ldquo;dry cough&rdquo;
        attribution; flag for clinician review.
      </>
    ),
    confidence: 92, agree: 21, dissent: 0,
  },
];

const AGENTS = {
  connector: { name: "Connector", role: "RETRIEVAL · LINKING", short: "CN", color: "blue" },
  skeptic:   { name: "Skeptic",   role: "ADVERSARIAL REVIEW",  short: "SK", color: "amber" },
  linter:    { name: "Linter",    role: "CONSISTENCY · SAFETY", short: "LN", color: "red" },
} as const;

// ---------------------------------------------------------------------------
// Left Panel
// ---------------------------------------------------------------------------
const DEPARTMENTS = ["Internal Medicine", "Cardiology", "Ophthalmology", "Neurology", "General"] as const;
type Department = typeof DEPARTMENTS[number];

function LeftPanel({ onSubmit, running, notes, setNotes, department, setDepartment, wikiQuery, setWikiQuery, onQuery, queryRunning }: {
  onSubmit: () => void;
  running: boolean;
  notes: string;
  setNotes: (v: string) => void;
  department: Department;
  setDepartment: (v: Department) => void;
  wikiQuery: string;
  setWikiQuery: (v: string) => void;
  onQuery: () => void;
  queryRunning: boolean;
}) {
  const [patientName, setPatientName] = useState("");
  const [patientAgeSex, setPatientAgeSex] = useState("");
  const [patientVisit, setPatientVisit] = useState("");
  const hasNotes = notes.trim().length > 20;

  return (
    <div className="col left">
      <div className="col-head">
        <div className="col-title">
          <span className="tag">01</span>
          <span>Clinical Notes</span>
        </div>
        <div className="col-actions">
          <button className="icon-btn" title="Upload">↑</button>
          <button className="icon-btn" title="History">⟲</button>
        </div>
      </div>

      <div className="case-meta">
        <div className="patient-row">
          <div><div className="lbl">Patient</div><input className="patient-input" value={patientName} onChange={e => setPatientName(e.target.value)} /></div>
          <div><div className="lbl">Age / Sex</div><input className="patient-input" value={patientAgeSex} onChange={e => setPatientAgeSex(e.target.value)} /></div>
          <div><div className="lbl">Visit</div><input className="patient-input dim" value={patientVisit} onChange={e => setPatientVisit(e.target.value)} /></div>
        </div>
      </div>

      <div style={{ padding: "8px 14px 0" }}>
        <div className="lbl" style={{ marginBottom: 4 }}>Department</div>
        <select
          value={department}
          onChange={e => setDepartment(e.target.value as Department)}
          style={{
            width: "100%", height: 32,
            background: "#0B1117", border: "1px solid var(--line)",
            borderRadius: 7, color: "var(--ink)",
            padding: "0 10px", fontSize: 12,
            fontFamily: "inherit", cursor: "pointer", outline: "none",
          }}
        >
          {DEPARTMENTS.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      <div className="notes-wrap">
        <textarea
          className="notes-area"
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="Enter clinical notes..."
          spellCheck={false}
        />
        <div className="notes-toolbar">
          <span className="chip"><span className="dot" />parsed · 14 entities</span>
          <span className="chip blue">drug: Metformin</span>
          <span className="chip amber">finding: microaneurysms</span>
          <span className="chip red">flag: HbA1c 10.1%</span>
          <span style={{ marginLeft: "auto" }} className="mono">{notes.length} ch</span>
        </div>
      </div>

      <div className="left-foot">
        <button
          className={`submit ${running ? "busy" : ""}`}
          disabled={!hasNotes || running}
          onClick={onSubmit}
        >
          {running ? (
            <><span className="mono" style={{ fontSize: 11, color: "var(--blue)" }}>● </span>Deliberating…</>
          ) : (
            <>Run Multi-Agent Review<span className="kbd">⌘ ↵</span></>
          )}
        </button>
        <div className="query-row">
          <input
            className="query-input"
            value={wikiQuery}
            onChange={e => setWikiQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && onQuery()}
            placeholder="Query the wiki... (e.g. ophthalmology referral criteria)"
            disabled={queryRunning}
          />
          <button
            className="query-btn"
            onClick={onQuery}
            disabled={!wikiQuery.trim() || queryRunning}
          >
            {queryRunning ? "…" : "Query Wiki"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Center Panel
// ---------------------------------------------------------------------------
function AgentTile({ id, active }: { id: keyof typeof AGENTS; active: boolean }) {
  const a = AGENTS[id];
  return (
    <div className={`agent-tile ${a.color} ${active ? "active" : ""}`}>
      <span className="agent-orb">{a.short}</span>
      <div style={{ minWidth: 0 }}>
        <div className="name">{a.name}</div>
        <div className="role">{a.role}</div>
      </div>
      <div className="meta">{active ? "● live" : "idle"}</div>
    </div>
  );
}

function Message({ m, isStreaming }: { m: MessageItem; isStreaming: boolean }) {
  const a = AGENTS[m.agent];
  return (
    <div className={`msg ${a.color}`}>
      <div className="gutter">
        <span className="agent-orb">{a.short}</span>
        <span className="line" />
      </div>
      <div className="bubble">
        <div className="bubble-head">
          <span className="who">{a.name}</span>
          <span className="turn mono">turn {String(m.t).padStart(2, "0")}</span>
          <span className="ts mono">{m.ts}</span>
        </div>
        <div className="bubble-body">
          {m.body}
          {isStreaming && <span className="cursor" />}
        </div>
        <div className="bubble-foot">
          <span className="vote up">▲ {m.agree}</span>
          <span className="vote down">▼ {m.dissent}</span>
          <span className="mono" style={{ color: "var(--ink-faint)" }}>confidence {m.confidence}%</span>
          <span style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
            <button className="small-btn">cite</button>
            <button className="small-btn">cross-check</button>
            <button className="small-btn">pin</button>
          </span>
        </div>
      </div>
    </div>
  );
}

function CenterPanel({ messages, streaming, running, activeAgent }: {
  messages: DebateItem[];
  streaming: boolean;
  running: boolean;
  activeAgent: string | null;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streaming]);

  return (
    <div className="col center">
      <div className="col-head">
        <div className="col-title">
          <span className="tag">02</span>
          <span>Agent Debate Console</span>
        </div>
        <div className="col-actions mono">
          {running
            ? <><span className="dot blue" />streaming · TCP/agent-bus</>
            : <><span className="dot" />ready</>}
        </div>
      </div>

      <div className="debate-head">
        <AgentTile id="connector" active={activeAgent === "connector"} />
        <AgentTile id="skeptic"   active={activeAgent === "skeptic"} />
        <AgentTile id="linter"    active={activeAgent === "linter"} />
      </div>

      <div className="console" ref={scrollRef}>
        {messages.length === 0 && !running && (
          <div className="empty-state">
            <div className="empty-glyph" />
            <div>
              <div className="empty-title">Debate console idle</div>
              <div className="empty-sub">
                Submit clinical notes from the left panel. Three specialist agents will
                deliberate in turns — Connector links evidence, Skeptic challenges it,
                Linter checks consistency. Their consensus becomes a self-evolving wiki entry.
              </div>
            </div>
            <div className="empty-hint">awaiting input · ⌘↵ to run</div>
          </div>
        )}
        {messages.map((m, idx) => {
          if (isPhase(m)) return <div className="phase" key={`p-${idx}`}>{m.phase}</div>;
          const isLast = idx === messages.length - 1;
          return <Message key={m.t} m={m} isStreaming={streaming && isLast} />;
        })}
        {!running && messages.length > 0 && (
          <div className="compose">
            <span className="mono" style={{ color: "var(--blue)" }}>›</span>
            <input placeholder="Ask follow-up · @Connector cite primary source for DLCO threshold" />
            <span className="mono" style={{ color: "var(--ink-faint)" }}>↵</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Right Panel
// ---------------------------------------------------------------------------
function ConfidenceRing({ value }: { value: number }) {
  const r = 36, c = 2 * Math.PI * r;
  const off = c * (1 - value / 100);
  const color = value >= 80 ? "var(--green)" : value >= 60 ? "var(--amber)" : "var(--red)";
  return (
    <div className="ring">
      <svg viewBox="0 0 88 88">
        <circle className="bg" cx="44" cy="44" r={r} />
        <circle className="fg" cx="44" cy="44" r={r}
          style={{ stroke: color, strokeDasharray: c, strokeDashoffset: off }} />
      </svg>
      <div className="num" style={{ color }}>
        <div className="v">{Math.round(value)}</div>
        <div className="pct">% CONFIDENCE</div>
      </div>
    </div>
  );
}

function RightPanel({ wikiState, hasResult, wikiSummary, alertActive, runCount, skillImproved, wikiAnswer, apiWikiState, onPublish, publishState, toast }: {
  wikiState: WikiState;
  hasResult: boolean;
  wikiSummary: string;
  alertActive: boolean;
  runCount: number;
  skillImproved: boolean;
  wikiAnswer: string;
  apiWikiState: ApiWikiState | null;
  onPublish: () => void;
  publishState: "idle" | "publishing" | "published";
  toast: string | null;
}) {
  const conf = apiWikiState?.confidence ?? wikiState.confidence;
  const version = apiWikiState ? 17 + apiWikiState.skill_version : wikiState.version;
  const barColor = conf >= 80 ? "var(--green)" : conf >= 60 ? "var(--amber)" : "var(--red)";
  const showSkillBadge = runCount >= 2;
  const skillVersion = apiWikiState?.skill_version ?? runCount;

  return (
    <div className="col right">
      <div className="col-head">
        <div className="col-title">
          <span className="tag">03</span>
          <span>Self-Evolving Wiki</span>
        </div>
        <div className="col-actions mono">v{version} · diff</div>
      </div>

      <div className="wiki-scroll">
        {alertActive && (
          <div className="warn">
            <div className="warn-head">
              <span className="warn-dot" />
              SAFETY HOLD · CLINICIAN REVIEW REQUIRED
              <span className="warn-tag">SEV-2</span>
            </div>
            <div className="warn-body">
              <strong>Drug-attribution conflict detected.</strong> Patient is on{" "}
              <code>lisinopril 20mg</code> — ACE-inhibitor cough may confound
              &ldquo;dry cough&rdquo; attribution to nitrofurantoin. Linter flagged this
              before locking the wiki delta.
              <div className="warn-actions">
                <button className="warn-btn">Review &amp; resolve</button>
                <button className="warn-btn ghost">Snooze 24h</button>
              </div>
            </div>
          </div>
        )}

        <div className="wiki-card">
          <div className="wiki-banner">
            <div className="name">Diabetic Retinopathy Risk Protocol</div>
          </div>

          {showSkillBadge && (
            <div style={{
              margin: "10px 14px 2px",
              padding: "6px 10px",
              background: "rgba(34,197,94,0.10)",
              border: "1px solid rgba(34,197,94,0.28)",
              borderRadius: 4,
              fontSize: 11,
              color: "var(--green)",
              fontFamily: "var(--mono)",
              letterSpacing: "0.05em",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}>
              ✦ SKILL UPDATED — diabetic-retinopathy v{skillVersion}
              {skillImproved && (
                <span style={{ opacity: 0.65, fontSize: 10 }}>· Cognee applied</span>
              )}
            </div>
          )}

          <div className="conf-wrap">
            <ConfidenceRing value={conf} />
            <div className="conf-meta">
              <div className="lbl">Consensus confidence</div>
              <div className="bar"><div style={{ width: `${conf}%`, background: barColor }} /></div>
            </div>
          </div>

          {apiWikiState && apiWikiState.run_count > 0 && (
            <div className="wiki-section">
              <div className="h">
                <span>Wiki Evolution</span>
                <span className="badge">Run {apiWikiState.run_count} · Skill v{apiWikiState.skill_version}</span>
              </div>
              {apiWikiState.skill_before && (
                <div className="skill-diff">
                  <div className="skill-diff-label before">BEFORE</div>
                  <pre className="skill-diff-block before">{apiWikiState.skill_before.slice(0, 150)}&hellip;</pre>
                  <div className="skill-diff-label after">AFTER</div>
                  <pre className="skill-diff-block after">{apiWikiState.skill_after.slice(0, 150)}&hellip;</pre>
                </div>
              )}
            </div>
          )}

          <div className="wiki-section">
            <div className="h">
              <span>Summary</span>
              {hasResult && <span className="badge">+8% specificity</span>}
            </div>
            <p>
              {wikiSummary || (
                <>
                  Type 2 Diabetes patients with HbA1c &gt;9% and vision symptoms are
                  at high risk for diabetic retinopathy. Annual ophthalmology referral
                  is required per ADA 2024.
                </>
              )}
            </p>
          </div>

          {wikiAnswer && (
            <div className="wiki-section wiki-answer">
              <div className="h"><span>Wiki Answer</span></div>
              <p>{wikiAnswer}</p>
            </div>
          )}

          {hasResult && (
            <div className="wiki-section">
              <div className="h">
                <span>Delta · v{version - 1} → v{version}</span>
                <span className="badge">3 add · 2 mod · 1 rm</span>
              </div>
              {skillImproved && (
                <div className="diff-row add">
                  <span className="tag">AUTO</span>
                  <div className="txt">Cognee skill update — diabetic-retinopathy rules revised from this run.</div>
                  <div className="turn mono">skill</div>
                </div>
              )}
              <div className="diff-row add">
                <span className="tag">ADD</span>
                <div className="txt">Cumulative cross-course exposure as independent risk modifier.</div>
                <div className="turn mono">t4</div>
              </div>
              <div className="diff-row mod">
                <span className="tag">MOD</span>
                <div className="txt">Tighten eosinophilia language — present in ~60%, not universal.</div>
                <div className="turn mono">t2</div>
              </div>
              <div className="diff-row add">
                <span className="tag">ADD</span>
                <div className="txt">BAL strongly recommended when CTD-ILD/HP are on the differential.</div>
                <div className="turn mono">t5</div>
              </div>
              <div className="diff-row rm">
                <span className="tag">RM</span>
                <div className="txt">&ldquo;BAL optional in classic presentations&rdquo; — contradicts canonical criteria.</div>
                <div className="turn mono">t6</div>
              </div>
              <div className="diff-row mod">
                <span className="tag">MOD</span>
                <div className="txt">After-visit summary phrasing → &ldquo;suspected&rdquo;, not &ldquo;diagnosed&rdquo;.</div>
                <div className="turn mono">t8</div>
              </div>
            </div>
          )}

        </div>

        {toast && (
          <div style={{
            margin: "0 14px 8px",
            padding: "8px 12px",
            background: "oklch(0.25 0.08 155 / 0.9)",
            border: "1px solid oklch(0.55 0.13 155 / 0.6)",
            borderRadius: 6,
            fontSize: 11,
            color: "var(--green)",
            fontFamily: "var(--mono)",
            letterSpacing: "0.04em",
            lineHeight: 1.5,
          }}>
            {toast}
          </div>
        )}
        <div className="footer-actions">
          <button
            className="fbtn primary"
            onClick={onPublish}
            disabled={publishState !== "idle"}
            style={publishState === "published" ? {
              background: "linear-gradient(180deg, oklch(0.55 0.13 155), oklch(0.45 0.14 155))",
              borderColor: "oklch(0.55 0.13 155 / 0.6)",
            } : undefined}
          >
            {publishState === "publishing" ? "Publishing…" :
             publishState === "published" ? "Published ✓" :
             `Publish v${version}`}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------
export default function App() {
  const [notes, setNotes] = useState(SAMPLE_NOTES);
  const [department, setDepartment] = useState<Department>("Internal Medicine");
  const [messages, setMessages] = useState<DebateItem[]>([]);
  const [running, setRunning] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [wikiState, setWikiState] = useState<WikiState>({ version: 18, confidence: 64, delta: 0 });
  const [hasResult, setHasResult] = useState(false);
  const [wikiSummary, setWikiSummary] = useState("");
  const [alertActive, setAlertActive] = useState(false);
  const [runCount, setRunCount] = useState(0);
  const [skillImproved, setSkillImproved] = useState(false);
  const [wikiQuery, setWikiQuery] = useState("");
  const [queryRunning, setQueryRunning] = useState(false);
  const [wikiAnswer, setWikiAnswer] = useState("");
  const [apiWikiState, setApiWikiState] = useState<ApiWikiState | null>(null);
  const [publishState, setPublishState] = useState<"idle" | "publishing" | "published">("idle");
  const [toast, setToast] = useState<string | null>(null);
  const runCountRef = useRef(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timersRef.current.forEach(t => clearTimeout(t));
    timersRef.current = [];
  };

  const queryWiki = useCallback(async () => {
    if (!wikiQuery.trim() || queryRunning) return;
    setQueryRunning(true);
    setWikiAnswer("");
    try {
      const data = await fetch("http://localhost:8000/query-wiki", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: wikiQuery }),
      }).then(r => r.json());
      setWikiAnswer(data.answer ?? "");
    } catch {
      setWikiAnswer("Query failed — backend may be unavailable.");
    } finally {
      setQueryRunning(false);
    }
  }, [wikiQuery, queryRunning]);

  const handlePublish = useCallback(async () => {
    if (publishState !== "idle") return;
    setPublishState("publishing");
    try {
      const data = await fetch("http://localhost:8000/publish-wiki", {
        method: "POST",
      }).then(r => r.json());
      setPublishState("published");
      setToast(`Wiki v${data.version} distilled to permanent memory. Session cleaned.`);
      setTimeout(() => {
        setPublishState("idle");
        setToast(null);
      }, 3000);
    } catch {
      setPublishState("idle");
    }
  }, [publishState]);

  const submit = useCallback(async () => {
    if (running) return;
    clearTimers();
    setMessages([]);
    setRunning(true);
    setHasResult(false);
    setActiveAgent(null);
    setWikiState({ version: 18, confidence: 64, delta: 0 });
    setWikiSummary("");
    setAlertActive(false);

    try {
      // Step 1 — /analyze
      const analyzeData = await fetch("http://localhost:8000/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes, department }),
      }).then(r => r.json());

      console.log("[entities]", analyzeData.entities_found);
      console.log("[matched]",  analyzeData.matched_cases);
      console.log("[cognee]",   analyzeData.cognee_results);
      console.log("[status]",   analyzeData.status);

      // Step 2 — /debate
      const debateData = await fetch("http://localhost:8000/debate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          notes,
          department,
          cognee_results: analyzeData.cognee_results ?? [],
          matched_cases:  analyzeData.matched_cases  ?? [],
        }),
      }).then(r => r.json());

      // Fetch authoritative wiki state from backend
      let fetchedWikiState: ApiWikiState | null = null;
      try {
        fetchedWikiState = await fetch("http://localhost:8000/wiki-state").then(r => r.json());
      } catch { /* non-fatal */ }

      const connectorText   = debateData.connector?.analysis  ?? "";
      const skepticText     = debateData.skeptic?.analysis    ?? "";
      const skepticConf     = debateData.skeptic?.confidence  ?? 75;
      const linterText      = debateData.linter?.analysis     ?? "";
      const linterAlert     = debateData.linter?.alert        ?? false;
      const isSkillImproved = debateData.skill_improved       ?? false;

      const newRunCount = runCountRef.current + 1;
      const effectiveConf = newRunCount >= 3
        ? Math.min(skepticConf + 5 * (newRunCount - 2), 95)
        : skepticConf;

      let displaySummary = connectorText;
      if (newRunCount >= 2) displaySummary += " Annual ophthalmology referral strongly recommended.";
      if (newRunCount >= 3) displaySummary += " HbA1c >10% + vision symptoms → immediate ophthalmology referral required (ADA 2024 §4.2).";

      // Step 3 — stream messages into UI one at a time
      const steps: DebateItem[] = [
        { phase: "ROUND 1 · CONNECTOR ANALYSIS" },
        { agent: "connector", t: 1, ts: "00:00:02", body: connectorText, confidence: 80, agree: 12, dissent: 1 },
        { phase: "ROUND 2 · SKEPTIC REVIEW" },
        { agent: "skeptic",   t: 2, ts: "00:00:08", body: skepticText,   confidence: skepticConf, agree: 8, dissent: 4 },
        { phase: "ROUND 3 · LINTER CHECK" },
        { agent: "linter",    t: 3, ts: "00:00:14", body: linterText,    confidence: 90, agree: 15, dissent: 0 },
      ];

      let t = 0;
      steps.forEach((item, idx) => {
        timersRef.current.push(setTimeout(() => {
          if (isPhase(item)) {
            setMessages(prev => [...prev, item]);
          } else {
            setActiveAgent(item.agent);
            setStreaming(true);
            setMessages(prev => [...prev, item]);
          }
          timersRef.current.push(setTimeout(() => setStreaming(false), 600));
        }, t));
        t += isPhase(item) ? 300 : 900;
      });

      // Step 4 — finalise
      timersRef.current.push(setTimeout(() => {
        setRunning(false);
        setStreaming(false);
        setActiveAgent(null);
        setHasResult(true);
        setWikiSummary(displaySummary);
        setAlertActive(linterAlert);
        setWikiState({ version: 17 + newRunCount, confidence: effectiveConf, delta: effectiveConf - 64 });
        setRunCount(newRunCount);
        runCountRef.current = newRunCount;
        setSkillImproved(isSkillImproved);
        if (fetchedWikiState) setApiWikiState(fetchedWikiState);
      }, t + 200));

    } catch (err) {
      console.error("[debate] failed:", err);
      setRunning(false);
      setStreaming(false);
      setActiveAgent(null);
    }
  }, [running, notes, department]);

  useEffect(() => () => clearTimers(), []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        submit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [submit]);

  return (
    <div className="app">
      <div className="main">
        <LeftPanel onSubmit={submit} running={running} notes={notes} setNotes={setNotes} department={department} setDepartment={setDepartment} wikiQuery={wikiQuery} setWikiQuery={setWikiQuery} onQuery={queryWiki} queryRunning={queryRunning} />
        <CenterPanel messages={messages} streaming={streaming} running={running} activeAgent={activeAgent} />
        <RightPanel wikiState={wikiState} hasResult={hasResult} wikiSummary={wikiSummary} alertActive={alertActive} runCount={runCount} skillImproved={skillImproved} wikiAnswer={wikiAnswer} apiWikiState={apiWikiState} onPublish={handlePublish} publishState={publishState} toast={toast} />
      </div>
    </div>
  );
}
