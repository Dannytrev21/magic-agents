import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { AppProviders } from '@/app/AppProviders';
import { OperatorWorkspacePage } from '@/features/workspace/OperatorWorkspacePage';
import type { StartNegotiationResponse } from '@/lib/api/types';
import * as api from '@/lib/api/client';

const originalInnerWidth = window.innerWidth;
const originalLocalStorage = window.localStorage;

const completedSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Operator can approve the contract and launch verification from one surface',
    },
  ],
  approved: false,
  done: true,
  ears_statements: [
    {
      id: 'EARS-001',
      pattern: 'EVENT_DRIVEN',
      statement:
        'WHEN the operator finalizes the contract THEN the system SHALL gate verification behind explicit approval',
      traces_to: 'REQ-001.success',
    },
  ],
  jira_key: 'MAG-803',
  jira_summary: 'Verification launch wiring',
  phase_number: 7,
  phase_title: 'EARS Formalization',
  session_id: 'session-u8-verification',
  total_phases: 7,
  verification_routing: {
    checklist: [],
    routing: [],
  },
  verdicts: [],
};

function installStorage() {
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
}

function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: width,
    writable: true,
  });
  window.dispatchEvent(new Event('resize'));
}

function renderWorkspace(options?: {
  initialEntry?: string;
  initialSession?: StartNegotiationResponse | null;
  initialStorySummary?: string | null;
}) {
  const {
    initialEntry = '/?view=overview&inspector=evidence&pane=workspace',
    initialSession = null,
    initialStorySummary = null,
  } = options ?? {};

  return render(
    <AppProviders>
      <MemoryRouter initialEntries={[initialEntry]}>
        <OperatorWorkspacePage
          initialSession={initialSession}
          initialStorySummary={initialStorySummary}
        />
      </MemoryRouter>
    </AppProviders>,
  );
}

beforeEach(() => {
  setViewport(1440);
  installStorage();
  vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: false });
  vi.spyOn(api, 'fetchJiraStories').mockResolvedValue({ stories: [] });
  vi.spyOn(api, 'fetchSessionInfo').mockResolvedValue({ has_checkpoint: false });
  vi.spyOn(api, 'fetchSkills').mockResolvedValue([]);
  vi.spyOn(api, 'fetchScanStatus').mockResolvedValue({
    project_root: '/Users/dannytrevino/development/magic-agents',
    scanned: false,
    summary: 'No scan yet',
  });
  vi.spyOn(api, 'startNegotiation').mockImplementation(async (payload) => ({
    acceptance_criteria: payload.acceptance_criteria,
    done: false,
    jira_key: payload.jira_key,
    jira_summary: payload.jira_summary,
    phase_number: 1,
    phase_title: 'Interface & Actor Discovery',
    session_id: 'session-u8-manual',
    total_phases: 7,
  }));
  vi.spyOn(api, 'respondToSession').mockImplementation(async (payload) => ({
    acceptance_criteria: [
      { checked: false, index: 0, text: 'Operator can drive the phase loop from one surface' },
    ],
    done: false,
    jira_key: 'MAG-804',
    jira_summary: 'Manual story integration',
    phase_number: payload.input === 'approve' ? 2 : 1,
    phase_title:
      payload.input === 'approve'
        ? 'Happy Path Contract'
        : 'Interface & Actor Discovery',
    revised: payload.input !== 'approve',
    session_id: payload.session_id,
    total_phases: 7,
  }));
  vi.spyOn(api, 'approveEars').mockResolvedValue({
    approved: true,
    approved_at: '2026-04-01T16:30:00Z',
    approved_by: 'web_operator',
  });
  vi.spyOn(api, 'streamPipelineEvents').mockImplementation(async (_sessionId, onEvent) => {
    onEvent({
      type: 'step',
      step: 'compile',
      status: 'running',
      message: 'Compiling spec...',
    });
    onEvent({
      type: 'done',
      all_passed: true,
      message: 'Pipeline complete',
      success: true,
      verdicts: [
        {
          ac_checkbox: 0,
          ac_text: 'Operator can approve the contract and launch verification from one surface',
          passed: true,
        },
      ],
    });
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  Object.defineProperty(window, 'innerWidth', {
    configurable: true,
    value: originalInnerWidth,
    writable: true,
  });
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: originalLocalStorage,
  });
});

describe('Operator workspace integration', () => {
  it('supports manual story intake, revision requests, and in-place phase approval', async () => {
    const user = userEvent.setup();

    renderWorkspace();

    expect(await screen.findByText(/jira is unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /use manual entry/i }));
    await user.type(screen.getByLabelText(/jira key/i), 'MAG-804');
    await user.type(screen.getByLabelText(/summary/i), 'Manual story integration');
    await user.type(
      screen.getByLabelText(/acceptance criteria/i),
      'Operator can drive the phase loop from one surface',
    );
    await user.click(screen.getByRole('button', { name: /start session from manual story/i }));

    expect(await screen.findByText(/session-u8-manual/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('status', { name: /session status/i })).toHaveTextContent(
        /awaiting operator input/i,
      );
    });

    await user.type(screen.getByLabelText(/^notes$/i), 'Clarify the actor and interface before advancing.');
    await user.click(screen.getByRole('button', { name: /^revise$/i }));

    await waitFor(() => {
      expect(api.respondToSession).toHaveBeenCalledWith({
        input: 'Clarify the actor and interface before advancing.',
        session_id: 'session-u8-manual',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('status', { name: /session status/i })).toHaveTextContent(
        /revising phase output/i,
      );
    });

    await user.click(screen.getByRole('button', { name: /^approve$/i }));

    await waitFor(() => {
      expect(api.respondToSession).toHaveBeenLastCalledWith({
        input: 'approve',
        session_id: 'session-u8-manual',
      });
    });
    await waitFor(() => {
      expect(screen.getByRole('status', { name: /session status/i })).toHaveTextContent(
        /awaiting operator input/i,
      );
    });
    expect(screen.getAllByText(/happy path contract/i).length).toBeGreaterThan(0);
  });

  it('launches verification from the page-level workspace and preserves the pipeline result', async () => {
    const user = userEvent.setup();

    renderWorkspace({
      initialEntry: '/?view=verification&inspector=evidence&pane=workspace',
      initialSession: completedSession,
      initialStorySummary: completedSession.jira_summary,
    });

    await user.click(await screen.findByRole('button', { name: /approve ears/i }));
    expect(await screen.findByText(/approved by web_operator/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /run full pipeline/i }));

    expect(await screen.findByText(/pipeline complete/i)).toBeInTheDocument();
    expect(await screen.findByRole('log', { name: /pipeline console/i })).toHaveTextContent(
      /compiling spec/i,
    );
    expect(screen.getByText(/1 passed/i)).toBeInTheDocument();
  });

  it('switches into the verification workspace after the final approval marks negotiation done', async () => {
    const user = userEvent.setup();

    vi.mocked(api.respondToSession).mockResolvedValueOnce({
      ...completedSession,
      approved: false,
      done: true,
      session_id: 'session-u8-finalize',
    });

    renderWorkspace({
      initialEntry: '/?view=negotiation&inspector=evidence&pane=workspace',
      initialSession: {
        ...completedSession,
        done: false,
        session_id: 'session-u8-finalize',
      },
      initialStorySummary: completedSession.jira_summary,
    });

    await user.click(screen.getByRole('button', { name: /^approve$/i }));

    await waitFor(() => {
      expect(api.respondToSession).toHaveBeenCalledWith({
        input: 'approve',
        session_id: 'session-u8-finalize',
      });
    });

    expect(await screen.findByText(/proof artifacts, execution, and jira feedback stay in one surface/i)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /approve ears/i })).toBeInTheDocument();
  });
});
