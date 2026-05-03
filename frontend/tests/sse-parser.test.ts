import { describe, expect, test } from "vitest";
import { parseFrame } from "@/lib/sse-consumer";

describe("parseFrame", () => {
  test("parses event + JSON data", () => {
    const ev = parseFrame('event: lang_detect\ndata: {"language":"hi"}');
    expect(ev?.event).toBe("lang_detect");
    expect(ev?.data).toEqual({ language: "hi" });
  });

  test("multi-line data lines are joined with \\n", () => {
    const ev = parseFrame('event: final\ndata: {"text":"line1\\nline2"}');
    expect(ev?.event).toBe("final");
    expect((ev?.data as { text: string }).text).toBe("line1\nline2");
  });

  test("comment-only frame returns null", () => {
    const ev = parseFrame(": ping - heartbeat");
    expect(ev).toBeNull();
  });

  test("falls back to message event when only data given", () => {
    const ev = parseFrame('data: {"hello":1}');
    expect(ev?.event).toBe("message");
    expect(ev?.data).toEqual({ hello: 1 });
  });
});
