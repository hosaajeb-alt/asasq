"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function NewCollection() {
  const { t } = useI18n();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({
    name: "",
    description: "",
    source: "",
    source_type: "custom",
    category: "custom",
    languages: "en,fa",
    geographic_scope: "",
    tags: "",
    legal_classification: "internal",
    text_search: true,
    vector_search: false,
    face_search: false,
    graph_index: true,
    fuzzy_search: true,
    phonetic_search: true,
  });

  function set<K extends keyof typeof form>(k: K, v: (typeof form)[K]) {
    setForm({ ...form, [k]: v });
  }

  async function submit() {
    if (!form.name.trim()) return;
    setBusy(true);
    setErr("");
    try {
      const c = await api("/collections", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          description: form.description,
          source: form.source,
          source_type: form.source_type,
          category: form.category,
          languages: form.languages.split(",").map((s) => s.trim()).filter(Boolean),
          geographic_scope: form.geographic_scope,
          tags: form.tags.split(",").map((s) => s.trim()).filter(Boolean),
          legal_classification: form.legal_classification,
          index_policy: {
            text_search: form.text_search,
            metadata_search: true,
            vector_search: form.vector_search,
            face_search: form.face_search,
            graph_index: form.graph_index,
            fuzzy_search: form.fuzzy_search,
            phonetic_search: form.phonetic_search,
          },
        }),
      });
      router.push(`/collections/${c.id}`);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ display: "grid", gap: 14, maxWidth: 820 }}>
      <div>
        <div className="kicker">{t("collections.create")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("collections.wizardTitle")}</h1>
        <p className="muted">{t("collections.wizardBody")}</p>
      </div>
      {err && <div className="badge badge-red">{err}</div>}
      <div className="panel panel-b" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label={t("name")} span>
          <input className="input" value={form.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label={t("description")} span>
          <textarea className="textarea" value={form.description} onChange={(e) => set("description", e.target.value)} />
        </Field>
        <Field label={t("source")}>
          <input className="input" value={form.source} onChange={(e) => set("source", e.target.value)} />
        </Field>
        <Field label={t("collections.sourceType")}>
          <select className="select" value={form.source_type} onChange={(e) => set("source_type", e.target.value)}>
            {["custom", "registry", "network", "documents", "images", "research"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </Field>
        <Field label={t("category")}>
          <select className="select" value={form.category} onChange={(e) => set("category", e.target.value)}>
            {["custom", "people", "registry", "network", "documents", "images"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </Field>
        <Field label={t("legal")}>
          <select className="select" value={form.legal_classification} onChange={(e) => set("legal_classification", e.target.value)}>
            {["public", "internal", "confidential", "restricted"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </Field>
        <Field label={t("languages")}>
          <input className="input" value={form.languages} onChange={(e) => set("languages", e.target.value)} />
        </Field>
        <Field label={t("geo")}>
          <input className="input" value={form.geographic_scope} onChange={(e) => set("geographic_scope", e.target.value)} />
        </Field>
        <Field label={t("tags")} span>
          <input className="input" value={form.tags} onChange={(e) => set("tags", e.target.value)} />
        </Field>
        <div style={{ gridColumn: "1 / -1" }}>
          <div className="label">{t("collections.indexPolicy")}</div>
          <div className="chip-row">
            {(
              [
                ["text_search", t("collections.textSearch")],
                ["vector_search", t("collections.vectorSearch")],
                ["face_search", t("collections.faceOn")],
                ["graph_index", t("collections.graphOn")],
                ["fuzzy_search", t("collections.fuzzyOn")],
                ["phonetic_search", t("collections.phoneticOn")],
              ] as const
            ).map(([k, lab]) => (
              <label key={k} className="badge" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={!!form[k]} onChange={(e) => set(k, e.target.checked as any)} /> {lab}
              </label>
            ))}
          </div>
        </div>
        <div style={{ gridColumn: "1 / -1" }}>
          <button className="btn btn-primary" disabled={busy || !form.name} onClick={submit}>
            {t("create")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children, span }: { label: string; children: React.ReactNode; span?: boolean }) {
  return (
    <div style={{ gridColumn: span ? "1 / -1" : undefined }}>
      <label className="label">{label}</label>
      {children}
    </div>
  );
}
