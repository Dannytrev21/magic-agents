import type { PropsWithChildren } from "react";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { WorkspaceApi } from "@/lib/api/contracts";

import { WORKSPACE_QUERY_KEYS, useJiraStoriesQuery, useStartSessionMutation } from "./hooks";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }

  return { queryClient, wrapper: Wrapper };
}

describe("workspace hooks", () => {
  it("exposes stories through a query hook", async () => {
    const api: WorkspaceApi = {
      getJiraConfigured: vi.fn(),
      getJiraStories: vi.fn().mockResolvedValue([
        { key: "DEV-17", summary: "Budget guardrails", status: "In Progress" },
      ]),
      getJiraTicket: vi.fn(),
      startSession: vi.fn(),
      respondToSession: vi.fn(),
      compileSpec: vi.fn(),
      generateTests: vi.fn(),
      updateJira: vi.fn(),
    };
    const { wrapper } = createWrapper();

    const { result } = renderHook(() => useJiraStoriesQuery(api), { wrapper });

    expect(result.current.isPending).toBe(true);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.[0]?.key).toBe("DEV-17");
  });

  it("surfaces query failures cleanly", async () => {
    const api: WorkspaceApi = {
      getJiraConfigured: vi.fn(),
      getJiraStories: vi
        .fn()
        .mockRejectedValue(new ApiError("Unable to load stories", 503, { error: "offline" })),
      getJiraTicket: vi.fn(),
      startSession: vi.fn(),
      respondToSession: vi.fn(),
      compileSpec: vi.fn(),
      generateTests: vi.fn(),
      updateJira: vi.fn(),
    };
    const { wrapper } = createWrapper();

    const { result } = renderHook(() => useJiraStoriesQuery(api), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
  });

  it("invalidates story intake queries after a session starts", async () => {
    const api: WorkspaceApi = {
      getJiraConfigured: vi.fn(),
      getJiraStories: vi.fn(),
      getJiraTicket: vi.fn(),
      startSession: vi.fn().mockResolvedValue({
        done: false,
        sessionId: "session-17",
        phaseNumber: 1,
        totalPhases: 4,
        phaseTitle: "Phase 1",
        results: [],
        questions: [],
        revised: false,
      }),
      respondToSession: vi.fn(),
      compileSpec: vi.fn(),
      generateTests: vi.fn(),
      updateJira: vi.fn(),
    };
    const { queryClient, wrapper } = createWrapper();
    const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useStartSessionMutation(api), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        jiraKey: "DEV-17",
        jiraSummary: "Budget guardrails",
        acceptanceCriteria: [{ index: 0, text: "AC", checked: false }],
      });
    });

    expect(api.startSession).toHaveBeenCalledWith({
      jiraKey: "DEV-17",
      jiraSummary: "Budget guardrails",
      acceptanceCriteria: [{ index: 0, text: "AC", checked: false }],
    });
    expect(invalidateQueries).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: WORKSPACE_QUERY_KEYS.jiraStories(),
      }),
    );
  });
});
