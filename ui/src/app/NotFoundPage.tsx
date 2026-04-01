import { Link } from 'react-router-dom';
import { Button } from '@/components/primitives/Button';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Panel } from '@/components/primitives/Panel';

export function NotFoundPage() {
  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        background: 'var(--color-bg)',
        padding: 'var(--space-6)',
      }}
    >
      <Panel tone="subtle">
        <EmptyState
          title="Workspace not found"
          description="Return to the active operator workspace to resume intake, negotiation, and inspection."
          action={
            <Button asChild>
              <Link to="/">Return to workspace</Link>
            </Button>
          }
        />
      </Panel>
    </main>
  );
}
