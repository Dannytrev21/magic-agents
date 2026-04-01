import { startTransition, useEffect, useRef, useState } from "react";

import { ArtifactPanel } from "@/components/layout/ArtifactPanel";
import { Rail } from "@/components/layout/Rail";
import { Badge } from "@/components/primitives/Badge";
import { Button } from "@/components/primitives/Button";
import { Divider } from "@/components/primitives/Divider";
import { MonoText } from "@/components/primitives/MonoText";
import { Text } from "@/components/primitives/Text";

import styles from "./InspectorPreview.module.css";

type InspectorView = "evidence" | "activity";

const VIEW_COPY: Record<
  InspectorView,
  {
    title: string;
    description: string;
  }
> = {
  evidence: {
    title: "Evidence inspector",
    description:
      "Contract artifacts, trace refs, and source pointers stay available while the operator keeps the center pane focused on active work.",
  },
  activity: {
    title: "Activity inspector",
    description:
      "Session events and analyst notes can replace evidence in place without interrupting the active phase workspace.",
  },
};

export function InspectorPreview() {
  const [activeView, setActiveView] = useState<InspectorView>("evidence");
  const regionRef = useRef<HTMLElement>(null);
  const activeCopy = VIEW_COPY[activeView];

  useEffect(() => {
    regionRef.current?.focus();
  }, [activeView]);

  function handleViewChange(nextView: InspectorView) {
    startTransition(() => {
      setActiveView(nextView);
    });
  }

  return (
    <Rail
      ariaLabel="Evidence inspector"
      label="Inspector"
      title="Evidence inspector"
      description="Artifacts, traceability, and session activity stay adjacent to the dominant center pane."
    >
      <div className={styles.actions}>
        <Button
          variant={activeView === "evidence" ? "primary" : "ghost"}
          aria-pressed={activeView === "evidence"}
          onClick={() => handleViewChange("evidence")}
        >
          Evidence surface
        </Button>
        <Button
          variant={activeView === "activity" ? "primary" : "ghost"}
          aria-pressed={activeView === "activity"}
          onClick={() => handleViewChange("activity")}
        >
          Activity feed
        </Button>
      </div>
      <section
        ref={regionRef}
        tabIndex={-1}
        aria-label={activeCopy.title}
        className={styles.region}
        data-view={activeView}
      >
        <div className={styles.regionHeader}>
          <div>
            <span className={styles.label}>Inspector view</span>
            <h3 className={styles.title}>{activeCopy.title}</h3>
          </div>
          <Badge tone="muted">{activeView === "evidence" ? "Artifacts" : "Activity"}</Badge>
        </div>
        <Text tone="muted">{activeCopy.description}</Text>
      </section>
      <Divider />
      {activeView === "evidence" ? (
        <>
          <ArtifactPanel title={<Badge tone="muted">Contract surface</Badge>}>
            <Text tone="muted">
              Typed API adapters own the backend boundary, so presentational components never build
              routes by hand.
            </Text>
          </ArtifactPanel>
          <ArtifactPanel title="Spec reference">
            <MonoText>/specs/DEV-17.yaml</MonoText>
            <Text tone="muted">
              Mono treatment is reserved for IDs, refs, paths, and code-like content.
            </Text>
          </ArtifactPanel>
        </>
      ) : (
        <ArtifactPanel title="Session activity">
          <div className={styles.activityFeed}>
            <div className={styles.activityItem}>
              <strong>Phase advanced</strong>
              <Text tone="muted">The session remains inside the same workspace route context.</Text>
            </div>
            <div className={styles.activityItem}>
              <strong>Inspector swapped</strong>
              <Text tone="muted">
                Focus moves intentionally to the newly active inspector content.
              </Text>
            </div>
          </div>
        </ArtifactPanel>
      )}
    </Rail>
  );
}
