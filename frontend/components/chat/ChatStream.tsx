"use client";
import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { MessageBubble, type Markers } from "@/components/chat/MessageBubble";
import { Composer } from "@/components/chat/Composer";
import { streamChat, type SseEvent } from "@/lib/sse-consumer";
import { useLang, useT } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface AssistantMessage {
  id: string;
  role: "assistant";
  text: string;
  streaming: boolean;
  markers?: Markers;
}
interface UserMessage {
  id: string;
  role: "user";
  text: string;
}
type ChatMessage = AssistantMessage | UserMessage;

interface State {
  messages: ChatMessage[];
  /** Inline stage chips for the in-flight turn (only one turn at a time). */
  stages: { label: string; tone?: "info" | "specialist" | "tool" }[];
  busy: boolean;
  sessionId: string | null;
  error: string | null;
}

type Action =
  | { type: "user_send"; id: string; text: string }
  | { type: "assistant_start"; id: string }
  | { type: "stage"; label: string; tone?: "info" | "specialist" | "tool" }
  | { type: "delta"; id: string; chunk: string }
  | { type: "final"; id: string; text: string; markers?: Markers }
  | { type: "error"; message: string }
  | { type: "session"; sessionId: string };

const initial: State = { messages: [], stages: [], busy: false, sessionId: null, error: null };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "user_send":
      return {
        ...state,
        busy: true,
        error: null,
        stages: [],
        messages: [...state.messages, { id: action.id, role: "user", text: action.text }],
      };
    case "assistant_start":
      return {
        ...state,
        messages: [
          ...state.messages,
          { id: action.id, role: "assistant", text: "", streaming: true },
        ],
      };
    case "stage":
      return { ...state, stages: [...state.stages, { label: action.label, tone: action.tone }] };
    case "delta":
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.id && m.role === "assistant"
            ? { ...m, text: m.text + action.chunk }
            : m,
        ),
      };
    case "final":
      return {
        ...state,
        busy: false,
        stages: [],
        messages: state.messages.map((m) =>
          m.id === action.id && m.role === "assistant"
            ? { ...m, text: action.text, streaming: false, markers: action.markers }
            : m,
        ),
      };
    case "session":
      return { ...state, sessionId: action.sessionId };
    case "error":
      return { ...state, busy: false, error: action.message, stages: [] };
    default:
      return state;
  }
}

function shortLabel(t: (k: string) => string, ev: SseEvent): { label: string; tone: "info" | "specialist" | "tool" } | null {
  const data = (ev.data || {}) as Record<string, unknown>;
  if (ev.event === "lang_detect") {
    const l = (data.language as string) || "?";
    return { label: `${t("chat.stage.lang_detect")}: ${l}`, tone: "info" };
  }
  if (ev.event === "routing") return { label: t("chat.stage.routing"), tone: "info" };
  if (ev.event.startsWith("specialist:")) {
    const intent = (data.intent as string) || ev.event.slice("specialist:".length);
    return { label: `${t("chat.stage.specialist")}: ${intent}`, tone: "specialist" };
  }
  if (ev.event === "tool_call") {
    const name = (data.name as string) || "tool";
    return { label: `${t("chat.stage.tool")}: ${name}`, tone: "tool" };
  }
  return null;
}

export function ChatStream() {
  const [state, dispatch] = React.useReducer(reducer, initial);
  const t = useT();
  const { lang } = useLang();
  const abortRef = React.useRef<AbortController | null>(null);

  React.useEffect(() => () => abortRef.current?.abort(), []);

  const send = React.useCallback(
    async (text: string) => {
      const userId = crypto.randomUUID();
      const assistantId = crypto.randomUUID();
      dispatch({ type: "user_send", id: userId, text });
      dispatch({ type: "assistant_start", id: assistantId });

      abortRef.current?.abort();
      abortRef.current = new AbortController();

      try {
        const { sessionId } = await streamChat({
          body: { message: text, session_id: state.sessionId ?? undefined, language: lang },
          signal: abortRef.current.signal,
          onEvent: (ev) => {
            const stage = shortLabel(t, ev);
            if (stage) dispatch({ type: "stage", ...stage });
            if (ev.event === "delta") {
              const chunk = (ev.data as { text?: string })?.text || "";
              if (chunk) dispatch({ type: "delta", id: assistantId, chunk });
            }
            if (ev.event === "final") {
              const d = (ev.data as { ok: boolean; text?: string; markers?: Markers; user_message?: string }) || {};
              if (d.ok === false) {
                dispatch({ type: "final", id: assistantId, text: d.user_message || t("error.unknown") });
              } else {
                dispatch({ type: "final", id: assistantId, text: d.text || "", markers: d.markers });
              }
            }
          },
        });
        if (sessionId && sessionId !== state.sessionId) {
          dispatch({ type: "session", sessionId });
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          dispatch({ type: "error", message: t("error.network") });
          dispatch({ type: "final", id: assistantId, text: t("error.network") });
        }
      }
    },
    [state.sessionId, lang, t],
  );

  const handleCamera = React.useCallback((epic: string | null, _raw: string) => {
    if (!epic) return;
    void send(`Verify EPIC ${epic}`);
  }, [send]);

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col gap-3 px-4 py-4">
      <div
        className="flex-1 space-y-4 overflow-y-auto"
        aria-live="polite"
        aria-busy={state.busy}
      >
        {state.messages.length === 0 && (
          <div className="rounded-xl bg-secondary px-4 py-6 text-center text-sm text-muted-foreground">
            {t("chat.empty")}
          </div>
        )}
        {state.messages.map((m) =>
          m.role === "user" ? (
            <MessageBubble key={m.id} role="user" text={m.text} />
          ) : (
            <MessageBubble
              key={m.id}
              role="assistant"
              text={m.text}
              streaming={m.streaming}
              markers={m.markers}
            />
          ),
        )}
        {state.stages.length > 0 && (
          <div className="flex flex-wrap gap-2 rounded-xl border bg-secondary/30 px-3 py-2">
            {state.stages.map((s, i) => (
              <Badge
                key={i}
                variant="outline"
                className={cn(
                  "text-[11px] uppercase tracking-wider",
                  s.tone === "specialist" && "border-blue-400 text-blue-700 dark:text-blue-300",
                  s.tone === "tool" && "border-emerald-400 text-emerald-700 dark:text-emerald-300",
                )}
              >
                {s.label}
              </Badge>
            ))}
          </div>
        )}
      </div>
      <Composer
        onSubmit={send}
        onCameraResult={handleCamera}
        sessionId={state.sessionId}
        disabled={state.busy}
      />
    </div>
  );
}
