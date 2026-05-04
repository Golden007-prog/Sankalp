"use client";
import * as React from "react";
import { BookOpen, Copy, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataChip } from "@/components/disclosure/DemoDataChip";
import { useT } from "@/lib/i18n";

export interface StoryCardPayload {
  ac_code?: string;
  cover_url?: string;
  audio_url?: string;
  permalink?: string;
}

export function StoryCard({ payload, narrative }: { payload: StoryCardPayload; narrative: string }) {
  const t = useT();
  const [copied, setCopied] = React.useState(false);

  const share = async () => {
    if (!payload.permalink) return;
    const shareData: ShareData = {
      title: t("cards.story.title"),
      text: t("cards.story.title"),
      url: payload.permalink,
    };
    if (typeof navigator.share === "function") {
      try {
        if (typeof navigator.canShare !== "function" || navigator.canShare(shareData)) {
          await navigator.share(shareData);
          return;
        }
      } catch {
        /* user cancelled — fall through to clipboard */
      }
    }
    try {
      await navigator.clipboard.writeText(payload.permalink);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };

  return (
    <Card className="my-3 max-w-md">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <BookOpen className="h-5 w-5" />
          {t("cards.story.title")}
        </CardTitle>
        <DemoDataChip />
      </CardHeader>
      <CardContent className="space-y-3">
        {payload.cover_url && (
          // Cover served via the backend proxy (private GCS bucket → /api/story/:code/cover.png).
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={payload.cover_url}
            alt={`Cover for ${payload.ac_code ?? "constituency"}`}
            className="aspect-square w-full rounded-md object-cover"
            loading="lazy"
          />
        )}
        <p className="whitespace-pre-line leading-relaxed">{narrative}</p>
        {payload.audio_url && (
          <audio controls preload="none" className="w-full">
            <source src={payload.audio_url} type="audio/mpeg" />
          </audio>
        )}
      </CardContent>
      {payload.permalink && (
        <CardFooter>
          <Button onClick={share} size="sm" variant="outline" aria-label={t("cards.story.share")}>
            {typeof navigator !== "undefined" && "share" in navigator ? (
              <Share2 className="h-4 w-4" aria-hidden />
            ) : (
              <Copy className="h-4 w-4" aria-hidden />
            )}
            {copied ? "Copied" : t("cards.story.share")}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
