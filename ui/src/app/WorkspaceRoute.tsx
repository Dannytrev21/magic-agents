import { useEffect, useState } from "react";

import { AppShell } from "@/app/AppShell";
import { Button } from "@/components/primitives/Button";
import { InspectorPreview } from "@/features/inspector/InspectorPreview";
import { StoryIntakeRail } from "@/features/intake/StoryIntakeRail";
import { WorkspacePreview } from "@/features/workspace/WorkspacePreview";
import {
  WORKSPACE_COMPACT_BREAKPOINT,
  DEFAULT_PANEL_VISIBILITY,
  deriveSessionStateLabel,
  normalizePhaseState,
  readPanelVisibility,
  writePanelVisibility,
} from "@/features/workspace/workspaceLayout";
import type { JiraStory, PhaseResponse } from "@/lib/api/contracts";

const DEFAULT_STORY: JiraStory = {
  key: "WORKSPACE",
  summary: "Operator shell foundation",
  status: "Ready",
};

const DEFAULT_PHASE: PhaseResponse = normalizePhaseState({
  done: false,
  sessionId: null,
  phaseTitle: "Phase 1 of 7: Interface & Actor Discovery",
  phaseNumber: 1,
  totalPhases: 7,
  results: [],
  questions: [],
  revised: false,
});

type OverlayPanel = "left" | "right" | null;

function isCompactViewport() {
  if (typeof window === "undefined") {
    return false;
  }

  return window.innerWidth <= WORKSPACE_COMPACT_BREAKPOINT;
}

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage;
}

export function WorkspaceRoute() {
  const [selectedStory, setSelectedStory] = useState<JiraStory>(DEFAULT_STORY);
  const [phaseState, setPhaseState] = useState<PhaseResponse>(DEFAULT_PHASE);
  const [panelVisibility, setPanelVisibility] = useState(() => {
    return readPanelVisibility(getStorage());
  });
  const [isCompact, setIsCompact] = useState(() => isCompactViewport());
  const [overlayPanel, setOverlayPanel] = useState<OverlayPanel>(null);

  useEffect(() => {
    function handleResize() {
      setIsCompact(isCompactViewport());
    }

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  useEffect(() => {
    writePanelVisibility(getStorage(), panelVisibility);
  }, [panelVisibility]);

  useEffect(() => {
    if (!isCompact) {
      setOverlayPanel(null);
    }
  }, [isCompact]);

  function handleSessionStarted(response: PhaseResponse) {
    setPhaseState(normalizePhaseState(response));
  }

  function togglePanel(panel: Exclude<OverlayPanel, null>) {
    if (isCompact) {
      setOverlayPanel((current) => (current === panel ? null : panel));
      return;
    }

    setPanelVisibility((current) => {
      if (panel === "left") {
        return { ...current, leftCollapsed: !current.leftCollapsed };
      }

      return { ...current, rightCollapsed: !current.rightCollapsed };
    });
  }

  const sessionStateLabel = deriveSessionStateLabel(phaseState);
  const safePanelVisibility = panelVisibility ?? DEFAULT_PANEL_VISIBILITY;

  const controls = (
    <>
      <Button variant="ghost" onClick={() => togglePanel("left")}>
        {isCompact
          ? overlayPanel === "left"
            ? "Close story intake panel"
            : "Open story intake panel"
          : safePanelVisibility.leftCollapsed
            ? "Show story intake panel"
            : "Hide story intake panel"}
      </Button>
      <Button variant="ghost" onClick={() => togglePanel("right")}>
        {isCompact
          ? overlayPanel === "right"
            ? "Close inspector panel"
            : "Open inspector panel"
          : safePanelVisibility.rightCollapsed
            ? "Show inspector panel"
            : "Hide inspector panel"}
      </Button>
    </>
  );

  return (
    <AppShell
      storyKey={selectedStory.key}
      storySummary={selectedStory.summary}
      phaseLabel={phaseState.phaseTitle}
      sessionStateLabel={sessionStateLabel}
      controls={controls}
      leftPane={
        <StoryIntakeRail
          selectedStoryKey={selectedStory.key}
          onStorySelected={setSelectedStory}
          onSessionStarted={handleSessionStarted}
        />
      }
      centerPane={
        <WorkspacePreview
          story={selectedStory}
          phase={phaseState}
          sessionStateLabel={sessionStateLabel}
        />
      }
      rightPane={<InspectorPreview />}
      isCompact={isCompact}
      isLeftPaneCollapsed={safePanelVisibility.leftCollapsed}
      isRightPaneCollapsed={safePanelVisibility.rightCollapsed}
      isLeftOverlayOpen={overlayPanel === "left"}
      isRightOverlayOpen={overlayPanel === "right"}
      onDismissLeftOverlay={() => setOverlayPanel((current) => (current === "left" ? null : current))}
      onDismissRightOverlay={() =>
        setOverlayPanel((current) => (current === "right" ? null : current))
      }
    />
  );
}
