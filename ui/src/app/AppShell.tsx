import type { ReactNode } from "react";

import { Badge } from "@/components/primitives/Badge";
import { Button } from "@/components/primitives/Button";
import { MonoText } from "@/components/primitives/MonoText";
import { extractPhaseSummary, type SessionStateLabel } from "@/features/workspace/workspaceLayout";

import styles from "@/app/AppShell.module.css";

type AppShellProps = {
  storyKey: string;
  storySummary: string;
  phaseLabel: string;
  sessionStateLabel: SessionStateLabel;
  controls: ReactNode;
  leftPane: ReactNode;
  centerPane: ReactNode;
  rightPane: ReactNode;
  isCompact: boolean;
  isLeftPaneCollapsed: boolean;
  isRightPaneCollapsed: boolean;
  isLeftOverlayOpen: boolean;
  isRightOverlayOpen: boolean;
  onDismissLeftOverlay: () => void;
  onDismissRightOverlay: () => void;
};

function resolveDesktopLayout(
  isLeftPaneCollapsed: boolean,
  isRightPaneCollapsed: boolean,
): "full" | "left-collapsed" | "right-collapsed" | "center-only" {
  if (isLeftPaneCollapsed && isRightPaneCollapsed) {
    return "center-only";
  }

  if (isLeftPaneCollapsed) {
    return "left-collapsed";
  }

  if (isRightPaneCollapsed) {
    return "right-collapsed";
  }

  return "full";
}

type CompactPanelProps = {
  title: string;
  isOpen: boolean;
  onDismiss: () => void;
  children: ReactNode;
};

function CompactPanel({ title, isOpen, onDismiss, children }: CompactPanelProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.overlay}>
      <button
        type="button"
        aria-label={`Close ${title.toLowerCase()} panel`}
        className={styles.overlayBackdrop}
        onClick={onDismiss}
      />
      <div className={styles.overlayDrawer} role="dialog" aria-modal="true" aria-label={`${title} panel`}>
        <div className={styles.overlayHeader}>
          <div>
            <span className={styles.overlayLabel}>Panel</span>
            <strong className={styles.overlayTitle}>{title}</strong>
          </div>
          <Button variant="ghost" onClick={onDismiss}>
            Close
          </Button>
        </div>
        <div className={styles.overlayBody}>{children}</div>
      </div>
    </div>
  );
}

export function AppShell({
  storyKey,
  storySummary,
  phaseLabel,
  sessionStateLabel,
  controls,
  leftPane,
  centerPane,
  rightPane,
  isCompact,
  isLeftPaneCollapsed,
  isRightPaneCollapsed,
  isLeftOverlayOpen,
  isRightOverlayOpen,
  onDismissLeftOverlay,
  onDismissRightOverlay,
}: AppShellProps) {
  const desktopLayout = resolveDesktopLayout(isLeftPaneCollapsed, isRightPaneCollapsed);
  const phaseSummary = extractPhaseSummary(phaseLabel);

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.topBar}>
          <div className={styles.identity}>
            <span className={styles.product}>Magic Agents</span>
            <h1 className={styles.heading}>Operator workspace</h1>
          </div>
          <div className={styles.context}>
            <div className={styles.story}>
              <div className={styles.storyMeta}>
                <Badge tone="muted">Current story</Badge>
                <MonoText as="span" className={styles.storyKey}>
                  {storyKey}
                </MonoText>
              </div>
              <p className={styles.storySummary}>{storySummary}</p>
            </div>
            <div className={styles.sessionCluster}>
              <div className={styles.status}>
                <Badge>{phaseSummary}</Badge>
                <Badge tone="muted">Session status</Badge>
                <Badge tone={sessionStateLabel === "Running" ? "signal" : "muted"}>
                  {sessionStateLabel}
                </Badge>
              </div>
              <div className={styles.controls}>{controls}</div>
            </div>
          </div>
        </header>
        <div
          className={styles.workspace}
          data-compact={isCompact ? "true" : "false"}
          data-layout={desktopLayout}
        >
          {!isCompact && !isLeftPaneCollapsed ? (
            <aside className={styles.sidePane} aria-label="Story intake">
              {leftPane}
            </aside>
          ) : null}
          <main className={styles.centerPane}>{centerPane}</main>
          {!isCompact && !isRightPaneCollapsed ? (
            <aside className={styles.sidePane} aria-label="Evidence inspector">
              {rightPane}
            </aside>
          ) : null}
        </div>
      </div>
      {isCompact ? (
        <>
          <CompactPanel
            title="Story intake"
            isOpen={isLeftOverlayOpen}
            onDismiss={onDismissLeftOverlay}
          >
            {leftPane}
          </CompactPanel>
          <CompactPanel
            title="Evidence inspector"
            isOpen={isRightOverlayOpen}
            onDismiss={onDismissRightOverlay}
          >
            {rightPane}
          </CompactPanel>
        </>
      ) : null}
    </div>
  );
}
