import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import * as api from '@/lib/api/client';
import type { StartNegotiationResponse } from '@/lib/api/types';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

beforeEach(() => {
  vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
  vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });
  vi.spyOn(api, 'fetchSessionInfo').mockResolvedValue({ has_checkpoint: false });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const activeSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Operator can continue with the started Jira session from the rail.',
    },
  ],
  approved: false,
  done: false,
  jira_key: 'MAG-804',
  jira_summary: 'Manual fallback rail coverage',
  phase_number: 1,
  phase_title: 'Interface & Actor Discovery',
  session_id: 'session-ops-804',
  total_phases: 7,
};

describe('SessionBootstrap', () => {
  it('keeps manual entry available when Jira intake falls back', async () => {
    const user = userEvent.setup();

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    expect(await screen.findByText(/jira configuration required/i)).toBeInTheDocument();
    expect(screen.getByText(/jira is unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/manual entry stays available/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/story search/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /start session from jira/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /use manual entry/i }));

    await user.type(screen.getByLabelText(/jira key/i), 'MAG-801');
    await user.type(screen.getByLabelText(/summary/i), 'Manual fallback rail coverage');
    await user.type(
      screen.getByLabelText(/acceptance criteria/i),
      'Operator can continue from raw notes\nThe checklist stays visible in the rail',
    );

    expect(screen.getByRole('button', { name: /start session from manual story/i })).toBeEnabled();
    expect(screen.getByRole('list', { name: /story checklist/i })).toHaveTextContent(
      /operator can continue from raw notes/i,
    );
  });

  it('surfaces resumable Jira stories directly in the left rail', async () => {
    const user = userEvent.setup();

    vi.mocked(api.fetchJiraConfigured).mockResolvedValue({ configured: true });
    vi.mocked(api.fetchJiraStories).mockResolvedValue({
      stories: [{ key: 'MAG-802', status: 'In Progress', summary: 'Resume an existing session' }],
    });
    vi.mocked(api.fetchSessionInfo).mockResolvedValue({
      has_checkpoint: true,
      session: {
        approved: false,
        checkpoint_path: '.verify/checkpoints/MAG-802.json',
        current_phase: 'Failure Mode Enumeration',
        jira_key: 'MAG-802',
        log_entries: 14,
        phase_number: 4,
        phase_title: 'Failure Mode Enumeration',
      },
    });

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    await user.click(await screen.findByRole('button', { name: /select story mag-802/i }));

    await waitFor(() => {
      expect(screen.getByText(/resume from checkpoint/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /resume session/i })).toBeEnabled();
    expect(screen.getByText(/failure mode enumeration/i)).toBeInTheDocument();
    expect(screen.getByText(/14 log entries/i)).toBeInTheDocument();
  });

  it('resets the left rail scroll position when a new session becomes active', async () => {
    const { rerender } = render(
      <div data-testid="scroll-shell">
        <SessionBootstrap />
      </div>,
      { wrapper: createWrapper() },
    );

    const scrollShell = screen.getByTestId('scroll-shell');
    scrollShell.scrollTop = 180;

    rerender(
      <div data-testid="scroll-shell">
        <SessionBootstrap activeSession={activeSession} />
      </div>,
    );

    await waitFor(() => {
      expect(scrollShell.scrollTop).toBe(0);
    });
  });
});
