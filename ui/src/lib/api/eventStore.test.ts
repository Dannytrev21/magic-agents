import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import {
  createEventStore,
  EventStoreProvider,
  useBudgetEvents,
  useEventStore,
  useLatestEvent,
  usePhaseEvents,
  useValidationEvents,
} from '@/lib/api/eventStore';
import type { SSEEvent } from '@/lib/api/useSSE';

function makeWrapper(store: ReturnType<typeof createEventStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return EventStoreProvider({ store, children });
  };
}

describe('createEventStore', () => {
  it('starts with an empty event list', () => {
    const store = createEventStore();
    expect(store.getEvents()).toEqual([]);
  });

  it('dispatches events and stores them in order', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_1' });
    store.dispatch({ type: 'phase_complete', session_id: 's1', phase: 'phase_1' });

    expect(store.getEvents()).toHaveLength(2);
    expect(store.getEvents()[0].type).toBe('phase_start');
    expect(store.getEvents()[1].type).toBe('phase_complete');
  });

  it('enforces FIFO overflow at 100 events', () => {
    const store = createEventStore();

    for (let i = 0; i < 110; i++) {
      store.dispatch({ type: 'phase_progress', session_id: 's1', index: i });
    }

    const events = store.getEvents();
    expect(events).toHaveLength(100);
    // First event should be index 10 (oldest 10 were evicted)
    expect((events[0] as SSEEvent & { index: number }).index).toBe(10);
  });

  it('clears events when session changes', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_1' });
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_2' });

    expect(store.getEvents()).toHaveLength(2);
    store.clearForSession('s2');
    expect(store.getEvents()).toEqual([]);
  });

  it('does not clear when same session is set', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_1' });

    store.clearForSession('s1');
    // Same session set again — should NOT clear
    store.clearForSession('s1');
    expect(store.getEvents()).toEqual([]);
  });
});

describe('usePhaseEvents', () => {
  it('returns only phase-related events', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_1' });
    store.dispatch({ type: 'budget_warning', session_id: 's1' });
    store.dispatch({ type: 'phase_complete', session_id: 's1', phase: 'phase_1' });
    store.dispatch({ type: 'phase_error', session_id: 's1', phase: 'phase_2' });
    store.dispatch({ type: 'phase_progress', session_id: 's1', phase: 'phase_2' });

    const { result } = renderHook(() => usePhaseEvents(), {
      wrapper: makeWrapper(store),
    });

    expect(result.current).toHaveLength(4);
    expect(result.current.every((e) => e.type.startsWith('phase_'))).toBe(true);
  });
});

describe('useBudgetEvents', () => {
  it('returns only budget-related events', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1' });
    store.dispatch({ type: 'budget_warning', session_id: 's1' });
    store.dispatch({ type: 'budget_exceeded', session_id: 's1' });

    const { result } = renderHook(() => useBudgetEvents(), {
      wrapper: makeWrapper(store),
    });

    expect(result.current).toHaveLength(2);
    expect(result.current[0].type).toBe('budget_warning');
    expect(result.current[1].type).toBe('budget_exceeded');
  });
});

describe('useValidationEvents', () => {
  it('returns only validation_result events', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1' });
    store.dispatch({ type: 'validation_result', session_id: 's1', valid: true });
    store.dispatch({ type: 'budget_warning', session_id: 's1' });

    const { result } = renderHook(() => useValidationEvents(), {
      wrapper: makeWrapper(store),
    });

    expect(result.current).toHaveLength(1);
    expect(result.current[0].type).toBe('validation_result');
  });
});

describe('useLatestEvent', () => {
  it('returns the most recent event of a given type', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_1' });
    store.dispatch({ type: 'phase_start', session_id: 's1', phase: 'phase_2' });

    const { result } = renderHook(() => useLatestEvent('phase_start'), {
      wrapper: makeWrapper(store),
    });

    expect(result.current).toEqual(expect.objectContaining({ phase: 'phase_2' }));
  });

  it('returns null when no matching event exists', () => {
    const store = createEventStore();

    const { result } = renderHook(() => useLatestEvent('budget_exceeded'), {
      wrapper: makeWrapper(store),
    });

    expect(result.current).toBeNull();
  });
});

describe('useEventStore', () => {
  it('returns all events from the store', () => {
    const store = createEventStore();
    store.dispatch({ type: 'phase_start', session_id: 's1' });
    store.dispatch({ type: 'budget_warning', session_id: 's1' });

    const { result } = renderHook(() => useEventStore(), {
      wrapper: makeWrapper(store),
    });

    expect(result.current.events).toHaveLength(2);
    expect(typeof result.current.dispatch).toBe('function');
    expect(typeof result.current.clear).toBe('function');
  });

  it('re-renders when new events are dispatched via the hook', () => {
    const store = createEventStore();

    const { result } = renderHook(() => useEventStore(), {
      wrapper: makeWrapper(store),
    });

    expect(result.current.events).toHaveLength(0);

    act(() => {
      result.current.dispatch({ type: 'phase_start', session_id: 's1' });
    });

    expect(result.current.events).toHaveLength(1);
  });
});
