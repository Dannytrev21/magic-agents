import { useState } from "react";

import { AppShell } from "@/app/AppShell";
import { InspectorPreview } from "@/features/inspector/InspectorPreview";
import { StoryIntakeRail } from "@/features/intake/StoryIntakeRail";
import { WorkspacePreview } from "@/features/workspace/WorkspacePreview";
import type { JiraStory, PhaseResponse } from "@/lib/api/contracts";

const DEFAULT_STORY: JiraStory = {
  key: "WORKSPACE",
  summary: "Operator shell foundation",
  status: "Ready",
};

const DEFAULT_PHASE: PhaseResponse = {
  done: false,
  sessionId: null,
  phaseTitle: "Foundation",
  phaseNumber: 1,
  totalPhases: 4,
  results: [],
  questions: [],
  revised: false,
};

export function WorkspaceRoute() {
  const [selectedStory, setSelectedStory] = useState<JiraStory>(DEFAULT_STORY);
  const [phaseState, setPhaseState] = useState<PhaseResponse>(DEFAULT_PHASE);

  return (
    <AppShell
      sessionLabel={selectedStory.key}
      phaseLabel={phaseState.phaseTitle}
      leftRail={
        <StoryIntakeRail
          selectedStoryKey={selectedStory.key}
          onStorySelected={setSelectedStory}
          onSessionStarted={setPhaseState}
        />
      }
      centerPane={
        <WorkspacePreview
          storyLabel={selectedStory.summary}
          phaseLabel={`${phaseState.phaseTitle} (${phaseState.phaseNumber}/${phaseState.totalPhases})`}
        />
      }
      rightPane={<InspectorPreview />}
    />
  );
}
