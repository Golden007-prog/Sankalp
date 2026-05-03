"use client";
import { BookOpen, Copy } from "lucide-react";
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
  const onCopy = () => {
    if (payload.permalink) navigator.clipboard.writeText(payload.permalink).catch(() => {});
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
          // Phase 6 wires Imagen output to a real URL; until then this is rare.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={payload.cover_url} alt="" className="aspect-square w-full rounded-md" />
        )}
        <p className="whitespace-pre-line leading-relaxed">{narrative}</p>
      </CardContent>
      {payload.permalink && (
        <CardFooter>
          <Button onClick={onCopy} size="sm" variant="outline">
            <Copy className="h-4 w-4" />
            {t("cards.story.share")}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
