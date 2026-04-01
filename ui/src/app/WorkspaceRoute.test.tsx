import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { WorkspaceRoute } from "@/app/WorkspaceRoute";
import type { PhaseResponse } from "@/lib/api/contracts";

const STARTED_PHASE: PhaseResponse = {
  done: false,
  sessionId: "session-17",
  phaseTitle: "Phase 2 of 7: Happy Path Contract",
  phaseNumber: 2,
  totalPhases: 7,
  results: [],
  questions: [],
  revised: false,
};

const stories = [
  { key: "DEV-17", summary: "Budget guardrails", status: "In Progress" },
  { key: "DEV-42", summary: "Traceability export", status: "Ready" },
];

const hooksMock = vi.hoisted(() => ({
  useJiraConfiguredQuery: vi.fn(),
  useJiraStoriesQuery: vi.fn(),
  useStartSessionMutation: vi.fn(),
}));

vi.mock("@/features/intake/hooks", () => hooksMock);

const storageState = new Map<string, string>();

const localStorageMock = {
  getItem(key: string) {
    return storageState.get(key) ?? null;
  },
  setItem(key: string, value: string) {
    storageState.set(key, value);
  },
  removeItem(key: string) {
    storageState.delete(key);
  },
  clear() {
    storageState.clear();
  },
};

function resizeViewport(width: number) {
  act(() => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: width,
    });
    window.dispatchEvent(new Event("resize"));
  });
}

describe("WorkspaceRoute", () => {
  beforeEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: localStorageMock,
    });
    localStorage.clear();
    resizeViewport(1440);

    hooksMock.useJiraConfiguredQuery.mockReturnValue({ data: true });
    hooksMock.useJiraStoriesQuery.mockReturnValue({
      data: stories,
      isPending: false,
      isError: false,
    });
    hooksMock.useStartSessionMutation.mockReturnValue({
      isPending: false,
      mutate: (
        _request: unknown,
        options?: {
          onSuccess?: (response: PhaseResponse) => void;
        },
      ) => {
        options?.onSuccess?.(STARTED_PHASE);
      },
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders a three-pane workspace with sticky session context and a seven-phase rail", async () => {
    const user = userEvent.setup();

    render(<WorkspaceRoute />);

    await user.click(screen.getByRole("button", { name: /dev-17/i }));
    await user.click(screen.getByRole("button", { name: /start demo session/i }));

    expect(screen.getByRole("heading", { name: /operator workspace/i })).toBeInTheDocument();
    expect(screen.getByText("Magic Agents")).toBeInTheDocument();
    expect(screen.getAllByText("DEV-17").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/budget guardrails/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("complementary", { name: /story intake/i })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: /evidence inspector/i })).toBeInTheDocument();

    const phaseRail = screen.getByRole("navigation", { name: /session phases/i });
    expect(phaseRail).toBeInTheDocument();
    expect(within(phaseRail).getAllByRole("listitem")).toHaveLength(7);
    expect(within(phaseRail).getByRole("listitem", { name: /phase 2 happy path contract active/i })).toHaveAttribute(
      "aria-current",
      "step",
    );
    expect(screen.getAllByText(/session status/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/running/i).length).toBeGreaterThan(0);
  });

  it("swaps workspace and inspector surfaces in place while moving focus to the active region", async () => {
    const user = userEvent.setup();

    render(<WorkspaceRoute />);

    await user.click(screen.getByRole("button", { name: /traceability view/i }));

    const traceabilityRegion = screen.getByRole("region", { name: /traceability workspace/i });
    await waitFor(() => expect(traceabilityRegion).toHaveFocus());
    expect(screen.getByRole("heading", { name: /traceability workspace/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /activity feed/i }));

    const inspectorRegion = screen.getByRole("region", { name: /activity inspector/i });
    await waitFor(() => expect(inspectorRegion).toHaveFocus());
    expect(screen.getByRole("heading", { name: /activity inspector/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /traceability workspace/i })).toBeInTheDocument();
  });

  it("persists collapsed side panes and restores them after a rerender", async () => {
    const user = userEvent.setup();

    const { unmount } = render(<WorkspaceRoute />);

    await user.click(screen.getByRole("button", { name: /hide inspector panel/i }));

    expect(screen.queryByRole("complementary", { name: /evidence inspector/i })).not.toBeInTheDocument();
    expect(localStorage.getItem("magic-agents.workspace.layout")).toContain('"rightCollapsed":true');

    unmount();
    render(<WorkspaceRoute />);

    expect(screen.getByRole("button", { name: /show inspector panel/i })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /evidence inspector/i })).not.toBeInTheDocument();
  });

  it("uses overlay panels on compact widths and restores the multi-pane shell on wider screens", async () => {
    const user = userEvent.setup();
    resizeViewport(900);

    render(<WorkspaceRoute />);

    expect(screen.queryByRole("complementary", { name: /story intake/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /evidence inspector/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open story intake panel/i }));
    expect(screen.getByRole("dialog", { name: /story intake panel/i })).toBeInTheDocument();

    resizeViewport(1440);

    await waitFor(() =>
      expect(screen.getByRole("complementary", { name: /story intake/i })).toBeInTheDocument(),
    );
    expect(screen.getByRole("complementary", { name: /evidence inspector/i })).toBeInTheDocument();
  });
});
