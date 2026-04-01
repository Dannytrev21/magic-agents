import type { RefObject } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { SessionIntakeStory } from '@/features/session/sessionIntakeModel';
import { workspacePanelStorageKey } from '@/features/workspace/workspaceModel';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';
import type { StartNegotiationResponse } from '@/lib/api/types';

vi.mock('@/features/session/SessionBootstrap', () => {
  type SessionBootstrapProps = {
    onSessionStarted?: (session: StartNegotiationResponse, story: SessionIntakeStory) => void;
  };

  return {
    SessionBootstrap: ({ onSessionStarted }: SessionBootstrapProps) => (
      <button
        onClick={() =>
          onSessionStarted?.(
            {
              done: false,
              jira_key: 'MAG-222',
              phase_number: 2,
              phase_title: 'Happy Path Contract',
              session_id: 'session-started',
              total_phases: 7,
            },
            {
              acceptanceCriteria: [],
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
    ),
  };
});

vi.mock('@/features/workspace/WorkspaceCenterPane', () => {
  type WorkspaceCenterPaneProps = {
    activeView: string;
    focusRef: RefObject<HTMLElement | null>;
    onViewChange: (view: 'overview' | 'negotiation' | 'traceability') => void;
  };

  return {
    WorkspaceCenterPane: ({ activeView, focusRef, onViewChange }: WorkspaceCenterPaneProps) => (
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
        <section ref={focusRef} tabIndex={-1}>
          Center view: {activeView}
        </section>
      </div>
    ),
  };
});

vi.mock('@/features/workspace/WorkspaceInspector', () => {
  type WorkspaceInspectorProps = {
    activeView: string;
    focusRef: RefObject<HTMLElement | null>;
    onViewChange: (view: 'evidence' | 'scan' | 'traceability') => void;
  };

  return {
    WorkspaceInspector: ({ activeView, focusRef, onViewChange }: WorkspaceInspectorProps) => (
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
    expect(screen.getByText(/recovered story summary/i)).toBeInTheDocument();
    expect(screen.getByText('Center view: negotiation')).toBeInTheDocument();
  });
});
