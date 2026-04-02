import { type RefObject } from 'react';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/AppProviders';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';
import { workspacePanelStorageKey } from '@/features/workspace/workspaceModel';
import type { SessionIntakeStory } from '@/features/session/sessionIntakeModel';
import type { StartNegotiationResponse } from '@/lib/api/types';

const mockRespondMutation = vi.fn();

class MockEventSource {
  static instances: MockEventSource[] = [];

  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  closed = false;
  readyState = 0;

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
    this.readyState = 2;
  }

  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateOpen() {
    this.readyState = 1;
    this.onopen?.();
  }
}

vi.mock('@/lib/query/sessionHooks', () => ({
  useRespondMutation: () => ({
    mutateAsync: mockRespondMutation,
  }),
}));

vi.mock('@/features/session/SessionBootstrap', () => {
  type SessionBootstrapProps = {
    activeSession?: StartNegotiationResponse | null;
    draftFeedback?: string;
    onAcceptanceCriterionSelect?: (index: number) => void;
    onDraftFeedbackChange?: (value: string) => void;
    onPhaseSelect?: (phaseNumber: number) => void;
    onSessionStarted?: (session: StartNegotiationResponse, story: SessionIntakeStory) => void;
    selectedAcceptanceCriterionIndex?: number | null;
    selectedPhaseNumber?: number | null;
  };

  return {
    SessionBootstrap: ({
      activeSession,
      draftFeedback,
      onAcceptanceCriterionSelect,
      onDraftFeedbackChange,
      onPhaseSelect,
      onSessionStarted,
      selectedAcceptanceCriterionIndex,
      selectedPhaseNumber,
    }: SessionBootstrapProps) => (
      <div>
        <button
          onClick={() =>
            onSessionStarted?.(
              {
                acceptance_criteria: [
                  { checked: false, index: 0, text: 'Recovered acceptance criterion' },
                  { checked: false, index: 1, text: 'Selected AC should update the workspace' },
                ],
                done: false,
                jira_key: 'MAG-222',
                jira_summary: 'Recovered story summary',
                phase_number: 2,
                phase_title: 'Happy Path Contract',
                session_id: 'session-started',
                total_phases: 7,
              },
              {
                acceptanceCriteria: [
                  { checked: false, index: 0, text: 'Recovered acceptance criterion' },
                  { checked: false, index: 1, text: 'Selected AC should update the workspace' },
                ],
                key: 'MAG-222',
                source: 'jira',
                status: 'In Progress',
                summary: 'Recovered story summary',
              },
            )
          }
          type="button"
        >
          Start mock session
        </button>
        <button
          onClick={() =>
            onSessionStarted?.(
              {
                acceptance_criteria: [
                  { checked: false, index: 0, text: 'Recovered acceptance criterion' },
                  { checked: false, index: 1, text: 'Selected AC should update the workspace' },
                ],
                done: false,
                jira_key: 'MAG-222',
                jira_summary: 'Recovered story summary',
                phase_number: 4,
                phase_title: 'Failure Mode Enumeration',
                session_id: 'session-started',
                total_phases: 7,
              },
              {
                acceptanceCriteria: [
                  { checked: false, index: 0, text: 'Recovered acceptance criterion' },
                  { checked: false, index: 1, text: 'Selected AC should update the workspace' },
                ],
                key: 'MAG-222',
                source: 'jira',
                status: 'In Progress',
                summary: 'Recovered story summary',
              },
            )
          }
          type="button"
        >
          Refresh confirmed session
        </button>
        <button onClick={() => onAcceptanceCriterionSelect?.(1)} type="button">
          Select AC 2
        </button>
        <button onClick={() => onPhaseSelect?.(2)} type="button">
          Select phase 2
        </button>
        <label>
          Draft feedback
          <textarea
            onChange={(event) => onDraftFeedbackChange?.(event.target.value)}
            value={draftFeedback ?? ''}
          />
        </label>
        <p>Bootstrap session: {activeSession?.session_id ?? 'idle'}</p>
        <p>Bootstrap selected AC: {selectedAcceptanceCriterionIndex ?? 'none'}</p>
        <p>Bootstrap selected phase: {selectedPhaseNumber ?? 'none'}</p>
      </div>
    ),
  };
});

vi.mock('@/features/workspace/WorkspaceCenterPane', () => {
  type WorkspaceCenterPaneProps = {
    activeView: string;
    draftFeedback?: string;
    focusRef: RefObject<HTMLElement | null>;
    onApprovePhase?: () => void;
    onDraftFeedbackChange?: (value: string) => void;
    onPhaseSelect?: (phaseNumber: number) => void;
    onRevisePhase?: () => void;
    onViewChange: (view: 'overview' | 'negotiation' | 'traceability') => void;
    phaseActionState?: {
      message?: string | null;
      status?: string;
    };
    selectedAcceptanceCriterionIndex?: number | null;
    selectedPhaseNumber?: number | null;
    storySummary?: string | null;
  };

  return {
    WorkspaceCenterPane: ({
      activeView,
      draftFeedback,
      focusRef,
      onApprovePhase,
      onDraftFeedbackChange,
      onPhaseSelect,
      onRevisePhase,
      onViewChange,
      phaseActionState,
      selectedAcceptanceCriterionIndex,
      selectedPhaseNumber,
      storySummary,
    }: WorkspaceCenterPaneProps) => (
      <div>
        <button onClick={() => onViewChange('overview')} type="button">
          Center overview
        </button>
        <button onClick={() => onViewChange('negotiation')} type="button">
          Center negotiation
        </button>
        <button onClick={() => onViewChange('traceability')} type="button">
          Center traceability
        </button>
        <button onClick={() => onPhaseSelect?.(3)} type="button">
          Center phase 3
        </button>
        <button onClick={() => onApprovePhase?.()} type="button">
          Approve phase
        </button>
        <button onClick={() => onRevisePhase?.()} type="button">
          Revise phase
        </button>
        <label>
          Center revision feedback
          <textarea
            onChange={(event) => onDraftFeedbackChange?.(event.target.value)}
            value={draftFeedback ?? ''}
          />
        </label>
        <section ref={focusRef} tabIndex={-1}>
          Center view: {activeView}
        </section>
        <p>Center selected AC: {selectedAcceptanceCriterionIndex ?? 'none'}</p>
        <p>Center selected phase: {selectedPhaseNumber ?? 'none'}</p>
        <p>Center draft: {draftFeedback || 'empty'}</p>
        <p>Center story summary: {storySummary ?? 'empty'}</p>
        <p>Center action message: {phaseActionState?.message ?? 'none'}</p>
        <p>Center action status: {phaseActionState?.status ?? 'idle'}</p>
      </div>
    ),
  };
});

vi.mock('@/features/workspace/WorkspaceInspector', () => {
  type WorkspaceInspectorProps = {
    activeView: string;
    focusRef: RefObject<HTMLElement | null>;
    onAcceptanceCriterionSelect?: (index: number) => void;
    onViewChange: (view: 'analysis' | 'evidence' | 'scan' | 'traceability') => void;
    selectedAcceptanceCriterionIndex?: number | null;
  };

  return {
    WorkspaceInspector: ({
      activeView,
      focusRef,
      onAcceptanceCriterionSelect,
      onViewChange,
      selectedAcceptanceCriterionIndex,
    }: WorkspaceInspectorProps) => (
      <div>
        <button onClick={() => onViewChange('evidence')} type="button">
          Inspector evidence
        </button>
        <button onClick={() => onViewChange('scan')} type="button">
          Inspector scan
        </button>
        <button onClick={() => onViewChange('traceability')} type="button">
          Inspector traceability
        </button>
        <button onClick={() => onViewChange('analysis')} type="button">
          Inspector planning & critique
        </button>
        <button onClick={() => onAcceptanceCriterionSelect?.(2)} type="button">
          Inspector focus AC 3
        </button>
        <section ref={focusRef} tabIndex={-1}>
          Inspector view: {activeView}
        </section>
        <p>Inspector selected AC: {selectedAcceptanceCriterionIndex ?? 'none'}</p>
      </div>
    ),
  };
});

const originalInnerWidth = window.innerWidth;
const originalLocalStorage = window.localStorage;

const initialSession: StartNegotiationResponse = {
  done: false,
  jira_key: 'MAG-22',
  phase_number: 3,
  phase_title: 'Phase 3: Precondition Formalization',
  revised: false,
  session_id: 'session-123',
  total_phases: 7,
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{`${location.pathname}${location.search}`}</output>;
}

function renderWorkspace(entry = '/?view=overview&inspector=evidence&pane=workspace') {
  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[entry]}>
        <OperatorWorkspacePage
          initialSession={initialSession}
          initialStorySummary="Port the operator workspace layout"
        />
        <LocationProbe />
      </MemoryRouter>
    </AppProviders>,
  );
}

function setViewport(width: number) {
  act(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: width,
      writable: true,
    });
    window.dispatchEvent(new Event('resize'));
  });
}

function installStorage() {
  const store = new Map<string, string>();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      clear: () => { store.clear(); },
      getItem: (key: string) => store.get(key) ?? null,
      removeItem: (key: string) => { store.delete(key); },
      setItem: (key: string, value: string) => { store.set(key, value); },
    },
  });
}

function renderPage(options?: {
  initialEntry?: string;
  initialSessionValue?: StartNegotiationResponse | null;
  initialStorySummary?: string | null;
}) {
  const {
    initialEntry = '/?view=overview&inspector=evidence&pane=workspace',
    initialSessionValue = initialSession,
    initialStorySummary = 'Port the operator workspace layout',
  } = options ?? {};

  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[initialEntry]}>
        <OperatorWorkspacePage
          initialSession={initialSessionValue}
          initialStorySummary={initialStorySummary}
        />
        <LocationProbe />
      </MemoryRouter>
    </AppProviders>,
  );
}

afterEach(() => {
  cleanup();
  mockRespondMutation.mockReset();
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: originalInnerWidth,
  });
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: originalLocalStorage,
  });
});

describe('Operator workspace layout', () => {
  beforeEach(() => {
    setViewport(1440);
    installStorage();
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource);
  });

  it('renders top-bar session context and the wired workspace shell for active sessions', () => {
    renderWorkspace();

    expect(screen.getByRole('status', { name: /session status/i })).toHaveTextContent(
      /awaiting operator input/i,
    );
    expect(screen.getByText(/bootstrap session: session-123/i)).toBeInTheDocument();
    expect(screen.getByText(/phase 3: precondition formalization/i)).toBeInTheDocument();
    expect(screen.getByText('Center view: overview')).toBeInTheDocument();
    expect(screen.getByText('Inspector view: evidence')).toBeInTheDocument();
  });

  it('swaps center and inspector surfaces in place and keeps focus on the active region', async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole('button', { name: /center traceability/i }));

    await waitFor(() => {
      expect(screen.getByText('Center view: traceability').closest('section')).toHaveFocus();
    });
    expect(screen.getByTestId('location')).toHaveTextContent('/?view=traceability&inspector=evidence&pane=workspace');

    await user.click(screen.getByRole('button', { name: /inspector scan/i }));

    await waitFor(() => {
      expect(screen.getByText('Inspector view: scan').closest('section')).toHaveFocus();
    });
    expect(screen.getByTestId('location')).toHaveTextContent('/?view=traceability&inspector=scan&pane=workspace');
  });

  it('persists panel collapse state and falls back to single-panel mobile switching', async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole('button', { name: /toggle evidence panel/i }));

    expect(window.localStorage.getItem(workspacePanelStorageKey)).toContain('"rightCollapsed":true');
    expect(screen.getByTestId('workspace-grid')).toHaveStyle({
      '--workspace-right-width': '0rem',
    });

    setViewport(640);

    expect(await screen.findByRole('tablist', { name: /workspace panels/i })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /story panel/i }));

    expect(screen.getByTestId('location')).toHaveTextContent('/?view=overview&inspector=evidence&pane=story');

    setViewport(1440);

    expect(screen.getByTestId('workspace-grid')).toHaveAttribute('data-layout-mode', 'desktop');
    expect(screen.getByTestId('workspace-grid')).toHaveStyle({
      '--workspace-right-width': '0rem',
    });
    expect(screen.getByText('Inspector view: evidence')).toBeInTheDocument();
  });

  it('updates the top bar story context when intake starts a new session', async () => {
    const user = userEvent.setup();

    setViewport(1440);
    installStorage();
    renderPage({
      initialEntry: '/',
      initialSessionValue: null,
      initialStorySummary: null,
    });

    expect(screen.getByText(/no active story/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /start mock session/i }));

    expect(await screen.findByText('MAG-222')).toBeInTheDocument();
    expect(screen.getAllByText(/recovered story summary/i)).toHaveLength(2);
    expect(screen.getByText('Center view: negotiation')).toBeInTheDocument();
  });

  it('announces session and phase transitions while keeping focus on the active workspace flow', async () => {
    const user = userEvent.setup();

    mockRespondMutation.mockResolvedValue({
      ...initialSession,
      phase_number: 4,
      phase_title: 'Failure Mode Enumeration',
      session_id: 'session-started',
    });

    setViewport(1440);
    installStorage();
    renderPage({
      initialEntry: '/',
      initialSessionValue: null,
      initialStorySummary: null,
    });

    await user.click(screen.getByRole('button', { name: /start mock session/i }));

    const announcement = screen.getByRole('status', { name: /workspace announcements/i });

    await waitFor(() => {
      expect(announcement).toHaveTextContent(/session started for mag-222/i);
      expect(screen.getByText('Center view: negotiation').closest('section')).toHaveFocus();
    });

    await user.click(screen.getByRole('button', { name: /approve phase/i }));

    await waitFor(() => {
      expect(announcement).toHaveTextContent(/phase approved/i);
      expect(announcement).toHaveTextContent(/failure mode enumeration/i);
      expect(screen.getByText('Center view: negotiation').closest('section')).toHaveFocus();
    });
  });

  it('preserves draft feedback across view switches and confirmed session refreshes', async () => {
    const user = userEvent.setup();

    setViewport(1440);
    installStorage();
    renderPage({
      initialEntry: '/',
      initialSessionValue: null,
      initialStorySummary: null,
    });

    await user.click(screen.getByRole('button', { name: /start mock session/i }));
    await user.type(screen.getByLabelText(/draft feedback/i), 'Need clearer preconditions');

    expect(screen.getByText(/center draft: need clearer preconditions/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /inspector scan/i }));
    await user.click(screen.getByRole('button', { name: /refresh confirmed session/i }));

    expect(await screen.findAllByDisplayValue('Need clearer preconditions')).toHaveLength(2);
    expect(screen.getByText(/center draft: need clearer preconditions/i)).toBeInTheDocument();
    expect(screen.getByText(/failure mode enumeration/i)).toBeInTheDocument();
  });

  it('propagates selected acceptance criterion and phase context across workspace panes', async () => {
    const user = userEvent.setup();

    setViewport(1440);
    installStorage();
    renderPage({
      initialEntry: '/',
      initialSessionValue: null,
      initialStorySummary: null,
    });

    await user.click(screen.getByRole('button', { name: /start mock session/i }));
    await user.click(screen.getByRole('button', { name: /select ac 2/i }));
    await user.click(screen.getByRole('button', { name: /select phase 2/i }));

    expect(screen.getByText('Bootstrap selected AC: 1')).toBeInTheDocument();
    expect(screen.getByText('Center selected AC: 1')).toBeInTheDocument();
    expect(screen.getByText('Inspector selected AC: 1')).toBeInTheDocument();
    expect(screen.getByText('Bootstrap selected phase: 2')).toBeInTheDocument();
    expect(screen.getByText('Center selected phase: 2')).toBeInTheDocument();
  });

  it('applies approve responses in place and advances the confirmed phase context', async () => {
    const user = userEvent.setup();

    mockRespondMutation.mockResolvedValue({
      ...initialSession,
      phase_number: 4,
      phase_title: 'Failure Mode Enumeration',
      session_id: 'session-123',
    });

    setViewport(1440);
    installStorage();
    renderPage();

    await user.click(screen.getByRole('button', { name: /approve phase/i }));

    await waitFor(() => {
      expect(mockRespondMutation).toHaveBeenCalledWith({
        input: 'approve',
        session_id: 'session-123',
      });
    });
    expect(screen.getByText('Center selected phase: 4')).toBeInTheDocument();
    expect(screen.getByText(/center action message: phase approved/i)).toBeInTheDocument();
  });

  it('surfaces revise failures inline without losing the active draft feedback', async () => {
    const user = userEvent.setup();

    mockRespondMutation.mockRejectedValue(new Error('Revision request failed'));

    setViewport(1440);
    installStorage();
    renderPage();

    await user.type(screen.getByLabelText(/center revision feedback/i), 'Need tighter error handling');
    await user.click(screen.getByRole('button', { name: /revise phase/i }));

    await waitFor(() => {
      expect(mockRespondMutation).toHaveBeenCalledWith({
        input: 'Need tighter error handling',
        session_id: 'session-123',
      });
    });
    expect(screen.getAllByDisplayValue('Need tighter error handling')).toHaveLength(2);
    expect(screen.getByText(/center action status: error/i)).toBeInTheDocument();
    expect(screen.getByText(/revision request failed/i)).toBeInTheDocument();
  });

  it('connects the active session to SSE and surfaces live stream state in the shell', async () => {
    renderWorkspace();

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('/api/events/session-123');

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(screen.getByRole('status', { name: /stream status/i })).toHaveTextContent(/stream live/i);

    act(() => {
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_start',
        session_id: 'session-123',
        phase: 'phase_3',
        phase_index: 2,
      });
    });
  });
});
