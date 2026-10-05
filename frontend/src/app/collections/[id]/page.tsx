"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate, fmtNum } from "@/lib/format";

const TABS = [
  "overview",
  "datasets",
  "search",
  "entities",
  "images",
  "faceSearch",
  "indexes",
  "versions",
  "permissions",
  "settings",
];

export default function CollectionDetail() {
  const { id } = useParams<{ id: string }>();
  const { t, locale } = useI18n();
  const router = useRouter();
  const [c, setC] = useState<any>(null);
  const [tab, setTab] = useState("overview");
  const [datasets, setDatasets] = useState<any[]>([]);
  const [entities, setEntities] = useState<any[]>([]);
  const [indexes, setIndexes] = useState<any[]>([]);
  const [versions, setVersions] = useState<any[]>([]);
  const [images, setImages] = useState<any[]>([]);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any>(null);
  const [faceHits, setFaceHits] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const col = await api(`/collections/${id}`);
    setC(col);
    api(`/collections/${id}/datasets`).then((r) => setDatasets(r.items || [])).catch(() => {});
    api(`/collections/${id}/entities?page_size=40`).then((r) => setEntities(r.items || [])).catch(() => {});
    api(`/collections/${id}/indexes`).then((r) => setIndexes(r.items || [])).catch(() => {});
    api(`/collections/${id}/versions`).then((r) => setVersions(r.items || [])).catch(() => {});
    api(`/collections/${id}/images`).then((r) => setImages(r.items || [])).catch(() => {});
  }
  useEffect(() => {
    load().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function runSearch(e?: React.FormEvent) {
    e?.preventDefault();
    setBusy(true);
    try {
      setHits(await api(`/collections/${id}/search`, { method: "POST", body: JSON.stringify({ q, mode: "balanced" }) }));
    } finally {
      setBusy(false);
    }
  }

  async function faceSearch(file: File) {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      setFaceHits(await api(`/collections/${id}/face-search`, { method: "POST", body: fd }));
    } finally {
      setBusy(false);
    }
  }

  if (!c) return <div className="muted">{t("loading")}</div>;
  const st = c.stats || {};

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div className="kicker">{c.source_type} · {c.slug}</div>
          <h1 style={{ margin: "4px 0 0" }}>{c.name}</h1>
          <p className="muted">{c.description}</p>
          <div className="chip-row">
            <span className="badge badge-green">{c.status}</span>
            <span className="badge badge-amber">{c.legal_classification}</span>
            {(c.tags || []).map((tg: string) => <span key={tg} className="badge">{tg}</span>)}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "start" }}>
          <Link className="btn" href={`/datasets/import?collection=${c.id}`}>{t("import")}</Link>
          <Link className="btn" href={`/search?collections=${c.id}`}>{t("search")}</Link>
        </div>
      </div>

      <div className="panel" style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)" }}>
        {[
          [t("datasets"), st.datasets ?? c.dataset_count],
          [t("records"), st.records ?? c.record_count],
          [t("entities"), st.entities ?? c.entity_count],
          [t("collections.imagesCount"), st.images ?? c.image_count],
          [t("collections.embeddings"), st.embeddings ?? c.embedding_count],
          [t("collections.indexStatus"), st.index_status],
        ].map(([l, n]) => (
          <div key={String(l)} className="kpi" style={{ borderInlineEnd: "1px solid var(--line)" }}>
            <div className="n" style={{ fontSize: 20 }}>{typeof n === "number" ? fmtNum(n, locale) : n || "—"}</div>
            <div className="l">{l as string}</div>
          </div>
        ))}
      </div>

      <div className="tabs">
        {TABS.map((k) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
            {t(`collections.${k}`)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="panel panel-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Row l={t("source")} v={c.source} />
          <Row l={t("collections.sourceType")} v={c.source_type} />
          <Row l={t("languages")} v={(c.languages || []).join(", ")} />
          <Row l={t("geo")} v={c.geographic_scope} />
          <Row l={t("collections.lastImport")} v={fmtDate(c.last_import_at, locale)} />
          <Row l={t("collections.indexPolicy")} v={Object.entries(c.index_policy || {}).filter(([, v]) => v).map(([k]) => k).join(" · ")} />
          <Row l={t("collections.normPolicy")} v={JSON.stringify(c.normalization_policy || {})} />
          <Row l={t("collections.dedupPolicy")} v={JSON.stringify(c.dedup_policy || {})} />
        </div>
      )}

      {tab === "datasets" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("name")}</th>
                <th>{t("records")}</th>
                <th>{t("status")}</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id}>
                  <td><Link className="linkish" href={`/datasets/${d.id}`}>{d.name}</Link></td>
                  <td className="mono">{fmtNum(d.record_count, locale)}</td>
                  <td>{d.processing_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "search" && (
        <div className="panel panel-b">
          <form onSubmit={runSearch} style={{ display: "flex", gap: 8 }}>
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("searchPlaceholder")} />
            <button className="btn btn-primary" disabled={busy}>{t("search")}</button>
          </form>
          <table className="data" style={{ marginTop: 12 }}>
            <tbody>
              {(hits?.items || []).map((it: any) => (
                <tr key={it.record_id + it.field_name}>
                  <td>
                    {it.entity_id ? <Link className="linkish" href={`/entities/${it.entity_id}`}>{it.entity_name}</Link> : it.original}
                  </td>
                  <td className="faint">{it.match_type}</td>
                  <td className="mono">{Math.round((it.score || 0) * 100)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "entities" && (
        <div className="panel">
          <table className="data">
            <tbody>
              {entities.map((e) => (
                <tr key={e.id}>
                  <td><Link className="linkish" href={`/entities/${e.id}`}>{e.canonical_name}</Link></td>
                  <td className="badge">{e.entity_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "images" && (
        <div className="panel panel-b chip-row">
          {images.length === 0 && <div className="muted">{t("empty")}</div>}
          {images.map((im) => (
            <span key={im.id} className="badge badge-cyan">{im.uri}</span>
          ))}
        </div>
      )}

      {tab === "faceSearch" && (
        <div className="panel panel-b">
          <p className="muted">{t("collections.faceHint")}</p>
          <p className="badge badge-violet">{t("collections.noIdentity")}</p>
          {c.index_policy?.face_search === false ? (
            <p>{t("collections.faceDisabled")}</p>
          ) : (
            <input type="file" accept="image/*" onChange={(e) => e.target.files?.[0] && faceSearch(e.target.files[0])} />
          )}
          {(faceHits?.items || []).map((h: any, i: number) => (
            <div key={i} style={{ padding: "8px 0", borderBottom: "1px solid var(--line)", display: "flex", gap: 10 }}>
              <span className="mono">{h.score}</span>
              {h.entity_id ? <Link className="linkish" href={`/entities/${h.entity_id}`}>{h.entity_name}</Link> : h.id}
              <span className="badge">{h.review}</span>
            </div>
          ))}
        </div>
      )}

      {tab === "indexes" && (
        <div className="panel">
          <div className="panel-h">
            <span className="muted">{t("collections.rebuildHint")}</span>
            <button className="btn" onClick={async () => { await api(`/collections/${id}/indexes/rebuild`, { method: "POST" }); load(); }}>
              {t("collections.rebuild")}
            </button>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("type")}</th>
                <th>{t("status")}</th>
                <th>backend</th>
                <th>{t("records")}</th>
              </tr>
            </thead>
            <tbody>
              {indexes.map((i) => (
                <tr key={i.kind}>
                  <td className="mono">{i.kind}</td>
                  <td><span className="badge badge-green">{i.status}</span></td>
                  <td className="faint">{i.backend}</td>
                  <td className="mono">{fmtNum(i.document_count, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "versions" && (
        <div className="panel">
          <div className="panel-h">
            <span />
            <button className="btn" onClick={async () => { await api(`/collections/${id}/versions`, { method: "POST" }); load(); }}>
              {t("collections.snapshot")}
            </button>
          </div>
          <table className="data">
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>{v.version_label}</td>
                  <td className="faint">{fmtDate(v.created_at, locale)}</td>
                  <td className="faint">{v.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "permissions" && (
        <div className="panel panel-b muted">{t("collections.permissions")} · RBAC · {t("role")}</div>
      )}

      {tab === "settings" && (
        <div className="panel panel-b">
          <p className="muted">{t("collections.softDelete")}</p>
          <button
            className="btn btn-danger"
            onClick={async () => {
              await api(`/collections/${id}`, { method: "DELETE" });
              router.push("/collections");
            }}
          >
            {t("collections.softDelete")}
          </button>
        </div>
      )}
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
