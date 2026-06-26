export type Status = "ok" | "conflict" | "unassigned";

export interface Bar {
  flight: string;
  airline: string;
  gate: string | null;
  arrival: string;
  departure: string;
  arrival_min: number;
  departure_min: number;
  type: "domestic" | "international";
  preferred: string[];
  status: Status;
  delayed: boolean;
}

export interface GateInfo {
  id: string;
  position: number;
  type: string;
  label: string;
  closed: [string, string][];
}

export interface Score { total: number; U: number; C: number; W: number; R: number; }

export interface Plan {
  assignment: Record<string, string>;
  unassigned: string[];
  bars: Bar[];
  strategy: { name: string; priority_key: string; soft_weights: Record<string, number>; applies_to: string };
  gates: GateInfo[];
  score: Score;
}

export interface Discovery {
  strategy: Plan["strategy"];
  evals: number;
  source: "cold" | "warm";
  trace: { key: string; name: string; score: number }[];
  score: number;
}

export interface WikiVersion {
  version: number; signature: string; strategy: string;
  priority_key: string; score: number; note: string; ts: number;
}

export interface Wiki { timeline: WikiVersion[]; index: Record<string, any>; }

export interface AgentEvent { type: "agent"; agent: string; message: string; data: any; ts: number; }
