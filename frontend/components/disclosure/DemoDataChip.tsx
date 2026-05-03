"use client";
import * as React from "react";
import Link from "next/link";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

/**
 * Always-on disclosure chip. Mounts on every voter/booth/PDF/story card.
 * Per docs/DATA.md §5 — non-negotiable.
 */
export function DemoDataChip({ className }: { className?: string }) {
  const t = useT();
  return (
    <Tooltip delayDuration={200}>
      <TooltipTrigger asChild>
        <Link
          href="/about"
          className={cn(
            "inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-900",
            "dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200",
            className,
          )}
        >
          <Info className="h-3 w-3" aria-hidden />
          {t("cards.demo_data")}
        </Link>
      </TooltipTrigger>
      <TooltipContent>{t("cards.demo_data_tooltip")}</TooltipContent>
    </Tooltip>
  );
}
