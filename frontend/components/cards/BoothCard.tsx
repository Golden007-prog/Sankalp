"use client";
import { ExternalLink, MapPin, Accessibility } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataChip } from "@/components/disclosure/DemoDataChip";
import { useT } from "@/lib/i18n";

export interface BoothCardPayload {
  booth_id?: string;
  address?: string;
  lat?: string | number;
  lng?: string | number;
  wheelchair?: string | boolean;
  language_assist?: string;
  eta_walk?: string;
  eta_transit?: string;
}

function asBool(v: BoothCardPayload["wheelchair"]) {
  return v === true || v === "true";
}

export function BoothCard({ payload }: { payload: BoothCardPayload }) {
  const t = useT();
  const lat = Number(payload.lat ?? 0);
  const lng = Number(payload.lng ?? 0);
  const mapsHref =
    Number.isFinite(lat) && Number.isFinite(lng)
      ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
      : "https://www.google.com/maps";

  return (
    <Card className="my-3 max-w-md">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <MapPin className="h-5 w-5" />
          {t("cards.booth.title")}
        </CardTitle>
        <DemoDataChip />
      </CardHeader>
      <CardContent className="space-y-3">
        {payload.address && (
          <p>
            <span className="text-muted-foreground">{t("cards.booth.address")}: </span>
            {payload.address}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          {asBool(payload.wheelchair) && (
            <Badge variant="secondary" className="gap-1">
              <Accessibility className="h-3 w-3" />
              {t("cards.booth.wheelchair")}
            </Badge>
          )}
          {payload.language_assist && (
            <Badge variant="outline">
              {t("cards.booth.langs")}: {payload.language_assist}
            </Badge>
          )}
          {payload.eta_walk && (
            <Badge variant="outline">
              {t("cards.booth.eta_walk")}: {payload.eta_walk}
            </Badge>
          )}
          {payload.eta_transit && (
            <Badge variant="outline">
              {t("cards.booth.eta_transit")}: {payload.eta_transit}
            </Badge>
          )}
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild size="sm">
          <a href={mapsHref} target="_blank" rel="noopener noreferrer">
            <ExternalLink className="h-4 w-4" />
            {t("cards.booth.directions")}
          </a>
        </Button>
      </CardFooter>
    </Card>
  );
}
