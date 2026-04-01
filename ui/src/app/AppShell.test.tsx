import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AppErrorBoundary } from "@/app/AppErrorBoundary";
import { AppShell } from "@/app/AppShell";
import { NotFoundView } from "@/app/NotFoundView";

function Explodes(): null {
  throw new Error("boom");
}

describe("AppShell", () => {
  it("renders the stable workspace landmarks", () => {
    render(
      <AppShell
        controls={<button type="button">Hide inspector panel</button>}
        isCompact={false}
        isLeftOverlayOpen={false}
        isRightOverlayOpen={false}
        isLeftPaneCollapsed={false}
        isRightPaneCollapsed={false}
        onDismissLeftOverlay={() => undefined}
        onDismissRightOverlay={() => undefined}
        phaseLabel="Phase 2 of 7: Happy Path Contract"
        sessionStateLabel="Running"
        storyKey="DEV-17"
        storySummary="Budget guardrails"
        leftPane={<div>Story intake rail</div>}
        centerPane={<div>Workspace placeholder</div>}
        rightPane={<div>Evidence inspector</div>}
      />,
    );

    expect(screen.getByRole("heading", { name: /operator workspace/i })).toBeInTheDocument();
    expect(screen.getByText("DEV-17")).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: /story intake/i })).toHaveTextContent(
      "Story intake rail",
    );
    expect(screen.getByRole("main")).toHaveTextContent("Workspace placeholder");
    expect(
      screen.getByRole("complementary", { name: /evidence inspector/i }),
    ).toHaveTextContent("Evidence inspector");
    expect(screen.getByRole("button", { name: /hide inspector panel/i })).toBeInTheDocument();
  });

  it("renders a controlled top-level error state", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(
      <AppErrorBoundary>
        <Explodes />
      </AppErrorBoundary>,
    );

    expect(screen.getByRole("heading", { name: /workspace unavailable/i })).toBeInTheDocument();
    consoleError.mockRestore();
  });

  it("renders a route-level not found fallback", () => {
    render(
      <MemoryRouter>
        <NotFoundView />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: /route not found/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /return to workspace/i })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
