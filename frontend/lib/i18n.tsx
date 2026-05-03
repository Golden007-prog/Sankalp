"use client";
import * as React from "react";

import bn from "@/i18n/bn.json";
import en from "@/i18n/en.json";
import hi from "@/i18n/hi.json";
import kn from "@/i18n/kn.json";
import mr from "@/i18n/mr.json";
import ta from "@/i18n/ta.json";
import te from "@/i18n/te.json";

export type LangCode = "en" | "hi" | "bn" | "ta" | "kn" | "te" | "mr";

export const LANGS: { code: LangCode; native: string }[] = [
  { code: "en", native: "English" },
  { code: "hi", native: "हिन्दी" },
  { code: "bn", native: "বাংলা" },
  { code: "ta", native: "தமிழ்" },
  { code: "kn", native: "ಕನ್ನಡ" },
  { code: "te", native: "తెలుగు" },
  { code: "mr", native: "मराठी" },
];

export const BUNDLES: Record<LangCode, Record<string, string>> = { en, hi, bn, ta, kn, te, mr };

const STORAGE_KEY = "sankalp_lang";

type Ctx = {
  lang: LangCode;
  setLang: (l: LangCode) => void;
  t: (key: string, fallback?: string) => string;
};

const LangContext = React.createContext<Ctx | null>(null);

function pickInitial(): LangCode {
  if (typeof window === "undefined") return "en";
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY) as LangCode | null;
    if (saved && saved in BUNDLES) return saved;
    const nav = navigator.language?.slice(0, 2) as LangCode;
    if (nav && nav in BUNDLES) return nav;
  } catch {
    /* localStorage may throw in strict modes */
  }
  return "en";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = React.useState<LangCode>("en");
  React.useEffect(() => {
    setLangState(pickInitial());
  }, []);

  const setLang = React.useCallback((l: LangCode) => {
    setLangState(l);
    try {
      window.localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* ignore */
    }
  }, []);

  const t = React.useCallback(
    (key: string, fallback?: string): string => {
      return BUNDLES[lang][key] ?? BUNDLES.en[key] ?? fallback ?? key;
    },
    [lang],
  );

  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export function useLang(): Ctx {
  const ctx = React.useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside <LanguageProvider>");
  return ctx;
}

export function useT() {
  return useLang().t;
}
