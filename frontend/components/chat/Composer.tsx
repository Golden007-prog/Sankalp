"use client";
import * as React from "react";
import { Camera, SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { EpicCamera } from "@/components/camera/EpicCamera";
import { VoiceButton } from "@/components/voice/VoiceButton";
import { useT } from "@/lib/i18n";

export interface ComposerProps {
  /**
   * Called for every user-originated message (typed text, voice transcript,
   * or auto-submitted "Verify EPIC X" after camera OCR).
   */
  onSubmit: (text: string) => void;
  sessionId?: string | null;
  disabled?: boolean;
}

export function Composer({ onSubmit, sessionId, disabled }: ComposerProps) {
  const t = useT();
  const [value, setValue] = React.useState("");
  const [cameraOpen, setCameraOpen] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const submit = (override?: string) => {
    const text = (override ?? value).trim();
    if (!text || disabled) return;
    onSubmit(text);
    setValue("");
  };

  const handleVoice = (final: string) => {
    if (final.trim()) submit(final);
  };

  const handleEpicConfirm = (epic: string) => {
    submit(`Please verify my voter record. My EPIC number is ${epic}.`);
  };

  return (
    <div className="space-y-2">
      {cameraOpen && (
        <EpicCamera
          sessionId={sessionId ?? null}
          onConfirm={handleEpicConfirm}
          onClose={() => setCameraOpen(false)}
        />
      )}
      <form
        className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Tooltip delayDuration={150}>
          <TooltipTrigger asChild>
            <Button
              type="button"
              size="icon"
              variant={cameraOpen ? "secondary" : "ghost"}
              onClick={() => setCameraOpen((v) => !v)}
              aria-pressed={cameraOpen}
              aria-label={t("camera.label")}
              disabled={disabled}
            >
              <Camera className="h-5 w-5" aria-hidden />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t("camera.label")}</TooltipContent>
        </Tooltip>
        <VoiceButton onTranscript={handleVoice} disabled={disabled || cameraOpen} />
        <Input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("chat.placeholder")}
          className="flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0"
          aria-label={t("chat.placeholder")}
          disabled={disabled || cameraOpen}
        />
        <Button
          type="submit"
          size="icon"
          disabled={disabled || cameraOpen || !value.trim()}
          aria-label={t("chat.send_aria")}
        >
          <SendHorizontal className="h-5 w-5" aria-hidden />
        </Button>
      </form>
    </div>
  );
}
