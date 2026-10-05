"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { pct } from "@/lib/format";

const STEPS = [
  "stepUpload",
  "stepInfo",
  "stepDetect",
  "stepMap",
  "stepNorm",
  "stepQuality",
  "stepEntity",
  "stepReview",
  "stepImport",
];

export default function ImportWizard() {
  const { t } = useI18n();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [job, setJob] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [meta, setMeta] = useState({
    name: "",
    description: "",
    category: "custom",
    source: "",
    source_description: "",
    languages: "en,fa",
    geographic_scope: "",
    version_label: "v1",
    legal_classification: "internal",
    tags: "imported",
    notes: "",
  });
  const [fields, setFields] = useState<any[]>([]);
  const [mappings, setMappings] = useState<Record<string, string>>({ PersonName: "person", OrganizationName: "organization" });
  const [profile, setProfile] = useState<any>(null);

  const state = job?.wizard_state || {};

  async function upload(file: File) {
    setBusy(true);
    setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const j = await api("/imports/upload", { method: "POST", body: fd });
      setJob(j);
      setMeta((m) => ({ ...m, name: m.name || file.name.replace(/\.[^.]+$/, "") }));
      setStep(1);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveMeta() {
    setBusy(true);
    try {
      const j = await api(`/imports/${job.id}/meta`, {
        method: "POST",
        body: JSON.stringify({
          ...meta,
          languages: meta.languages.split(",").map((s) => s.trim()).filter(Boolean),
          tags: meta.tags.split(",").map((s) => s.trim()).filter(Boolean),
        }),
      });
      setJob(j);
      const det = await api(`/imports/${job.id}/detect-schema`, { method: "POST" });
      setJob(det);
      setFields(det.detected_schema || []);
      setStep(2);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveMap() {
    setBusy(true);
    try {
      const mapped = fields.map((f) => ({ ...f, approved: true }));
      const j = await api(`/imports/${job.id}/map-fields`, { method: "POST", body: JSON.stringify({ fields: mapped }) });
      setJob(j);
      await api(`/imports/${job.id}/normalization`, { method: "POST", body: JSON.stringify({ rules: { language_aware: true } }) });
      setStep(4);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function runProfile() {
    setBusy(true);
    try {
      const j = await api(`/imports/${job.id}/profile`, { method: "POST" });
      setJob(j);
      setProfile(j.profile);
      setStep(5);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveEntity() {
    setBusy(true);
    try {
      const j = await api(`/imports/${job.id}/entity-mapping`, { method: "POST", body: JSON.stringify({ mappings }) });
      setJob(j);
      setStep(7);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function commit() {
    setBusy(true);
    try {
      const res = await api(`/imports/${job.id}/commit`, { method: "POST" });
      router.push(`/datasets/${res.dataset.id}`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  const semanticOptions = useMemo(
    () => ["PersonName", "OrganizationName", "Email", "Phone", "Username", "Domain", "URL", "IPv4", "City", "Country", "Address", "Date", "Timestamp", "Hash", "DocumentID", "Identifier", "FreeText"],
    []
  );

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("datasets.importWizard")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("import")}</h1>
      </div>
      <div className="wizard-steps">
        {STEPS.map((s, i) => (
          <button key={s} className={`wiz-step ${i === step ? "on" : ""} ${i < step ? "done" : ""}`} onClick={() => i <= step && setStep(i)}>
            {i + 1}. {t(`datasets.${s}`)}
          </button>
        ))}
      </div>
      {err && <div className="badge badge-red">{err}</div>}

      {step === 0 && (
        <div className="panel panel-b">
          <p className="muted">{t("datasets.uploadHint")}</p>
          <input
            type="file"
            accept=".csv,.json,.jsonl,.ndjson,.parquet"
            onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
          />
          {busy && <div className="muted">{t("loading")}</div>}
        </div>
      )}

      {step === 1 && (
        <div className="panel panel-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {(["name", "description", "source", "source_description", "geographic_scope", "notes"] as const).map((k) => (
            <div key={k} style={{ gridColumn: k === "description" || k === "notes" ? "1 / -1" : undefined }}>
              <label className="label">{t(k === "name" ? "datasets.name" : k === "source" ? "source" : k)}</label>
              {k === "description" || k === "notes" ? (
                <textarea className="textarea" value={(meta as any)[k]} onChange={(e) => setMeta({ ...meta, [k]: e.target.value })} />
              ) : (
                <input className="input" value={(meta as any)[k]} onChange={(e) => setMeta({ ...meta, [k]: e.target.value })} />
              )}
            </div>
          ))}
          <div>
            <label className="label">{t("category")}</label>
            <select className="select" value={meta.category} onChange={(e) => setMeta({ ...meta, category: e.target.value })}>
              {["people", "registry", "network", "documents", "custom"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("legal")}</label>
            <select className="select" value={meta.legal_classification} onChange={(e) => setMeta({ ...meta, legal_classification: e.target.value })}>
              {["public", "internal", "confidential", "restricted"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="label">{t("languages")}</label>
            <input className="input" value={meta.languages} onChange={(e) => setMeta({ ...meta, languages: e.target.value })} />
          </div>
          <div>
            <label className="label">{t("tags")}</label>
            <input className="input" value={meta.tags} onChange={(e) => setMeta({ ...meta, tags: e.target.value })} />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button className="btn btn-primary" disabled={!meta.name || busy} onClick={saveMeta}>{t("next")}</button>
          </div>
        </div>
      )}

      {(step === 2 || step === 3) && (
        <div className="panel">
          <div className="panel-h">
            <span className="muted">{t("datasets.proposal")}</span>
            <button className="btn btn-primary" onClick={saveMap} disabled={busy}>{t("next")}</button>
          </div>
          <table className="data">
            <thead>
              <tr>
                <th>{t("field")}</th>
                <th>{t("physical")}</th>
                <th>{t("semantic")}</th>
                <th>{t("datasets.confidence")}</th>
                <th>{t("sample")}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f, i) => (
                <tr key={f.name}>
                  <td className="mono">{f.name}</td>
                  <td>{f.physical_type}</td>
                  <td>
                    <select
                      className="select"
                      value={f.semantic_type}
                      onChange={(e) => {
                        const next = [...fields];
                        next[i] = { ...f, semantic_type: e.target.value };
                        setFields(next);
                      }}
                    >
                      {semanticOptions.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </td>
                  <td className="mono">{Math.round((f.confidence || 0) * 1000) / 10}%</td>
                  <td className="faint">{(f.sample_values || []).slice(0, 3).join(" · ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {step === 4 && (
        <div className="panel panel-b">
          <p>{t("datasets.languageAware")}</p>
          <p className="muted">{t("datasets.preserve")}</p>
          <ul className="muted">
            <li>fa / ar / tr / ku / he / ru / en modules</li>
            <li>original_value · normalized_value · canonical_value · transliterated_value · phonetic_value</li>
          </ul>
          <button className="btn" onClick={() => setStep(3)}>{t("back")}</button>{" "}
          <button className="btn btn-primary" onClick={runProfile} disabled={busy}>{t("next")}</button>
        </div>
      )}

      {step === 5 && (
        <div className="panel">
          <div className="panel-h">
            <span>{t("datasets.qualityPreview")}</span>
            <button className="btn btn-primary" onClick={() => setStep(6)}>{t("next")}</button>
          </div>
          <div className="panel-b chip-row">
            <span className="badge">{t("records")} {profile?.records}</span>
            <span className="badge badge-amber">{t("duplicates")} {profile?.duplicates}</span>
            <span className="badge badge-red">{t("invalid")} {profile?.invalid_phone}</span>
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
              </tr>
            </thead>
            <tbody>
              {(profile?.fields || []).map((f: any) => (
                <tr key={f.field}>
                  <td className="mono">{f.field}</td>
                  <td>{f.semantic_type}</td>
                  <td>{pct(f.null_rate)}</td>
                  <td>{pct(f.unique_rate)}</td>
                  <td>{pct(f.invalid_rate)}</td>
                  <td>{f.cardinality}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {step === 6 && (
        <div className="panel panel-b">
          <p>{t("datasets.entityMapHint")}</p>
          {["PersonName", "OrganizationName", "Email", "Domain"].map((k) => (
            <div key={k} style={{ display: "flex", gap: 8, margin: "8px 0", alignItems: "center" }}>
              <div style={{ width: 180 }} className="mono">{k}</div>
              <select className="select" value={mappings[k] || ""} onChange={(e) => setMappings({ ...mappings, [k]: e.target.value })}>
                <option value="">—</option>
                {["person", "organization", "email", "domain", "identifier"].map((x) => <option key={x}>{x}</option>)}
              </select>
            </div>
          ))}
          <button className="btn btn-primary" onClick={saveEntity} disabled={busy}>{t("next")}</button>
        </div>
      )}

      {(step === 7 || step === 8) && (
        <div className="panel panel-b">
          <p>{t("datasets.reviewHint")}</p>
          <div className="chip-row">
            <span className="badge">{meta.name}</span>
            <span className="badge">{meta.category}</span>
            <span className="badge">{meta.legal_classification}</span>
            <span className="badge">{fields.length} fields</span>
            <span className="badge">{state.kind}</span>
            <span className="badge mono">{job?.checksum?.slice(0, 12)}</span>
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
            <button className="btn" onClick={() => setStep(6)}>{t("back")}</button>
            <button className="btn btn-primary" onClick={commit} disabled={busy}>{t("commit")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
