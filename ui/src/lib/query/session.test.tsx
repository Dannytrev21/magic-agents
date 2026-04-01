import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import * as api from '@/lib/api/client';

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
});
