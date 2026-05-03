"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataChip } from "@/components/disclosure/DemoDataChip";
import { useT } from "@/lib/i18n";

export interface VoterRecordPayload {
  epic?: string;
  name?: string;
  ac?: string;
  booth?: string;
}

export function VoterRecordCard({ payload }: { payload: VoterRecordPayload }) {
  const t = useT();
  return (
    <Card className="my-3 max-w-md">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>{t("cards.voter.title")}</CardTitle>
        <DemoDataChip />
      </CardHeader>
      <CardContent className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2">
        {payload.name && (
          <>
            <span className="text-muted-foreground">Name</span>
            <span className="font-medium">{payload.name}</span>
          </>
        )}
        <span className="text-muted-foreground">{t("cards.voter.epic")}</span>
        <span className="font-mono">{payload.epic || "—"}</span>
        <span className="text-muted-foreground">{t("cards.voter.ac")}</span>
        <span>{payload.ac || "—"}</span>
        <span className="text-muted-foreground">{t("cards.voter.booth")}</span>
        <span>{payload.booth || "—"}</span>
      </CardContent>
    </Card>
  );
}
