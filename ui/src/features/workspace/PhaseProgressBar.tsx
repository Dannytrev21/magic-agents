import { useEffect, useRef, useState } from 'react';
import { usePhaseEvents } from '@/lib/api/eventStore';

type ProgressState = 'active' | 'complete' | 'error' | 'idle';

function formatElapsed(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s`;
  }
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

/**
 * Indeterminate progress bar that appears between `phase_start` and
 * `phase_complete` / `phase_error` events.  Driven by the event store.
 */
export function PhaseProgressBar() {
  const phaseEvents = usePhaseEvents();
  const [elapsed, setElapsed] = useState(0);
  const [stepMessage, setStepMessage] = useState('');
  const [state, setState] = useState<ProgressState>('idle');
  const [activePhase, setActivePhase] = useState<string | null>(null);
  const processedEventCountRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Apply newly appended events in order so batched start/progress updates are preserved.
  useEffect(() => {
    if (phaseEvents.length === 0) {
      processedEventCountRef.current = 0;
      setState('idle');
      setActivePhase(null);
      setStepMessage('');
      setElapsed(0);
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    if (phaseEvents.length < processedEventCountRef.current) {
      processedEventCountRef.current = 0;
    }

    for (let index = processedEventCountRef.current; index < phaseEvents.length; index += 1) {
      const nextEvent = phaseEvents[index];

      if (nextEvent.type === 'phase_start') {
        const phase = (nextEvent as Record<string, unknown>).phase as string;
        setState('active');
        setActivePhase(phase);
        setStepMessage('');
        setElapsed(0);
        startTimeRef.current = Date.now();

        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
        }
        timerRef.current = setInterval(() => {
          setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
        }, 1000);
      } else if (nextEvent.type === 'phase_complete') {
        setState('idle');
        setActivePhase(null);
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      } else if (nextEvent.type === 'phase_error') {
        setState('error');
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      } else if (nextEvent.type === 'phase_progress') {
        const msg = (nextEvent as Record<string, unknown>).message;
        if (typeof msg === 'string') {
          setStepMessage(msg);
        }
      }
    }

    processedEventCountRef.current = phaseEvents.length;
  }, [phaseEvents]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  if (state === 'idle') {
    return null;
  }

  return (
    <div
      aria-label={activePhase ? `Phase ${activePhase} in progress` : 'Phase in progress'}
      data-state={state}
      role="progressbar"
      style={{
        position: 'relative',
        zIndex: 5,
        display: 'grid',
        gap: 'var(--space-2)',
        padding: 'var(--space-2) var(--space-4)',
        background: 'color-mix(in srgb, var(--color-surface) 80%, transparent)',
        borderBottom: '1px solid var(--color-border)',
      }}
    >
      <div
        style={{
          height: '3px',
          borderRadius: 'var(--radius-round)',
          background: state === 'error' ? 'var(--color-error)' : 'var(--color-signal)',
          opacity: state === 'error' ? 1 : 0.72,
        }}
      />
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-3)',
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 'var(--text-xs)',
            color: 'var(--color-text-muted)',
          }}
        >
          {formatElapsed(elapsed)}
        </span>
        {stepMessage ? (
          <span
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {stepMessage}
          </span>
        ) : null}
      </div>
    </div>
  );
}
