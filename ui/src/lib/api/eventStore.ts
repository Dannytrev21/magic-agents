import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
} from 'react';
import type { ReactNode } from 'react';
import type { SSEEvent } from '@/lib/api/useSSE';

const MAX_EVENTS = 100;

const PHASE_EVENT_TYPES = new Set([
  'phase_start',
  'phase_progress',
  'phase_complete',
  'phase_error',
]);

const BUDGET_EVENT_TYPES = new Set(['budget_warning', 'budget_exceeded']);

const VALIDATION_EVENT_TYPES = new Set(['validation_result']);

// ---------------------------------------------------------------------------
// Store core (framework-agnostic)
// ---------------------------------------------------------------------------

export type EventStore = {
  dispatch: (event: SSEEvent) => void;
  getEvents: () => SSEEvent[];
  subscribe: (listener: () => void) => () => void;
  clearForSession: (sessionId: string) => void;
  clear: () => void;
};

export function createEventStore(): EventStore {
  let events: SSEEvent[] = [];
  let currentSessionId: string | null = null;
  const listeners = new Set<() => void>();

  function notify() {
    for (const listener of listeners) {
      listener();
    }
  }

  function dispatch(event: SSEEvent) {
    events = [...events, event];
    if (events.length > MAX_EVENTS) {
      events = events.slice(events.length - MAX_EVENTS);
    }
    notify();
  }

  function getEvents() {
    return events;
  }

  function subscribe(listener: () => void) {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }

  function clearForSession(sessionId: string) {
    if (sessionId !== currentSessionId) {
      events = [];
      currentSessionId = sessionId;
      notify();
    }
  }

  function clear() {
    events = [];
    currentSessionId = null;
    notify();
  }

  return { dispatch, getEvents, subscribe, clearForSession, clear };
}

// ---------------------------------------------------------------------------
// React context & provider
// ---------------------------------------------------------------------------

const EventStoreContext = createContext<EventStore | null>(null);

type EventStoreProviderProps = {
  store: EventStore;
  children: ReactNode;
};

export function EventStoreProvider({ store, children }: EventStoreProviderProps) {
  return createElement(EventStoreContext.Provider, { value: store }, children);
}

function useStore(): EventStore {
  const store = useContext(EventStoreContext);
  if (!store) {
    throw new Error('useEventStore must be used within an EventStoreProvider');
  }
  return store;
}

// ---------------------------------------------------------------------------
// Selector hooks
// ---------------------------------------------------------------------------

/**
 * Access the full event store — events array, dispatch, and clear.
 */
export function useEventStore() {
  const store = useStore();
  const events = useSyncExternalStore(store.subscribe, store.getEvents);
  return { events, dispatch: store.dispatch, clear: store.clear };
}

/**
 * Returns only phase lifecycle events (start, progress, complete, error).
 */
export function usePhaseEvents(): SSEEvent[] {
  const store = useStore();
  const events = useSyncExternalStore(store.subscribe, store.getEvents);
  return useMemo(() => events.filter((e) => PHASE_EVENT_TYPES.has(e.type)), [events]);
}

/**
 * Returns only budget-related events (warning, exceeded).
 */
export function useBudgetEvents(): SSEEvent[] {
  const store = useStore();
  const events = useSyncExternalStore(store.subscribe, store.getEvents);
  return useMemo(() => events.filter((e) => BUDGET_EVENT_TYPES.has(e.type)), [events]);
}

/**
 * Returns only validation_result events.
 */
export function useValidationEvents(): SSEEvent[] {
  const store = useStore();
  const events = useSyncExternalStore(store.subscribe, store.getEvents);
  return useMemo(() => events.filter((e) => VALIDATION_EVENT_TYPES.has(e.type)), [events]);
}

/**
 * Returns the most recent event of the given type, or null.
 */
export function useLatestEvent(type: string): SSEEvent | null {
  const store = useStore();
  const events = useSyncExternalStore(store.subscribe, store.getEvents);
  return useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].type === type) {
        return events[i];
      }
    }
    return null;
  }, [events, type]);
}
