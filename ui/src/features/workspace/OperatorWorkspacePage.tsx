import { useEffect, useRef, useState, useTransition } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import type { SessionIntakeStory } from '@/features/session/sessionIntakeModel';
import {
  WorkspaceCenterPane,
  type PhaseActionState,
} from '@/features/workspace/WorkspaceCenterPane';
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
import { useRespondMutation } from '@/lib/query/sessionHooks';

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

const defaultPhaseActionState: PhaseActionState = {
  activeAction: null,
  isPending: false,
  message: null,
  status: 'idle',
};

export function OperatorWorkspacePage({
  initialSession = null,
  initialStorySummary = null,
}: OperatorWorkspacePageProps) {
  const [activeSession, setActiveSession] = useState<StartNegotiationResponse | null>(initialSession);
  const [activeStory, setActiveStory] = useState<SessionIntakeStory | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(
    initialSession ? `Session loaded for ${initialSession.jira_key}.` : null,
  );
  const [storySummary, setStorySummary] = useState<string | null>(initialStorySummary);
  const [sessionDrafts, setSessionDrafts] = useState<Record<string, string>>({});
  const [selectedAcceptanceCriterionIndex, setSelectedAcceptanceCriterionIndex] = useState<number | null>(null);
  const [selectedPhaseNumber, setSelectedPhaseNumber] = useState<number | null>(
    initialSession?.phase_number ?? null,
  );
  const [phaseActionState, setPhaseActionState] = useState<PhaseActionState>(defaultPhaseActionState);
  const [layoutMode, setLayoutMode] = useState(() => getWorkspaceLayoutMode(window.innerWidth));
  const [panelPreferences, setPanelPreferences] = useState<PanelPreferences>(readPanelPreferences);
  const [tabletInspectorOpen, setTabletInspectorOpen] = useState(false);
  const [isTransitionPending, startShellTransition] = useTransition();
  const [searchParams, setSearchParams] = useSearchParams();
  const respondMutation = useRespondMutation();
  const centerFocusRef = useRef<HTMLElement | null>(null);
  const inspectorFocusRef = useRef<HTMLElement | null>(null);
  const hasRenderedCenterView = useRef(false);
  const hasRenderedInspectorView = useRef(false);
  const announcedSessionIdRef = useRef<string | null>(initialSession?.session_id ?? null);
  const announcedPhaseMessageRef = useRef<string | null>(null);

  const centerView = parseCenterWorkspaceView(searchParams.get('view'));
  const inspectorView = parseInspectorWorkspaceView(searchParams.get('inspector'));
  const mobilePane = parseMobileWorkspacePane(searchParams.get('pane'));
  const statusLabel = getWorkspaceStatusLabel(activeSession);
  const workspaceLabel =
    centerWorkspaceViews.find((view) => view.value === centerView)?.label ?? 'Overview';
  const rightPaneCollapsed =
    layoutMode === 'desktop' ? panelPreferences.rightCollapsed : layoutMode !== 'tablet' || !tabletInspectorOpen;
  const draftFeedback = activeSession ? sessionDrafts[activeSession.session_id] ?? '' : '';

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

    setAnnouncement(`Workspace view changed to ${workspaceLabel}.`);
    centerFocusRef.current?.focus();
  }, [centerView, workspaceLabel]);

  useEffect(() => {
    if (!hasRenderedInspectorView.current) {
      hasRenderedInspectorView.current = true;
      return;
    }

    const nextInspectorLabel =
      inspectorView === 'analysis'
        ? 'Planning and critique'
        : inspectorView === 'traceability'
          ? 'Traceability'
          : inspectorView === 'scan'
            ? 'Scan output'
            : 'Evidence';

    setAnnouncement(`Inspector view changed to ${nextInspectorLabel}.`);
    inspectorFocusRef.current?.focus();
  }, [inspectorView]);

  useEffect(() => {
    if (!activeSession?.session_id || announcedSessionIdRef.current === activeSession.session_id) {
      return;
    }

    announcedSessionIdRef.current = activeSession.session_id;
    setAnnouncement(`Session loaded for ${activeSession.jira_key}. Focus moved to the active workspace.`);

    window.requestAnimationFrame(() => {
      centerFocusRef.current?.focus();
    });
  }, [activeSession?.jira_key, activeSession?.session_id]);

  useEffect(() => {
    if (phaseActionState.status !== 'success' || !phaseActionState.message) {
      return;
    }

    if (announcedPhaseMessageRef.current === phaseActionState.message) {
      return;
    }

    announcedPhaseMessageRef.current = phaseActionState.message;
    setAnnouncement(phaseActionState.message);

    window.requestAnimationFrame(() => {
      centerFocusRef.current?.focus();
    });
  }, [phaseActionState.message, phaseActionState.status]);

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

  function handleSessionStarted(session: StartNegotiationResponse, story: SessionIntakeStory) {
    startShellTransition(() => {
      setActiveSession(session);
      setActiveStory(story);
      setStorySummary(session.jira_summary ?? story.summary);
      setSelectedAcceptanceCriterionIndex((current) =>
        story.acceptanceCriteria.some((criterion) => criterion.index === current) ? current : null,
      );
      setSelectedPhaseNumber(session.phase_number);

      const next = new URLSearchParams(searchParams);
      next.set('view', 'negotiation');
      next.set('inspector', 'evidence');
      next.set('pane', 'workspace');
      setSearchParams(next, { replace: true });
      setPhaseActionState(defaultPhaseActionState);
    });
  }

  function handleDraftFeedbackChange(value: string) {
    if (!activeSession) {
      return;
    }

    setSessionDrafts((current) => ({
      ...current,
      [activeSession.session_id]: value,
    }));
    setPhaseActionState((current) =>
      current.status === 'idle' && !current.message ? current : defaultPhaseActionState,
    );
  }

  function handleAcceptanceCriterionSelect(index: number) {
    setSelectedAcceptanceCriterionIndex(index);
  }

  function handlePhaseSelect(phaseNumber: number) {
    setSelectedPhaseNumber(phaseNumber);
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

  async function submitPhaseResponse(input: string, action: 'approve' | 'revise') {
    if (!activeSession) {
      return;
    }

    setPhaseActionState({
      activeAction: action,
      isPending: true,
      message: action === 'approve' ? 'Submitting approval' : 'Submitting revision request',
      status: 'idle',
    });

    try {
      const nextSession = await respondMutation.mutateAsync({
        input,
        session_id: activeSession.session_id,
      });

      startShellTransition(() => {
        setActiveSession(nextSession);
        setStorySummary(nextSession.jira_summary ?? storySummary);
        setSelectedPhaseNumber((current) => resolveSelectedPhaseNumber(current, activeSession, nextSession));
        if (action === 'approve' && nextSession.done) {
          const next = new URLSearchParams(searchParams);
          next.set('view', 'verification');
          setSearchParams(next, { replace: true });
        }
        setPhaseActionState({
          activeAction: action,
          isPending: false,
          message: buildPhaseActionMessage(action, nextSession),
          status: 'success',
        });
      });
    } catch (error) {
      setPhaseActionState({
        activeAction: action,
        isPending: false,
        message: resolvePhaseActionError(error, action),
        status: 'error',
      });
    }
  }

  function handleApprovePhase() {
    if (!activeSession || phaseActionState.isPending) {
      return;
    }

    void submitPhaseResponse('approve', 'approve');
  }

  function handleRevisePhase() {
    if (!activeSession || phaseActionState.isPending) {
      return;
    }

    if (!draftFeedback.trim()) {
      setPhaseActionState({
        activeAction: 'revise',
        isPending: false,
        message: 'Enter revision feedback before requesting a revised phase response.',
        status: 'error',
      });
      return;
    }

    void submitPhaseResponse(draftFeedback, 'revise');
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
      announcement={announcement}
      centerPane={
        <WorkspaceCenterPane
          activeSession={activeSession}
          activeView={centerView}
          draftFeedback={draftFeedback}
          focusRef={centerFocusRef}
          isTransitionPending={isTransitionPending}
          onApprovePhase={handleApprovePhase}
          onDraftFeedbackChange={handleDraftFeedbackChange}
          onPhaseSelect={handlePhaseSelect}
          onRevisePhase={handleRevisePhase}
          onViewChange={handleCenterViewChange}
          phaseActionState={phaseActionState}
          selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
          selectedPhaseNumber={selectedPhaseNumber}
          statusLabel={statusLabel}
          storySummary={activeStory?.summary ?? storySummary}
        />
      }
      layoutMode={layoutMode}
      leftPaneCollapsed={panelPreferences.leftCollapsed}
      leftRail={
        <SessionBootstrap
          activeSession={activeSession}
          draftFeedback={draftFeedback}
          onAcceptanceCriterionSelect={handleAcceptanceCriterionSelect}
          onDraftFeedbackChange={handleDraftFeedbackChange}
          onPhaseSelect={handlePhaseSelect}
          onSessionStarted={handleSessionStarted}
          selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
          selectedPhaseNumber={selectedPhaseNumber}
        />
      }
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
          onAcceptanceCriterionSelect={handleAcceptanceCriterionSelect}
          onViewChange={handleInspectorViewChange}
          selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
        />
      }
      sessionState={getWorkspaceSessionState(activeSession)}
      statusLabel={statusLabel}
      storyKey={activeStory?.key ?? activeSession?.jira_key}
      storySummary={activeStory?.summary ?? storySummary}
      workspaceLabel={workspaceLabel}
    />
  );
}

function buildPhaseActionMessage(
  action: 'approve' | 'revise',
  session: StartNegotiationResponse,
) {
  if (action === 'revise') {
    return `Revision response loaded for ${session.phase_title}.`;
  }

  if (session.done) {
    return 'Negotiation complete. Review the final summary and traceability.';
  }

  return `Phase approved. The workspace advanced to ${session.phase_title}.`;
}

function resolveSelectedPhaseNumber(
  current: number | null,
  previousSession: StartNegotiationResponse,
  nextSession: StartNegotiationResponse,
) {
  if (current === null || current >= previousSession.phase_number) {
    return nextSession.phase_number;
  }

  return current;
}

function resolvePhaseActionError(error: unknown, action: 'approve' | 'revise') {
  if (error instanceof Error) {
    return error.message;
  }

  return action === 'approve'
    ? 'Unable to approve the active phase.'
    : 'Unable to request a revised phase response.';
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
