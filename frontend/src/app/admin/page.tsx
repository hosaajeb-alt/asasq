"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { fmtDate } from "@/lib/format";

export default function AdminPage() {
  const { t, locale } = useI18n();
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState<any[]>([]);
  const [types, setTypes] = useState<any[]>([]);
  const [audit, setAudit] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [teams, setTeams] = useState<any[]>([]);

  useEffect(() => {
    api("/admin/users").then((r) => setUsers(r.items || [])).catch(() => {});
    api("/admin/semantic-types").then((r) => setTypes(r.items || [])).catch(() => {});
    api("/admin/audit?page_size=40").then(setAudit).catch(() => {});
    api("/admin/metrics").then(setMetrics).catch(() => {});
    api("/admin/teams").then((r) => setTeams(r.items || [])).catch(() => {});
  }, []);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("admin")}</div>
        <h1 style={{ margin: "4px 0 0" }}>RBAC · {t("registry")} · {t("audit")}</h1>
      </div>
      <div className="tabs">
        {["users", "registry", "audit", "architecture"].map((k) => (
          <button key={k} className={`tab ${tab === k ? "active" : ""}`} onClick={() => setTab(k)}>
            {t(k === "architecture" ? "architecture" : k === "users" ? "users" : k === "registry" ? "registry" : "audit")}
          </button>
        ))}
      </div>

      {tab === "users" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("displayName")}</th>
                <th>{t("email")}</th>
                <th>{t("role")}</th>
                <th>{t("locale")}</th>
                <th>{t("lastLogin")}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>{u.display_name}</td>
                  <td className="mono">{u.email}</td>
                  <td><span className="badge badge-amber">{u.role}</span></td>
                  <td>{u.locale}</td>
                  <td className="faint">{fmtDate(u.last_login_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="panel-b">
            <div className="kicker">{t("team")}</div>
            {teams.map((tm) => (
              <div key={tm.id} className="muted">{tm.name} — {(tm.members || []).length} members</div>
            ))}
          </div>
        </div>
      )}

      {tab === "registry" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>Key</th>
                <th>{t("name")}</th>
                <th>{t("privacy")}</th>
                <th>{t("physical")}</th>
                <th>{t("system")}</th>
              </tr>
            </thead>
            <tbody>
              {types.map((s) => (
                <tr key={s.key}>
                  <td className="mono">{s.key}</td>
                  <td>{s.label}</td>
                  <td><span className="badge">{s.privacy_classification}</span></td>
                  <td>{s.physical_hint}</td>
                  <td>{s.is_system ? "●" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "audit" && (
        <div className="panel">
          <table className="data">
            <thead>
              <tr>
                <th>{t("action")}</th>
                <th>{t("resource")}</th>
                <th>{t("ip")}</th>
                <th>{t("created")}</th>
              </tr>
            </thead>
            <tbody>
              {(audit?.items || []).map((a: any) => (
                <tr key={a.id}>
                  <td className="mono">{a.action}</td>
                  <td className="faint">{a.resource_type} {a.resource_id?.slice?.(0, 8)}</td>
                  <td className="faint">{a.ip}</td>
                  <td className="faint">{fmtDate(a.created_at, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "architecture" && (
        <div className="panel panel-b">
          <div className="kicker">{t("architecture")}</div>
          <pre className="mono faint" style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(metrics, null, 2)}</pre>
          <p className="muted">{t("scaleNote")}</p>
        </div>
      )}
    </div>
  );
}
