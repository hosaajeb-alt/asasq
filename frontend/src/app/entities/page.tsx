"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";

export default function EntitiesPage() {
  const { t, locale } = useI18n();
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [data, setData] = useState<any>(null);
  const [props, setProps] = useState<any>(null);
  const [collections, setCollections] = useState<any[]>([]);
  const [collectionId, setCollectionId] = useState("");

  async function load() {
    const col = collectionId ? `&collection_id=${encodeURIComponent(collectionId)}` : "";
    const r = await api(`/entities?q=${encodeURIComponent(q)}&entity_type=${encodeURIComponent(type)}&page_size=50${col}`);
    setData(r);
  }
  useEffect(() => {
    load().catch(() => {});
    api("/collections?page_size=100").then((r) => setCollections(r.items || [])).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runEr() {
    const r = await api("/entities/resolve?min_confidence=0.55", { method: "POST" });
    setProps(r);
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end" }}>
        <div>
          <div className="kicker">{t("entities.title")}</div>
          <h1 style={{ margin: "4px 0 0" }}>{t("entities.subtitle")}</h1>
        </div>
        <button className="btn" onClick={runEr}>{t("entities.runEr")}</button>
      </div>
      <form style={{ display: "flex", gap: 8 }} onSubmit={(e) => { e.preventDefault(); load(); }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} />
        <select className="select" style={{ maxWidth: 180 }} value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">{t("all")}</option>
          {["person", "organization", "domain", "email", "document"].map((x) => <option key={x} value={x}>{t(x)}</option>)}
        </select>
        <select className="select" style={{ maxWidth: 220 }} value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
          <option value="">{t("collections.allCollections")}</option>
          {collections.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button className="btn btn-primary">{t("filter")}</button>
      </form>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>{t("name")}</th>
              <th>{t("type")}</th>
              <th>{t("confidence")}</th>
              <th>{t("records")}</th>
              <th>{t("status")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((e: any) => (
              <tr key={e.id}>
                <td><Link className="linkish" href={`/entities/${e.id}`}>{e.canonical_name}</Link></td>
                <td><span className="badge badge-cyan">{e.entity_type}</span></td>
                <td>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <div className="conf-bar"><i style={{ width: `${Math.round(e.confidence * 100)}%` }} /></div>
                    <span className="mono">{Math.round(e.confidence * 100)}</span>
                  </div>
                </td>
                <td>{fmtNum(e.record_count, locale)}</td>
                <td className="faint">{e.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {props && (
        <div className="panel">
          <div className="panel-h">
            <span className="kicker">{t("entities.proposals")}</span>
            <span className="badge">{props.total}</span>
          </div>
          <p className="panel-b muted" style={{ paddingBottom: 0 }}>{t("entities.mergeWarn")}</p>
          <table className="data">
            <thead>
              <tr>
                <th>A</th>
                <th>B</th>
                <th>{t("confidence")}</th>
                <th>{t("explain")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(props.items || []).slice(0, 20).map((p: any, i: number) => (
                <tr key={i}>
                  <td className="mono faint">{p.record_a.slice(0, 8)}</td>
                  <td className="mono faint">{p.record_b.slice(0, 8)}</td>
                  <td>{Math.round(p.confidence * 100)}%</td>
                  <td className="faint">{(p.reasons || []).join(" · ")}</td>
                  <td>{p.auto_link_eligible ? <span className="badge badge-green">{t("autoLink")}</span> : <span className="badge">{t("notAutoLink")}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
