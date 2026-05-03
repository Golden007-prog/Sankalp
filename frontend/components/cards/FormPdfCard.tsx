"use client";
import { Download, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { DemoDataChip } from "@/components/disclosure/DemoDataChip";
import { useT } from "@/lib/i18n";

export interface FormPdfPayload {
  url?: string;
  form_type?: string;
  filename?: string;
}

const ECI_PORTAL = "https://voters.eci.gov.in/";

export function FormPdfCard({ payload }: { payload: FormPdfPayload }) {
  const t = useT();
  const href = payload.url || "#";
  const qrSrc = `https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(ECI_PORTAL)}`;

  return (
    <Card className="my-3 max-w-md">
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          {t("cards.pdf.title")} {payload.form_type && `· Form ${payload.form_type}`}
        </CardTitle>
        <DemoDataChip />
      </CardHeader>
      <CardContent className="flex gap-4">
        <div className="flex-1 text-sm">
          <p className="text-muted-foreground">{t("cards.pdf.next_step")}</p>
          {payload.filename && <p className="mt-2 font-mono text-xs text-muted-foreground">{payload.filename}</p>}
        </div>
        {/* QR is purely a convenience deeplink; the disclosure copy still mandates manual upload. */}
        <img
          src={qrSrc}
          alt={t("cards.pdf.qr_label")}
          className="h-24 w-24 self-start rounded border bg-white p-1"
          loading="lazy"
        />
      </CardContent>
      <CardFooter>
        <Button asChild size="sm">
          <a href={href} target="_blank" rel="noopener noreferrer" download={payload.filename}>
            <Download className="h-4 w-4" />
            {t("cards.pdf.download")}
          </a>
        </Button>
      </CardFooter>
    </Card>
  );
}
