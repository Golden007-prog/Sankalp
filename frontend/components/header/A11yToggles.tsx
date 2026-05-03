"use client";
import * as React from "react";
import { Moon, Sun, Type } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";

const STORAGE_THEME = "sankalp_theme";
const STORAGE_LARGE = "sankalp_large_text";

export function A11yToggles() {
  const t = useT();
  const [dark, setDark] = React.useState(false);
  const [large, setLarge] = React.useState(false);

  React.useEffect(() => {
    try {
      const ts = localStorage.getItem(STORAGE_THEME);
      const ls = localStorage.getItem(STORAGE_LARGE);
      const prefersDark =
        ts === "dark" || (!ts && window.matchMedia?.("(prefers-color-scheme: dark)").matches);
      setDark(prefersDark);
      setLarge(ls === "1");
    } catch { /* ignore */ }
  }, []);

  React.useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    try { localStorage.setItem(STORAGE_THEME, dark ? "dark" : "light"); } catch { /* ignore */ }
  }, [dark]);

  React.useEffect(() => {
    document.documentElement.style.setProperty("--font-scale", large ? "1.25" : "1");
    try { localStorage.setItem(STORAGE_LARGE, large ? "1" : "0"); } catch { /* ignore */ }
  }, [large]);

  return (
    <div className="flex items-center gap-1">
      <Tooltip delayDuration={150}>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            onClick={() => setLarge((v) => !v)}
            aria-pressed={large}
            aria-label={t("header.largetext")}
          >
            <Type className="h-4 w-4" aria-hidden />
          </Button>
        </TooltipTrigger>
        <TooltipContent>{t("header.largetext")}</TooltipContent>
      </Tooltip>
      <Tooltip delayDuration={150}>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            onClick={() => setDark((v) => !v)}
            aria-pressed={dark}
            aria-label={t("header.darkmode")}
          >
            {dark ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{t("header.darkmode")}</TooltipContent>
      </Tooltip>
    </div>
  );
}
