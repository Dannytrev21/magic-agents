import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { PhaseTranscript } from '@/features/workspace/PhaseTranscript';
import type { WorkspaceTranscriptEntry } from '@/features/workspace/phaseReviewModel';

const baseEntries: WorkspaceTranscriptEntry[] = [
  {
    content: 'Session restored from checkpoint.',
    id: 'system-1',
    label: 'System',
    phaseNumber: null,
    role: 'system' as const,
    timestamp: '2026-04-01T10:00:00Z',
  },
  {
    content: 'Please tighten the 404 vs 410 decision.',
    id: 'operator-1',
    label: 'Operator',
    phaseNumber: 4,
    role: 'operator' as const,
    timestamp: '2026-04-01T10:01:00Z',
  },
  {
    content: 'Failure mode coverage updated for deleted users.',
    id: 'model-1',
    label: 'Model',
    phaseNumber: 4,
    role: 'model' as const,
    timestamp: '2026-04-01T10:02:00Z',
  },
];

afterEach(() => {
  cleanup();
});

describe('PhaseTranscript', () => {
  it('renders system, operator, and model entries with distinct transcript roles', () => {
    render(<PhaseTranscript entries={baseEntries} />);

    expect(screen.getByText(/system/i)).toBeInTheDocument();
    expect(screen.getByText(/operator/i)).toBeInTheDocument();
    expect(screen.getByText(/model/i)).toBeInTheDocument();
    expect(screen.getByText(/session restored from checkpoint/i)).toBeInTheDocument();
    expect(screen.getByText(/tighten the 404 vs 410 decision/i)).toBeInTheDocument();
    expect(screen.getByText(/failure mode coverage updated/i)).toBeInTheDocument();
  });

  it('auto-scrolls only while the operator is pinned to the bottom of the transcript', async () => {
    const { rerender } = render(<PhaseTranscript entries={baseEntries} />);
    const transcript = screen.getByRole('log', { name: /phase transcript/i });

    let scrollTop = 400;
    const scrollTo = vi.fn(({ top }: { top: number }) => {
      scrollTop = top;
    });

    Object.defineProperty(transcript, 'clientHeight', {
      configurable: true,
      value: 200,
    });
    Object.defineProperty(transcript, 'scrollHeight', {
      configurable: true,
      value: 600,
    });
    Object.defineProperty(transcript, 'scrollTop', {
      configurable: true,
      get: () => scrollTop,
      set: (value: number) => {
        scrollTop = value;
      },
    });
    Object.defineProperty(transcript, 'scrollTo', {
      configurable: true,
      value: scrollTo,
    });

    rerender(
      <PhaseTranscript
        entries={[
          ...baseEntries,
          {
            content: 'Another model update landed.',
            id: 'model-2',
            label: 'Model',
            phaseNumber: 4,
            role: 'model' as const,
            timestamp: '2026-04-01T10:03:00Z',
          },
        ]}
      />,
    );

    await waitFor(() => {
      expect(scrollTo).toHaveBeenCalled();
    });

    scrollTo.mockClear();
    scrollTop = 120;
    fireEvent.scroll(transcript);

    rerender(
      <PhaseTranscript
        entries={[
          ...baseEntries,
          {
            content: 'Another model update landed.',
            id: 'model-2',
            label: 'Model',
            phaseNumber: 4,
            role: 'model' as const,
            timestamp: '2026-04-01T10:03:00Z',
          },
          {
            content: 'Operator is still reading older transcript content.',
            id: 'operator-2',
            label: 'Operator',
            phaseNumber: 4,
            role: 'operator' as const,
            timestamp: '2026-04-01T10:04:00Z',
          },
        ]}
      />,
    );

    await waitFor(() => {
      expect(scrollTo).not.toHaveBeenCalled();
    });
  });
});
