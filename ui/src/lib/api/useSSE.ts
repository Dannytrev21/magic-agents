import { useCallback, useEffect, useRef, useState } from 'react';

export type SSEConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export type SSEEvent = Record<string, unknown> & { type: string };

type UseSSEOptions = {
  /** Callback fired for every incoming event. */
  onEvent?: (event: SSEEvent) => void;
  /** Maximum reconnection attempts before giving up. Default: 8. */
  maxRetries?: number;
  /** Base backoff in ms. Doubles per retry, capped at 30 000 ms. Default: 1000. */
  baseBackoff?: number;
};

type UseSSEReturn = {
  lastEvent: SSEEvent | null;
  status: SSEConnectionStatus;
};

const MAX_BACKOFF_MS = 30_000;

function resolveEventSourceConstructor() {
  return typeof globalThis.EventSource === 'function' ? globalThis.EventSource : null;
}

/**
 * React hook that maintains a persistent SSE connection to
 * `GET /api/events/{sessionId}` with automatic exponential-backoff
 * reconnection.
 *
 * Only one EventSource per session is created regardless of re-renders.
 * Cleanup runs on unmount and on session ID change.
 */
export function useSSE(
  sessionId: string | null,
  options: UseSSEOptions = {},
): UseSSEReturn {
  const { onEvent, maxRetries = 8, baseBackoff = 1000 } = options;

  const [status, setStatus] = useState<SSEConnectionStatus>(
    sessionId ? 'connecting' : 'disconnected',
  );
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);

  // Stable refs so the effect doesn't re-run on callback identity changes.
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const retriesRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const esRef = useRef<EventSource | null>(null);

  const connect = useCallback(
    (sid: string) => {
      const EventSourceConstructor = resolveEventSourceConstructor();

      if (!EventSourceConstructor) {
        setStatus('disconnected');
        return;
      }

      const es = new EventSourceConstructor(`/api/events/${sid}`);
      esRef.current = es;

      es.onopen = () => {
        retriesRef.current = 0;
        setStatus('connected');
      };

      es.onmessage = (ev: MessageEvent) => {
        try {
          const parsed = JSON.parse(ev.data) as SSEEvent;
          setLastEvent(parsed);
          onEventRef.current?.(parsed);
        } catch {
          /* ignore malformed payloads */
        }
      };

      es.onerror = () => {
        es.close();

        if (retriesRef.current >= maxRetries) {
          setStatus('disconnected');
          return;
        }

        setStatus('reconnecting');
        const delay = Math.min(baseBackoff * 2 ** retriesRef.current, MAX_BACKOFF_MS);
        retriesRef.current += 1;

        timerRef.current = setTimeout(() => {
          connect(sid);
        }, delay);
      };
    },
    [maxRetries, baseBackoff],
  );

  useEffect(() => {
    if (!sessionId) {
      setStatus('disconnected');
      return;
    }

    if (!resolveEventSourceConstructor()) {
      setStatus('disconnected');
      return;
    }

    retriesRef.current = 0;
    setStatus('connecting');
    connect(sessionId);

    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }
    };
  }, [sessionId, connect]);

  return { status, lastEvent };
}
