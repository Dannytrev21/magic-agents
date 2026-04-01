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

    expect(screen.getByText(/loading workspace context/i)).toBeInTheDocument();
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
      expect(screen.getByText(/workspace bootstrap failed/i)).toBeInTheDocument();
    });
  });

  it('returns the active story summary when a manual session starts', async () => {
    const user = userEvent.setup();
    const onSessionStarted = vi.fn();

    vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
    vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });
    vi.spyOn(api, 'startNegotiation').mockResolvedValue({
      done: false,
      jira_key: 'DEMO-UI',
      phase_number: 1,
      phase_title: 'Interface & Actor Discovery',
      session_id: 'session-001',
      total_phases: 7,
    });

    render(<SessionBootstrap onSessionStarted={onSessionStarted} />, {
      wrapper: createWrapper(),
    });

    await user.click(screen.getByRole('button', { name: /start negotiation session/i }));

    await waitFor(() => {
      expect(onSessionStarted).toHaveBeenCalledWith(
        expect.objectContaining({
          jira_key: 'DEMO-UI',
          session_id: 'session-001',
        }),
        'Operator workspace foundation',
      );
    });
  });
});
