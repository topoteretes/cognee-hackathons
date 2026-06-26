import { Component, type ReactNode, useMemo } from "react";
import Gantt3D from "./Gantt3D";
import GanttFallback from "./GanttFallback";
import type { Plan } from "./types";

function webglOK(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch { return false; }
}

class Boundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

export default function GanttStage({ plan }: { plan: Plan }) {
  const ok = useMemo(webglOK, []);
  if (!ok) return <GanttFallback plan={plan} />;
  return (
    <Boundary fallback={<GanttFallback plan={plan} />}>
      <Gantt3D plan={plan} />
    </Boundary>
  );
}
