import type { Bar, Plan } from "./types";

/** 2D Gantt — renders when WebGL is unavailable. Same palette as the 3D deck. */
const COL: Record<string, string> = {
  ok_domestic: "#36e08a", ok_international: "#38d6ff", conflict: "#ff4d57", unassigned: "#4a525e",
};
function color(b: Bar) {
  if (b.status === "unassigned") return COL.unassigned;
  if (b.status === "conflict") return COL.conflict;
  return b.type === "international" ? COL.ok_international : COL.ok_domestic;
}

export default function GanttFallback({ plan }: { plan: Plan }) {
  const mins = plan.bars.flatMap((b) => [b.arrival_min, b.departure_min]);
  const t0 = Math.min(...mins) - 15, t1 = Math.max(...mins) + 15;
  const span = Math.max(1, t1 - t0);
  const pct = (m: number) => ((m - t0) / span) * 100;
  const gates = [...plan.gates].sort((a, b) => a.position - b.position);
  const rows = [...gates.map((g) => g.id), "REMOTE"];
  const hours: number[] = [];
  for (let m = Math.ceil(t0 / 60) * 60; m <= t1; m += 60) hours.push(m);

  return (
    <div style={{ position: "absolute", inset: 0, padding: "48px 28px 76px", display: "flex", flexDirection: "column", gap: 7 }}>
      <div style={{ position: "relative", height: 20, marginLeft: 92,
                    fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--ink-faint)",
                    letterSpacing: "0.04em" }}>
        {hours.map((m) => (
          <span key={m} style={{ position: "absolute", left: `${pct(m)}%`, transform: "translateX(-50%)" }}>
            {`${String(Math.floor(m / 60)).padStart(2, "0")}:00`}
          </span>
        ))}
      </div>
      {rows.map((row) => {
        const closed = gates.find((g) => g.id === row)?.closed ?? [];
        const bars = plan.bars.filter((b) => (b.gate ?? "REMOTE") === row);
        return (
          <div key={row} style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minHeight: 0 }}>
            <div style={{ width: 80, textAlign: "right",
                          fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 14,
                          color: closed.length ? "var(--red)"
                                : row === "REMOTE" ? "var(--ink-faint)"
                                : "var(--ink)" }}>
              {row}
            </div>
            <div style={{ position: "relative", flex: 1, height: "100%",
                          background: "var(--surface)",
                          border: "1px solid var(--hairline)",
                          borderRadius: "var(--radius-m)",
                          boxShadow: "var(--shadow-1)",
                          overflow: "hidden" }}>
              {closed.map(([s, e], i) => {
                const toM = (x: string) => { const [h, m] = x.split(":").map(Number); return h * 60 + m; };
                return <div key={i} style={{ position: "absolute",
                  left: `${pct(toM(s))}%`,
                  width: `${pct(toM(e)) - pct(toM(s))}%`,
                  top: 0, bottom: 0,
                  background: "var(--red-bg)",
                  borderLeft: "1px dashed var(--red)",
                  borderRight: "1px dashed var(--red)" }} />;
              })}
              {bars.map((b) => (
                <div key={b.flight} title={`${b.flight} ${b.arrival}-${b.departure}`}
                  style={{ position: "absolute",
                    left: `${pct(b.arrival_min)}%`,
                    width: `${Math.max(3, pct(b.departure_min) - pct(b.arrival_min))}%`,
                    top: 7, bottom: 7,
                    background: color(b),
                    borderRadius: 8,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 12,
                    color: "#0c0d10",
                    boxShadow: b.status === "conflict"
                      ? "0 0 0 1px var(--red), 0 6px 16px -6px var(--red)"
                      : "0 2px 8px -4px rgba(15,17,22,0.18)",
                    opacity: b.status === "unassigned" ? 0.55 : 1,
                    overflow: "hidden", whiteSpace: "nowrap" }}>
                  {b.flight}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
