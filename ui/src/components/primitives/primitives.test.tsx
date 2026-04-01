import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Button } from "@/components/primitives/Button";
import { EmptyState } from "@/components/primitives/EmptyState";
import { MonoText } from "@/components/primitives/MonoText";

describe("workspace primitives", () => {
  it("renders loading buttons as busy and disabled", () => {
    render(<Button isLoading>Start session</Button>);

    const button = screen.getByRole("button", { name: /start session/i });

    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });

  it("renders mono content with code semantics", () => {
    render(<MonoText>/specs/DEV-17.yaml</MonoText>);

    expect(screen.getByText("/specs/DEV-17.yaml").tagName).toBe("CODE");
  });

  it("renders empty states without bespoke card wrappers", () => {
    render(
      <EmptyState
        title="No session selected"
        description="Start a session from the left rail to populate the workspace."
      />,
    );

    expect(screen.getByRole("heading", { name: /no session selected/i })).toBeInTheDocument();
    expect(
      screen.getByText(/start a session from the left rail to populate the workspace/i),
    ).toBeInTheDocument();
  });
});
