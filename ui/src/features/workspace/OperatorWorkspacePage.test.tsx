import type { RefObject } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SessionIntakeStory } from '@/features/session/sessionIntakeModel';
import { workspacePanelStorageKey } from '@/features/workspace/workspaceModel';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';
import type { StartNegotiationResponse } from '@/lib/api/types';

const mockRespondMutation = vi.fn();

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
    onViewChange: (view: 'evidence' | 'scan' | 'traceability') => void;
    selectedAcceptanceCriterionIndex?: number | null;
  };

  return {
    WorkspaceInspector: ({
      activeView,
      focusRef,
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
  jira_key: 'MAG-201',
  phase_number: 3,
  phase_title: 'Precondition Formalization',
  session_id: 'session-u2',
  total_phases: 7,
};

type StorageStub = Storage & {
  dump: () => Record<string, string>;
};

function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    writable: true,
    value: width,
  });
}

function installStorage(initial: Record<string, string> = {}): StorageStub {
  const values = new Map(Object.entries(initial));
  const storage = {
    clear: vi.fn(() => {
      values.clear();
    }),
    dump: () => Object.fromEntries(values.entries()),
    getItem: vi.fn((key: string) => values.get(key) ?? null),
    key: vi.fn((index: number) => Array.from(values.keys())[index] ?? null),
    get length() {
      return values.size;
    },
    removeItem: vi.fn((key: string) => {
      values.delete(key);
    }),
    setItem: vi.fn((key: string, value: string) => {
      values.set(key, value);
    }),
  } satisfies StorageStub;

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: storage,
  });

  return storage;
}

function renderPage({
  initialEntry = '/?view=overview&inspector=evidence&pane=workspace',
  initialSessionValue = initialSession,
  initialStorySummary = 'Port operator workspace layout',
}: {
  initialEntry?: string;
  initialSessionValue?: StartNegotiationResponse | null;
  initialStorySummary?: string | null;
} = {}) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route
          element={
            <OperatorWorkspacePage
              initialSession={initialSessionValue}
              initialStorySummary={initialStorySummary}
            />
          }
          path="/"
        />
      </Routes>
    </MemoryRouter>,
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
  vi.restoreAllMocks();
});

describe('OperatorWorkspacePage', () => {
  it('falls back to default pane state when storage APIs are unavailable', () => {
    setViewport(1440);
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: {},
    });

    renderPage();

    expect(screen.getByRole('heading', { name: /magic agents/i })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /story intake/i })).toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: /evidence inspector/i })).toBeInTheDocument();
  });

  it('persists collapsed side panes across reloads on desktop', async () => {
    const user = userEvent.setup();
    const storage = installStorage();

    setViewport(1440);
    const view = renderPage();

    await user.click(screen.getByRole('button', { name: /toggle story intake panel/i }));
    await user.click(screen.getByRole('button', { name: /toggle evidence panel/i }));

    expect(storage.setItem).toHaveBeenLastCalledWith(
      workspacePanelStorageKey,
      JSON.stringify({ leftCollapsed: true, rightCollapsed: true }),
    );
    expect(storage.dump()[workspacePanelStorageKey]).toBe(
      JSON.stringify({ leftCollapsed: true, rightCollapsed: true }),
    );
    expect(screen.queryByRole('complementary', { name: /story intake/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('complementary', { name: /evidence inspector/i }),
    ).not.toBeInTheDocument();

    view.unmount();
    renderPage();

    expect(screen.queryByRole('complementary', { name: /story intake/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('complementary', { name: /evidence inspector/i }),
    ).not.toBeInTheDocument();
  });

  it('switches center and inspector content in place and moves focus to the active region', async () => {
    const user = userEvent.setup();

    setViewport(1440);
    installStorage();
    renderPage();

    expect(screen.getByText('Center view: overview')).toBeInTheDocument();
    expect(screen.getByText('Inspector view: evidence')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /center traceability/i }));

    await waitFor(() => {
      expect(screen.getByText('Center view: traceability')).toHaveFocus();
    });
    expect(screen.getByText('Inspector view: evidence')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /inspector scan/i }));

    await waitFor(() => {
      expect(screen.getByText('Inspector view: scan')).toHaveFocus();
    });
    expect(screen.getByText('Center view: traceability')).toBeInTheDocument();
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
      session_id: 'session-u2',
    });

    setViewport(1440);
    installStorage();
    renderPage();

    await user.click(screen.getByRole('button', { name: /approve phase/i }));

    await waitFor(() => {
      expect(mockRespondMutation).toHaveBeenCalledWith({
        input: 'approve',
        session_id: 'session-u2',
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
        session_id: 'session-u2',
      });
    });
    expect(screen.getAllByDisplayValue('Need tighter error handling')).toHaveLength(2);
    expect(screen.getByText(/center action status: error/i)).toBeInTheDocument();
    expect(screen.getByText(/revision request failed/i)).toBeInTheDocument();
  });
});
