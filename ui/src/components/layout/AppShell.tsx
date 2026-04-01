import type { CSSProperties, ReactNode } from 'react';
import styles from '@/components/layout/AppShell.module.css';
import { Button } from '@/components/primitives/Button';
import { Mono } from '@/components/primitives/Mono';
import { Text } from '@/components/primitives/Text';
import type {
  WorkspaceLayoutMode,
  WorkspacePaneId,
  WorkspaceSessionState,
} from '@/features/workspace/workspaceModel';

type AppShellProps = {
  leftRail: ReactNode;
  centerPane: ReactNode;
  rightRail: ReactNode;
  layoutMode: WorkspaceLayoutMode;
  leftPaneCollapsed: boolean;
  rightPaneCollapsed: boolean;
  mobilePane: WorkspacePaneId;
  onMobilePaneChange: (pane: WorkspacePaneId) => void;
  onToggleLeftPane: () => void;
  onToggleRightPane: () => void;
  phaseLabel: string;
  sessionState: WorkspaceSessionState;
  statusLabel: string;
  storyKey?: string | null;
  storySummary?: string | null;
  workspaceLabel: string;
};

export function AppShell({
  leftRail,
  centerPane,
  rightRail,
  layoutMode,
  leftPaneCollapsed,
  rightPaneCollapsed,
  mobilePane,
  onMobilePaneChange,
  onToggleLeftPane,
  onToggleRightPane,
  phaseLabel,
  sessionState,
  statusLabel,
  storyKey,
  storySummary,
  workspaceLabel,
}: AppShellProps) {
  const gridStyle = {
    '--workspace-left-width':
      layoutMode === 'desktop' && !leftPaneCollapsed
        ? '18rem'
        : layoutMode === 'tablet' && !leftPaneCollapsed
          ? '18rem'
          : '0rem',
    '--workspace-right-width': layoutMode === 'desktop' && !rightPaneCollapsed ? '20rem' : '0rem',
  } as CSSProperties;

  const leftPaneHidden = layoutMode === 'mobile' ? mobilePane !== 'story' : leftPaneCollapsed;
  const centerPaneHidden = layoutMode === 'mobile' ? mobilePane !== 'workspace' : false;
  const rightPaneHidden =
    layoutMode === 'desktop'
      ? rightPaneCollapsed
      : layoutMode === 'mobile'
        ? mobilePane !== 'evidence'
        : true;
  const inspectorOverlayVisible = layoutMode === 'tablet' && !rightPaneCollapsed;

  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#workspace-main">
        Skip to active workspace
      </a>
      <header className={styles.topBar} data-sticky="true">
        <div className={styles.brandBlock}>
          <Text as="p" size="xs" tone="muted" className={styles.kicker}>
            Acceptance criteria to proof
          </Text>
          <div className={styles.brandName}>
            <Text as="h1" size="lg" weight="semibold">
              Magic Agents
            </Text>
            <Text as="p" size="sm" tone="muted">
              Operator workspace
            </Text>
          </div>
        </div>
        <div className={styles.contextBlock}>
          <div className={styles.metaColumn}>
            <Text as="p" size="xs" tone="muted">
              Current story
            </Text>
            <div className={styles.storyContext}>
              {storyKey ? <Mono>{storyKey}</Mono> : <Text size="sm">No active story</Text>}
              {storySummary ? (
                <Text as="p" size="sm" tone="muted" className={styles.storySummary}>
                  {storySummary}
                </Text>
              ) : null}
            </div>
          </div>
          <div className={styles.metaColumn}>
            <Text as="p" size="xs" tone="muted">
              Workspace context
            </Text>
            <Text as="p" size="sm" weight="medium" className={styles.contextLabel}>
              {workspaceLabel}
            </Text>
            <Text as="p" size="sm" tone="muted" className={styles.phaseLabel}>
              {phaseLabel}
            </Text>
          </div>
        </div>
        <div className={styles.headerMeta}>
          <div className={styles.statusPill} role="status">
            <span
              aria-hidden="true"
              className={`${styles.statusDot} ${sessionStateClassName(sessionState, styles)}`}
            />
            <Text as="span" size="sm" weight="medium">
              {statusLabel}
            </Text>
          </div>
          <div className={styles.controlGroup}>
            <Button
              aria-expanded={layoutMode === 'mobile' ? mobilePane === 'story' : !leftPaneCollapsed}
              className={styles.controlButton}
              onClick={onToggleLeftPane}
              variant="ghost"
            >
              Toggle story intake panel
            </Button>
            <Button
              aria-expanded={
                layoutMode === 'desktop'
                  ? !rightPaneCollapsed
                  : layoutMode === 'tablet'
                    ? inspectorOverlayVisible
                    : mobilePane === 'evidence'
              }
              className={styles.controlButton}
              onClick={onToggleRightPane}
              variant="ghost"
            >
              Toggle evidence panel
            </Button>
          </div>
        </div>
      </header>
      <div className={styles.workspaceFrame}>
        <div
          className={styles.workspaceGrid}
          data-layout-mode={layoutMode}
          data-testid="workspace-grid"
          style={gridStyle}
        >
          <aside
            aria-hidden={leftPaneHidden}
            aria-label="Story intake"
            className={styles.pane}
            data-pane-state={leftPaneHidden ? 'collapsed' : 'expanded'}
            data-scroll-region="independent"
            hidden={leftPaneHidden}
            role="complementary"
          >
            <div className={styles.paneSurface}>{leftRail}</div>
          </aside>
          <main
            aria-hidden={centerPaneHidden}
            className={`${styles.pane} ${styles.mainPane}`}
            data-pane-priority="primary"
            data-scroll-region="independent"
            hidden={centerPaneHidden}
            id="workspace-main"
          >
            <div className={styles.paneSurface}>{centerPane}</div>
          </main>
          <aside
            aria-hidden={rightPaneHidden}
            aria-label="Evidence inspector"
            className={`${styles.pane} ${styles.inspectorPane}`}
            data-pane-state={rightPaneHidden ? 'collapsed' : 'expanded'}
            data-scroll-region="independent"
            hidden={rightPaneHidden}
            role="complementary"
          >
            <div className={styles.paneSurface}>{rightRail}</div>
          </aside>
        </div>
        {inspectorOverlayVisible ? (
          <div className={styles.overlayFrame}>
            <aside
              aria-label="Evidence inspector"
              className={`${styles.pane} ${styles.overlayPane}`}
              data-pane-state="expanded"
              data-scroll-region="independent"
              role="complementary"
            >
              <div className={styles.paneSurface}>{rightRail}</div>
            </aside>
          </div>
        ) : null}
        {layoutMode === 'mobile' ? (
          <nav aria-label="Workspace panels" className={styles.mobileTabs} role="tablist">
            <button
              aria-selected={mobilePane === 'story'}
              className={styles.mobileTab}
              onClick={() => onMobilePaneChange('story')}
              role="tab"
              type="button"
            >
              Story panel
            </button>
            <button
              aria-selected={mobilePane === 'workspace'}
              className={styles.mobileTab}
              onClick={() => onMobilePaneChange('workspace')}
              role="tab"
              type="button"
            >
              Workspace panel
            </button>
            <button
              aria-selected={mobilePane === 'evidence'}
              className={styles.mobileTab}
              onClick={() => onMobilePaneChange('evidence')}
              role="tab"
              type="button"
            >
              Evidence panel
            </button>
          </nav>
        ) : null}
      </div>
    </div>
  );
}

function sessionStateClassName(
  sessionState: WorkspaceSessionState,
  css: Record<string, string>,
): string {
  switch (sessionState) {
    case 'active':
      return css.statusActive;
    case 'revising':
      return css.statusRevising;
    case 'complete':
      return css.statusComplete;
    default:
      return css.statusIdle;
  }
}
