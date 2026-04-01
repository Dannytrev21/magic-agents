import { startTransition, useState } from "react";

import { WorkspaceSection } from "@/components/layout/WorkspaceSection";
import { Badge } from "@/components/primitives/Badge";
import { Button } from "@/components/primitives/Button";
import { Divider } from "@/components/primitives/Divider";
import { SectionHeader } from "@/components/primitives/SectionHeader";
import { Text } from "@/components/primitives/Text";

import styles from "./WorkspacePreview.module.css";

type WorkspacePreviewProps = {
  storyLabel: string;
  phaseLabel: string;
};

type ViewMode = "overview" | "handoff";

const CHECKLIST_ITEMS = [
  {
    label: "Provider stack",
    summary: "Query, router, and theme providers are mounted once at the shell boundary.",
  },
  {
    label: "Layout primitives",
    summary: "Rails, sections, and artifact panels compose the shell without card sprawl.",
  },
  {
    label: "React ownership",
    summary: "Top-level view state swaps use startTransition instead of DOM mutation.",
  },
];

export function WorkspacePreview({ storyLabel, phaseLabel }: WorkspacePreviewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("overview");

  function handleViewMode(mode: ViewMode) {
    startTransition(() => {
      setViewMode(mode);
    });
  }

  return (
    <div className={styles.surface}>
      <WorkspaceSection>
        <div className={styles.toolbar}>
          <SectionHeader
            eyebrow="Active shell"
            title="Operator workspace"
            description="The shell stays stable while intake, negotiation, and evidence surfaces swap inside it."
          />
          <div className={styles.actions}>
            <Button
              variant={viewMode === "overview" ? "primary" : "ghost"}
              onClick={() => handleViewMode("overview")}
            >
              Overview
            </Button>
            <Button
              variant={viewMode === "handoff" ? "primary" : "ghost"}
              onClick={() => handleViewMode("handoff")}
            >
              Handoff
            </Button>
          </div>
        </div>
        <Divider />
        <div className={styles.grid}>
          <Badge>{storyLabel}</Badge>
          <Text tone="muted">
            {viewMode === "overview"
              ? `Phase context: ${phaseLabel}. The shell currently hosts a placeholder three-pane workspace while feature surfaces are ported over.`
              : "The handoff view keeps artifact ownership, routes, and bundle serving explicit before richer workflows arrive."}
          </Text>
        </div>
      </WorkspaceSection>
      <WorkspaceSection>
        <SectionHeader
          eyebrow="Foundation status"
          title="Checklist"
          description="This is the bridge from the legacy single-file UI to the operator workspace."
        />
        <div className={styles.checklist}>
          {CHECKLIST_ITEMS.map((item) => (
            <div key={item.label} className={styles.item}>
              <span className={styles.status}>Ready for extension</span>
              <strong>{item.label}</strong>
              <Text tone="muted">{item.summary}</Text>
            </div>
          ))}
        </div>
      </WorkspaceSection>
    </div>
  );
}
