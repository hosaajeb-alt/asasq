"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate, fmtNum } from "@/lib/format";

export default function DatasetsPage() {
  const { t, locale } = useI18n();
  const [q, setQ] = useState("");
  const [data, setData] = useState<any>(null);

  async function load(query = q) {
    const r = await api(`/datasets?q=${encodeURIComponent(query)}&page_size=50`);
    setData(r);
  }
  useEffect(() => {
    load("").catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end" }}>
        <div>
          <div className="kicker">{t("datasets.holdings")}</div>
          <h1 style={{ margin: "4px 0 0" }}>{t("datasets.title")}</h1>
          <p className="muted">{t("datasets.subtitle")}</p>
        </div>
        <Link className="btn btn-primary" href="/datasets/import"><Upload size={14} /> {t("datasets.importWizard")}</Link>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); load(); }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} />
      </form>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>{t("name")}</th>
              <th>{t("category")}</th>
              <th>{t("source")}</th>
              <th>{t("languages")}</th>
              <th>{t("records")}</th>
              <th>{t("status")}</th>
              <th>{t("classification")}</th>
              <th>{t("importedAt")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((d: any) => (
              <tr key={d.id}>
                <td>
                  <Link className="linkish" href={`/datasets/${d.id}`}>{d.name}</Link>
                  <div className="faint" style={{ maxWidth: 360 }}>{d.description}</div>
                </td>
                <td><span className="badge">{d.category}</span></td>
                <td className="muted">{d.source}</td>
                <td className="mono faint">{(d.languages || []).join(", ")}</td>
                <td className="mono">{fmtNum(d.record_count, locale)}</td>
                <td><span className="badge badge-green">{d.processing_status}</span></td>
                <td><span className="badge badge-amber">{d.legal_classification}</span></td>
                <td className="faint">{fmtDate(d.imported_at, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.total === 0 && <div className="panel-b muted">{t("datasets.empty")}</div>}
      </div>
    </div>
  );
}
