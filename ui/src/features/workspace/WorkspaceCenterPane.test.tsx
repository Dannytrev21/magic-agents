import { createRef } from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { WorkspaceCenterPane } from '@/features/workspace/WorkspaceCenterPane';
import type { StartNegotiationResponse } from '@/lib/api/types';

const activeSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Authenticated users can view their profile',
    },
  ],
  classifications: [
    {
      ac_index: 0,
      actor: 'authenticated_user',
      interface: { method: 'GET', path: '/api/v1/users/me' },
      type: 'api_behavior',
    },
  ],
  current_phase: 'phase_3',
  done: false,
  failure_modes: [
    {
      body: { error: 'unauthorized', message: 'Bearer token required' },
      id: 'FAIL-001',
      status: 401,
      violates: 'PRE-001',
    },
  ],
  invariants: [
    {
      id: 'INV-001',
      rule: 'Responses MUST NOT expose password fields.',
      source: 'constitution',
      type: 'security',
    },
  ],
  jira_key: 'MAG-201',
  jira_summary: 'Port the active phase workspace',
  negotiation_log: [
    {
      content: 'Failure mode enumeration produced 1 response path.',
      phase: 'phase_3',
      role: 'ai',
      timestamp: '2026-04-01T10:00:00Z',
    },
    {
      content: 'Please tighten the deleted-user response.',
      phase: 'phase_3',
      role: 'human',
      timestamp: '2026-04-01T10:01:00Z',
    },
  ],
  phase_number: 4,
  phase_title: 'Failure Mode Enumeration',
  postconditions: [
    {
      ac_index: 0,
      constraints: ['response.id MUST equal jwt.sub'],
      content_type: 'application/json',
      forbidden_fields: ['password'],
      schema: { id: { required: true, type: 'string' } },
      status: 200,
    },
  ],
  preconditions: [
    {
      category: 'authentication',
      description: 'A valid bearer token is present.',
      formal: "request.headers['Authorization'].startsWith('Bearer ')",
      id: 'PRE-001',
    },
  ],
  questions: ['Should soft-deleted users return 404 or 410?'],
  session_events: [
    {
      detail: 'MAG-201',
      timestamp: '2026-04-01T09:59:00Z',
      title: 'session_created',
    },
  ],
  session_id: 'session-u4',
  total_phases: 7,
  usage: null,
  verification_routing: {
    checklist: [],
    routing: [],
  },
  verdicts: [],
};

afterEach(() => {
  cleanup();
});

describe('WorkspaceCenterPane', () => {
  it('renders a sticky mini-rail with completed, active, and pending phase states', () => {
    const focusRef = createRef<HTMLElement>();
    const { container } = render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback="Need clearer deleted-user guidance"
        focusRef={focusRef}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    const stickyRail = container.querySelector('[data-sticky="true"]');
    const phaseRail = screen.getByRole('list', { name: /negotiation phases/i });
    const phaseButtons = within(phaseRail).getAllByRole('button');

    expect(stickyRail).toBeInTheDocument();
    expect(screen.getAllByText(/mag-201/i)).toHaveLength(2);
    expect(screen.getByRole('tab', { name: /negotiation/i })).toBeInTheDocument();
    expect(phaseButtons).toHaveLength(7);
    expect(phaseButtons[0]).toHaveAttribute('data-state', 'complete');
    expect(phaseButtons[3]).toHaveAttribute('data-state', 'active');
    expect(phaseButtons[4]).toHaveAttribute('data-state', 'pending');
  });

  it('renders a structured review surface with a summary-first hierarchy, clarifying questions, and raw payload fallback', () => {
    render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback="Need clearer deleted-user guidance"
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    expect(screen.getByText(/primary decision/i)).toBeInTheDocument();
    expect(screen.getByText(/failure responses are mapped/i)).toBeInTheDocument();
    expect(screen.getByText(/clarifying questions/i)).toBeInTheDocument();
    expect(screen.getByText(/404 or 410/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /approve phase/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /request revision/i })).toBeInTheDocument();
    expect(screen.getByText(/raw payload/i)).toBeInTheDocument();
    expect(screen.getByRole('log', { name: /phase transcript/i })).toBeInTheDocument();
  });

  it('routes revise feedback inline and disables duplicate submissions while an action is pending', async () => {
    const user = userEvent.setup();
    const onRevisePhase = vi.fn();
    const onDraftFeedbackChange = vi.fn();
    const { rerender } = render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback="Need clearer deleted-user guidance"
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={onDraftFeedbackChange}
        onPhaseSelect={vi.fn()}
        onRevisePhase={onRevisePhase}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    await user.type(screen.getByLabelText(/revision feedback/i), ' Please keep owner checks explicit.');
    await user.click(screen.getByRole('button', { name: /request revision/i }));

    expect(onDraftFeedbackChange).toHaveBeenCalled();
    expect(onRevisePhase).toHaveBeenCalledTimes(1);

    rerender(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback="Need clearer deleted-user guidance"
        focusRef={createRef<HTMLElement>()}
        isTransitionPending={false}
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={onDraftFeedbackChange}
        onPhaseSelect={vi.fn()}
        onRevisePhase={onRevisePhase}
        onViewChange={vi.fn()}
        phaseActionState={{
          activeAction: 'approve',
          isPending: true,
          message: 'Submitting approval',
          status: 'idle',
        }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    expect(screen.getByRole('button', { name: /approve phase/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /request revision/i })).toBeDisabled();
  });

  it('supports completed-phase reopening and suppresses quick jumps while the feedback field is focused', async () => {
    const user = userEvent.setup();
    const onPhaseSelect = vi.fn();

    render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback="Need clearer deleted-user guidance"
        focusRef={createRef<HTMLElement>()}
        isTransitionPending
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={onPhaseSelect}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'success' }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    await user.click(screen.getByRole('button', { name: /phase 2 happy path contract/i }));
    expect(onPhaseSelect).toHaveBeenCalledWith(2);

    await user.keyboard('3');
    expect(onPhaseSelect).toHaveBeenCalledWith(3);

    const feedback = screen.getByLabelText(/revision feedback/i);
    await user.click(feedback);
    await user.keyboard('2');

    await waitFor(() => {
      expect(onPhaseSelect).toHaveBeenCalledTimes(2);
    });
  });

  it('marks the active workspace region busy during in-place transitions', () => {
    render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending
        onApprovePhase={vi.fn()}
        onDraftFeedbackChange={vi.fn()}
        onPhaseSelect={vi.fn()}
        onRevisePhase={vi.fn()}
        onViewChange={vi.fn()}
        phaseActionState={{ activeAction: null, isPending: false, message: null, status: 'idle' }}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={4}
        statusLabel="Awaiting operator input"
        storySummary="Port the active phase workspace"
      />,
    );

    expect(screen.getByRole('region', { name: /active workspace region/i })).toHaveAttribute(
      'aria-busy',
      'true',
    );
  });
});
