"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate, fmtNum, pct } from "@/lib/format";

export default function DatasetDetail() {
  const { id } = useParams<{ id: string }>();
  const { t, locale } = useI18n();
  const [ds, setDs] = useState<any>(null);
  const [recs, setRecs] = useState<any>(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    api(`/datasets/${id}`).then(setDs).catch(() => {});
    api(`/datasets/${id}/records?page_size=25`).then(setRecs).catch(() => {});
  }, [id]);

  if (!ds) return <div className="muted">{t("loading")}</div>;
  const q = ds.data_quality || {};

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{ds.category} · {ds.version_label}</div>
        <h1 style={{ margin: "4px 0 0" }}>{ds.name}</h1>
        <p className="muted">{ds.description}</p>
        <div className="chip-row" style={{ marginTop: 8 }}>
          {(ds.tags || []).map((tg: string) => <span key={tg} className="badge">{tg}</span>)}
          <span className="badge badge-amber">{ds.legal_classification}</span>
          <span className="badge badge-cyan">{fmtNum(ds.record_count, locale)} {t("records")}</span>
        </div>
      </div>
      <div className="tabs">
        {["overview", "schema", "records", "quality", "versions", "provenance"].map((k) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
            {t(k === "quality" ? "quality" : k === "schema" ? "schema" : k === "records" ? "records" : k === "versions" ? "versions" : k === "provenance" ? "provenance" : "overview")}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="panel panel-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Row l={t("source")} v={ds.source} />
          <Row l={t("sourceDesc")} v={ds.source_description} />
          <Row l={t("languages")} v={(ds.languages || []).join(", ")} />
          <Row l={t("geo")} v={ds.geographic_scope} />
          <Row l={t("datasetDate")} v={ds.dataset_date} />
          <Row l={t("importedAt")} v={fmtDate(ds.imported_at, locale)} />
          <Row l={t("notes")} v={ds.notes} />
        </div>
      )}

      {tab === "schema" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("field")}</th>
                <th>{t("physical")}</th>
                <th>{t("semantic")}</th>
                <th>{t("confidence")}</th>
                <th>{t("approve")}</th>
              </tr>
            </thead>
            <tbody>
              {(ds.fields || []).map((f: any) => (
                <tr key={f.name}>
                  <td className="mono">{f.name}</td>
                  <td>{f.physical_type}</td>
                  <td><span className="badge badge-cyan">{f.semantic_type}</span></td>
                  <td className="mono">{Math.round((f.confidence || 0) * 100)}%</td>
                  <td>{f.approved ? <span className="badge badge-green">✓</span> : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "records" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>#</th>
                <th>{t("rawPayload")}</th>
                <th>{t("duplicateOf")}</th>
              </tr>
            </thead>
            <tbody>
              {(recs?.items || []).map((r: any) => (
                <tr key={r.id}>
                  <td className="mono faint">{r.row_number}</td>
                  <td className="mono" style={{ fontSize: 11, maxWidth: 720, whiteSpace: "pre-wrap" }}>
                    {JSON.stringify(r.raw, null, 0)}
                  </td>
                  <td className="faint">{r.duplicate_reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "quality" && (
        <div className="panel">
          <div className="panel-b chip-row">
            <span className="badge">{t("records")} {fmtNum(q.records, locale)}</span>
            <span className="badge badge-green">{t("ready")} {fmtNum(q.valid, locale)}</span>
            <span className="badge badge-amber">{t("duplicates")} {fmtNum(q.duplicates, locale)}</span>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("field")}</th>
                <th>{t("semantic")}</th>
                <th>{t("nullRate")}</th>
                <th>{t("uniqueRate")}</th>
                <th>{t("invalidRate")}</th>
                <th>{t("cardinality")}</th>
                <th>{t("sample")}</th>
              </tr>
            </thead>
            <tbody>
              {(q.fields || []).map((f: any) => (
                <tr key={f.field}>
                  <td className="mono">{f.field}</td>
                  <td>{f.semantic_type}</td>
                  <td>{pct(f.null_rate)}</td>
                  <td>{pct(f.unique_rate)}</td>
                  <td>{pct(f.invalid_rate)}</td>
                  <td className="mono">{f.cardinality}</td>
                  <td className="faint">{(f.sample_values || []).slice(0, 3).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "versions" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("version")}</th>
                <th>{t("records")}</th>
                <th>{t("checksum")}</th>
                <th>{t("created")}</th>
              </tr>
            </thead>
            <tbody>
              {(ds.versions || []).map((v: any) => (
                <tr key={v.id}>
                  <td>{v.version_label}</td>
                  <td>{fmtNum(v.record_count, locale)}</td>
                  <td className="mono faint">{v.checksum}</td>
                  <td className="faint">{fmtDate(v.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "provenance" && (
        <div className="panel panel-b">
          <div className="kicker">{t("spine")}</div>
          <pre className="mono faint" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(ds.provenance, null, 2)}</pre>
          <p className="muted">{t("whereFrom")} / {t("whenAdded")}</p>
          <Link className="linkish" href="/evidence">{t("evidence")} →</Link>
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
