import styles from '@/features/workspace/workspace.module.css';
import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import type { StartNegotiationResponse } from '@/lib/api/types';

type WorkspaceInspectorProps = {
  activeSession: StartNegotiationResponse | null;
};

export function WorkspaceInspector({ activeSession }: WorkspaceInspectorProps) {
  const contractState = activeSession ? 'Session-bound' : 'Waiting for session';

  return (
    <div className={styles.stack}>
      <SectionHeader
        title="Evidence inspector"
        description="Foundation-level evidence surfaces keep future artifacts, traceability, and pipeline outputs in one stable region."
      />
      <div className={styles.summaryTile}>
        <Text as="p" size="xs" tone="muted">
          Contract state
        </Text>
        <Text as="p" size="base" weight="semibold">
          {contractState}
        </Text>
        <Badge tone={activeSession ? 'success' : 'warning'}>
          {activeSession ? 'Phase surface mounted' : 'Awaiting intake'}
        </Badge>
      </div>
      <div className={styles.summaryTile}>
        <Text as="p" size="xs" tone="muted">
          Typed API handoff
        </Text>
        <Mono>/api/start</Mono>
        <Mono>/api/respond</Mono>
        <Mono>/api/compile</Mono>
      </div>
      <Divider />
      <div className={styles.inspectorList}>
        <EmptyState
          title="No evidence yet"
          description="Run the next phase to populate traceability, specs, and generated verification artifacts."
        />
        <Badge tone="neutral">Spec viewer</Badge>
        <Badge tone="neutral">Transcript</Badge>
        <Badge tone="neutral">Traceability</Badge>
      </div>
    </div>
  );
}
