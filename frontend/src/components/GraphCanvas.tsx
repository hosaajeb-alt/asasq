"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useI18n } from "@/lib/i18n";
import { originClass } from "@/lib/format";

type Node = { id: string; label: string; entity_type: string; confidence: number; status?: string };
type Edge = { id: string; from: string; to: string; rel_type: string; origin: string; confidence: number };

const TYPE_COLOR: Record<string, string> = {
  person: "#e4b04a",
  organization: "#5cb8d1",
  domain: "#9b8cff",
  email: "#4ecb8d",
  document: "#e0894a",
  location: "#93a0b0",
};

export default function GraphCanvas({
  nodes,
  edges,
  onSelect,
  height = 520,
}: {
  nodes: Node[];
  edges: Edge[];
  onSelect?: (id: string) => void;
  height?: number;
}) {
  const { t } = useI18n();
  const [sel, setSel] = useState<string | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: height });

  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setSize({ w: el.clientWidth, h: height }));
    ro.observe(el);
    setSize({ w: el.clientWidth, h: height });
    return () => ro.disconnect();
  }, [height]);

  const layout = useMemo(() => {
    const cx = size.w / 2;
    const cy = size.h / 2;
    const r = Math.min(size.w, size.h) * 0.36;
    const pos: Record<string, { x: number; y: number }> = {};
    nodes.forEach((n, i) => {
      const a = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
      const jitter = n.entity_type === "organization" ? 0.72 : 1;
      pos[n.id] = { x: cx + Math.cos(a) * r * jitter, y: cy + Math.sin(a) * r * jitter };
    });
    return pos;
  }, [nodes, size]);

  const selected = nodes.find((n) => n.id === sel);
  const incident = edges.filter((e) => e.from === sel || e.to === sel);

  return (
    <div>
      <div ref={wrap} className="graph-canvas" style={{ height }}>
        <svg width={size.w} height={size.h}>
          {edges.map((e) => {
            const a = layout[e.from];
            const b = layout[e.to];
            if (!a || !b) return null;
            const col =
              e.origin === "inferred" ? "#9b8cff" : e.origin === "derived" ? "#e4b04a" : "#5cb8d1";
            return (
              <g key={e.id}>
                <line
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  stroke={col}
                  strokeWidth={e.origin === "inferred" ? 1 : 1.6}
                  strokeDasharray={e.origin === "inferred" ? "4 3" : e.origin === "derived" ? "8 4" : undefined}
                  opacity={0.7}
                />
              </g>
            );
          })}
          {nodes.map((n) => {
            const p = layout[n.id];
            if (!p) return null;
            const c = TYPE_COLOR[n.entity_type] || "#e8eef4";
            const active = sel === n.id;
            return (
              <g
                key={n.id}
                style={{ cursor: "pointer" }}
                onClick={() => {
                  setSel(n.id);
                  onSelect?.(n.id);
                }}
              >
                <circle cx={p.x} cy={p.y} r={active ? 16 : 12} fill={c} opacity={0.2} />
                <circle cx={p.x} cy={p.y} r={active ? 8 : 6} fill={c} />
                <text
                  x={p.x}
                  y={p.y + 22}
                  textAnchor="middle"
                  fill="#e8eef4"
                  fontSize="11"
                  fontFamily="IBM Plex Sans, Vazirmatn, sans-serif"
                >
                  {n.label.length > 22 ? n.label.slice(0, 20) + "…" : n.label}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="chip-row" style={{ marginTop: 10 }}>
        <span className="badge badge-cyan">{t("observed")} ──</span>
        <span className="badge badge-amber">{t("derived")} - - -</span>
        <span className="badge badge-violet">{t("inferred")} · · ·</span>
        <span className="badge">{t("similarityNotIdentity")}</span>
      </div>
      {selected && (
        <div className="panel" style={{ marginTop: 12 }}>
          <div className="panel-h">
            <div>
              <div className="kicker">{selected.entity_type}</div>
              <strong>{selected.label}</strong>
            </div>
            <span className="badge badge-amber">{Math.round(selected.confidence * 100)}%</span>
          </div>
          <div className="panel-b">
            {incident.length === 0 && <div className="muted">{t("empty")}</div>}
            {incident.map((e) => {
              const otherId = e.from === selected.id ? e.to : e.from;
              const other = nodes.find((n) => n.id === otherId);
              return (
                <div key={e.id} style={{ display: "flex", gap: 8, padding: "6px 0", borderBottom: "1px solid var(--line)" }}>
                  <span className="badge">{e.rel_type}</span>
                  <span className={originClass(e.origin)}>{t(e.origin)}</span>
                  <span>{other?.label}</span>
                  <span className="faint mono" style={{ marginInlineStart: "auto" }}>{Math.round(e.confidence * 100)}%</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
