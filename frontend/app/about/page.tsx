"use client";
import Link from "next/link";
import { Header } from "@/components/header/Header";
import { useT } from "@/lib/i18n";

export default function About() {
  const t = useT();
  return (
    <>
      <Header />
      <main id="main" className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="mb-4 text-2xl font-semibold tracking-tight">{t("about.title")}</h1>
        <p className="leading-relaxed text-muted-foreground">{t("about.body")}</p>

        <h2 className="mt-8 mb-2 text-lg font-semibold">Disclosures</h2>
        <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
          <li>
            voters.eci.gov.in does not expose a public API. Sankalp ships with a representative
            mock dataset of ~100 constituencies and ~5,000 synthetic voter records. We never
            access the live electoral roll.
          </li>
          <li>
            Sankalp does not submit forms to ECI on the user's behalf. We generate a pre-filled
            PDF the user submits themselves at <span className="font-mono">voters.eci.gov.in</span>.
          </li>
          <li>
            No login or account. Sessions are anonymous, opaque IDs, TTL'd 24 hours.
          </li>
          <li>
            Booth-level accessibility flags are synthesised — ECI does not publish them. Every
            card surfaces a "demo data" chip.
          </li>
        </ul>

        <p className="mt-8 text-xs text-muted-foreground">
          Built for Hack2skill PromptWars 3 · Election Process Education ·{" "}
          <Link href="https://github.com/Golden007-prog/Sankalp" className="underline">
            github.com/Golden007-prog/Sankalp
          </Link>
        </p>
      </main>
    </>
  );
}
