/**
 * SSE consumer for the /api/proxy/chat stream.
 *
 * `fetch()` based (NOT EventSource — we need POST). Yields each event as
 * { event, data } where data is parsed JSON. Calls `onChunk` immediately
 * for every frame so the UI renders incrementally; never buffers.
 */

export type SseEvent = { event: string; data: unknown };

export interface ChatRequestBody {
  message: string;
  session_id?: string;
  language?: string;
}

export interface StreamChatOptions {
  body: ChatRequestBody;
  onEvent: (ev: SseEvent) => void;
  signal?: AbortSignal;
}

export async function streamChat(opts: StreamChatOptions): Promise<{ sessionId: string | null }> {
  const res = await fetch("/api/proxy/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(opts.body),
    signal: opts.signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`/api/proxy/chat returned ${res.status}`);
  }

  const sessionId = res.headers.get("X-Sankalp-Session-Id");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Process every full SSE frame in the buffer.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const ev = parseFrame(frame);
      if (ev) opts.onEvent(ev);
    }
  }
  // Flush trailing frame, if any.
  if (buffer.trim()) {
    const ev = parseFrame(buffer);
    if (ev) opts.onEvent(ev);
  }

  return { sessionId };
}

export function parseFrame(raw: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (!dataLines.length) return null;
  const dataStr = dataLines.join("\n");
  let data: unknown = dataStr;
  try {
    data = JSON.parse(dataStr);
  } catch {
    /* leave as string */
  }
  return { event, data };
}
