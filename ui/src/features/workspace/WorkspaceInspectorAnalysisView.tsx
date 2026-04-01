import { Button } from '@/components/primitives/Button';
import { Badge } from '@/components/primitives/Badge';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import { phaseKeyFromNumber } from '@/features/workspace/workspaceInspectorModel';
import type { StartNegotiationResponse } from '@/lib/api/types';
import { useInspectorActions } from '@/lib/query/sessionHooks';
import styles from '@/features/workspace/workspace.module.css';

type InspectorActions = ReturnType<typeof useInspectorActions>;

type WorkspaceInspectorAnalysisViewProps = {
  activeSession: StartNegotiationResponse | null;
  critiqueMutation: InspectorActions['critiqueMutation'];
  planningMutation: InspectorActions['planningMutation'];
  selectedAcceptanceCriterionIndex: number | null;
  specDiffMutation: InspectorActions['specDiffMutation'];
};

export default function WorkspaceInspectorAnalysisView({
  activeSession,
  critiqueMutation,
  planningMutation,
  selectedAcceptanceCriterionIndex,
  specDiffMutation,
}: WorkspaceInspectorAnalysisViewProps) {
  if (!activeSession) {
    return (
      <EmptyState
        title="No analyst context yet"
        description="Start a session to open planner, critique, and spec-diff surfaces without leaving the workspace."
      />
    );
  }

  const selectedCriterionLabel =
    selectedAcceptanceCriterionIndex !== null
      ? `AC ${selectedAcceptanceCriterionIndex + 1}`
      : 'Story-wide context';
  const activePhaseKey = phaseKeyFromNumber(activeSession.phase_number);

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Planning & critique"
        description="Analyst tools stay secondary to the active phase while keeping planner, critique, and spec-diff context one click away."
      />
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Session context
          </Text>
          <div className={styles.inlineCluster}>
            <Mono>{activeSession.session_id}</Mono>
            <Badge tone="neutral">{selectedCriterionLabel}</Badge>
            <Badge tone="info">{activePhaseKey}</Badge>
          </div>
        </div>
      </div>
      <div className={styles.reviewList}>
        <article className={styles.reviewItem}>
          <div className={styles.reviewItemHeader}>
            <Text as="h3" size="sm" weight="medium">
              Planner output
            </Text>
            <Button
              loading={planningMutation.isPending}
              onClick={() => planningMutation.mutate()}
              variant="secondary"
            >
              Load planner output
            </Button>
          </div>
          {planningMutation.data ? (
            <div className={styles.detailList}>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Estimated complexity
                </Text>
                <Badge tone="info">{planningMutation.data.estimated_complexity ?? 'unknown'}</Badge>
              </div>
              <div className={styles.reviewList}>
                {planningMutation.data.ac_groups.map((group, index) => (
                  <div className={styles.reviewItem} key={`${group.endpoint}-${index}`}>
                    <div className={styles.reviewItemHeader}>
                      <Mono>{group.endpoint}</Mono>
                      <Badge tone="neutral">{group.methods.join(', ')}</Badge>
                    </div>
                    <Text as="p" size="sm">
                      Covers AC {group.ac_indices.map((acIndex) => acIndex + 1).join(', ')}
                    </Text>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <Text as="p" size="sm">
              Session-scoped planning summarizes the next proof steps without taking the operator out of the negotiation workspace.
            </Text>
          )}
        </article>
        <article className={styles.reviewItem}>
          <div className={styles.reviewItemHeader}>
            <Text as="h3" size="sm" weight="medium">
              Phase critique
            </Text>
            <Button
              loading={critiqueMutation.isPending}
              onClick={() => critiqueMutation.mutate(activePhaseKey)}
              variant="secondary"
            >
              Run phase critique
            </Button>
          </div>
          {critiqueMutation.data ? (
            <div className={styles.reviewList}>
              <div className={styles.reviewItemHeader}>
                <Badge tone={critiqueMutation.data.has_issues ? 'warning' : 'success'}>
                  {critiqueMutation.data.has_issues ? 'Issues found' : 'No issues'}
                </Badge>
              </div>
              {critiqueMutation.data.issues.map((issue) => (
                <Text as="p" key={issue} size="sm">
                  {issue}
                </Text>
              ))}
              {critiqueMutation.data.suggestions.map((suggestion) => (
                <Text as="p" key={suggestion} size="sm" tone="muted">
                  {suggestion}
                </Text>
              ))}
            </div>
          ) : (
            <Text as="p" size="sm">
              Critique output flags missing coverage and quality gaps for the active phase without interrupting the operator workflow.
            </Text>
          )}
        </article>
        <article className={styles.reviewItem}>
          <div className={styles.reviewItemHeader}>
            <Text as="h3" size="sm" weight="medium">
              Spec diff
            </Text>
            <Button
              loading={specDiffMutation.isPending}
              onClick={() => specDiffMutation.mutate()}
              variant="secondary"
            >
              Compare historical specs
            </Button>
          </div>
          {specDiffMutation.data ? (
            specDiffMutation.data.has_old_spec ? (
              <pre className={styles.rawPayloadPre}>{specDiffMutation.data.diff ?? 'No textual diff returned.'}</pre>
            ) : (
              <EmptyState
                title="Nothing to compare yet"
                description="Historical spec comparisons will appear here once an older contract exists for this story."
              />
            )
          ) : (
            <Text as="p" size="sm">
              Historical spec comparisons remain optional and session-scoped so the primary phase composer stays untouched.
            </Text>
          )}
        </article>
      </div>
    </div>
  );
}
