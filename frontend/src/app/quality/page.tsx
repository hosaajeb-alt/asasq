"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";

export default function QualityPage() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<any>(null);
  useEffect(() => {
    api("/quality/overview").then(setData).catch(() => {});
  }, []);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("quality")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("quality")}</h1>
      </div>
      <div className="panel" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="kpi">
          <div className="n">{fmtNum(data?.totals?.records, locale)}</div>
          <div className="l">{t("records")}</div>
        </div>
        <div className="kpi">
          <div className="n">{fmtNum(data?.totals?.duplicates, locale)}</div>
          <div className="l">{t("duplicates")}</div>
        </div>
        <div className="kpi">
          <div className="n">{fmtNum(data?.datasets?.length, locale)}</div>
          <div className="l">{t("datasets")}</div>
        </div>
      </div>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>{t("name")}</th>
              <th>{t("records")}</th>
              <th>{t("status")}</th>
              <th>{t("classification")}</th>
              <th>{t("duplicates")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.datasets || []).map((d: any) => (
              <tr key={d.id}>
                <td><Link className="linkish" href={`/datasets/${d.id}`}>{d.name}</Link></td>
                <td className="mono">{fmtNum(d.records, locale)}</td>
                <td><span className="badge badge-green">{d.status}</span></td>
                <td>{d.classification}</td>
                <td>{d.quality?.duplicates ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
