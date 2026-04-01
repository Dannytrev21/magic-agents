import { describe, expect, it, vi } from "vitest";

import { ApiError, jsonRequest } from "@/lib/api/client";
import { createEventStream } from "@/lib/api/sse";

describe("jsonRequest", () => {
  it("adds JSON headers and parses JSON payloads", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ stories: [{ key: "DEV-17" }] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const response = await jsonRequest<{ stories: Array<{ key: string }> }>(
      "/api/jira/stories",
      { fetchImpl },
    );

    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/jira/stories",
      expect.objectContaining({
        headers: expect.objectContaining({
          Accept: "application/json",
        }),
      }),
    );
    expect(response.stories[0]?.key).toBe("DEV-17");
  });

  it("raises ApiError for non-ok responses", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ error: "No active session" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await expect(
      jsonRequest("/api/start", {
        method: "POST",
        body: { jira_key: "DEV-17" },
        fetchImpl,
      }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});

describe("createEventStream", () => {
  it("wraps typed event subscriptions and cleanup", () => {
    class FakeEventSource {
      addEventListener = vi.fn();
      close = vi.fn();

      constructor(public readonly url: string) {}
    }

    const stream = createEventStream("/api/events/session-1", {
      EventSourceImpl: FakeEventSource as unknown as typeof EventSource,
    });
    const listener = vi.fn();

    stream.subscribe("phase_progress", listener);
    stream.close();

    expect(stream.eventSource.url).toBe("/api/events/session-1");
    expect(stream.eventSource.addEventListener).toHaveBeenCalledWith(
      "phase_progress",
      listener,
    );
    expect(stream.eventSource.close).toHaveBeenCalled();
  });
});
