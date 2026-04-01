import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import * as api from '@/lib/api/client';
import type { StartNegotiationResponse } from '@/lib/api/types';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const activeCheckpointSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Operator can resume a checkpointed session without rebuilding local state',
    },
    {
      checked: false,
      index: 1,
      text: 'Operators can start a fresh session when a checkpoint exists for a story with a very long acceptance criterion that should still remain readable inside the rail without blowing out the compact layout',
    },
  ],
  approved: false,
  classifications: [{ ac_index: 0, type: 'workflow_state' }],
  current_phase: 'phase_3',
  done: false,
  jira_key: 'MAG-31',
  jira_summary: 'Recover active checkpoint sessions',
  log_entries: 12,
  phase_number: 3,
  phase_title: 'Precondition Formalization',
  resumed: true,
  session_id: 'session-restore-31',
  total_phases: 7,
  usage: {
    api_calls: 12,
    budget_state: 'warning',
    cost_usd: 0.42,
    max_api_calls: 50,
    max_tokens: 500_000,
    tokens_used: 420_000,
    wall_clock_seconds: 272,
  },
  verdicts: [{ ac_checkbox: 0, passed: true }],
};

describe('Session bootstrap query layer', () => {
  it('renders loading state while bootstrap queries resolve', () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockReturnValue(new Promise(() => undefined));
    vi.spyOn(api, 'fetchJiraStories').mockReturnValue(new Promise(() => undefined));

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    expect(screen.getByText(/loading jira intake/i)).toBeInTheDocument();
  });

  it('renders explicit Jira configuration fallback while keeping manual entry available', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      error: 'JIRA_BASE_URL is not configured',
      stories: [],
    });

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/jira configuration required/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole('tab', { name: /manual entry/i }));

    expect(screen.getByLabelText(/acceptance criteria/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start session from manual story/i })).toBeInTheDocument();
  });

  it('renders explicit empty state when Jira is configured but there are no in-progress stories', async () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/no in-progress jira stories/i)).toBeInTheDocument();
    });
  });

  it('renders stories after the query layer resolves', async () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      stories: [{ key: 'MAG-22', summary: 'Port the workspace shell' }],
    });

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('MAG-22')).toBeInTheDocument();
    });
  });

  it('renders a controlled failure state when the query layer rejects', async () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockRejectedValue(new Error('network'));
    vi.spyOn(api, 'fetchJiraStories').mockRejectedValue(new Error('network'));

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText(/jira intake is temporarily unavailable/i)).toBeInTheDocument();
    });
  });

  it('filters populated stories while keeping search input responsive', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      stories: [
        { key: 'MAG-22', summary: 'Port the workspace shell' },
        { key: 'MAG-31', summary: 'Recover active checkpoint sessions' },
      ],
    });

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    const search = await screen.findByRole('searchbox', { name: /story search/i });

    await user.type(search, 'checkpoint');

    expect(search).toHaveValue('checkpoint');

    await waitFor(() => {
      expect(screen.queryByText('MAG-22')).not.toBeInTheDocument();
    });
    expect(screen.getByText('MAG-31')).toBeInTheDocument();
  });

  it('starts a session from the selected Jira story using the shared normalized story model', async () => {
    const user = userEvent.setup();
    const onSessionStarted = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      stories: [{ key: 'MAG-22', summary: 'Port the workspace shell' }],
    });
    vi.spyOn(api, 'fetchJiraTicket').mockResolvedValue({
      acceptance_criteria: [
        { checked: false, index: 0, text: 'Workspace stays in one route' },
        { checked: false, index: 1, text: 'Operators can scan story metadata quickly' },
      ],
      key: 'MAG-22',
      status: 'In Progress',
      summary: 'Port the workspace shell',
    });
    vi.spyOn(api, 'startNegotiation').mockResolvedValue({
      done: false,
      jira_key: 'MAG-22',
      phase_number: 1,
      phase_title: 'Interface & Actor Discovery',
      session_id: 'session-001',
      total_phases: 7,
    });

    render(<SessionBootstrap onSessionStarted={onSessionStarted} />, {
      wrapper: createWrapper(),
    });

    await user.click(await screen.findByRole('button', { name: /select story mag-22/i }));
    await user.click(screen.getByRole('button', { name: /start session from jira/i }));

    await waitFor(() => {
      expect(onSessionStarted).toHaveBeenCalledWith(
        expect.objectContaining({
          jira_key: 'MAG-22',
          session_id: 'session-001',
        }),
        expect.objectContaining({
          acceptanceCriteria: [
            { checked: false, index: 0, text: 'Workspace stays in one route' },
            { checked: false, index: 1, text: 'Operators can scan story metadata quickly' },
          ],
          key: 'MAG-22',
          source: 'jira',
          summary: 'Port the workspace shell',
        }),
      );
    });
  });

  it('normalizes manual intake into the shared story model when a session starts', async () => {
    const user = userEvent.setup();
    const onSessionStarted = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });
    vi.spyOn(api, 'startNegotiation').mockResolvedValue({
      done: false,
      jira_key: 'OPS-44',
      phase_number: 1,
      phase_title: 'Interface & Actor Discovery',
      session_id: 'session-ops-44',
      total_phases: 7,
    });

    render(<SessionBootstrap onSessionStarted={onSessionStarted} />, {
      wrapper: createWrapper(),
    });

    await user.click(await screen.findByRole('tab', { name: /manual entry/i }));
    await user.clear(screen.getByLabelText(/jira key/i));
    await user.type(screen.getByLabelText(/jira key/i), 'OPS-44');
    await user.clear(screen.getByLabelText(/summary/i));
    await user.type(screen.getByLabelText(/summary/i), 'Capture manual intake');
    await user.clear(screen.getByLabelText(/acceptance criteria/i));
    await user.type(
      screen.getByLabelText(/acceptance criteria/i),
      'Operator can enter a story{enter}Operator can keep working without Jira',
    );

    await user.click(screen.getByRole('button', { name: /start session from manual story/i }));

    await waitFor(() => {
      expect(api.startNegotiation).toHaveBeenCalledWith({
        acceptance_criteria: [
          { checked: false, index: 0, text: 'Operator can enter a story' },
          { checked: false, index: 1, text: 'Operator can keep working without Jira' },
        ],
        jira_key: 'OPS-44',
        jira_summary: 'Capture manual intake',
      });
    });
    expect(onSessionStarted).toHaveBeenCalledWith(
      expect.objectContaining({
        jira_key: 'OPS-44',
        session_id: 'session-ops-44',
      }),
      expect.objectContaining({
        acceptanceCriteria: [
          { checked: false, index: 0, text: 'Operator can enter a story' },
          { checked: false, index: 1, text: 'Operator can keep working without Jira' },
        ],
        key: 'OPS-44',
        source: 'manual',
        summary: 'Capture manual intake',
      }),
    );
  });

  it('shows resume affordances when checkpoint data exists and hydrates the saved session context', async () => {
    const user = userEvent.setup();
    const onSessionStarted = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      stories: [{ key: 'MAG-31', summary: 'Recover active checkpoint sessions' }],
    });
    vi.spyOn(api, 'fetchSessionInfo').mockResolvedValue({
      has_checkpoint: true,
      session: {
        approved: false,
        current_phase: 'phase_3',
        jira_key: 'MAG-31',
        jira_summary: 'Recover active checkpoint sessions',
        log_entries: 12,
        phase_number: 3,
        phase_title: 'Precondition Formalization',
      },
    });
    vi.spyOn(api, 'resumeSession').mockResolvedValue(activeCheckpointSession);

    render(<SessionBootstrap onSessionStarted={onSessionStarted} />, {
      wrapper: createWrapper(),
    });

    await user.click(await screen.findByRole('button', { name: /select story mag-31/i }));

    expect(await screen.findByRole('button', { name: /resume session/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start fresh session/i })).toBeInTheDocument();
    expect(screen.getByText(/phase 3/i)).toBeInTheDocument();
    expect(screen.getByText(/12 log entries/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /resume session/i }));

    await waitFor(() => {
      expect(onSessionStarted).toHaveBeenCalledWith(
        expect.objectContaining({
          jira_key: 'MAG-31',
          resumed: true,
          session_id: 'session-restore-31',
        }),
        expect.objectContaining({
          acceptanceCriteria: activeCheckpointSession.acceptance_criteria,
          key: 'MAG-31',
          source: 'jira',
          summary: 'Recover active checkpoint sessions',
        }),
      );
    });
  });

  it('returns controlled error feedback when a resume attempt fails', async () => {
    const user = userEvent.setup();
    const onSessionStarted = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({
      stories: [{ key: 'MAG-31', summary: 'Recover active checkpoint sessions' }],
    });
    vi.spyOn(api, 'fetchSessionInfo').mockResolvedValue({
      has_checkpoint: true,
      session: {
        current_phase: 'phase_3',
        jira_key: 'MAG-31',
        jira_summary: 'Recover active checkpoint sessions',
        log_entries: 12,
        phase_number: 3,
        phase_title: 'Precondition Formalization',
      },
    });
    vi.spyOn(api, 'resumeSession').mockRejectedValue(new Error('Checkpoint restore failed'));

    render(<SessionBootstrap onSessionStarted={onSessionStarted} />, {
      wrapper: createWrapper(),
    });

    await user.click(await screen.findByRole('button', { name: /select story mag-31/i }));
    await user.click(await screen.findByRole('button', { name: /resume session/i }));

    expect(await screen.findByText(/checkpoint restore failed/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start fresh session/i })).toBeInTheDocument();
    expect(onSessionStarted).not.toHaveBeenCalled();
  });

  it('renders a phase-aware checklist and timeline for the active session', async () => {
    const user = userEvent.setup();
    const onAcceptanceCriterionSelect = vi.fn();
    const onPhaseSelect = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });

    render(
      <SessionBootstrap
        activeSession={activeCheckpointSession}
        onAcceptanceCriterionSelect={onAcceptanceCriterionSelect}
        onPhaseSelect={onPhaseSelect}
        selectedAcceptanceCriterionIndex={1}
        selectedPhaseNumber={2}
      />,
      { wrapper: createWrapper() },
    );

    const checklist = await screen.findByRole('list', { name: /story checklist/i });
    const criteriaRows = within(checklist).getAllByRole('button');

    expect(criteriaRows).toHaveLength(2);
    expect(screen.getByText('workflow_state')).toBeInTheDocument();
    expect(screen.getByText(/passed/i)).toBeInTheDocument();

    await user.click(criteriaRows[0]);
    expect(onAcceptanceCriterionSelect).toHaveBeenCalledWith(0);

    const phaseTimeline = screen.getByRole('list', { name: /left rail phase timeline/i });
    const phaseItems = within(phaseTimeline).getAllByRole('button');

    expect(phaseItems).toHaveLength(7);
    expect(phaseItems[0]).toHaveAttribute('data-state', 'complete');
    expect(phaseItems[1]).toHaveAttribute('data-state', 'complete');
    expect(phaseItems[2]).toHaveAttribute('data-state', 'active');
    expect(phaseItems[3]).toHaveAttribute('data-state', 'pending');

    await user.click(phaseItems[1]);
    expect(onPhaseSelect).toHaveBeenCalledWith(2);
  });

  it('renders session health telemetry when usage data is available', async () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });

    render(<SessionBootstrap activeSession={activeCheckpointSession} />, {
      wrapper: createWrapper(),
    });

    const progress = await screen.findByRole('progressbar', { name: /token budget utilization/i });

    expect(progress).toHaveAttribute('aria-valuenow', '84');
    expect(screen.getByText(/12 \/ 50 calls/i)).toBeInTheDocument();
    expect(screen.getByText(/4m 32s/i)).toBeInTheDocument();
    expect(screen.getByText(/\$0.42/i)).toBeInTheDocument();
    expect(screen.getByText(/warning state/i)).toBeInTheDocument();
  });

  it('renders a clear fallback when usage telemetry is unavailable', async () => {
    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });

    render(
      <SessionBootstrap
        activeSession={{
          ...activeCheckpointSession,
          usage: null,
        }}
      />,
      { wrapper: createWrapper() },
    );

    expect(await screen.findByText(/telemetry unavailable/i)).toBeInTheDocument();
  });
});
