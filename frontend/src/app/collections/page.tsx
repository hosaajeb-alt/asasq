"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Layers } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";

export default function CollectionsPage() {
  const { t, locale } = useI18n();
  const [data, setData] = useState<any>(null);
  const [q, setQ] = useState("");

  async function load(query = q) {
    setData(await api(`/collections?q=${encodeURIComponent(query)}&page_size=50`));
  }
  useEffect(() => {
    load("").catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end" }}>
        <div>
          <div className="kicker">{t("collections.title")}</div>
          <h1 style={{ margin: "4px 0 0" }}>{t("collections.subtitle")}</h1>
        </div>
        <Link className="btn btn-primary" href="/collections/new">
          <Layers size={14} /> {t("collections.create")}
        </Link>
      </div>
      <form onSubmit={(e) => { e.preventDefault(); load(); }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("search")} />
      </form>
      <div className="panel">
        <table className="data">
          <thead>
            <tr>
              <th>{t("name")}</th>
              <th>{t("status")}</th>
              <th>{t("category")}</th>
              <th>{t("datasets")}</th>
              <th>{t("records")}</th>
              <th>{t("collections.embeddings")}</th>
              <th>{t("classification")}</th>
            </tr>
          </thead>
          <tbody>
            {(data?.items || []).map((c: any) => (
              <tr key={c.id}>
                <td>
                  <Link className="linkish" href={`/collections/${c.id}`}>{c.name}</Link>
                  <div className="faint">{c.description}</div>
                </td>
                <td><span className="badge badge-green">{c.status}</span></td>
                <td><span className="badge">{c.category}</span></td>
                <td className="mono">{fmtNum(c.dataset_count, locale)}</td>
                <td className="mono">{fmtNum(c.record_count, locale)}</td>
                <td className="mono">{fmtNum(c.embedding_count, locale)}</td>
                <td className="faint">{c.legal_classification}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.total === 0 && <div className="panel-b muted">{t("collections.empty")}</div>}
      </div>
    </div>
  );
}
