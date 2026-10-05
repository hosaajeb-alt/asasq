"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { Languages, Shield } from "lucide-react";

export default function LoginPage() {
  const { t, locale, setLocale } = useI18n();
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("analyst@nexus.local");
  const [password, setPassword] = useState("NexusAnalyst!23");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      await login(email, password);
      router.replace("/");
    } catch {
      setErr(t("unauthorized"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-hero nx-app nx-grid-bg">
      <section style={{ padding: "64px 56px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div className="logo-mark" style={{ width: 36, height: 36 }}>N</div>
            <div>
              <div className="kicker">{t("loginLegal")}</div>
              <h1 style={{ margin: "6px 0 0", fontSize: 36, letterSpacing: "0.08em" }}>{t("app")}</h1>
            </div>
          </div>
          <p className="muted" style={{ maxWidth: 480, marginTop: 28, fontSize: 16, lineHeight: 1.6 }}>
            {t("loginBody")}
          </p>
          <ul className="muted" style={{ marginTop: 28, lineHeight: 1.9, paddingInlineStart: 18 }}>
            <li>{t("common.original") === "common.original" ? t("original") : t("original")} → immutable</li>
            <li>{t("normalized")} → derived</li>
            <li>{t("similarityNotIdentity")}</li>
            <li>EN / FA · RTL / LTR</li>
          </ul>
        </div>
        <div className="faint mono" style={{ fontSize: 11 }}>
          Phase 1 workspace · designed for 10B+ records
        </div>
      </section>
      <section style={{ display: "grid", placeItems: "center", padding: 32, background: "rgba(0,0,0,0.25)", borderInlineStart: "1px solid var(--line)" }}>
        <form className="panel" style={{ width: "min(420px, 100%)" }} onSubmit={onSubmit}>
          <div className="panel-h">
            <div>
              <div className="kicker">{t("loginTitle")}</div>
              <strong>{t("signIn")}</strong>
            </div>
            <button type="button" className="btn btn-ghost" onClick={() => setLocale(locale === "en" ? "fa" : "en")}>
              <Languages size={14} /> {locale === "en" ? "فارسی" : "EN"}
            </button>
          </div>
          <div className="panel-b" style={{ display: "grid", gap: 12 }}>
            <div>
              <label className="label">{t("email")}</label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
            </div>
            <div>
              <label className="label">{t("password")}</label>
              <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            </div>
            {err && <div className="badge badge-red">{err}</div>}
            <button className="btn btn-primary" disabled={busy} type="submit">
              <Shield size={14} /> {t("signIn")}
            </button>
            <div className="faint" style={{ fontSize: 11 }}>
              admin@nexus.local / NexusAdmin!23
              <br />
              analyst@nexus.local / NexusAnalyst!23
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
