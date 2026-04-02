import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MutableRefObject,
} from 'react';
import styles from '@/features/workspace/phase-progress-bar.module.css';
import { usePhaseEvents } from '@/lib/api/eventStore';

type ProgressState = 'active' | 'complete' | 'error' | 'idle';
type PhaseProgressBarSurface = 'rail' | 'workspace';

type PhaseProgressBarProps = {
  surface?: PhaseProgressBarSurface;
};

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
 * `phase_complete` / `phase_error` events. Driven by the shared event store.
 */
export function PhaseProgressBar({ surface = 'workspace' }: PhaseProgressBarProps) {
  const phaseEvents = usePhaseEvents();
  const [elapsed, setElapsed] = useState(0);
  const [stepMessage, setStepMessage] = useState('');
  const [state, setState] = useState<ProgressState>('idle');
  const processedEventCountRef = useRef(0);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    if (phaseEvents.length === 0) {
      processedEventCountRef.current = 0;
      clearHideTimer(hideTimerRef);
      setState('idle');
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
        clearHideTimer(hideTimerRef);
        setState('active');
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
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        setState('complete');
        hideTimerRef.current = setTimeout(() => {
          hideTimerRef.current = null;
          setElapsed(0);
          setState('idle');
          setStepMessage('');
        }, 320);
      } else if (nextEvent.type === 'phase_error') {
        clearHideTimer(hideTimerRef);
        setState('error');
        if (timerRef.current !== null) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
      } else if (nextEvent.type === 'phase_progress') {
        const msg =
          (nextEvent as Record<string, unknown>).message ??
          (nextEvent as Record<string, unknown>).step;
        if (typeof msg === 'string') {
          setStepMessage(msg);
        }
      }
    }

    processedEventCountRef.current = phaseEvents.length;
  }, [phaseEvents]);

  useEffect(() => {
    return () => {
      if (timerRef.current !== null) {
        clearInterval(timerRef.current);
      }
      clearHideTimer(hideTimerRef);
    };
  }, []);

  if (state === 'idle') {
    return null;
  }

  return (
    <div
      aria-label={
        surface === 'rail'
          ? 'Phase progress in the phase rail'
          : 'Phase progress in the workspace header'
      }
      data-state={state}
      role="progressbar"
      style={containerStyle(surface, state)}
    >
      <div className={styles.bar} style={barStyle(state)} />
      <div style={metaStyle}>
        <span style={elapsedStyle}>{formatElapsed(elapsed)}</span>
        {stepMessage ? <span style={stepStyle}>{stepMessage}</span> : null}
      </div>
    </div>
  );
}

function clearHideTimer(timerRef: MutableRefObject<ReturnType<typeof setTimeout> | null>) {
  if (timerRef.current !== null) {
    clearTimeout(timerRef.current);
    timerRef.current = null;
  }
}

function containerStyle(surface: PhaseProgressBarSurface, state: ProgressState): CSSProperties {
  const base: CSSProperties = {
    display: 'grid',
    gap: 'var(--space-2)',
    opacity: state === 'complete' ? 0 : 1,
    position: 'relative',
    transform: state === 'complete' ? 'translateY(-0.18rem)' : 'none',
    transition:
      'opacity var(--motion-normal) var(--easing-standard), transform var(--motion-normal) var(--easing-standard)',
    zIndex: 5,
  };

  if (surface === 'rail') {
    return {
      ...base,
      padding: 'var(--space-2) 0 0',
    };
  }

  return {
    ...base,
    padding: 'var(--space-3) var(--space-4)',
    border: '1px solid color-mix(in srgb, var(--color-border) 72%, transparent)',
    borderRadius: 'var(--radius-xl)',
    background:
      'linear-gradient(180deg, color-mix(in srgb, var(--color-surface-strong) 90%, transparent), color-mix(in srgb, var(--color-bg-elevated) 88%, transparent))',
    boxShadow: 'var(--shadow-soft)',
  };
}

function barStyle(state: ProgressState): CSSProperties {
  switch (state) {
    case 'error':
      return {
        animation: 'none',
        background: 'var(--color-error)',
      };
    case 'complete':
      return {
        animation: 'none',
        background:
          'linear-gradient(90deg, color-mix(in srgb, var(--color-success) 68%, white 12%), var(--color-success))',
      };
    default:
      return {
        background:
          'linear-gradient(90deg, transparent 0%, var(--color-signal) 50%, transparent 100%)',
      };
  }
}

const metaStyle: CSSProperties = {
  alignItems: 'center',
  display: 'flex',
  gap: 'var(--space-3)',
};

const elapsedStyle: CSSProperties = {
  color: 'var(--color-text-muted)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--text-xs)',
};

const stepStyle: CSSProperties = {
  color: 'var(--color-text-muted)',
  fontSize: 'var(--text-xs)',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};
