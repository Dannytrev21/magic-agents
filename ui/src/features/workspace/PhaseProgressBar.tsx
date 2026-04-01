import { useEffect, useRef, useState } from 'react';
import { usePhaseEvents } from '@/lib/api/eventStore';
import styles from '@/features/workspace/phase-progress-bar.module.css';

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
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  // Derive state from the event stream
  useEffect(() => {
    if (phaseEvents.length === 0) {
      return;
    }

    const latest = phaseEvents[phaseEvents.length - 1];

    if (latest.type === 'phase_start') {
      const phase = (latest as Record<string, unknown>).phase as string;
      setState('active');
      setActivePhase(phase);
      setStepMessage('');
      setElapsed(0);
      startTimeRef.current = Date.now();

      // Clear any prior timer
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
      }
      timerRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
    } else if (latest.type === 'phase_complete') {
      setState('idle');
      setActivePhase(null);
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } else if (latest.type === 'phase_error') {
      setState('error');
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } else if (latest.type === 'phase_progress') {
      const msg = (latest as Record<string, unknown>).message;
      if (typeof msg === 'string') {
        setStepMessage(msg);
      }
    }
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
      className={styles.container}
      data-state={state}
      role="progressbar"
    >
      <div className={`${styles.bar} ${state === 'error' ? styles.barError : ''}`} />
      <div className={styles.meta}>
        <span className={styles.elapsed}>{formatElapsed(elapsed)}</span>
        {stepMessage ? <span className={styles.step}>{stepMessage}</span> : null}
      </div>
    </div>
  );
}
