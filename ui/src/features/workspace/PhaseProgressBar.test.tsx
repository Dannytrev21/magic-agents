import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PhaseProgressBar } from '@/features/workspace/PhaseProgressBar';
import { createEventStore, EventStoreProvider } from '@/lib/api/eventStore';
import type { EventStore } from '@/lib/api/eventStore';
import type { ReactNode } from 'react';

function makeWrapper(store: EventStore) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return EventStoreProvider({ store, children });
  };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe('PhaseProgressBar', () => {
  it('renders nothing when no phase is active', () => {
    const store = createEventStore();
    const { container } = render(<PhaseProgressBar />, {
      wrapper: makeWrapper(store),
    });

    expect(container.querySelector('[role="progressbar"]')).toBeNull();
  });

  it('shows a progress bar when a phase_start event arrives', () => {
    const store = createEventStore();
    const { container } = render(<PhaseProgressBar />, {
      wrapper: makeWrapper(store),
    });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    expect(container.querySelector('[role="progressbar"]')).toBeInTheDocument();
  });

  it('displays elapsed time that counts up', () => {
    const store = createEventStore();
    render(<PhaseProgressBar />, { wrapper: makeWrapper(store) });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    expect(screen.getByText('0s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(screen.getByText('5s')).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(58000);
    });

    expect(screen.getByText('1m 03s')).toBeInTheDocument();
  });

  it('updates step description from phase_progress events', () => {
    const store = createEventStore();
    render(<PhaseProgressBar />, { wrapper: makeWrapper(store) });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    act(() => {
      store.dispatch({
        type: 'phase_progress',
        session_id: 's1',
        phase: 'phase_1',
        turn: 1,
        message: 'Classifying acceptance criteria',
      });
    });

    expect(screen.getByText('Classifying acceptance criteria')).toBeInTheDocument();
  });

  it('stays active when phase_start and phase_progress arrive in the same batch', () => {
    const store = createEventStore();
    render(<PhaseProgressBar />, { wrapper: makeWrapper(store) });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
      store.dispatch({
        type: 'phase_progress',
        session_id: 's1',
        phase: 'phase_1',
        turn: 1,
        message: 'Formalizing preconditions',
      });
    });

    expect(
      screen.getByRole('progressbar', { name: /phase progress in the workspace header/i }),
    ).toHaveAttribute('data-state', 'active');
    expect(screen.getByText('Formalizing preconditions')).toBeInTheDocument();
  });

  it('marks the indicator complete on phase_complete and hides after the linger window', () => {
    const store = createEventStore();
    const { container } = render(<PhaseProgressBar />, {
      wrapper: makeWrapper(store),
    });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    expect(container.querySelector('[role="progressbar"]')).toBeInTheDocument();

    act(() => {
      store.dispatch({
        type: 'phase_complete',
        session_id: 's1',
        phase: 'phase_1',
        result_count: 5,
        phase_index: 0,
      });
    });

    expect(container.querySelector('[role="progressbar"]')).toHaveAttribute('data-state', 'complete');

    act(() => {
      vi.advanceTimersByTime(320);
    });

    expect(container.querySelector('[role="progressbar"]')).toBeNull();
  });

  it('shows error state on phase_error', () => {
    const store = createEventStore();
    const { container } = render(<PhaseProgressBar />, {
      wrapper: makeWrapper(store),
    });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    act(() => {
      store.dispatch({
        type: 'phase_error',
        session_id: 's1',
        phase: 'phase_1',
        error: 'Something went wrong',
        phase_index: 0,
      });
    });

    const bar = container.querySelector('[role="progressbar"]');
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveAttribute('data-state', 'error');
  });

  it('resets when a new phase_start arrives', () => {
    const store = createEventStore();
    render(<PhaseProgressBar />, { wrapper: makeWrapper(store) });

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(screen.getByText('10s')).toBeInTheDocument();

    act(() => {
      store.dispatch({
        type: 'phase_start',
        session_id: 's1',
        phase: 'phase_2',
        phase_index: 1,
      });
    });

    expect(screen.getByText('0s')).toBeInTheDocument();
  });
});
