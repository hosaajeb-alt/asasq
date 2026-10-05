"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";

export default function CasesPage() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<any>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");

  async function load() {
    setData(await api("/investigations?page_size=50"));
  }
  useEffect(() => {
    load().catch(() => {});
  }, []);

  async function create() {
    if (!title.trim()) return;
    const c = await api("/investigations", { method: "POST", body: JSON.stringify({ title, summary }) });
    setTitle("");
    setSummary("");
    window.location.href = `/investigations/${c.id}`;
  }

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("investigations.title")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("investigations.subtitle")}</h1>
      </div>
      <div className="panel panel-b" style={{ display: "grid", gridTemplateColumns: "1fr 2fr auto", gap: 8, alignItems: "end" }}>
        <div>
          <label className="label">{t("title")}</label>
          <input className="input" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="label">{t("summary")}</label>
          <input className="input" value={summary} onChange={(e) => setSummary(e.target.value)} />
        </div>
        <button className="btn btn-primary" onClick={create}>{t("investigations.newCase")}</button>
      </div>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>{t("title")}</th>
              <th>{t("status")}</th>
              <th>{t("classification")}</th>
              <th>{t("item")}</th>
              <th>{t("updated")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((c: any) => (
              <tr key={c.id}>
                <td>
                  <Link className="linkish" href={`/investigations/${c.id}`}>{c.title}</Link>
                  <div className="faint">{c.summary}</div>
                </td>
                <td><span className="badge badge-green">{t(c.status)}</span></td>
                <td>{c.classification}</td>
                <td>{c.item_count}</td>
                <td className="faint">{fmtDate(c.updated_at, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
