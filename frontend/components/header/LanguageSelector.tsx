"use client";
import { Languages } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { LANGS, useLang, useT, type LangCode } from "@/lib/i18n";

export function LanguageSelector() {
  const { lang, setLang } = useLang();
  const t = useT();
  return (
    <div className="flex items-center gap-1">
      <Languages className="h-4 w-4 text-muted-foreground" aria-hidden />
      <Select value={lang} onValueChange={(v) => setLang(v as LangCode)}>
        <SelectTrigger className="h-8 w-32" aria-label={t("header.language")}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {LANGS.map((l) => (
            <SelectItem key={l.code} value={l.code}>
              {l.native}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
