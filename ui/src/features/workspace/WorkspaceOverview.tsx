import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import type { StartNegotiationResponse } from '@/lib/api/types';
import styles from '@/features/workspace/workspace.module.css';

type WorkspaceOverviewProps = {
  activeSession: StartNegotiationResponse | null;
  isTransitionPending: boolean;
};

const phasePlan = [
  'Story intake',
  'Typed API and query boundary',
  'Shell and provider stack',
  'Tokenized visual system',
  'Accessible primitives',
];

export function WorkspaceOverview({ activeSession, isTransitionPending }: WorkspaceOverviewProps) {
  if (!activeSession) {
    return (
      <div className={styles.stack}>
        <SectionHeader
          title="Active workspace"
          description="The center pane is ready for a stable three-pane workflow before deeper feature surfaces land."
        />
        <EmptyState
          title="No session in flight"
          description="Use the left rail to start a negotiation session and bind the shell to real phase data."
        />
      </div>
    );
  }

  return (
    <div className={styles.stack}>
      <SectionHeader
        title="Active workspace"
        description="Global shell state is owned in React so panel changes can stay responsive while the backend remains the source of truth."
        action={<Badge tone={isTransitionPending ? 'warning' : 'success'}>{isTransitionPending ? 'Updating shell' : 'Shell ready'}</Badge>}
      />
      <div className={styles.phaseStrip}>
        <Badge tone="info">Phase {activeSession.phase_number}</Badge>
        <Badge tone="neutral">of {activeSession.total_phases}</Badge>
        <Mono>{activeSession.session_id}</Mono>
      </div>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryTile}>
          <Text as="p" size="xs" tone="muted">
            Current title
          </Text>
          <Text as="p" size="base" weight="semibold">
            {activeSession.phase_title}
          </Text>
        </div>
        <div className={styles.summaryTile}>
          <Text as="p" size="xs" tone="muted">
            Jira key
          </Text>
          <Mono>{activeSession.jira_key}</Mono>
        </div>
        <div className={styles.summaryTile}>
          <Text as="p" size="xs" tone="muted">
            Status
          </Text>
          <Text as="p" size="base" weight="medium">
            {activeSession.revised ? 'Revising phase output' : 'Awaiting operator input'}
          </Text>
        </div>
      </div>
      <Divider />
      <div className={styles.timeline}>
        {phasePlan.map((item, index) => (
          <div className={styles.timelineItem} key={item}>
            <span aria-hidden="true" className={styles.timelineMarker} />
            <div>
              <Text as="p" size="sm" weight="semibold">
                {item}
              </Text>
              <Text as="p" size="sm" tone="muted">
                {index + 1 <= activeSession.phase_number
                  ? 'This checkpoint is now mounted in the workspace shell.'
                  : 'This checkpoint will land in-place without route jumps.'}
              </Text>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
