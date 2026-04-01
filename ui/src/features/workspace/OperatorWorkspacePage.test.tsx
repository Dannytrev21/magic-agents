import { act, cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/AppProviders';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';
import { workspacePanelStorageKey } from '@/features/workspace/workspaceModel';
import type { StartNegotiationResponse } from '@/lib/api/types';

vi.mock('@/lib/query/sessionHooks', () => ({
  useInspectorQueries: () => ({
    isLoading: false,
    scanStatus: {
      project_root: '/Users/dannytrevino/development/magic-agents',
      scanned: true,
    },
    skills: [{ name: 'phase1' }, { name: 'phase2' }],
  }),
  useSessionBootstrapQueries: () => ({
    configured: true,
    isError: false,
    isLoading: false,
    stories: [{ key: 'MAG-22', summary: 'Port the operator workspace layout' }],
    storiesError: null,
  }),
  useStorySessionQueries: () => ({
    'MAG-22': {
      has_checkpoint: false,
      session: undefined,
    },
  }),
  useStartNegotiationMutation: () => ({
    data: null,
    isPending: false,
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
  }),
  useResumeSessionMutation: () => ({
    data: null,
    isPending: false,
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
  }),
}));

const mockSession: StartNegotiationResponse = {
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
          initialSession={mockSession}
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

beforeEach(() => {
  const store = new Map<string, string>();

  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      clear: () => {
        store.clear();
      },
      getItem: (key: string) => store.get(key) ?? null,
      removeItem: (key: string) => {
        store.delete(key);
      },
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
    },
  });
  setViewport(1440);
});

afterEach(() => {
  cleanup();
  window.localStorage?.clear?.();
});

describe('Operator workspace layout', () => {
  it('renders a seven-phase sticky rail and session status strip for active sessions', () => {
    renderWorkspace();

    const phaseList = screen.getByRole('list', { name: /negotiation phases/i });
    const items = within(phaseList).getAllByRole('listitem');

    expect(items).toHaveLength(7);
    expect(items[0]).toHaveAttribute('data-state', 'complete');
    expect(items[2]).toHaveAttribute('data-state', 'active');
    expect(screen.getByText(/session status/i)).toBeInTheDocument();
    expect(screen.getAllByText(/awaiting operator input/i)[0]).toBeInTheDocument();
    expect(screen.getAllByText('session-123')[0]).toBeInTheDocument();
    expect(screen.getByText(/phase 3 of 7/i)).toBeInTheDocument();
  });

  it('swaps center and inspector surfaces in place and keeps focus on the active region', async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(
      within(screen.getByRole('tablist', { name: /workspace views/i })).getByRole('tab', {
        name: /traceability/i,
      }),
    );

    expect(screen.getByRole('heading', { name: /traceability matrix/i })).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /active workspace region/i })).toHaveFocus();
    expect(screen.getByTestId('location')).toHaveTextContent('/?view=traceability&inspector=evidence&pane=workspace');

    await user.click(
      within(screen.getByRole('tablist', { name: /inspector views/i })).getByRole('tab', {
        name: /scan output/i,
      }),
    );

    expect(screen.getByText(/project root/i)).toBeInTheDocument();
    expect(screen.getByRole('region', { name: /inspector detail region/i })).toHaveFocus();
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
  });
});
