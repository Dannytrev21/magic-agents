import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Badge } from '@/components/primitives/Badge';
import { Button } from '@/components/primitives/Button';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { Skeleton } from '@/components/primitives/Skeleton';

describe('Primitives', () => {
  it('renders a visible focus target and loading state for buttons', () => {
    render(
      <div>
        <Button>Primary action</Button>
        <Button loading>Busy action</Button>
      </div>,
    );

    screen.getByRole('button', { name: /primary action/i }).focus();

    expect(screen.getByRole('button', { name: /primary action/i })).toHaveFocus();
    expect(screen.getByRole('button', { name: /busy action/i })).toBeDisabled();
  });

  it('distinguishes mono refs from product copy', () => {
    render(<Mono>REQ-101</Mono>);
    expect(screen.getByText('REQ-101').tagName.toLowerCase()).toBe('code');
  });

  it('renders semantic badges, skeletons, and empty states', () => {
    render(
      <div>
        <Badge tone="success">Ready</Badge>
        <Skeleton aria-label="Loading panel" />
        <EmptyState title="No evidence yet" description="Run the next phase to populate the inspector." />
      </div>,
    );

    expect(screen.getByText('Ready')).toBeInTheDocument();
    expect(screen.getByLabelText(/loading panel/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /no evidence yet/i })).toBeInTheDocument();
  });
});
