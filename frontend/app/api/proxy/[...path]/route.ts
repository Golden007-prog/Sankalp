/**
 * Generic proxy to the FastAPI backend that preserves SSE streaming.
 *
 * Next.js route handlers can't natively stream a fetch() response — we
 * have to wrap it in a `ReadableStream` and pump chunks via
 * `controller.enqueue`. Without this, Next buffers the response until
 * the upstream closes, breaking the live-token UX.
 *
 * Forwards:
 *   - request body (JSON or FormData)
 *   - relevant request headers (Content-Type, Accept, X-Sankalp-Session-Id)
 *   - response headers (X-Sankalp-Session-Id, X-Request-Id)
 */
import { NextRequest } from "next/server";
import { BACKEND_URL } from "@/lib/config";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const FORWARDED_REQUEST_HEADERS = ["content-type", "accept", "x-sankalp-session-id", "x-request-id"];
const FORWARDED_RESPONSE_HEADERS = ["x-sankalp-session-id", "x-request-id"];

async function proxy(req: NextRequest, ctx: { params: { path: string[] } }) {
  const upstreamPath = ctx.params.path?.join("/") || "";
  const url = `${BACKEND_URL}/api/${upstreamPath}${req.nextUrl.search || ""}`;

  const headers = new Headers();
  for (const h of FORWARDED_REQUEST_HEADERS) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }

  const init: RequestInit = {
    method: req.method,
    headers,
    // Body is undefined for GET/HEAD; otherwise pass-through.
    body: req.method === "GET" || req.method === "HEAD" ? undefined : req.body,
    // @ts-expect-error — duplex is required when streaming the request body in Node.
    duplex: "half",
    cache: "no-store",
  };

  let upstream: Response;
  try {
    upstream = await fetch(url, init);
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: String(e) }), {
      status: 502,
      headers: { "Content-Type": "application/json" },
    });
  }

  const respHeaders = new Headers();
  upstream.headers.forEach((v, k) => {
    if (
      FORWARDED_RESPONSE_HEADERS.includes(k.toLowerCase()) ||
      k.toLowerCase() === "content-type" ||
      k.toLowerCase() === "cache-control"
    ) {
      respHeaders.set(k, v);
    }
  });
  // SSE-friendly hints; no-op for JSON responses.
  respHeaders.set("X-Accel-Buffering", "no");

  if (!upstream.body) {
    const text = await upstream.text();
    return new Response(text, { status: upstream.status, headers: respHeaders });
  }

  // Pipe the body through manually so chunks flush to the client immediately.
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const reader = upstream.body!.getReader();
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          if (value) controller.enqueue(value);
        }
      } catch (e) {
        controller.error(e);
        return;
      }
      controller.close();
    },
    cancel() {
      upstream.body?.cancel().catch(() => {});
    },
  });

  return new Response(stream, { status: upstream.status, headers: respHeaders });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
