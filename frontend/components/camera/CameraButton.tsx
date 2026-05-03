"use client";
import * as React from "react";
import { Camera, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";

export interface CameraButtonProps {
  /** Called with parsed EPIC after a successful OCR upload. */
  onResult: (epicNumber: string | null, rawText: string, confidence: number) => void;
  /** Optional session id to thread the OCR write into the same session. */
  sessionId?: string | null;
}

export function CameraButton({ onResult, sessionId }: CameraButtonProps) {
  const t = useT();
  const [busy, setBusy] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", f);
      if (sessionId) fd.append("session_id", sessionId);
      const r = await fetch("/api/proxy/vision/epic", { method: "POST", body: fd });
      const body = await r.json();
      onResult(body.epic_number ?? null, body.raw_text ?? "", body.confidence ?? 0);
    } catch {
      onResult(null, "", 0);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={onChange}
        aria-label={t("camera.label")}
      />
      <Tooltip delayDuration={150}>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            aria-label={t("camera.label")}
          >
            {busy ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> : <Camera className="h-5 w-5" aria-hidden />}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{busy ? t("camera.processing") : t("camera.label")}</TooltipContent>
      </Tooltip>
    </>
  );
}
