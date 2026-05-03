"use client";
import Link from "next/link";
import { LanguageSelector } from "@/components/header/LanguageSelector";
import { A11yToggles } from "@/components/header/A11yToggles";
import { useT } from "@/lib/i18n";

export function Header() {
  const t = useT();
  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-3 border-b bg-background/80 px-4 backdrop-blur">
      <Link href="/" className="flex items-baseline gap-2">
        <span className="text-xl font-semibold tracking-tight">{t("app.title")}</span>
        <span className="hidden text-xs text-muted-foreground sm:inline">{t("app.tagline")}</span>
      </Link>
      <nav className="flex items-center gap-2">
        <LanguageSelector />
        <A11yToggles />
        <Link href="/about" className="text-xs text-muted-foreground underline-offset-4 hover:underline">
          {t("header.about")}
        </Link>
      </nav>
    </header>
  );
}
