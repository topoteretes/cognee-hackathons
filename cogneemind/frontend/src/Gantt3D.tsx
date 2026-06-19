import { useMemo, useRef, useState, type ReactElement } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Grid, Html, OrbitControls, PerspectiveCamera, Text } from "@react-three/drei";
import * as THREE from "three";
import type { Bar, Plan } from "./types";

const WIDTH = 46;          // world units across the time axis
const ROW_GAP = 2.5;
const BAR_DEPTH = 1.55;
const BAR_H = 0.95;

const COL = {
  okDom: "#36e08a",
  okIntl: "#38d6ff",
  conflict: "#ff4d57",
  unassigned: "#4a525e",
};

function barColor(b: Bar): string {
  if (b.status === "unassigned") return COL.unassigned;
  if (b.status === "conflict") return COL.conflict;
  return b.type === "international" ? COL.okIntl : COL.okDom;
}

interface Layout {
  t0: number; t1: number;
  rowZ: Record<string, number>;   // gate id -> z
  remoteZ: number;
  xOf: (min: number) => number;
  wOf: (a: number, d: number) => number;
}

function useLayout(plan: Plan): Layout {
  return useMemo(() => {
    const mins = plan.bars.flatMap((b) => [b.arrival_min, b.departure_min]);
    const t0 = Math.min(...mins) - 15;
    const t1 = Math.max(...mins) + 15;
    const span = Math.max(1, t1 - t0);
    const scale = WIDTH / span;
    const gates = [...plan.gates].sort((a, b) => a.position - b.position);
    const n = gates.length;
    const rowZ: Record<string, number> = {};
    gates.forEach((g, i) => { rowZ[g.id] = (i - (n - 1) / 2) * ROW_GAP; });
    const remoteZ = ((n - (n - 1) / 2)) * ROW_GAP + 0.4;
    return {
      t0, t1, rowZ, remoteZ,
      xOf: (m) => (m - t0) * scale - WIDTH / 2,
      wOf: (a, d) => Math.max(1.1, (d - a) * scale),
    };
  }, [plan]);
}

function FlightBar({ bar, layout, hovered, setHovered }: {
  bar: Bar; layout: Layout; hovered: string | null; setHovered: (s: string | null) => void;
}) {
  const ref = useRef<THREE.Group>(null);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  const targetZ = bar.gate ? layout.rowZ[bar.gate] : layout.remoteZ;
  const targetX = layout.xOf((bar.arrival_min + bar.departure_min) / 2);
  const w = layout.wOf(bar.arrival_min, bar.departure_min);
  const color = useMemo(() => new THREE.Color(barColor(bar)), [bar.status, bar.type]);
  const isHot = hovered === bar.flight;

  useFrame(() => {
    const g = ref.current; if (!g) return;
    g.position.x += (targetX - g.position.x) * 0.16;
    g.position.z += (targetZ - g.position.z) * 0.16;
    const ty = isHot ? 1.5 : BAR_H / 2 + 0.05;
    g.position.y += (ty - g.position.y) * 0.18;
    if (matRef.current) matRef.current.color.lerp(color, 0.15);
  });

  const emissive = bar.status === "conflict" ? 0.9 : 0.42;

  return (
    <group
      ref={ref}
      position={[targetX, BAR_H, targetZ]}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(bar.flight); }}
      onPointerOut={() => setHovered(null)}
    >
      <mesh scale={[w, BAR_H, BAR_DEPTH]} castShadow>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial
          ref={matRef}
          color={color}
          emissive={color}
          emissiveIntensity={emissive}
          metalness={0.3}
          roughness={0.35}
          transparent
          opacity={bar.status === "unassigned" ? 0.55 : 0.92}
        />
      </mesh>
      <Text font="/JetBrainsMono.ttf" position={[0, 0, BAR_DEPTH / 2 + 0.02]} fontSize={0.52} color="#0c0d10"
            anchorX="center" anchorY="middle" maxWidth={w}>
        {bar.flight}
      </Text>
      {isHot && (
        <Html position={[0, 1.6, 0]} center distanceFactor={26} style={{ pointerEvents: "none" }}>
          <div style={{
            fontFamily: "JetBrains Mono, monospace", fontSize: 11, whiteSpace: "nowrap",
            background: "rgba(255,255,255,0.96)", border: "1px solid rgba(15,17,22,0.10)", borderRadius: 10,
            padding: "8px 11px", color: "#0c0d10", boxShadow: "0 12px 32px -10px rgba(15,17,22,0.22)",
            backdropFilter: "blur(10px)",
          }}>
            <b style={{ color: barColor(bar) }}>{bar.flight}</b> · {bar.airline}<br />
            {bar.arrival}–{bar.departure} · {bar.type}{bar.delayed ? " · DELAYED" : ""}<br />
            gate {bar.gate ?? "REMOTE STAND"} · pref {bar.preferred.join("/")}
          </div>
        </Html>
      )}
    </group>
  );
}

function ClosedOverlay({ plan, layout }: { plan: Plan; layout: Layout }) {
  const blocks: ReactElement[] = [];
  plan.gates.forEach((g) => {
    g.closed.forEach(([s, e], i) => {
      const toMin = (hhmm: string) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
      const a = toMin(s), d = toMin(e);
      const x = layout.xOf((a + d) / 2);
      const w = layout.wOf(a, d);
      blocks.push(
        <mesh key={g.id + i} position={[x, 0.05, layout.rowZ[g.id]]}>
          <boxGeometry args={[w, 0.08, BAR_DEPTH + 0.4]} />
          <meshBasicMaterial color="#c8253a" transparent opacity={0.18} />
        </mesh>
      );
    });
  });
  return <>{blocks}</>;
}

function GateRows({ plan, layout }: { plan: Plan; layout: Layout }) {
  const gates = [...plan.gates].sort((a, b) => a.position - b.position);
  return (
    <>
      {gates.map((g) => {
        const closed = g.closed.length > 0;
        return (
          <group key={g.id} position={[0, 0, layout.rowZ[g.id]]}>
            <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
              <planeGeometry args={[WIDTH + 4, BAR_DEPTH + 0.5]} />
              <meshBasicMaterial color={closed ? "#fce6e9" : "#ffffff"} transparent opacity={0.62} />
            </mesh>
            <Text font="/JetBrainsMono.ttf" position={[-WIDTH / 2 - 2.4, 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}
                  fontSize={0.95} color={closed ? "#c8253a" : "#0c0d10"} anchorX="right" anchorY="middle">
              {g.id}
            </Text>
            <Text font="/JetBrainsMono.ttf" position={[-WIDTH / 2 - 2.4, 0.05, 1.0]} rotation={[-Math.PI / 2, 0, 0]}
                  fontSize={0.42} color="#8e919a" anchorX="right" anchorY="middle">
              {closed ? "CLOSED" : g.label}
            </Text>
          </group>
        );
      })}
      {/* remote stand row */}
      <group position={[0, 0, layout.remoteZ]}>
        <Text font="/JetBrainsMono.ttf" position={[-WIDTH / 2 - 2.4, 0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}
              fontSize={0.7} color="#8e919a" anchorX="right" anchorY="middle">
          REMOTE
        </Text>
      </group>
    </>
  );
}

function TimeAxis({ layout }: { layout: Layout }) {
  const ticks: ReactElement[] = [];
  const start = Math.ceil(layout.t0 / 60) * 60;
  for (let m = start; m <= layout.t1; m += 60) {
    const x = layout.xOf(m);
    ticks.push(
      <group key={m} position={[x, 0, 0]}>
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <planeGeometry args={[0.05, 30]} />
          <meshBasicMaterial color="#cfd2d8" />
        </mesh>
        <Text font="/JetBrainsMono.ttf" position={[0, 0.05, -16]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.7}
              color="#8e919a" anchorX="center">
          {`${String(Math.floor(m / 60)).padStart(2, "0")}:00`}
        </Text>
      </group>
    );
  }
  return <>{ticks}</>;
}

export default function Gantt3D({ plan }: { plan: Plan }) {
  const layout = useLayout(plan);
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <Canvas shadows dpr={[1, 2]} gl={{ antialias: true }}>
      <color attach="background" args={["#f4f4f6"]} />
      <fog attach="fog" args={["#f4f4f6", 38, 80]} />
      <PerspectiveCamera makeDefault position={[2, 27, 31]} fov={42} />
      <OrbitControls enableDamping dampingFactor={0.08} minPolarAngle={0.2}
        maxPolarAngle={Math.PI / 2.25} minDistance={18} maxDistance={64} target={[0, 0, 0]} />

      <ambientLight intensity={0.85} />
      <directionalLight position={[14, 24, 10]} intensity={1.0} color="#ffffff" castShadow />
      <directionalLight position={[-12, 18, -10]} intensity={0.4} color="#dfe6f0" />
      <pointLight position={[22, 12, 18]} intensity={50} color="#ffd591" distance={60} />

      <Grid args={[120, 120]} cellSize={2} cellThickness={0.5} cellColor="#dadde2"
        sectionSize={10} sectionThickness={1} sectionColor="#bcc1c9"
        fadeDistance={92} fadeStrength={1.4} infiniteGrid position={[0, 0, 0]} />

      <TimeAxis layout={layout} />
      <GateRows plan={plan} layout={layout} />
      <ClosedOverlay plan={plan} layout={layout} />
      {plan.bars.map((b) => (
        <FlightBar key={b.flight} bar={b} layout={layout} hovered={hovered} setHovered={setHovered} />
      ))}
    </Canvas>
  );
}
