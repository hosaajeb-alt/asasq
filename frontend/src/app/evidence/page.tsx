"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate, originClass } from "@/lib/format";

export default function EvidencePage() {
  const { t, locale } = useI18n();
  const [items, setItems] = useState<any[]>([]);
  const [sel, setSel] = useState<any>(null);

  useEffect(() => {
    api("/evidence").then((r) => setItems(r.items || [])).catch(() => {});
  }, []);

  async function open(id: string) {
    setSel(await api(`/evidence/${id}`));
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: 14 }}>
      <div>
        <div className="kicker">{t("evidence")}</div>
        <h1 style={{ margin: "4px 0 12px" }}>{t("spine")}</h1>
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("title")}</th>
                <th>{t("origin")}</th>
                <th>{t("dataset")}</th>
                <th>{t("created")}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.id} onClick={() => open(e.id)} style={{ cursor: "pointer" }}>
                  <td>{e.title}</td>
                  <td><span className={originClass(e.origin)}>{t(e.origin)}</span></td>
                  <td className="faint">{e.dataset_name}</td>
                  <td className="faint">{fmtDate(e.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="panel">
        <div className="panel-h"><span className="kicker">{t("whereFrom")}</span></div>
        <div className="panel-b">
          {!sel && <div className="muted">{t("empty")}</div>}
          {sel && (
            <div style={{ display: "grid", gap: 10 }}>
              <Row l="Evidence" v={sel.evidence} />
              <Row l={t("entity")} v={sel.entity ? <Link className="linkish" href={`/entities/${sel.entity.id}`}>{sel.entity.name}</Link> : "—"} />
              <Row l={t("dataset")} v={sel.dataset ? <Link className="linkish" href={`/datasets/${sel.dataset.id}`}>{sel.dataset.name}</Link> : "—"} />
              <Row l={t("source")} v={sel.dataset?.source} />
              <Row l={t("whenAdded")} v={fmtDate(sel.created_at, locale)} />
              <Row l={t("origin")} v={<span className={originClass(sel.origin)}>{t(sel.origin)}</span>} />
              <div>
                <div className="label">{t("rawPayload")}</div>
                <pre className="mono faint" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(sel.record?.raw || sel.import, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ l, v }: { l: string; v: any }) {
  return (
    <div>
      <div className="label">{l}</div>
      <div>{v || "—"}</div>
    </div>
  );
}
