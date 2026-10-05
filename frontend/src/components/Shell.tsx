"use client";

import {
  Activity,
  Box,
  Fingerprint,
  GitBranch,
  LayoutDashboard,
  Search,
  Shield,
  FolderLock,
  Database,
  Layers,
  Settings,
  Languages,
  LogOut,
  Command,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { fmtNum } from "@/lib/format";
import { api } from "@/lib/api";

const NAV = [
  { href: "/", key: "dashboard", icon: LayoutDashboard },
  { href: "/collections", key: "collections", icon: Layers },
  { href: "/datasets", key: "datasets", icon: Database },
  { href: "/search", key: "search", icon: Search },
  { href: "/entities", key: "entities", icon: Fingerprint },
  { href: "/graph", key: "graph", icon: GitBranch },
  { href: "/investigations", key: "investigations", icon: FolderLock },
  { href: "/evidence", key: "evidence", icon: Box },
  { href: "/quality", key: "quality", icon: Activity },
  { href: "/admin", key: "admin", icon: Settings },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const { t, locale, setLocale } = useI18n();
  const { user, ready, logout } = useAuth();
  const path = usePathname();
  const router = useRouter();
  const [cmd, setCmd] = useState(false);
  const [q, setQ] = useState("");
  const [kpis, setKpis] = useState<any>(null);

  useEffect(() => {
    if (ready && !user && path !== "/login") router.replace("/login");
  }, [ready, user, path, router]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmd(true);
      }
      if (e.key === "Escape") setCmd(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!user) return;
    api("/dashboard")
      .then(setKpis)
      .catch(() => {});
  }, [user]);

  const commands = useMemo(
    () => [
      { label: t("search"), run: () => router.push("/search") },
      { label: t("collections"), run: () => router.push("/collections") },
      { label: t("datasets"), run: () => router.push("/datasets") },
      { label: t("newImport"), run: () => router.push("/datasets/import") },
      { label: t("entities"), run: () => router.push("/entities") },
      { label: t("graph"), run: () => router.push("/graph") },
      { label: t("investigations"), run: () => router.push("/investigations") },
      { label: t("admin"), run: () => router.push("/admin") },
    ],
    [t, router]
  );

  if (path === "/login") return <>{children}</>;
  if (!ready) return <div className="nx-app" style={{ padding: 40, color: "var(--muted)" }}>{t("loading")}</div>;
  if (!user) return null;

  const filtered = commands.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()) || q.length < 1);

  return (
    <div className="nx-app" style={{ display: "flex", minHeight: "100vh" }}>
      <aside className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "16px 16px 12px" }}>
          <div className="logo-mark">N</div>
          <div>
            <div style={{ fontWeight: 700, letterSpacing: "0.12em", fontSize: 13 }}>{t("app")}</div>
            <div className="faint" style={{ fontSize: 10 }}>{t("tagline")}</div>
          </div>
        </div>
        <nav style={{ flex: 1, paddingTop: 8 }}>
          {NAV.map((n) => {
            const Icon = n.icon;
            const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
            return (
              <Link key={n.href} href={n.href} className={`nav-item ${active ? "active" : ""}`}>
                <Icon size={16} />
                <span className="label">{t(n.key)}</span>
              </Link>
            );
          })}
        </nav>
        <div style={{ padding: 12, borderTop: "1px solid var(--line)" }}>
          <div className="muted" style={{ fontSize: 12 }}>{user.display_name}</div>
          <div className="faint mono" style={{ fontSize: 10 }}>{user.role}</div>
        </div>
      </aside>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <header className="topbar">
          <button className="btn btn-ghost" onClick={() => setCmd(true)} title="⌘K">
            <Command size={14} /> {t("openPalette")}
          </button>
          <form
            style={{ flex: 1, maxWidth: 640 }}
            onSubmit={(e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              const qq = String(fd.get("q") || "");
              router.push(`/search?q=${encodeURIComponent(qq)}`);
            }}
          >
            <div style={{ position: "relative" }}>
              <Search size={14} style={{ position: "absolute", top: 10, insetInlineStart: 10, color: "var(--faint)" }} />
              <input className="input" name="q" placeholder={t("searchPlaceholder")} style={{ paddingInlineStart: 30 }} />
            </div>
          </form>
          <button
            className="btn"
            onClick={() => setLocale(locale === "en" ? "fa" : "en")}
            title={t("language")}
          >
            <Languages size={14} />
            {locale === "en" ? "FA" : "EN"}
          </button>
          <button className="btn btn-ghost" onClick={logout}>
            <LogOut size={14} /> {t("signOut")}
          </button>
        </header>
        <div style={{ padding: "8px 16px 0" }}>
          <div className="badge badge-amber">{t("demoBanner")}</div>
        </div>
        <main className="scroll-y" style={{ flex: 1, padding: 16 }}>{children}</main>
        <footer className="statusbar">
          <span style={{ color: "var(--green)" }}>● {t("connected")}</span>
          <span>
            {t("records")} {fmtNum(kpis?.kpis?.records, locale)}
          </span>
          <span>
            {t("entities")} {fmtNum(kpis?.kpis?.entities, locale)}
          </span>
          <span>
            {t("datasets")} {fmtNum(kpis?.kpis?.datasets, locale)}
          </span>
          <span style={{ marginInlineStart: "auto" }}>
            <Shield size={11} style={{ display: "inline", verticalAlign: -2 }} /> RBAC · v0.1.0 · {t("scaleNote")}
          </span>
        </footer>
      </div>
      {cmd && (
        <div className="cmdk" onClick={() => setCmd(false)}>
          <div className="cmdk-box" onClick={(e) => e.stopPropagation()}>
            <input
              autoFocus
              className="input"
              style={{ border: 0, borderRadius: 0, padding: 14, fontSize: 15 }}
              placeholder={t("command")}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && filtered[0]) {
                  filtered[0].run();
                  setCmd(false);
                  setQ("");
                }
              }}
            />
            <div>
              {filtered.map((c) => (
                <button
                  key={c.label}
                  className="nav-item"
                  style={{ width: "calc(100% - 16px)", textAlign: "start" }}
                  onClick={() => {
                    c.run();
                    setCmd(false);
                    setQ("");
                  }}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
