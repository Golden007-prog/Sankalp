"use client";
import * as React from "react";
import { SendHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CameraButton } from "@/components/camera/CameraButton";
import { VoiceButton } from "@/components/voice/VoiceButton";
import { useT } from "@/lib/i18n";

export interface ComposerProps {
  onSubmit: (text: string) => void;
  onCameraResult: (epicNumber: string | null, rawText: string) => void;
  sessionId?: string | null;
  disabled?: boolean;
}

export function Composer({ onSubmit, onCameraResult, sessionId, disabled }: ComposerProps) {
  const t = useT();
  const [value, setValue] = React.useState("");
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

  return (
    <form
      className="flex items-end gap-2 rounded-2xl border bg-card p-2 shadow-sm"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <CameraButton sessionId={sessionId ?? null} onResult={(epic, raw) => onCameraResult(epic, raw)} />
      <VoiceButton onTranscript={handleVoice} disabled={disabled} />
      <Input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={t("chat.placeholder")}
        className="flex-1 border-0 bg-transparent shadow-none focus-visible:ring-0"
        aria-label={t("chat.placeholder")}
        disabled={disabled}
      />
      <Button
        type="submit"
        size="icon"
        disabled={disabled || !value.trim()}
        aria-label={t("chat.send_aria")}
      >
        <SendHorizontal className="h-5 w-5" aria-hidden />
      </Button>
    </form>
  );
}
