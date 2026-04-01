import { startTransition, useEffect, useRef, useState } from "react";

import { WorkspaceSection } from "@/components/layout/WorkspaceSection";
import { Badge } from "@/components/primitives/Badge";
import { Button } from "@/components/primitives/Button";
import { Text } from "@/components/primitives/Text";
import type { JiraStory, PhaseResponse } from "@/lib/api/contracts";

import {
  NEGOTIATION_PHASES,
  extractPhaseSummary,
  type SessionStateLabel,
} from "./workspaceLayout";
import styles from "./WorkspacePreview.module.css";

type WorkspacePreviewProps = {
  story: JiraStory;
  phase: PhaseResponse;
  sessionStateLabel: SessionStateLabel;
};

type CenterView = "phase-review" | "traceability" | "execution";

const VIEW_CONTENT: Record<
  CenterView,
  {
    title: string;
    description: string;
    note: string;
    bullets: string[];
  }
> = {
  "phase-review": {
    title: "Phase review workspace",
    description:
      "Negotiation content stays in the center surface while the operator keeps phase state and the current story in view.",
    note: "This is the primary review surface for the active phase.",
    bullets: [
      "Acceptance criteria stay anchored to the active story without route changes.",
      "Clarifying feedback returns to the same phase instead of jumping to a new screen.",
      "The phase rail remains visible while long review content scrolls below it.",
    ],
  },
  traceability: {
    title: "Traceability workspace",
    description:
      "Trace links, contract refs, and artifact summaries replace the center surface in place so the operator never loses story context.",
    note: "Evidence review happens in this same route context.",
    bullets: [
      "Requirement coverage stays connected to the active phase and story metadata.",
      "Inspectors can change independently without resetting the main work surface.",
      "Operators can return to negotiation without rebuilding context from scratch.",
    ],
  },
  execution: {
    title: "Execution workspace",
    description:
      "Verification controls and live pipeline output occupy the dominant pane when the operator shifts from review into proof of correctness.",
    note: "The layout favors the center console when execution is active.",
    bullets: [
      "Execution status remains visible even when intake and evidence panes are collapsed.",
      "Results, verdicts, and follow-up work stay within the same operator shell.",
      "The shell preserves the session rail and story context around the console.",
    ],
  },
};

function resolvePhaseState(phase: PhaseResponse, phaseNumber: number) {
  if (phase.done || phase.phaseNumber > phaseNumber) {
    return "complete";
  }

  if (phase.phaseNumber === phaseNumber) {
    return "active";
  }

  return "pending";
}

export function WorkspacePreview({ story, phase, sessionStateLabel }: WorkspacePreviewProps) {
  const [activeView, setActiveView] = useState<CenterView>("phase-review");
  const regionRef = useRef<HTMLElement>(null);
  const activeContent = VIEW_CONTENT[activeView];

  useEffect(() => {
    regionRef.current?.focus();
  }, [activeView]);

  function handleViewChange(nextView: CenterView) {
    startTransition(() => {
      setActiveView(nextView);
    });
  }

  return (
    <div className={styles.surface}>
      <div className={styles.stickyHeader}>
        <div className={styles.statusStrip}>
          <div className={styles.statusMeta}>
            <span className={styles.label}>Session status</span>
            <div className={styles.statusRow}>
              <Badge>{sessionStateLabel}</Badge>
              <Badge tone="muted">{story.status}</Badge>
            </div>
          </div>
          <div className={styles.phaseSummary}>
            <span className={styles.label}>Active phase</span>
            <Text className={styles.phaseSummaryText}>{extractPhaseSummary(phase.phaseTitle)}</Text>
          </div>
        </div>
        <nav className={styles.phaseRail} aria-label="Session phases">
          <ol className={styles.phaseList}>
            {NEGOTIATION_PHASES.map((phaseItem, index) => {
              const phaseNumber = index + 1;
              const state = resolvePhaseState(phase, phaseNumber);

              return (
                <li
                  key={phaseItem.id}
                  aria-current={state === "active" ? "step" : undefined}
                  aria-label={`Phase ${phaseNumber} ${phaseItem.label} ${state}`}
                  className={styles.phaseItem}
                  data-state={state}
                >
                  <span className={styles.phaseToken}>{phaseItem.shortLabel}</span>
                  <span className={styles.phaseCopy}>
                    <strong>{phaseItem.label}</strong>
                    <span>{state}</span>
                  </span>
                </li>
              );
            })}
          </ol>
        </nav>
        <div className={styles.viewBar}>
          <div className={styles.viewMeta}>
            <span className={styles.label}>Workspace view</span>
            <Text tone="muted">
              Center and inspector surfaces update in place so the operator keeps route and session
              context stable.
            </Text>
          </div>
          <div className={styles.actions}>
            <Button
              variant={activeView === "phase-review" ? "primary" : "ghost"}
              aria-pressed={activeView === "phase-review"}
              onClick={() => handleViewChange("phase-review")}
            >
              Phase review
            </Button>
            <Button
              variant={activeView === "traceability" ? "primary" : "ghost"}
              aria-pressed={activeView === "traceability"}
              onClick={() => handleViewChange("traceability")}
            >
              Traceability view
            </Button>
            <Button
              variant={activeView === "execution" ? "primary" : "ghost"}
              aria-pressed={activeView === "execution"}
              onClick={() => handleViewChange("execution")}
            >
              Execution console
            </Button>
          </div>
        </div>
      </div>
      <WorkspaceSection>
        <section
          ref={regionRef}
          tabIndex={-1}
          aria-label={activeContent.title}
          className={styles.region}
          data-view={activeView}
        >
          <div className={styles.regionHeader}>
            <div>
              <span className={styles.label}>Primary surface</span>
              <h2 className={styles.regionTitle}>{activeContent.title}</h2>
            </div>
            <Badge tone="muted">{story.key}</Badge>
          </div>
          <Text>{activeContent.description}</Text>
          <Text tone="muted">{activeContent.note}</Text>
          <ul className={styles.bullets}>
            {activeContent.bullets.map((bullet) => (
              <li key={bullet} className={styles.bulletItem}>
                {bullet}
              </li>
            ))}
          </ul>
        </section>
      </WorkspaceSection>
    </div>
  );
}
