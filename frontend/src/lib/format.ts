export function fmtDate(iso?: string | null, locale: string = "en") {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return new Intl.DateTimeFormat(locale === "fa" ? "fa-IR" : "en-GB", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(d);
  } catch {
    return iso;
  }
}

export function fmtNum(n: number | undefined | null, locale: string = "en") {
  if (n == null) return "—";
  return new Intl.NumberFormat(locale === "fa" ? "fa-IR" : "en-US").format(n);
}

export function pct(n: number | undefined | null) {
  if (n == null) return "—";
  return `${Math.round(n * 1000) / 10}%`;
}

export function originClass(origin?: string) {
  if (origin === "observed") return "badge badge-cyan badge-obs";
  if (origin === "derived") return "badge badge-amber badge-der";
  if (origin === "inferred") return "badge badge-violet badge-inf";
  if (origin === "user_confirmed") return "badge badge-green badge-conf";
  return "badge";
}
