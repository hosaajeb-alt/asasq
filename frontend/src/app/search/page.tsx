"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";

function SearchInner() {
  const { t, locale } = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const [q, setQ] = useState(params.get("q") || "");
  const [mode, setMode] = useState(params.get("mode") || "balanced");
  const [entityType, setEntityType] = useState("");
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [cases, setCases] = useState<any[]>([]);
  const [caseId, setCaseId] = useState("");
  const [collections, setCollections] = useState<any[]>([]);
  const [collectionIds, setCollectionIds] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    const saved = localStorage.getItem("nexus.collectionScope");
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    api("/datasets?page_size=100").then((r) => setDatasets(r.items || [])).catch(() => {});
    api("/investigations?page_size=50").then((r) => setCases(r.items || [])).catch(() => {});
    api("/collections?page_size=100").then((r) => setCollections(r.items || [])).catch(() => {});
    const fromUrl = params.get("collections");
    if (fromUrl) setCollectionIds(fromUrl.split(",").filter(Boolean));
  }, []);

  async function run(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    try {
      const res = await api("/search", {
        method: "POST",
        body: JSON.stringify({
          q,
          mode,
          entity_type: entityType || null,
          dataset_id: datasetId || null,
          page: 1,
          page_size: 40,
          scope: { collections: collectionIds.length ? collectionIds : ["*"], datasets: datasetId ? [datasetId] : [] },
        }),
      });
      setData(res);
      router.replace(`/search?q=${encodeURIComponent(q)}&mode=${mode}`);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (params.get("q")) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function pin(item: any) {
    if (!caseId) return;
    await api(`/investigations/${caseId}/items`, {
      method: "POST",
      body: JSON.stringify({
        item_type: item.entity_id ? "entity" : "record",
        item_id: item.entity_id || item.record_id,
        label: item.entity_name || item.original,
        meta: { score: item.score, dataset: item.dataset_name },
      }),
    });
  }

  const ex = data?.expanded || {};

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("search.title")}</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 24 }}>{t("search.subtitle")}</h1>
      </div>
      <form className="panel" onSubmit={run}>
        <div className="panel-b" style={{ display: "grid", gap: 10 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("searchPlaceholder")} />
            <button className="btn btn-primary" disabled={busy}><Search size={14} /> {t("search")}</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8 }}>
            <div>
              <label className="label">{t("collections.scope")}</label>
              <select
                className="select"
                value={collectionIds[0] || ""}
                onChange={(e) => {
                  const v = e.target.value;
                  const next = v ? [v] : [];
                  setCollectionIds(next);
                  localStorage.setItem("nexus.collectionScope", JSON.stringify(next));
                }}
              >
                <option value="">{t("collections.allCollections")}</option>
                {collections.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("search.mode")}</label>
              <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
                {["exact", "high_precision", "balanced", "broad"].map((m) => (
                  <option key={m} value={m}>{t(m)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("entityType")}</label>
              <select className="select" value={entityType} onChange={(e) => setEntityType(e.target.value)}>
                <option value="">{t("all")}</option>
                {["person", "organization", "domain", "email", "document"].map((m) => (
                  <option key={m} value={m}>{t(m)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("dataset")}</label>
              <select className="select" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                <option value="">{t("all")}</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">{t("addToCase")}</label>
              <select className="select" value={caseId} onChange={(e) => setCaseId(e.target.value)}>
                <option value="">—</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </form>

      {data && (
        <div className="panel">
          <div className="panel-h">
            <span className="kicker">{t("search.expanded")}</span>
            <span className="badge">{t("search.hits")} {fmtNum(data.total, locale)}</span>
          </div>
          <div className="panel-b chip-row">
            <span className="badge">{t("original")}: {ex.original}</span>
            {ex.normalized && <span className="badge badge-cyan">{t("normalized")}: {ex.normalized}</span>}
            {ex.transliteration && <span className="badge badge-amber">{t("transliteration")}: {ex.transliteration}</span>}
            {ex.phonetic && <span className="badge badge-violet">{t("phonetic")}: {ex.phonetic}</span>}
            {ex.language && <span className="badge">{ex.language}/{ex.script}</span>}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>{t("search.result")}</th>
                <th>{t("source")}</th>
                <th>{t("matchType")}</th>
                <th>{t("confidence")}</th>
                <th>{t("why")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(data?.items || []).map((it: any) => (
                <tr key={it.record_id + it.field_name}>
                  <td>
                    <div>
                      {it.entity_id ? (
                        <Link className="linkish" href={`/entities/${it.entity_id}`}>{it.entity_name}</Link>
                      ) : (
                        <strong>{it.original}</strong>
                      )}
                    </div>
                    <div className="faint" style={{ fontSize: 11 }}>
                      {it.semantic_type} · {t("original")} {it.original}
                      {it.normalized && it.normalized !== it.original ? ` · ${t("normalized")} ${it.normalized}` : ""}
                    </div>
                  </td>
                  <td>
                    {it.collection_id && (
                      <div><Link className="linkish" href={`/collections/${it.collection_id}`}>{it.collection_name}</Link></div>
                    )}
                    <Link className="linkish" href={`/datasets/${it.dataset_id}`}>{it.dataset_name}</Link>
                    <div className="faint">{it.field_name}</div>
                  </td>
                  <td><span className="badge badge-amber">{it.match_type}</span></td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div className="conf-bar" style={{ width: 72 }}><i style={{ width: `${Math.round((it.score || 0) * 100)}%` }} /></div>
                      <span className="mono">{Math.round((it.score || 0) * 100)}</span>
                    </div>
                  </td>
                  <td className="faint">{(it.explain || []).join(" · ")}</td>
                  <td>
                    {it.entity_id && <Link className="btn" href={`/entities/${it.entity_id}`}>{t("view")}</Link>}
                    {caseId && (
                      <button className="btn btn-ghost" onClick={() => pin(it)}>{t("addToCase")}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!busy && data && data.total === 0 && (
          <div className="panel-b muted">{t("noResults")} — {t("search.emptyHint")}</div>
        )}
        {!data && <div className="panel-b muted">{t("search.emptyHint")}</div>}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="muted">…</div>}>
      <SearchInner />
    </Suspense>
  );
}
