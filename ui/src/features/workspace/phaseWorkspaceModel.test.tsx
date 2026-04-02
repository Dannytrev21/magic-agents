import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EventStoreProvider, createEventStore, usePhaseEvents } from '@/lib/api/eventStore';
import { usePhaseWorkspaceModel } from '@/features/workspace/phaseWorkspaceModel';

class MockEventSource {
  static instances: MockEventSource[] = [];

  onerror: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  closed = false;

  constructor(public readonly url: string) {
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent);
  }

  simulateOpen() {
    this.onopen?.();
  }
}

function Probe({ sessionId }: { sessionId: string | null }) {
  const { connectionStatus } = usePhaseWorkspaceModel(sessionId);
  const phaseEvents = usePhaseEvents();

  return (
    <div>
      <output data-testid="connection-status">{connectionStatus}</output>
      <output data-testid="phase-event-count">{phaseEvents.length}</output>
    </div>
  );
}

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal('EventSource', MockEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('usePhaseWorkspaceModel', () => {
  it('bridges the SSE status into UI state and dispatches incoming phase events to the store', async () => {
    const store = createEventStore();

    render(
      <EventStoreProvider store={store}>
        <Probe sessionId="session-123" />
      </EventStoreProvider>,
    );

    expect(MockEventSource.instances).toHaveLength(1);
    expect(screen.getByTestId('connection-status')).toHaveTextContent('connecting');
    expect(screen.getByTestId('phase-event-count')).toHaveTextContent('0');

    act(() => {
      MockEventSource.instances[0].simulateOpen();
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_start',
        session_id: 'session-123',
        phase: 'phase_3',
        phase_index: 2,
      });
    });

    expect(screen.getByTestId('connection-status')).toHaveTextContent('connected');

    await waitFor(() => {
      expect(screen.getByTestId('phase-event-count')).toHaveTextContent('1');
    });
  });

  it('keeps back-to-back phase events when they arrive in the same React batch', async () => {
    const store = createEventStore();

    render(
      <EventStoreProvider store={store}>
        <Probe sessionId="session-123" />
      </EventStoreProvider>,
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_start',
        session_id: 'session-123',
        phase: 'phase_3',
        phase_index: 2,
      });
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_progress',
        session_id: 'session-123',
        phase: 'phase_3',
        phase_index: 2,
        message: 'Scanning repository',
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('phase-event-count')).toHaveTextContent('2');
    });
  });

  it('clears session-scoped events when the active session is removed', async () => {
    const store = createEventStore();

    const { rerender } = render(
      <EventStoreProvider store={store}>
        <Probe sessionId="session-123" />
      </EventStoreProvider>,
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_start',
        session_id: 'session-123',
        phase: 'phase_3',
        phase_index: 2,
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId('phase-event-count')).toHaveTextContent('1');
    });

    rerender(
      <EventStoreProvider store={store}>
        <Probe sessionId={null} />
      </EventStoreProvider>,
    );

    expect(screen.getByTestId('connection-status')).toHaveTextContent('disconnected');

    await waitFor(() => {
      expect(screen.getByTestId('phase-event-count')).toHaveTextContent('0');
    });
  });
});
