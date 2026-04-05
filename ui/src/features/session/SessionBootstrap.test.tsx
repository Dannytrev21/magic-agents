import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import * as api from '@/lib/api/client';

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

describe('SessionBootstrap', () => {
  it('keeps manual entry available when Jira intake falls back', async () => {
    const user = userEvent.setup();

    render(<SessionBootstrap />, { wrapper: createWrapper() });

    expect(await screen.findByText(/jira configuration required/i)).toBeInTheDocument();
    expect(screen.getByText(/manual entry remains available/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /manual entry/i }));
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
});
