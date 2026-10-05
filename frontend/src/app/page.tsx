"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate, fmtNum } from "@/lib/format";
import { Search, Upload, FolderPlus } from "lucide-react";

export default function Dashboard() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api("/dashboard")
      .then(setData)
      .catch((e) => setErr(String(e.message || e)));
  }, []);

  if (!data && !err) return <div className="muted">{t("loading")}</div>;

  const k = data?.kpis || {};
  const cats = Object.entries(data?.datasets_by_category || {});
  const types = Object.entries(data?.entities_by_type || {});

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div className="kicker">{t("welcome")}</div>
          <h1 style={{ margin: "4px 0 0", fontSize: 26 }}>{t("dashboard")}</h1>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Link href="/search" className="btn btn-primary"><Search size={14} /> {t("quickSearch")}</Link>
          <Link href="/datasets/import" className="btn"><Upload size={14} /> {t("newImport")}</Link>
          <Link href="/investigations" className="btn"><FolderPlus size={14} /> {t("newCase")}</Link>
        </div>
      </div>

      <div className="panel" style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)" }}>
        {[
          [t("datasets"), k.datasets],
          [t("records"), k.records],
          [t("entities"), k.entities],
          [t("relationships"), k.relationships],
          [t("investigations"), k.investigations],
        ].map(([l, n]) => (
          <div key={String(l)} className="kpi" style={{ borderInlineEnd: "1px solid var(--line)" }}>
            <div className="n">{fmtNum(n as number, locale)}</div>
            <div className="l">{l as string}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: 16 }}>
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("kpis")} · {t("category")}</span></div>
          <div className="panel-b">
            {cats.map(([c, n]) => (
              <div key={c} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <div style={{ width: 110 }} className="muted">{c}</div>
                <div style={{ flex: 1, height: 8, background: "var(--bg-0)", borderRadius: 99 }}>
                  <div style={{ width: `${Math.min(100, Number(n) * 22)}%`, height: "100%", background: "var(--amber)", borderRadius: 99 }} />
                </div>
                <div className="mono faint">{fmtNum(n as number, locale)}</div>
              </div>
            ))}
            <div className="faint" style={{ marginTop: 16 }}>{data?.scale_note}</div>
          </div>
        </div>
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("entities")}</span></div>
          <div className="panel-b" style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {types.map(([c, n]) => (
              <div key={c} className="badge badge-cyan">{t(c) === c ? c : t(c)} · {fmtNum(n as number, locale)}</div>
            ))}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("ingestJobs")}</span></div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t("filename")}</th>
                  <th>{t("status")}</th>
                  <th>{t("records")}</th>
                  <th>{t("created")}</th>
                </tr>
              </thead>
              <tbody>
                {(data?.jobs || []).map((j: any) => (
                  <tr key={j.id}>
                    <td className="mono">{j.filename}</td>
                    <td><span className="badge badge-green">{t(j.status) === j.status ? j.status : t(j.status)}</span></td>
                    <td>{fmtNum(j.records_processed, locale)}</td>
                    <td className="faint">{fmtDate(j.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("recentActivity")}</span></div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>{t("action")}</th>
                  <th>{t("resource")}</th>
                  <th>{t("created")}</th>
                </tr>
              </thead>
              <tbody>
                {(data?.audit || []).map((a: any, i: number) => (
                  <tr key={i}>
                    <td>{a.action}</td>
                    <td className="faint">{a.resource_type}</td>
                    <td className="faint">{fmtDate(a.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      {err && <div className="badge badge-red">{err}</div>}
    </div>
  );
}
