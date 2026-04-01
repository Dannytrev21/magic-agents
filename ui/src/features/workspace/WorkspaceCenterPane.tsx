import type { RefObject } from 'react';
import { centerWorkspaceViews, negotiationPhases, type WorkspaceCenterView } from '@/features/workspace/workspaceModel';
import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import type { StartNegotiationResponse } from '@/lib/api/types';
import styles from '@/features/workspace/workspace.module.css';

type WorkspaceCenterPaneProps = {
  activeSession: StartNegotiationResponse | null;
  activeView: WorkspaceCenterView;
  draftFeedback: string;
  focusRef: RefObject<HTMLElement | null>;
  isTransitionPending: boolean;
  onViewChange: (view: WorkspaceCenterView) => void;
  selectedAcceptanceCriterionIndex: number | null;
  selectedPhaseNumber: number | null;
  statusLabel: string;
};

export function WorkspaceCenterPane({
  activeSession,
  activeView,
  draftFeedback,
  focusRef,
  isTransitionPending,
  onViewChange,
  selectedAcceptanceCriterionIndex,
  selectedPhaseNumber,
  statusLabel,
}: WorkspaceCenterPaneProps) {
  if (!activeSession) {
    return (
      <div className={styles.stack}>
        <SectionHeader
          title="Operator workspace"
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
      <section className={styles.stickyRail} data-sticky="true">
        <div className={styles.statusStrip}>
          <div className={styles.statusMeta}>
            <Text as="p" size="xs" tone="muted">
              Session status
            </Text>
            <Text as="p" size="sm" weight="medium">
              {statusLabel}
            </Text>
          </div>
          <div className={styles.statusMeta}>
            <Text as="p" size="xs" tone="muted">
              Session ref
            </Text>
            <Mono>{activeSession.session_id}</Mono>
          </div>
          <Badge tone={isTransitionPending ? 'warning' : 'success'}>
            {isTransitionPending ? 'Updating in place' : 'In-place workspace'}
          </Badge>
        </div>
        <ol aria-label="Negotiation phases" className={styles.phaseRail}>
          {negotiationPhases.map((phase, index) => {
            const phaseNumber = index + 1;
            const state =
              phaseNumber < activeSession.phase_number
                ? 'complete'
                : phaseNumber === activeSession.phase_number
                  ? 'active'
                  : 'pending';

            return (
              <li className={styles.phaseRailItem} data-state={state} key={phase}>
                <span aria-hidden="true" className={styles.phaseRailMarker}>
                  {phaseNumber}
                </span>
                <div>
                  <Text as="p" size="xs" tone="muted">
                    Phase {phaseNumber}
                  </Text>
                  <Text as="p" size="sm" weight="medium">
                    {phase}
                  </Text>
                </div>
              </li>
            );
          })}
        </ol>
        <div aria-label="Workspace views" className={styles.viewTabs} role="tablist">
          {centerWorkspaceViews.map((view) => (
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
      </section>

      <section className={styles.focusRegion} ref={focusRef} tabIndex={-1}>
        {activeView === 'overview' ? (
          <OverviewContent activeSession={activeSession} selectedPhaseNumber={selectedPhaseNumber} />
        ) : null}
        {activeView === 'negotiation' ? (
          <NegotiationContent
            activeSession={activeSession}
            draftFeedback={draftFeedback}
            selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
            selectedPhaseNumber={selectedPhaseNumber}
          />
        ) : null}
        {activeView === 'traceability' ? (
          <TraceabilityContent
            activeSession={activeSession}
            selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
          />
        ) : null}
      </section>
    </div>
  );
}

function OverviewContent({
  activeSession,
  selectedPhaseNumber,
}: {
  activeSession: StartNegotiationResponse;
  selectedPhaseNumber: number | null;
}) {
  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Active workspace"
        description="The center pane stays dominant while story intake and evidence remain available on either side."
        action={<Badge tone="info">Phase {activeSession.phase_number} of 7</Badge>}
      />
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Current phase
          </Text>
          <Text as="p" size="sm" weight="medium">
            {activeSession.phase_title}
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Story key
          </Text>
          <Mono>{activeSession.jira_key}</Mono>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Session flow
          </Text>
          <Text as="p" size="sm">
            Intake, negotiation, traceability review, and verification stay in one route context.
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected phase
          </Text>
          <Text as="p" size="sm">
            {selectedPhaseNumber ? `Phase ${selectedPhaseNumber}` : 'Live phase focus'}
          </Text>
        </div>
      </div>
      <Divider />
      <Text as="p" size="sm" tone="muted">
        Use the workspace tabs above to swap the center surface in place instead of navigating to separate screens.
      </Text>
    </div>
  );
}

function NegotiationContent({
  activeSession,
  draftFeedback,
  selectedAcceptanceCriterionIndex,
  selectedPhaseNumber,
}: {
  activeSession: StartNegotiationResponse;
  draftFeedback: string;
  selectedAcceptanceCriterionIndex: number | null;
  selectedPhaseNumber: number | null;
}) {
  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title={activeSession.phase_title}
        description="Phase work stays mounted in the center pane so operators can review, revise, and continue without losing side-pane context."
        action={<Badge tone={activeSession.revised ? 'warning' : 'success'}>{activeSession.revised ? 'Revision active' : 'Ready for review'}</Badge>}
      />
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Working surface
          </Text>
          <Text as="p" size="sm">
            Structured phase output remains centered while the evidence inspector can switch independently.
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Interaction model
          </Text>
          <Text as="p" size="sm">
            Non-urgent updates use React transitions so selection and typing stay responsive.
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected acceptance criterion
          </Text>
          <Text as="p" size="sm">
            {selectedAcceptanceCriterionIndex !== null
              ? `AC ${selectedAcceptanceCriterionIndex + 1}`
              : 'No rail selection'}
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected phase focus
          </Text>
          <Text as="p" size="sm">
            {selectedPhaseNumber ? `Phase ${selectedPhaseNumber}` : `Phase ${activeSession.phase_number}`}
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Draft feedback
          </Text>
          <Text as="p" size="sm">
            {draftFeedback || 'No draft feedback'}
          </Text>
        </div>
      </div>
    </div>
  );
}

function TraceabilityContent({
  activeSession,
  selectedAcceptanceCriterionIndex,
}: {
  activeSession: StartNegotiationResponse;
  selectedAcceptanceCriterionIndex: number | null;
}) {
  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Traceability matrix"
        description="Evidence stays linked to the active story without leaving the operator workspace."
        action={<Badge tone="neutral">{activeSession.jira_key}</Badge>}
      />
      <div className={styles.matrix}>
        <div className={styles.matrixHeader}>
          <Text as="p" size="xs" tone="muted">
            Acceptance criteria
          </Text>
          <Text as="p" size="xs" tone="muted">
            Phase output
          </Text>
          <Text as="p" size="xs" tone="muted">
            Verification path
          </Text>
        </div>
        <div className={styles.matrixRow}>
          <Text as="p" size="sm">
            {selectedAcceptanceCriterionIndex !== null
              ? `AC ${selectedAcceptanceCriterionIndex + 1}`
              : 'Operator can stay inside one workspace route.'}
          </Text>
          <Text as="p" size="sm">
            Phase {activeSession.phase_number} review surface
          </Text>
          <Text as="p" size="sm">
            Inspector trace links and pipeline verdicts
          </Text>
        </div>
      </div>
    </div>
  );
}
