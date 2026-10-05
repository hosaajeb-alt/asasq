"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";
import { originClass } from "@/lib/format";

export default function CaseWorkspace() {
  const { id } = useParams<{ id: string }>();
  const { t, locale } = useI18n();
  const [c, setC] = useState<any>(null);
  const [note, setNote] = useState("");
  const [tab, setTab] = useState("overview");

  async function load() {
    setC(await api(`/investigations/${id}`));
  }
  useEffect(() => {
    load().catch(() => {});
  }, [id]);

  async function addNote() {
    if (!note.trim()) return;
    await api(`/investigations/${id}/notes`, { method: "POST", body: JSON.stringify({ body: note }) });
    setNote("");
    load();
  }

  if (!c) return <div className="muted">{t("loading")}</div>;

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("investigations.workspace")} · {c.classification}</div>
        <h1 style={{ margin: "4px 0 0" }}>{c.title}</h1>
        <p className="muted">{c.summary}</p>
      </div>
      <div className="tabs">
        {["overview", "pinned", "notes", "evidence", "timeline"].map((k) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
            {k === "pinned" ? t("investigations.pinned") : t(k === "notes" ? "notes" : k)}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="panel panel-b chip-row">
          <span className="badge badge-green">{t(c.status)}</span>
          {(c.tags || []).map((tg: string) => <span key={tg} className="badge">{tg}</span>)}
          <span className="badge">{(c.items || []).length} items</span>
          <span className="badge">{(c.evidence || []).length} {t("evidence")}</span>
        </div>
      )}

      {(tab === "overview" || tab === "pinned") && (
        <div className="panel">
          <div className="panel-h"><span className="kicker">{t("investigations.pinned")}</span></div>
          {(c.items || []).length === 0 && <div className="panel-b muted">{t("investigations.noItems")}</div>}
          <table className="data">
            <tbody>
              {(c.items || []).map((it: any) => (
                <tr key={it.id}>
                  <td><span className="badge">{it.item_type}</span></td>
                  <td>
                    {it.item_type === "entity" ? (
                      <Link className="linkish" href={`/entities/${it.item_id}`}>{it.label}</Link>
                    ) : (
                      it.label
                    )}
                  </td>
                  <td className="faint">{fmtDate(it.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "notes" && (
        <div className="panel panel-b">
          <textarea className="textarea" value={note} onChange={(e) => setNote(e.target.value)} />
          <button className="btn btn-primary" style={{ marginTop: 8 }} onClick={addNote}>{t("addNote")}</button>
          <div style={{ marginTop: 16 }}>
            {(c.notes || []).map((n: any) => (
              <div key={n.id} style={{ padding: "10px 0", borderBottom: "1px solid var(--line)" }}>
                <div>{n.body}</div>
                <div className="faint">{fmtDate(n.created_at, locale)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "evidence" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("title")}</th>
                <th>{t("origin")}</th>
                <th>{t("notes")}</th>
              </tr>
            </thead>
            <tbody>
              {(c.evidence || []).map((e: any) => (
                <tr key={e.id}>
                  <td>
                    <Link className="linkish" href={`/evidence`}>{e.title}</Link>
                  </td>
                  <td><span className={originClass(e.origin)}>{t(e.origin)}</span></td>
                  <td className="muted">{e.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "timeline" && (
        <div className="panel panel-b">
          {(c.timeline || []).map((ev: any) => (
            <div key={ev.id} style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--line)" }}>
              <div className="mono faint">{fmtDate(ev.occurred_at, locale)}</div>
              <div>
                <strong>{ev.title}</strong>
                <div className="muted">{ev.body}</div>
                <span className={originClass(ev.origin)}>{t(ev.origin)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
