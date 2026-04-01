import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRef, type ReactNode } from 'react';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { WorkspaceCenterPane } from '@/features/workspace/WorkspaceCenterPane';
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

const completedSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Operator can approve the negotiated EARS contract before running verification',
    },
  ],
  approved: false,
  done: true,
  ears_statements: [
    {
      id: 'EARS-001',
      pattern: 'EVENT_DRIVEN',
      statement:
        'WHEN the operator finalizes the negotiated contract THEN the system SHALL require explicit approval before verification execution begins',
      traces_to: 'REQ-001.success',
    },
  ],
  jira_key: 'MAG-601',
  jira_summary: 'Verification console approval gate',
  phase_number: 7,
  phase_title: 'EARS Formalization',
  session_id: 'session-u6',
  summary: {
    jira_key: 'MAG-601',
  },
  total_phases: 7,
  verdicts: [],
  verification_routing: {
    checklist: [],
    routing: [],
  },
};

beforeEach(() => {
  vi.spyOn(api, 'fetchJiraConfigured').mockResolvedValue({ configured: true });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Workspace verification console', () => {
  it('requires explicit EARS approval before enabling verification actions', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'approveEars').mockResolvedValue({
      approved: true,
      approved_at: '2026-04-01T13:04:00Z',
      approved_by: 'web_operator',
    });

    render(
      <WorkspaceCenterPane
        activeSession={completedSession}
        activeView="verification"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={0}
        selectedPhaseNumber={7}
        statusLabel="Verification-ready session"
        storySummary="Verification console approval gate"
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.getByText(/ears approval required/i)).toBeInTheDocument();

    const compileButton = screen.getByRole('button', { name: /compile spec/i });
    const generateButton = screen.getByRole('button', { name: /generate tests/i });
    const pipelineButton = screen.getByRole('button', { name: /run full pipeline/i });

    expect(compileButton).toBeDisabled();
    expect(generateButton).toBeDisabled();
    expect(pipelineButton).toBeDisabled();

    await user.click(screen.getByRole('button', { name: /approve ears/i }));

    await waitFor(() => {
      expect(api.approveEars).toHaveBeenCalledWith({
        approved_by: 'web_operator',
        session_id: 'session-u6',
      });
    });

    expect(await screen.findByText(/approved by web_operator/i)).toBeInTheDocument();
    expect(screen.getByText(/2026-04-01T13:04:00Z/i)).toBeInTheDocument();
    expect(compileButton).toBeEnabled();
    expect(pipelineButton).toBeEnabled();
  });

  it('shows compiled specs and generated tests in revisit-friendly artifact tabs', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'approveEars').mockResolvedValue({
      approved: true,
      approved_at: '2026-04-01T13:04:00Z',
      approved_by: 'web_operator',
    });
    vi.spyOn(api, 'compileSpec').mockResolvedValue({
      requirements: [{ ac_checkbox: 0, id: 'REQ-001' }],
      spec_content: 'requirements:\n  - id: REQ-001\n    title: Approval gate\n',
      spec_path: 'specs/MAG-601.yaml',
      traceability: { ac_mappings: [] },
    });
    vi.spyOn(api, 'generateTests').mockResolvedValue({
      all_passed: false,
      steps: [{ step: 'generate', status: 'ok' }],
      test_content:
        'def test_req_001_success():\n    assert True\n\ndef test_req_001_fail_001():\n    assert False\n',
      test_path: 'tests/test_mag_601.py',
      verdicts: [],
    });

    render(
      <WorkspaceCenterPane
        activeSession={completedSession}
        activeView="verification"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={0}
        selectedPhaseNumber={7}
        statusLabel="Verification-ready session"
        storySummary="Verification console approval gate"
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByRole('button', { name: /approve ears/i }));
    await user.click(await screen.findByRole('button', { name: /compile spec/i }));

    expect(await screen.findByText(/specs\/MAG-601.yaml/i)).toBeInTheDocument();
    expect(screen.getByText(/REQ-001/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /generate tests/i }));

    expect(await screen.findByText(/tests\/test_mag_601.py/i)).toBeInTheDocument();
    expect(screen.getByText(/test_req_001_success/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /spec yaml/i }));
    expect(screen.getByText(/requirements:/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /generated tests/i }));
    expect(screen.getByText(/test_req_001_fail_001/i)).toBeInTheDocument();
  });

  it('streams pipeline events into a live console and preserves the final run state', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'approveEars').mockResolvedValue({
      approved: true,
      approved_at: '2026-04-01T13:04:00Z',
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
        type: 'step',
        step: 'compile',
        status: 'done',
        message: 'Compiled spec',
      });
      onEvent({
        type: 'step',
        step: 'generate',
        status: 'skipped',
        message: 'Reused generated tests',
      });
      onEvent({
        type: 'done',
        all_passed: true,
        message: 'Pipeline complete',
        success: true,
        verdicts: [{ ac_checkbox: 0, ac_text: completedSession.acceptance_criteria?.[0].text, passed: true }],
      });
    });

    render(
      <WorkspaceCenterPane
        activeSession={completedSession}
        activeView="verification"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={0}
        selectedPhaseNumber={7}
        statusLabel="Verification-ready session"
        storySummary="Verification console approval gate"
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByRole('button', { name: /approve ears/i }));
    await user.click(await screen.findByRole('button', { name: /run full pipeline/i }));

    expect(await screen.findByText(/compiling spec/i)).toBeInTheDocument();
    expect(screen.getByText(/reused generated tests/i)).toBeInTheDocument();
    expect(screen.getByText(/pipeline complete/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /pipeline console/i })).toBeInTheDocument();
    expect(screen.getByText(/^complete$/i)).toBeInTheDocument();
  });

  it('renders verdicts with evidence detail and posts Jira feedback from the post-run surface', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'approveEars').mockResolvedValue({
      approved: true,
      approved_at: '2026-04-01T13:04:00Z',
      approved_by: 'web_operator',
    });
    vi.spyOn(api, 'compileSpec').mockResolvedValue({
      requirements: [{ ac_checkbox: 0, id: 'REQ-001' }],
      spec_content: 'requirements:\n  - id: REQ-001\n',
      spec_path: 'specs/MAG-601.yaml',
      traceability: { ac_mappings: [] },
    });
    vi.spyOn(api, 'generateTests').mockResolvedValue({
      all_passed: false,
      steps: [{ step: 'generate', status: 'ok' }],
      test_content: 'def test_req_001_success():\n    assert True\n',
      test_path: 'tests/test_mag_601.py',
      verdicts: [
        {
          ac_checkbox: 0,
          ac_text: 'Operator can approve the negotiated EARS contract before running verification',
          evidence: [
            {
              details: "Test 'test_req_001_success' passed",
              passed: true,
              ref: 'REQ-001.success',
              verification_type: 'test_result',
            },
          ],
          passed: true,
          summary: '1/1 verifications passed',
        },
      ],
    });
    vi.spyOn(api, 'postJiraUpdate').mockResolvedValue({
      checkboxes_ticked: 1,
      evidence_posted: true,
      jira_key: 'MAG-601',
      status: 'ok',
    });

    render(
      <WorkspaceCenterPane
        activeSession={completedSession}
        activeView="verification"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={0}
        selectedPhaseNumber={7}
        statusLabel="Verification-ready session"
        storySummary="Verification console approval gate"
      />,
      { wrapper: createWrapper() },
    );

    await user.click(screen.getByRole('button', { name: /approve ears/i }));
    await user.click(await screen.findByRole('button', { name: /compile spec/i }));
    await user.click(await screen.findByRole('button', { name: /generate tests/i }));

    expect(await screen.findByText(/1\/1 verifications passed/i)).toBeInTheDocument();
    expect(screen.getByText(/REQ-001.success/i)).toBeInTheDocument();
    expect(screen.getByText(/Test 'test_req_001_success' passed/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /send jira feedback/i }));

    expect(await screen.findByText(/1 checkbox updated\. evidence posted\./i)).toBeInTheDocument();
  });
});
