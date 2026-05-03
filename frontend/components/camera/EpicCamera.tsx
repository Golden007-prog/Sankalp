"use client";
import * as React from "react";
import { Camera, Check, Loader2, RefreshCw, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export interface OcrResult {
  ok: boolean;
  epic_number: string | null;
  raw_text: string;
  confidence: number;
  matched_name?: string | null;
  alternatives?: string[] | null;
  strategy_used?: string | null;
  session_id?: string;
}

const AUTO_SUBMIT_THRESHOLD = 0.85;
const EPIC_RE = /^[A-Z]{3}\d{7}$/;

export interface EpicCameraProps {
  /**
   * Called when the user (or auto-flow) confirms a parsed EPIC and wants
   * to verify it. The chat layer should treat this as a normal user
   * message ("Verify EPIC X").
   */
  onConfirm: (epic: string) => void;
  /** Called to dismiss the camera tray. */
  onClose: () => void;
  sessionId?: string | null;
}

type Stage = "capture" | "processing" | "result" | "error";

export function EpicCamera({ onConfirm, onClose, sessionId }: EpicCameraProps) {
  const t = useT();
  const [stage, setStage] = React.useState<Stage>("capture");
  const [previewUrl, setPreviewUrl] = React.useState<string | null>(null);
  const [result, setResult] = React.useState<OcrResult | null>(null);
  const [manualEpic, setManualEpic] = React.useState("");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const autoSubmitTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  React.useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (autoSubmitTimerRef.current) clearTimeout(autoSubmitTimerRef.current);
  }, [previewUrl]);

  const reset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    if (autoSubmitTimerRef.current) clearTimeout(autoSubmitTimerRef.current);
    setPreviewUrl(null);
    setResult(null);
    setManualEpic("");
    setErrorMsg(null);
    setStage("capture");
    if (inputRef.current) inputRef.current.value = "";
  };

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPreviewUrl(URL.createObjectURL(f));
    setStage("processing");
    setErrorMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      if (sessionId) fd.append("session_id", sessionId);
      const r = await fetch("/api/proxy/vision/epic", { method: "POST", body: fd });
      if (!r.ok) {
        setStage("error");
        setErrorMsg(t("camera.failed"));
        return;
      }
      const body: OcrResult = await r.json();
      setResult(body);
      setManualEpic(body.epic_number || "");
      setStage("result");
      if (
        body.ok &&
        body.epic_number &&
        body.confidence >= AUTO_SUBMIT_THRESHOLD &&
        EPIC_RE.test(body.epic_number)
      ) {
        // Brief delay so the user sees the result panel before the chat
        // bubble pops up.
        autoSubmitTimerRef.current = setTimeout(() => {
          onConfirm(body.epic_number!);
          onClose();
          reset();
        }, 700);
      }
    } catch {
      setStage("error");
      setErrorMsg(t("camera.failed"));
    }
  };

  const submitManual = () => {
    const v = manualEpic.trim().toUpperCase();
    if (!EPIC_RE.test(v)) return;
    onConfirm(v);
    onClose();
    reset();
  };

  const conf = result?.confidence ?? 0;
  const confPct = Math.round(conf * 100);
  const lowConfidence = !!result && conf < AUTO_SUBMIT_THRESHOLD;
  const validManual = EPIC_RE.test(manualEpic.trim().toUpperCase());

  return (
    <Card className="relative my-2">
      <CardHeader className="flex-row items-center justify-between pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Camera className="h-4 w-4" aria-hidden />
          {t("camera.label")}
        </CardTitle>
        <Tooltip delayDuration={150}>
          <TooltipTrigger asChild>
            <Button type="button" size="icon" variant="ghost" onClick={onClose} aria-label="Close">
              <X className="h-4 w-4" aria-hidden />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Close</TooltipContent>
        </Tooltip>
      </CardHeader>

      <CardContent className="space-y-3">
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          onChange={onFile}
          aria-label={t("camera.label")}
        />
        {stage === "capture" && (
          <Button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="w-full"
          >
            <Camera className="h-4 w-4" />
            {t("camera.take")}
          </Button>
        )}
        {previewUrl && stage !== "capture" && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt="EPIC preview"
            className="aspect-[8/5] w-full rounded-md border bg-muted object-contain"
          />
        )}
        {stage === "processing" && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            {t("camera.processing")}
          </p>
        )}
        {stage === "result" && result && (
          <div className="space-y-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={lowConfidence ? "outline" : "default"} className="font-mono text-sm">
                {result.epic_number || "—"}
              </Badge>
              <span className={cn("text-xs", lowConfidence ? "text-amber-600" : "text-emerald-600")}>
                {confPct}% confidence
              </span>
              {result.matched_name && (
                <Badge variant="secondary">match: {result.matched_name}</Badge>
              )}
            </div>
            {lowConfidence && (
              <div className="space-y-2 rounded-md border border-amber-300 bg-amber-50 p-2 dark:border-amber-700 dark:bg-amber-950/40">
                <p className="text-xs text-amber-900 dark:text-amber-200">
                  Low confidence — please correct if needed.
                </p>
                <Input
                  type="text"
                  value={manualEpic}
                  onChange={(e) => setManualEpic(e.target.value.toUpperCase())}
                  placeholder="ABC1234567"
                  pattern="[A-Z]{3}[0-9]{7}"
                  maxLength={11}
                  className="font-mono uppercase"
                  aria-label="Edit EPIC number"
                />
              </div>
            )}
          </div>
        )}
        {stage === "error" && (
          <p className="text-sm text-destructive">{errorMsg || t("camera.failed")}</p>
        )}
      </CardContent>

      <CardFooter className="flex-wrap gap-2">
        {(stage === "result" || stage === "error") && (
          <Button type="button" variant="outline" onClick={reset}>
            <RefreshCw className="h-4 w-4" />
            {t("camera.retake")}
          </Button>
        )}
        {stage === "result" && lowConfidence && (
          <Button type="button" onClick={submitManual} disabled={!validManual}>
            <Check className="h-4 w-4" />
            Verify
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
