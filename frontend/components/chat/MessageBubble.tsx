"use client";
import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import {
  VoterRecordCard,
  type VoterRecordPayload,
} from "@/components/cards/VoterRecordCard";
import { BoothCard, type BoothCardPayload } from "@/components/cards/BoothCard";
import { FormPdfCard, type FormPdfPayload } from "@/components/cards/FormPdfCard";
import { StoryCard, type StoryCardPayload } from "@/components/cards/StoryCard";

export type Markers = {
  voter_record?: VoterRecordPayload;
  booth_card?: BoothCardPayload;
  pdf_ready?: FormPdfPayload;
  story?: StoryCardPayload;
};

export interface BubbleProps {
  role: "user" | "assistant";
  text: string;
  /** Set on the streaming assistant bubble while delta events arrive. */
  streaming?: boolean;
  /** Parsed structured markers from the `final` SSE event. */
  markers?: Markers;
}

export function MessageBubble({ role, text, streaming, markers }: BubbleProps) {
  const isUser = role === "user";
  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-3 text-sm md:max-w-[80%]",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-secondary-foreground",
        )}
      >
        {text && (
          <div className="prose prose-sm dark:prose-invert max-w-none [&_a]:text-primary [&_a]:underline">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        )}
        {streaming && (
          <div className="mt-1 flex gap-1" aria-label="thinking">
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current opacity-40" />
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current opacity-40" style={{ animationDelay: "0.2s" }} />
            <span className="h-1.5 w-1.5 animate-pulseDot rounded-full bg-current opacity-40" style={{ animationDelay: "0.4s" }} />
          </div>
        )}
        {markers?.voter_record && <VoterRecordCard payload={markers.voter_record} />}
        {markers?.booth_card && <BoothCard payload={markers.booth_card} />}
        {markers?.pdf_ready && <FormPdfCard payload={markers.pdf_ready} />}
        {markers?.story && <StoryCard payload={markers.story} narrative={text} />}
      </div>
    </div>
  );
}
