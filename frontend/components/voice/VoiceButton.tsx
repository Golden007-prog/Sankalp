"use client";
import * as React from "react";
import { Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useLang, useT } from "@/lib/i18n";

const LANG_TO_BCP47: Record<string, string> = {
  en: "en-IN",
  hi: "hi-IN",
  bn: "bn-IN",
  ta: "ta-IN",
  kn: "kn-IN",
  te: "te-IN",
  mr: "mr-IN",
};

interface SR extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((ev: any) => void) | null;
  onerror: ((ev: any) => void) | null;
  onend: ((ev: any) => void) | null;
}

function getRecognition(): SR | null {
  if (typeof window === "undefined") return null;
  const Cls = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
  if (!Cls) return null;
  return new Cls() as SR;
}

export interface VoiceButtonProps {
  /** Final transcript handler — fires when the user pauses speaking. */
  onTranscript: (text: string) => void;
  /** Live partial transcript — fires while the user is speaking. */
  onPartial?: (text: string) => void;
  disabled?: boolean;
}

export function VoiceButton({ onTranscript, onPartial, disabled }: VoiceButtonProps) {
  const t = useT();
  const { lang } = useLang();
  const [supported, setSupported] = React.useState<boolean | null>(null);
  const [listening, setListening] = React.useState(false);
  const recRef = React.useRef<SR | null>(null);

  React.useEffect(() => {
    const r = getRecognition();
    setSupported(!!r);
    if (r) {
      r.continuous = false;
      r.interimResults = true;
      r.lang = LANG_TO_BCP47[lang] || "en-IN";
      r.onresult = (event: any) => {
        let interim = "";
        let final_ = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const seg = event.results[i];
          if (seg.isFinal) final_ += seg[0].transcript;
          else interim += seg[0].transcript;
        }
        if (interim && onPartial) onPartial(interim);
        if (final_) onTranscript(final_.trim());
      };
      r.onerror = () => {
        setListening(false);
      };
      r.onend = () => setListening(false);
      recRef.current = r;
    }
    return () => {
      try { recRef.current?.abort(); } catch { /* ignore */ }
    };
  }, [lang, onTranscript, onPartial]);

  const toggle = () => {
    const r = recRef.current;
    if (!r) return;
    if (listening) {
      try { r.stop(); } catch { /* ignore */ }
      setListening(false);
    } else {
      try {
        r.lang = LANG_TO_BCP47[lang] || "en-IN";
        r.start();
        setListening(true);
      } catch {
        setListening(false);
      }
    }
  };

  if (supported === false) {
    return (
      <Tooltip delayDuration={150}>
        <TooltipTrigger asChild>
          <Button type="button" size="icon" variant="ghost" disabled aria-label={t("voice.unsupported")}>
            <MicOff className="h-5 w-5" aria-hidden />
          </Button>
        </TooltipTrigger>
        <TooltipContent>{t("voice.unsupported")}</TooltipContent>
      </Tooltip>
    );
  }

  return (
    <Tooltip delayDuration={150}>
      <TooltipTrigger asChild>
        <Button
          type="button"
          size="icon"
          variant={listening ? "destructive" : "ghost"}
          onClick={toggle}
          disabled={disabled || supported === null}
          aria-pressed={listening}
          aria-label={listening ? t("voice.stop") : t("voice.start")}
        >
          <Mic className="h-5 w-5" aria-hidden />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{listening ? t("voice.listening") : t("voice.start")}</TooltipContent>
    </Tooltip>
  );
}
