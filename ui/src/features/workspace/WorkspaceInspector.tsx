import type { RefObject } from 'react';
import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import {
  inspectorViews,
  type WorkspaceInspectorView,
} from '@/features/workspace/workspaceModel';
import type { StartNegotiationResponse } from '@/lib/api/types';
import { useInspectorQueries } from '@/lib/query/sessionHooks';
import styles from '@/features/workspace/workspace.module.css';

type WorkspaceInspectorProps = {
  activeSession: StartNegotiationResponse | null;
  activeView: WorkspaceInspectorView;
  focusRef: RefObject<HTMLElement | null>;
  onViewChange: (view: WorkspaceInspectorView) => void;
  selectedAcceptanceCriterionIndex: number | null;
};

export function WorkspaceInspector({
  activeSession,
  activeView,
  focusRef,
  onViewChange,
  selectedAcceptanceCriterionIndex,
}: WorkspaceInspectorProps) {
  const { isLoading, scanStatus, skills } = useInspectorQueries();
  const contractState = activeSession ? 'Session-bound' : 'Waiting for session';

  return (
    <div className={styles.stack}>
      <SectionHeader
        title="Evidence inspector"
        description="Evidence, scan output, and traceability stay visible without forcing a route change."
      />
      <div aria-label="Inspector views" className={styles.viewTabs} role="tablist">
        {inspectorViews.map((view) => (
          <button
            aria-selected={activeView === view.value}
            className={styles.viewTab}
            key={view.value}
            onClick={() => onViewChange(view.value)}
            role="tab"
            type="button"
          >
            {view.label}
          </button>
        ))}
      </div>
      <section className={styles.focusRegion} ref={focusRef} tabIndex={-1}>
        <div className={styles.sectionStack}>
          <div className={styles.detailList}>
            <div className={styles.detailRow}>
              <Text as="p" size="xs" tone="muted">
                Contract state
              </Text>
              <div className={styles.inlineCluster}>
                <Text as="p" size="sm" weight="medium">
                  {contractState}
                </Text>
                <Badge tone={activeSession ? 'success' : 'warning'}>
                  {activeSession ? 'Phase surface mounted' : 'Awaiting intake'}
                </Badge>
              </div>
            </div>
          </div>
          <Divider />
          {activeView === 'evidence' ? (
            <EvidenceView
              activeSession={activeSession}
              selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
            />
          ) : null}
          {activeView === 'scan' ? (
            <ScanView isLoading={isLoading} projectRoot={scanStatus.project_root} scanned={scanStatus.scanned} skillCount={skills.length} />
          ) : null}
          {activeView === 'traceability' ? (
            <TraceabilityView
              activeSession={activeSession}
              selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
            />
          ) : null}
        </div>
      </section>
    </div>
  );
}

function EvidenceView({
  activeSession,
  selectedAcceptanceCriterionIndex,
}: {
  activeSession: StartNegotiationResponse | null;
  selectedAcceptanceCriterionIndex: number | null;
}) {
  return (
    <>
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Typed API handoff
          </Text>
          <div className={styles.codeList}>
            <Mono>/api/start</Mono>
            <Mono>/api/respond</Mono>
            <Mono>/api/compile</Mono>
          </div>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected AC
          </Text>
          <Text as="p" size="sm">
            {selectedAcceptanceCriterionIndex !== null
              ? `AC ${selectedAcceptanceCriterionIndex + 1}`
              : 'Awaiting rail selection'}
          </Text>
        </div>
      </div>
      {!activeSession ? (
        <EmptyState
          title="No evidence yet"
          description="Run the next phase to populate traceability, specs, and generated verification artifacts."
        />
      ) : (
        <Text as="p" size="sm">
          Evidence remains mounted while the center workspace swaps between phase output and traceability review.
        </Text>
      )}
    </>
  );
}

type ScanViewProps = {
  isLoading: boolean;
  projectRoot: string;
  scanned: boolean;
  skillCount: number;
};

function ScanView({ isLoading, projectRoot, scanned, skillCount }: ScanViewProps) {
  if (isLoading) {
    return <Text size="sm">Loading scan output</Text>;
  }

  return (
    <div className={styles.detailList}>
      <div className={styles.detailRow}>
        <Text as="p" size="xs" tone="muted">
          Scan status
        </Text>
        <Badge tone={scanned ? 'success' : 'warning'}>{scanned ? 'Indexed' : 'Pending'}</Badge>
      </div>
      <div className={styles.detailRow}>
        <Text as="p" size="xs" tone="muted">
          Project root
        </Text>
        <Mono>{projectRoot || '/unknown'}</Mono>
      </div>
      <div className={styles.detailRow}>
        <Text as="p" size="xs" tone="muted">
          Skills discovered
        </Text>
        <Text as="p" size="sm">
          {skillCount}
        </Text>
      </div>
    </div>
  );
}

function TraceabilityView({
  activeSession,
  selectedAcceptanceCriterionIndex,
}: {
  activeSession: StartNegotiationResponse | null;
  selectedAcceptanceCriterionIndex: number | null;
}) {
  return (
    <div className={styles.matrix}>
      <div className={styles.matrixHeader}>
        <Text as="p" size="xs" tone="muted">
          Source
        </Text>
        <Text as="p" size="xs" tone="muted">
          Evidence
        </Text>
        <Text as="p" size="xs" tone="muted">
          Outcome
        </Text>
      </div>
      <div className={styles.matrixRow}>
        <Text as="p" size="sm">
          {selectedAcceptanceCriterionIndex !== null
            ? `AC ${selectedAcceptanceCriterionIndex + 1}`
            : 'Story context'}
        </Text>
        <Text as="p" size="sm">
          {activeSession?.jira_key ?? 'Manual draft'}
        </Text>
        <Text as="p" size="sm">
          Linked to workspace and verification surfaces
        </Text>
      </div>
    </div>
  );
}
