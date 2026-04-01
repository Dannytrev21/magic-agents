import { useEffect, useRef, useState, useTransition } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import { WorkspaceCenterPane } from '@/features/workspace/WorkspaceCenterPane';
import { WorkspaceInspector } from '@/features/workspace/WorkspaceInspector';
import {
  centerWorkspaceViews,
  getWorkspaceLayoutMode,
  getWorkspaceSessionState,
  getWorkspaceStatusLabel,
  parseCenterWorkspaceView,
  parseInspectorWorkspaceView,
  parseMobileWorkspacePane,
  workspacePanelStorageKey,
  type WorkspacePaneId,
} from '@/features/workspace/workspaceModel';
import type { StartNegotiationResponse } from '@/lib/api/types';

type OperatorWorkspacePageProps = {
  initialSession?: StartNegotiationResponse | null;
  initialStorySummary?: string | null;
};

type PanelPreferences = {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
};

const defaultPanelPreferences: PanelPreferences = {
  leftCollapsed: false,
  rightCollapsed: false,
};

export function OperatorWorkspacePage({
  initialSession = null,
  initialStorySummary = null,
}: OperatorWorkspacePageProps) {
  const [activeSession, setActiveSession] = useState<StartNegotiationResponse | null>(initialSession);
  const [storySummary, setStorySummary] = useState<string | null>(initialStorySummary);
  const [layoutMode, setLayoutMode] = useState(() => getWorkspaceLayoutMode(window.innerWidth));
  const [panelPreferences, setPanelPreferences] = useState<PanelPreferences>(readPanelPreferences);
  const [tabletInspectorOpen, setTabletInspectorOpen] = useState(false);
  const [isTransitionPending, startShellTransition] = useTransition();
  const [searchParams, setSearchParams] = useSearchParams();
  const centerFocusRef = useRef<HTMLElement | null>(null);
  const inspectorFocusRef = useRef<HTMLElement | null>(null);
  const hasRenderedCenterView = useRef(false);
  const hasRenderedInspectorView = useRef(false);

  const centerView = parseCenterWorkspaceView(searchParams.get('view'));
  const inspectorView = parseInspectorWorkspaceView(searchParams.get('inspector'));
  const mobilePane = parseMobileWorkspacePane(searchParams.get('pane'));
  const statusLabel = getWorkspaceStatusLabel(activeSession);
  const workspaceLabel =
    centerWorkspaceViews.find((view) => view.value === centerView)?.label ?? 'Overview';
  const rightPaneCollapsed =
    layoutMode === 'desktop' ? panelPreferences.rightCollapsed : layoutMode !== 'tablet' || !tabletInspectorOpen;

  useEffect(() => {
    function handleResize() {
      setLayoutMode(getWorkspaceLayoutMode(window.innerWidth));
    }

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  useEffect(() => {
    if (layoutMode !== 'tablet') {
      setTabletInspectorOpen(false);
    }
  }, [layoutMode]);

  useEffect(() => {
    if (!hasRenderedCenterView.current) {
      hasRenderedCenterView.current = true;
      return;
    }

    centerFocusRef.current?.focus();
  }, [centerView]);

  useEffect(() => {
    if (!hasRenderedInspectorView.current) {
      hasRenderedInspectorView.current = true;
      return;
    }

    inspectorFocusRef.current?.focus();
  }, [inspectorView]);

  function updatePanelPreferences(next: PanelPreferences) {
    setPanelPreferences(next);
    writePanelPreferences(next);
  }

  function updateWorkspaceRoute(partial: {
    view?: string;
    inspector?: string;
    pane?: WorkspacePaneId;
  }) {
    startShellTransition(() => {
      const next = new URLSearchParams(searchParams);

      if (partial.view) {
        next.set('view', partial.view);
      }

      if (partial.inspector) {
        next.set('inspector', partial.inspector);
      }

      if (partial.pane) {
        next.set('pane', partial.pane);
      }

      setSearchParams(next, { replace: true });
    });
  }

  function handleSessionStarted(session: StartNegotiationResponse, summary?: string) {
    startShellTransition(() => {
      setActiveSession(session);
      setStorySummary(summary ?? null);

      const next = new URLSearchParams(searchParams);
      next.set('view', 'negotiation');
      next.set('inspector', 'evidence');
      next.set('pane', 'workspace');
      setSearchParams(next, { replace: true });
    });
  }

  function handleCenterViewChange(view: string) {
    updateWorkspaceRoute({ view });
  }

  function handleInspectorViewChange(view: string) {
    updateWorkspaceRoute({ inspector: view });
  }

  function handleMobilePaneChange(pane: WorkspacePaneId) {
    updateWorkspaceRoute({ pane });
  }

  function handleToggleLeftPane() {
    if (layoutMode === 'mobile') {
      handleMobilePaneChange(mobilePane === 'story' ? 'workspace' : 'story');
      return;
    }

    updatePanelPreferences({
      ...panelPreferences,
      leftCollapsed: !panelPreferences.leftCollapsed,
    });
  }

  function handleToggleRightPane() {
    if (layoutMode === 'mobile') {
      handleMobilePaneChange(mobilePane === 'evidence' ? 'workspace' : 'evidence');
      return;
    }

    if (layoutMode === 'tablet') {
      setTabletInspectorOpen((current) => !current);
      return;
    }

    updatePanelPreferences({
      ...panelPreferences,
      rightCollapsed: !panelPreferences.rightCollapsed,
    });
  }

  return (
    <AppShell
      centerPane={
        <WorkspaceCenterPane
          activeSession={activeSession}
          activeView={centerView}
          focusRef={centerFocusRef}
          isTransitionPending={isTransitionPending}
          onViewChange={handleCenterViewChange}
          statusLabel={statusLabel}
        />
      }
      layoutMode={layoutMode}
      leftPaneCollapsed={panelPreferences.leftCollapsed}
      leftRail={<SessionBootstrap onSessionStarted={handleSessionStarted} />}
      mobilePane={mobilePane}
      onMobilePaneChange={handleMobilePaneChange}
      onToggleLeftPane={handleToggleLeftPane}
      onToggleRightPane={handleToggleRightPane}
      phaseLabel={activeSession?.phase_title ?? 'Foundation bootstrap'}
      rightPaneCollapsed={rightPaneCollapsed}
      rightRail={
        <WorkspaceInspector
          activeSession={activeSession}
          activeView={inspectorView}
          focusRef={inspectorFocusRef}
          onViewChange={handleInspectorViewChange}
        />
      }
      sessionState={getWorkspaceSessionState(activeSession)}
      statusLabel={statusLabel}
      storyKey={activeSession?.jira_key}
      storySummary={storySummary}
      workspaceLabel={workspaceLabel}
    />
  );
}

function readPanelPreferences(): PanelPreferences {
  const storage = getWorkspaceStorage();

  if (!storage) {
    return defaultPanelPreferences;
  }

  let stored: string | null;

  try {
    stored = storage.getItem(workspacePanelStorageKey);
  } catch {
    return defaultPanelPreferences;
  }

  if (!stored) {
    return defaultPanelPreferences;
  }

  try {
    const parsed = JSON.parse(stored) as Partial<PanelPreferences>;

    return {
      leftCollapsed: parsed.leftCollapsed ?? false,
      rightCollapsed: parsed.rightCollapsed ?? false,
    };
  } catch {
    return defaultPanelPreferences;
  }
}

function writePanelPreferences(preferences: PanelPreferences) {
  const storage = getWorkspaceStorage();

  if (!storage) {
    return;
  }

  try {
    storage.setItem(workspacePanelStorageKey, JSON.stringify(preferences));
  } catch {
    // Ignore storage write failures and keep the in-memory state authoritative.
  }
}

function getWorkspaceStorage(): Pick<Storage, 'getItem' | 'setItem'> | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const storage = window.localStorage;

  if (
    !storage ||
    typeof storage.getItem !== 'function' ||
    typeof storage.setItem !== 'function'
  ) {
    return null;
  }

  return storage;
}
