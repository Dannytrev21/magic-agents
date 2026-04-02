import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSSE } from '@/lib/api/useSSE';

/**
 * Minimal EventSource mock that lets tests simulate open, message, and error.
 */
class MockEventSource {
  static instances: MockEventSource[] = [];

  public readyState = 0; // CONNECTING
  public onopen: ((ev: Event) => void) | null = null;
  public onmessage: ((ev: MessageEvent) => void) | null = null;
  public onerror: ((ev: Event) => void) | null = null;
  public url: string;
  public closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
    this.readyState = 2; // CLOSED
  }

  simulateOpen() {
    this.readyState = 1; // OPEN
    this.onopen?.(new Event('open'));
  }

  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }

  simulateError() {
    this.readyState = 2; // CLOSED
    this.onerror?.(new Event('error'));
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal('EventSource', MockEventSource);
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('useSSE', () => {
  it('connects to the SSE endpoint and reports connected status', async () => {
    const { result } = renderHook(() => useSSE('test-session'));

    expect(result.current.status).toBe('connecting');
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('/api/events/test-session');

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.status).toBe('connected');
  });

  it('receives events and stores them', async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() => useSSE('test-session', { onEvent }));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateMessage({
        type: 'phase_start',
        session_id: 'test-session',
        phase: 'phase_1',
        phase_index: 0,
      });
    });

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'phase_start', phase: 'phase_1' }),
    );
    expect(result.current.lastEvent).toEqual(
      expect.objectContaining({ type: 'phase_start' }),
    );
  });

  it('reconnects with exponential backoff on connection drop', async () => {
    renderHook(() => useSSE('test-session'));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    // simulate connection drop
    act(() => {
      MockEventSource.instances[0].simulateError();
    });

    expect(MockEventSource.instances).toHaveLength(1); // not reconnected yet

    // advance past first backoff (1000ms)
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances).toHaveLength(2); // reconnected
    expect(MockEventSource.instances[1].url).toBe('/api/events/test-session');
  });

  it('reports reconnecting status during backoff', () => {
    const { result } = renderHook(() => useSSE('test-session'));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    act(() => {
      MockEventSource.instances[0].simulateError();
    });

    expect(result.current.status).toBe('reconnecting');
  });

  it('reports disconnected after max retries exhausted', () => {
    const { result } = renderHook(() => useSSE('test-session', { maxRetries: 2 }));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    // Retry 1
    act(() => {
      MockEventSource.instances[0].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Retry 2
    act(() => {
      MockEventSource.instances[1].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Retry 3 - exceeds maxRetries
    act(() => {
      MockEventSource.instances[2].simulateError();
    });

    expect(result.current.status).toBe('disconnected');
  });

  it('resets backoff after successful reconnection', () => {
    const { result } = renderHook(() => useSSE('test-session'));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    // First disconnect
    act(() => {
      MockEventSource.instances[0].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000); // first backoff
    });

    // Successful reconnect
    act(() => {
      MockEventSource.instances[1].simulateOpen();
    });
    expect(result.current.status).toBe('connected');

    // Second disconnect - backoff should reset to 1s, not 2s
    act(() => {
      MockEventSource.instances[1].simulateError();
    });
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances).toHaveLength(3);
  });

  it('cleans up the EventSource on unmount', () => {
    const { unmount } = renderHook(() => useSSE('test-session'));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    unmount();

    expect(MockEventSource.instances[0].closed).toBe(true);
  });

  it('only maintains one connection per session (no duplicates on re-render)', () => {
    const { rerender } = renderHook(
      ({ sessionId }) => useSSE(sessionId),
      { initialProps: { sessionId: 'session-a' } },
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    // Rerender with same session - should not create new connection
    rerender({ sessionId: 'session-a' });
    expect(MockEventSource.instances).toHaveLength(1);
  });

  it('reconnects when session ID changes', () => {
    const { rerender } = renderHook(
      ({ sessionId }) => useSSE(sessionId),
      { initialProps: { sessionId: 'session-a' } },
    );

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    rerender({ sessionId: 'session-b' });

    expect(MockEventSource.instances[0].closed).toBe(true);
    expect(MockEventSource.instances).toHaveLength(2);
    expect(MockEventSource.instances[1].url).toBe('/api/events/session-b');
  });

  it('does not connect when session ID is null', () => {
    const { result } = renderHook(() => useSSE(null));

    expect(MockEventSource.instances).toHaveLength(0);
    expect(result.current.status).toBe('disconnected');
  });
});
