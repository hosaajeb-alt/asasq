"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";
import { originClass } from "@/lib/format";
import GraphCanvas from "@/components/GraphCanvas";

export default function EntityProfile() {
  const { id } = useParams<{ id: string }>();
  const { t, locale } = useI18n();
  const [e, setE] = useState<any>(null);
  const [tab, setTab] = useState("overview");
  const [graph, setGraph] = useState<any>(null);

  useEffect(() => {
    api(`/entities/${id}`).then(setE).catch(() => {});
    api(`/graph/${id}?depth=2`).then(setGraph).catch(() => {});
  }, [id]);

  if (!e) return <div className="muted">{t("loading")}</div>;

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div className="kicker">{e.entity_type} · {t("entities.profile")}</div>
          <h1 style={{ margin: "4px 0 0" }}>{e.canonical_name}</h1>
          {e.summary && <p className="muted">{e.summary}</p>}
          <div className="chip-row" style={{ marginTop: 8 }}>
            {(e.aliases || []).slice(0, 8).map((a: any, i: number) => (
              <span key={i} className="badge">{a.alias} <span className="faint">{a.source}</span></span>
            ))}
          </div>
          {(e.collections || []).length > 0 && (
            <div className="chip-row" style={{ marginTop: 8 }}>
              {(e.collections || []).map((c: any) => (
                <Link key={c.id} className="badge badge-cyan" href={`/collections/${c.id}`}>
                  {t("collections.observedIn")}: {c.name}
                </Link>
              ))}
            </div>
          )}
        </div>
        <div style={{ textAlign: "end" }}>
          <div className="mono" style={{ fontSize: 28 }}>{Math.round(e.confidence * 100)}</div>
          <div className="faint">{t("confidence")}</div>
          <Link className="btn" href={`/graph?root=${e.id}`} style={{ marginTop: 8 }}>{t("graph")}</Link>
        </div>
      </div>
      <div className="tabs">
        {["overview", "attributes", "relationships", "evidence", "timeline", "sources"].map((k) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>{t(k)}</button>
        ))}
      </div>

      {tab === "overview" && graph && (
        <GraphCanvas nodes={graph.nodes || []} edges={graph.edges || []} />
      )}

      {tab === "attributes" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("name")}</th>
                <th>{t("original")}</th>
                <th>{t("semantic")}</th>
                <th>{t("origin")}</th>
                <th>{t("source")}</th>
              </tr>
            </thead>
            <tbody>
              {(e.attributes || []).map((a: any, i: number) => (
                <tr key={i}>
                  <td className="mono faint">{a.name}</td>
                  <td>{a.value}</td>
                  <td>{a.semantic_type}</td>
                  <td><span className={originClass(a.origin)}>{t(a.origin)}</span></td>
                  <td className="faint">{a.dataset_id ? a.dataset_id.slice(0, 8) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "relationships" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("type")}</th>
                <th></th>
                <th>{t("origin")}</th>
                <th>{t("confidence")}</th>
                <th>{t("source")}</th>
              </tr>
            </thead>
            <tbody>
              {(e.relationships || []).map((r: any) => (
                <tr key={r.id}>
                  <td className="mono">{r.rel_type}</td>
                  <td>
                    {r.other ? (
                      <Link className="linkish" href={`/entities/${r.other.id}`}>{r.other.canonical_name}</Link>
                    ) : "—"}
                  </td>
                  <td><span className={originClass(r.origin)}>{t(r.origin)}</span></td>
                  <td>{Math.round(r.confidence * 100)}%</td>
                  <td className="faint">{r.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(tab === "evidence" || tab === "sources" || tab === "timeline") && (
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("spine")}</span></div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("field")}</th>
                <th>{t("original")}</th>
                <th>{t("origin")}</th>
                <th>{t("dataset")}</th>
                <th>{t("whenAdded")}</th>
              </tr>
            </thead>
            <tbody>
              {(e.provenance || []).map((p: any, i: number) => (
                <tr key={i}>
                  <td className="mono faint">{p.attribute}</td>
                  <td>{p.value}</td>
                  <td><span className={originClass(p.origin)}>{t(p.origin)}</span></td>
                  <td>
                    {p.dataset_id ? (
                      <Link className="linkish" href={`/datasets/${p.dataset_id}`}>{p.dataset_name}</Link>
                    ) : "—"}
                  </td>
                  <td className="faint">{fmtDate(p.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="panel-b">
            <div className="kicker">{t("entities.recordSupport")}</div>
            {(e.sources || []).map((s: any) => (
              <div key={s.record_id} style={{ padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
                <Link className="linkish" href={`/datasets/${s.dataset_id}`}>{s.dataset_name}</Link>
                <span className="faint"> · row {s.row_number} · {Math.round(s.confidence * 100)}%</span>
                <pre className="mono faint" style={{ margin: "6px 0 0", whiteSpace: "pre-wrap" }}>{JSON.stringify(s.raw)}</pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
