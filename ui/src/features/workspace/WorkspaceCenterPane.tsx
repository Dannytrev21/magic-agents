import { useEffect, useId, useState, type RefObject } from 'react';
import { Button } from '@/components/primitives/Button';
import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import { PhaseTranscript } from '@/features/workspace/PhaseTranscript';
import {
  buildInitialVerificationState,
  WorkspaceVerificationConsole,
  type VerificationWorkspaceState,
} from '@/features/workspace/WorkspaceVerificationConsole';
import {
  buildPhaseReview,
  buildTranscriptEntries,
  type PhaseReview,
} from '@/features/workspace/phaseReviewModel';
import {
  centerWorkspaceViews,
  negotiationPhases,
  type WorkspaceCenterView,
} from '@/features/workspace/workspaceModel';
import type { StartNegotiationResponse } from '@/lib/api/types';
import styles from '@/features/workspace/workspace.module.css';

export type PhaseActionState = {
  activeAction: 'approve' | 'revise' | null;
  isPending: boolean;
  message: string | null;
  status: 'error' | 'idle' | 'success';
};

type WorkspaceCenterPaneProps = {
  activeSession: StartNegotiationResponse | null;
  activeView: WorkspaceCenterView;
  draftFeedback: string;
  focusRef: RefObject<HTMLElement | null>;
  isTransitionPending: boolean;
  onApprovePhase?: () => void;
  onDraftFeedbackChange?: (value: string) => void;
  onPhaseSelect?: (phaseNumber: number) => void;
  onRevisePhase?: () => void;
  onViewChange: (view: WorkspaceCenterView) => void;
  phaseActionState?: PhaseActionState;
  selectedAcceptanceCriterionIndex: number | null;
  selectedPhaseNumber: number | null;
  statusLabel: string;
  storySummary?: string | null;
};

const defaultPhaseActionState: PhaseActionState = {
  activeAction: null,
  isPending: false,
  message: null,
  status: 'idle',
};

export function WorkspaceCenterPane({
  activeSession,
  activeView,
  draftFeedback,
  focusRef,
  isTransitionPending,
  onApprovePhase,
  onDraftFeedbackChange,
  onPhaseSelect,
  onRevisePhase,
  onViewChange,
  phaseActionState = defaultPhaseActionState,
  selectedAcceptanceCriterionIndex,
  selectedPhaseNumber,
  statusLabel,
  storySummary = null,
}: WorkspaceCenterPaneProps) {
  const workspaceViewId = useId();
  const [verificationState, setVerificationState] = useState<VerificationWorkspaceState>(() =>
    buildInitialVerificationState(activeSession),
  );

  useEffect(() => {
    if (!activeSession || activeView !== 'negotiation') {
      return;
    }

    const maxPhaseNumber = activeSession.phase_number;

    function handleKeydown(event: KeyboardEvent) {
      if (event.altKey || event.ctrlKey || event.metaKey) {
        return;
      }

      if (isTextInputTarget(event.target)) {
        return;
      }

      const phaseNumber = Number(event.key);
      if (!Number.isInteger(phaseNumber) || phaseNumber < 1 || phaseNumber > maxPhaseNumber) {
        return;
      }

      event.preventDefault();
      onPhaseSelect?.(phaseNumber);
    }

    window.addEventListener('keydown', handleKeydown);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
    };
  }, [activeSession, activeView, onPhaseSelect]);

  useEffect(() => {
    setVerificationState(buildInitialVerificationState(activeSession));
  }, [activeSession?.session_id]);

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

  const visiblePhaseNumber = selectedPhaseNumber ?? activeSession.phase_number;
  const phaseReview = buildPhaseReview(activeSession, visiblePhaseNumber);
  const transcriptEntries = buildTranscriptEntries(activeSession, visiblePhaseNumber);
  const workspaceLabel =
    centerWorkspaceViews.find((view) => view.value === activeView)?.label ?? 'Overview';
  const selectedCriterionLabel =
    selectedAcceptanceCriterionIndex !== null ? `AC ${selectedAcceptanceCriterionIndex + 1}` : 'Story-wide';
  const activeViewPanelId = `${workspaceViewId}-${activeView}-panel`;
  const activeViewTabId = `${workspaceViewId}-${activeView}-tab`;

  return (
    <div className={styles.stack}>
      <section className={styles.stickyRail} data-sticky="true">
        <div className={styles.breadcrumbs}>
          <Mono>{activeSession.jira_key}</Mono>
          <Text as="p" size="xs" tone="muted">
            /
          </Text>
          <Text as="p" size="xs" tone="muted">
            {workspaceLabel}
          </Text>
          <Text as="p" size="xs" tone="muted">
            /
          </Text>
          <Text as="p" size="xs" tone="muted">
            {phaseReview.phaseTitle}
          </Text>
        </div>
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
            const state = getPhaseState(phaseNumber, activeSession.phase_number);
            const disabled = phaseNumber > activeSession.phase_number;

            return (
              <li key={phase}>
                <button
                  aria-label={`Phase ${phaseNumber} ${phase}`}
                  className={styles.phaseRailButton}
                  data-selected={visiblePhaseNumber === phaseNumber}
                  data-state={state}
                  disabled={disabled}
                  onClick={() => onPhaseSelect?.(phaseNumber)}
                  type="button"
                >
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
                </button>
              </li>
            );
          })}
        </ol>
        <div aria-label="Workspace views" className={styles.viewTabs} role="tablist">
          {centerWorkspaceViews.map((view) => (
            <button
              aria-controls={`${workspaceViewId}-${view.value}-panel`}
              aria-selected={activeView === view.value}
              className={styles.viewTab}
              id={`${workspaceViewId}-${view.value}-tab`}
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

      <section
        aria-labelledby={activeViewTabId}
        aria-busy={isTransitionPending}
        className={styles.focusRegion}
        id={activeViewPanelId}
        ref={focusRef}
        role="tabpanel"
        tabIndex={-1}
      >
        {activeView === 'overview' ? (
          <OverviewContent
            activeSession={activeSession}
            selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
            selectedPhaseNumber={visiblePhaseNumber}
            storySummary={storySummary}
          />
        ) : null}
        {activeView === 'negotiation' ? (
          <NegotiationContent
            canActOnPhase={visiblePhaseNumber === activeSession.phase_number && !activeSession.done}
            draftFeedback={draftFeedback}
            onApprovePhase={onApprovePhase}
            onDraftFeedbackChange={onDraftFeedbackChange}
            onRevisePhase={onRevisePhase}
            phaseActionState={phaseActionState}
            phaseReview={phaseReview}
            selectedCriterionLabel={selectedCriterionLabel}
            transcriptEntries={transcriptEntries}
          />
        ) : null}
        {activeView === 'traceability' ? (
          <TraceabilityContent
            activeSession={activeSession}
            selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
          />
        ) : null}
        {activeView === 'verification' ? (
          activeSession.done ? (
            <WorkspaceVerificationConsole
              activeSession={activeSession}
              onStateChange={setVerificationState}
              state={verificationState}
            />
          ) : (
            <EmptyState
              title="Verification unlocks after negotiation"
              description="Finish the negotiation loop to approve EARS, inspect proof artifacts, and run the verification pipeline."
            />
          )
        ) : null}
      </section>
    </div>
  );
}

function OverviewContent({
  activeSession,
  selectedAcceptanceCriterionIndex,
  selectedPhaseNumber,
  storySummary,
}: {
  activeSession: StartNegotiationResponse;
  selectedAcceptanceCriterionIndex: number | null;
  selectedPhaseNumber: number;
  storySummary: string | null;
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
            Story
          </Text>
          <Text as="p" size="sm" weight="medium">
            {storySummary ?? activeSession.jira_summary ?? 'Active negotiation story'}
          </Text>
        </div>
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
            Working focus
          </Text>
          <Text as="p" size="sm">
            {selectedAcceptanceCriterionIndex !== null
              ? `Centered on AC ${selectedAcceptanceCriterionIndex + 1}`
              : 'Centered on the full story contract'}
          </Text>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected phase
          </Text>
          <Text as="p" size="sm">
            Phase {selectedPhaseNumber}
          </Text>
        </div>
      </div>
    </div>
  );
}

function NegotiationContent({
  canActOnPhase,
  draftFeedback,
  onApprovePhase,
  onDraftFeedbackChange,
  onRevisePhase,
  phaseActionState,
  phaseReview,
  selectedCriterionLabel,
  transcriptEntries,
}: {
  canActOnPhase: boolean;
  draftFeedback: string;
  onApprovePhase?: () => void;
  onDraftFeedbackChange?: (value: string) => void;
  onRevisePhase?: () => void;
  phaseActionState: PhaseActionState;
  phaseReview: PhaseReview;
  selectedCriterionLabel: string;
  transcriptEntries: ReturnType<typeof buildTranscriptEntries>;
}) {
  return (
    <div className={styles.sectionStack}>
      <section className={styles.phaseSummary} data-phase-summary="true">
        <div className={styles.phaseSummaryHeader}>
          <div>
            <Text as="p" size="xs" tone="muted">
              {phaseReview.summaryLabel}
            </Text>
            <Text as="h2" size="lg" weight="medium">
              {phaseReview.summary}
            </Text>
          </div>
          <div className={styles.inlineCluster}>
            <Badge tone={phaseReview.state === 'active' ? 'warning' : phaseReview.state === 'complete' ? 'success' : 'neutral'}>
              {phaseReview.phaseTitle}
            </Badge>
            <Badge tone="neutral">{selectedCriterionLabel}</Badge>
          </div>
        </div>
        <Text as="p" size="sm" tone="muted">
          {phaseReview.description}
        </Text>
      </section>

      {phaseReview.questions.length ? (
        <section className={styles.questionRegion}>
          <SectionHeader
            title="Clarifying questions"
            description="Human follow-ups stay distinct from backend-confirmed phase output."
          />
          <ul className={styles.questionList}>
            {phaseReview.questions.map((question) => (
              <li key={question}>
                <Text as="p" size="sm">
                  {question}
                </Text>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {phaseReview.groups.map((group) => (
        <section className={styles.reviewGroup} key={group.title}>
          <SectionHeader title={group.title} />
          {group.items.length ? (
            <div className={styles.reviewList}>
              {group.items.map((item) => (
                <article className={styles.reviewItem} key={item.id}>
                  <div className={styles.reviewItemHeader}>
                    <Mono>{item.title}</Mono>
                    <Badge tone="neutral">{item.label}</Badge>
                  </div>
                  <Text as="p" size="sm">
                    {item.body}
                  </Text>
                  {item.meta ? (
                    <Text as="p" size="xs" tone="muted">
                      {item.meta}
                    </Text>
                  ) : null}
                  {item.extra ? (
                    <details className={styles.inlineDisclosure}>
                      <summary className={styles.inlineDisclosureSummary}>Additional fields</summary>
                      <pre className={styles.rawPayloadPre}>{JSON.stringify(item.extra, null, 2)}</pre>
                    </details>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Awaiting backend confirmation"
              description="This phase will populate once the operator advances the session."
            />
          )}
        </section>
      ))}

      <details className={styles.rawPayloadDisclosure}>
        <summary className={styles.rawPayloadSummary}>Raw payload</summary>
        <pre className={styles.rawPayloadPre}>{JSON.stringify(phaseReview.rawPayload, null, 2)}</pre>
      </details>

      <section className={styles.actionSurface}>
        <SectionHeader
          title="Phase actions"
          description="Approve or revise the active phase without leaving the center workspace."
        />
        <div className={styles.field}>
          <Text as="label" htmlFor="phase-feedback" size="xs" tone="muted">
            Revision feedback
          </Text>
          <textarea
            className={styles.feedbackTextarea}
            disabled={!canActOnPhase || phaseActionState.isPending}
            id="phase-feedback"
            onChange={(event) => onDraftFeedbackChange?.(event.target.value)}
            value={draftFeedback}
          />
        </div>
        <div className={styles.actionRow}>
          <Button
            disabled={!canActOnPhase || phaseActionState.isPending}
            loading={phaseActionState.isPending && phaseActionState.activeAction === 'approve'}
            onClick={onApprovePhase}
            type="button"
          >
            Approve phase
          </Button>
          <Button
            disabled={!canActOnPhase || phaseActionState.isPending}
            loading={phaseActionState.isPending && phaseActionState.activeAction === 'revise'}
            onClick={onRevisePhase}
            type="button"
            variant="secondary"
          >
            Request revision
          </Button>
        </div>
        {phaseActionState.message ? (
          <Text
            as="p"
            className={styles.actionMessage}
            data-state={phaseActionState.status}
            size="sm"
          >
            {phaseActionState.message}
          </Text>
        ) : null}
      </section>

      <section className={styles.sectionStack}>
        <SectionHeader
          title="Transcript"
          description="System activity, operator feedback, and model output stay readable in chronological order."
        />
        <PhaseTranscript entries={transcriptEntries} />
      </section>
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
  const mappings = activeSession.traceability_map?.ac_mappings ?? [];

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Traceability"
        description="Current requirement-to-proof links stay visible without leaving the workspace route."
      />
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
        {mappings.length ? (
          mappings.map((mapping, index) => (
            <div className={styles.matrixRow} key={`mapping-${index}`}>
              <Text as="p" size="sm">
                {selectedAcceptanceCriterionIndex !== null
                  ? `AC ${selectedAcceptanceCriterionIndex + 1}`
                  : `AC ${(Number(mapping.ac_checkbox) || 0) + 1}`}
              </Text>
              <Text as="p" size="sm">
                {String(mapping.req_id ?? activeSession.jira_key)}
              </Text>
              <Text as="p" size="sm">
                {Array.isArray(mapping.ears_refs) ? mapping.ears_refs.join(', ') : 'Linked to negotiated outputs'}
              </Text>
            </div>
          ))
        ) : (
          <div className={styles.matrixRow}>
            <Text as="p" size="sm">
              Story context
            </Text>
            <Text as="p" size="sm">
              {activeSession.jira_key}
            </Text>
            <Text as="p" size="sm">
              Traceability will populate after synthesis.
            </Text>
          </div>
        )}
      </div>
    </div>
  );
}

function isTextInputTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  return ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName);
}

function getPhaseState(phaseNumber: number, activePhaseNumber: number) {
  if (phaseNumber < activePhaseNumber) {
    return 'complete';
  }

  if (phaseNumber === activePhaseNumber) {
    return 'active';
  }

  return 'pending';
}
