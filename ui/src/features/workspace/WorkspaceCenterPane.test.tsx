import { createRef } from 'react';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { WorkspaceCenterPane } from '@/features/workspace/WorkspaceCenterPane';
import type { StartNegotiationResponse } from '@/lib/api/types';

const activeSession: StartNegotiationResponse = {
  done: false,
  jira_key: 'MAG-201',
  phase_number: 3,
  phase_title: 'Precondition Formalization',
  session_id: 'session-u2',
  total_phases: 7,
};

afterEach(() => {
  cleanup();
});

describe('WorkspaceCenterPane', () => {
  it('renders a sticky seven-phase rail with active, complete, and pending states', () => {
    const focusRef = createRef<HTMLElement>();
    const { container } = render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="negotiation"
        draftFeedback=""
        focusRef={focusRef}
        isTransitionPending={false}
        onViewChange={vi.fn()}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={null}
        statusLabel="Awaiting operator input"
      />,
    );

    const stickyRail = container.querySelector('[data-sticky="true"]');
    const phaseRail = screen.getByRole('list', { name: /negotiation phases/i });
    const phaseItems = within(phaseRail).getAllByRole('listitem');

    expect(stickyRail).toBeInTheDocument();
    expect(phaseItems).toHaveLength(7);
    expect(phaseItems[0]).toHaveAttribute('data-state', 'complete');
    expect(phaseItems[1]).toHaveAttribute('data-state', 'complete');
    expect(phaseItems[2]).toHaveAttribute('data-state', 'active');
    expect(phaseItems[3]).toHaveAttribute('data-state', 'pending');
    expect(screen.getByText(/awaiting operator input/i)).toBeInTheDocument();
    expect(screen.getByText('session-u2')).toBeInTheDocument();
    expect(screen.getByText(/in-place workspace/i)).toBeInTheDocument();
  });

  it('switches center views without remounting the shell route', async () => {
    const user = userEvent.setup();
    const onViewChange = vi.fn();

    render(
      <WorkspaceCenterPane
        activeSession={activeSession}
        activeView="overview"
        draftFeedback=""
        focusRef={createRef<HTMLElement>()}
        isTransitionPending
        onViewChange={onViewChange}
        selectedAcceptanceCriterionIndex={null}
        selectedPhaseNumber={null}
        statusLabel="Awaiting operator input"
      />,
    );

    await user.click(screen.getByRole('tab', { name: /traceability/i }));

    expect(onViewChange).toHaveBeenCalledWith('traceability');
    expect(screen.getByText(/updating in place/i)).toBeInTheDocument();
  });
});
