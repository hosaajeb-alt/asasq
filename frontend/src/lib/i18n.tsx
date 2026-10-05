"use client";

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import enCommon from "../../i18n/en/common.json";
import enDatasets from "../../i18n/en/datasets.json";
import enSearch from "../../i18n/en/search.json";
import enEntities from "../../i18n/en/entities.json";
import enInvestigations from "../../i18n/en/investigations.json";
import enCollections from "../../i18n/en/collections.json";
import faCommon from "../../i18n/fa/common.json";
import faDatasets from "../../i18n/fa/datasets.json";
import faSearch from "../../i18n/fa/search.json";
import faEntities from "../../i18n/fa/entities.json";
import faInvestigations from "../../i18n/fa/investigations.json";
import faCollections from "../../i18n/fa/collections.json";

export type Locale = "en" | "fa";

const catalogs: Record<Locale, Record<string, any>> = {
  en: {
    common: enCommon,
    datasets: enDatasets,
    search: enSearch,
    entities: enEntities,
    investigations: enInvestigations,
    collections: enCollections,
  },
  fa: {
    common: faCommon,
    datasets: faDatasets,
    search: faSearch,
    entities: faEntities,
    investigations: faInvestigations,
    collections: faCollections,
  },
};

function lookup(locale: Locale, key: string): string {
  const parts = key.split(".");
  let cur: any = catalogs[locale];
  for (const p of parts) {
    if (cur && typeof cur === "object" && p in cur) cur = cur[p];
    else {
      cur = catalogs.en;
      for (const q of parts) {
        if (cur && typeof cur === "object" && q in cur) cur = cur[q];
        else return key;
      }
      break;
    }
  }
  return typeof cur === "string" ? cur : key;
}

type Ctx = {
  locale: Locale;
  dir: "ltr" | "rtl";
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
};

const I18nCtx = createContext<Ctx | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    const saved = (typeof window !== "undefined" && localStorage.getItem("nexus.locale")) as Locale | null;
    if (saved === "fa" || saved === "en") setLocaleState(saved);
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    localStorage.setItem("nexus.locale", l);
  }, []);

  useEffect(() => {
    const dir = locale === "fa" ? "rtl" : "ltr";
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
    document.documentElement.classList.toggle("rtl", locale === "fa");
  }, [locale]);

  const value = useMemo<Ctx>(
    () => ({
      locale,
      dir: locale === "fa" ? "rtl" : "ltr",
      setLocale,
      t: (key: string) => {
        if (key.includes(".")) return lookup(locale, key);
        return lookup(locale, `common.${key}`);
      },
    }),
    [locale, setLocale]
  );

  return <I18nCtx.Provider value={value}>{children}</I18nCtx.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nCtx);
  if (!ctx) throw new Error("I18nProvider missing");
  return ctx;
}
