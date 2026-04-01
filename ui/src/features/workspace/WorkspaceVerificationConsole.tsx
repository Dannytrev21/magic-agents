import type { Dispatch, SetStateAction } from 'react';
import { Button } from '@/components/primitives/Button';
import { Badge } from '@/components/primitives/Badge';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import { streamPipelineEvents } from '@/lib/api/client';
import type {
  CompileSpecResponse,
  EarsApprovalResponse,
  GenerateTestsResponse,
  JiraUpdateResponse,
  PipelineEvent,
  StartNegotiationResponse,
} from '@/lib/api/types';
import {
  useVerificationActions,
  useVerificationQueries,
} from '@/lib/query/sessionHooks';
import styles from '@/features/workspace/workspace.module.css';

export type VerificationWorkspaceState = {
  approval: EarsApprovalResponse | null;
  approvalError: string | null;
  artifactView: 'spec' | 'tests';
  compileError: string | null;
  compileResult: CompileSpecResponse | null;
  generateError: string | null;
  generateResult: GenerateTestsResponse | null;
  jiraUpdateError: string | null;
  jiraUpdateResult: JiraUpdateResponse | null;
  pipelineError: string | null;
  pipelineEvents: PipelineEvent[];
  pipelineRunning: boolean;
  pipelineSummary: PipelineEvent | null;
};

type WorkspaceVerificationConsoleProps = {
  activeSession: StartNegotiationResponse;
  state: VerificationWorkspaceState;
  onStateChange: Dispatch<SetStateAction<VerificationWorkspaceState>>;
};

export function buildInitialVerificationState(
  session: StartNegotiationResponse | null,
): VerificationWorkspaceState {
  return {
    approval: resolveSessionApproval(session),
    approvalError: null,
    artifactView: 'spec',
    compileError: null,
    compileResult: null,
    generateError: null,
    generateResult: null,
    jiraUpdateError: null,
    jiraUpdateResult: null,
    pipelineError: null,
    pipelineEvents: [],
    pipelineRunning: false,
    pipelineSummary: null,
  };
}

export function WorkspaceVerificationConsole({
  activeSession,
  state,
  onStateChange,
}: WorkspaceVerificationConsoleProps) {
  const { jiraConfigured } = useVerificationQueries();
  const { approveMutation, compileMutation, generateMutation, jiraUpdateMutation } =
    useVerificationActions(activeSession.session_id);
  const approval = state.approval ?? resolveSessionApproval(activeSession);
  const compiledSpec = state.compileResult ?? buildCompileResultFromPipeline(state.pipelineSummary);
  const generatedTests =
    state.generateResult ?? buildGeneratedTestsFromPipeline(state.pipelineSummary);
  const verdicts =
    generatedTests?.verdicts ?? state.pipelineSummary?.verdicts ?? activeSession.verdicts ?? [];
  const approvalLocked = !approval?.approved;
  const failuresFirstVerdicts = [...verdicts].sort((left, right) => {
    const leftWeight = left.passed ? 1 : 0;
    const rightWeight = right.passed ? 1 : 0;
    return leftWeight - rightWeight;
  });
  const passedCount = verdicts.filter((verdict) => verdict.passed).length;
  const failedCount = verdicts.length - passedCount;
  const jiraCount = countCheckboxes(state.jiraUpdateResult);
  const artifactTabs: Array<{ label: string; value: 'spec' | 'tests' }> = [];

  if (compiledSpec) {
    artifactTabs.push({ label: 'Spec YAML', value: 'spec' });
  }

  if (generatedTests?.test_content) {
    artifactTabs.push({ label: 'Generated tests', value: 'tests' });
  }

  async function handleApprove() {
    onStateChange((current) => ({
      ...current,
      approvalError: null,
    }));

    try {
      const response = await approveMutation.mutateAsync('web_operator');
      onStateChange((current) => ({
        ...current,
        approval: response,
        approvalError: null,
      }));
    } catch (error) {
      onStateChange((current) => ({
        ...current,
        approvalError: resolveErrorMessage(error, 'Unable to approve the EARS contract.'),
      }));
    }
  }

  async function handleCompile() {
    onStateChange((current) => ({
      ...current,
      compileError: null,
      jiraUpdateResult: null,
    }));

    try {
      const response = await compileMutation.mutateAsync();
      onStateChange((current) => ({
        ...current,
        artifactView: 'spec',
        compileError: null,
        compileResult: response,
      }));
    } catch (error) {
      onStateChange((current) => ({
        ...current,
        compileError: resolveErrorMessage(error, 'Unable to compile the current spec.'),
      }));
    }
  }

  async function handleGenerate() {
    onStateChange((current) => ({
      ...current,
      generateError: null,
      jiraUpdateResult: null,
    }));

    try {
      const response = await generateMutation.mutateAsync();
      onStateChange((current) => ({
        ...current,
        artifactView: response.test_content ? 'tests' : current.artifactView,
        generateError: null,
        generateResult: response,
      }));
    } catch (error) {
      onStateChange((current) => ({
        ...current,
        generateError: resolveErrorMessage(
          error,
          'Unable to generate tests for the current spec.',
        ),
      }));
    }
  }

  async function handleRunPipeline() {
    onStateChange((current) => ({
      ...current,
      jiraUpdateResult: null,
      pipelineError: null,
      pipelineEvents: [],
      pipelineRunning: true,
      pipelineSummary: null,
    }));

    try {
      await streamPipelineEvents(activeSession.session_id, (event) => {
        onStateChange((current) => updatePipelineState(current, event));
      });
      onStateChange((current) => ({
        ...current,
        pipelineRunning: false,
      }));
    } catch (error) {
      const message = resolveErrorMessage(error, 'Unable to stream the verification pipeline.');
      onStateChange((current) => ({
        ...current,
        pipelineError: message,
        pipelineRunning: false,
      }));
    }
  }

  async function handleSendJiraFeedback() {
    onStateChange((current) => ({
      ...current,
      jiraUpdateError: null,
    }));

    try {
      const response = await jiraUpdateMutation.mutateAsync();
      onStateChange((current) => ({
        ...current,
        jiraUpdateError: null,
        jiraUpdateResult: response,
      }));
    } catch (error) {
      onStateChange((current) => ({
        ...current,
        jiraUpdateError: resolveErrorMessage(
          error,
          'Unable to update Jira with the latest verification results.',
        ),
      }));
    }
  }

  return (
    <div className={styles.sectionStack}>
      <section className={styles.phaseSummary} data-phase-summary="true">
        <div className={styles.phaseSummaryHeader}>
          <div>
            <Text as="p" size="xs" tone="muted">
              Verification console
            </Text>
            <Text as="h2" size="lg" weight="medium">
              Proof artifacts, execution, and Jira feedback stay in one surface.
            </Text>
          </div>
          <div className={styles.inlineCluster}>
            <Badge tone={approvalLocked ? 'warning' : 'success'}>
              {approvalLocked ? 'Awaiting approval' : 'Approved'}
            </Badge>
            <Badge tone="neutral">{activeSession.ears_statements?.length ?? 0} EARS</Badge>
          </div>
        </div>
        <Text as="p" size="sm" tone="muted">
          Approval gates the compiled contract, generated proof artifacts, live execution stream,
          and the Jira update path.
        </Text>
      </section>

      <section className={styles.actionSurface}>
        <SectionHeader
          title="EARS approval gate"
          description="The backend-confirmed approval state unlocks the verification controls and stays visible inside the workspace."
          action={
            <Badge tone={approvalLocked ? 'warning' : 'success'}>
              {approvalLocked ? 'EARS approval required' : 'Approval recorded'}
            </Badge>
          }
        />
        <div className={styles.detailList}>
          <div className={styles.detailRow}>
            <Text as="p" size="xs" tone="muted">
              Approval status
            </Text>
            {approval ? (
              <div className={styles.inlineCluster}>
                <Text as="p" size="sm" weight="medium">
                  Approved by {approval.approved_by}
                </Text>
                <Mono>{approval.approved_at}</Mono>
              </div>
            ) : (
              <Text as="p" size="sm">
                Explicit approval is still required before verification can run.
              </Text>
            )}
          </div>
        </div>
        <div className={styles.actionRow}>
          <Button
            disabled={Boolean(approval)}
            loading={approveMutation.isPending}
            onClick={() => void handleApprove()}
          >
            Approve EARS
          </Button>
        </div>
        {state.approvalError ? (
          <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
            {state.approvalError}
          </Text>
        ) : null}
      </section>

      <section className={styles.actionSurface}>
        <SectionHeader
          title="Execution controls"
          description="Compile, test generation, and the full pipeline stay in-place so the operator never leaves the active story."
        />
        <div className={styles.actionRow}>
          <Button
            disabled={approvalLocked}
            loading={compileMutation.isPending}
            onClick={() => void handleCompile()}
          >
            Compile spec
          </Button>
          <Button
            disabled={approvalLocked || !compiledSpec}
            loading={generateMutation.isPending}
            onClick={() => void handleGenerate()}
            variant="secondary"
          >
            Generate tests
          </Button>
          <Button
            disabled={approvalLocked || state.pipelineRunning}
            loading={state.pipelineRunning}
            onClick={() => void handleRunPipeline()}
            variant="ghost"
          >
            Run full pipeline
          </Button>
        </div>
        {state.compileError ? (
          <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
            {state.compileError}
          </Text>
        ) : null}
        {state.generateError ? (
          <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
            {state.generateError}
          </Text>
        ) : null}
      </section>

      <section className={styles.sectionStack}>
        <SectionHeader
          title="Artifacts"
          description="Compiled YAML and generated tests remain readable and can be revisited after other workspace actions."
        />
        {!artifactTabs.length ? (
          <EmptyState
            title="No artifacts yet"
            description="Compile the spec or generate tests to inspect the read-only verification artifacts inline."
          />
        ) : (
          <div className={styles.sectionStack}>
            <div aria-label="Artifact views" className={styles.viewTabs} role="tablist">
              {artifactTabs.map((tab) => (
                <button
                  aria-selected={state.artifactView === tab.value}
                  className={styles.viewTab}
                  key={tab.value}
                  onClick={() =>
                    onStateChange((current) => ({
                      ...current,
                      artifactView: tab.value,
                    }))
                  }
                  role="tab"
                  type="button"
                >
                  {tab.label}
                </button>
              ))}
            </div>
            {state.artifactView === 'tests' && generatedTests?.test_content ? (
              <div className={styles.sectionStack}>
                {generatedTests.test_path ? <Mono>{generatedTests.test_path}</Mono> : null}
                <pre className={styles.rawPayloadPre}>{generatedTests.test_content}</pre>
              </div>
            ) : compiledSpec ? (
              <div className={styles.sectionStack}>
                <Mono>{compiledSpec.spec_path}</Mono>
                <pre className={styles.rawPayloadPre}>{compiledSpec.spec_content}</pre>
              </div>
            ) : null}
          </div>
        )}
      </section>

      <section className={styles.sectionStack}>
        <SectionHeader
          title="Pipeline console"
          description="Step-level progress appends in order so operators can monitor the run without polling or leaving the page."
          action={
            <Badge tone={resolvePipelineTone(state.pipelineRunning, state.pipelineError, state.pipelineSummary)}>
              {resolvePipelineLabel(state.pipelineRunning, state.pipelineError, state.pipelineSummary)}
            </Badge>
          }
        />
        {state.pipelineError ? (
          <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
            {state.pipelineError}
          </Text>
        ) : null}
        {!state.pipelineEvents.length ? (
          <EmptyState
            title="Console is idle"
            description="Run the full pipeline to stream compile, generation, and evaluation progress into the workspace."
          />
        ) : (
          <div className={styles.console}>
            {state.pipelineEvents.map((event, index) => (
              <article
                className={styles.consoleEntry}
                data-status={event.status ?? event.type}
                key={`${event.type}-${event.step ?? 'event'}-${index}`}
              >
                <div className={styles.consoleEntryHeader}>
                  <div className={styles.inlineCluster}>
                    <Badge tone={resolveConsoleTone(event.status)}>
                      {event.step ?? event.type}
                    </Badge>
                    <Badge tone="neutral">{event.status ?? event.type}</Badge>
                  </div>
                  {event.message ? (
                    <Text as="p" size="sm" weight="medium">
                      {event.message}
                    </Text>
                  ) : null}
                </div>
                {event.step || event.type === 'done' ? (
                  <Text as="p" size="sm" tone="muted">
                    {buildConsoleDetail(event)}
                  </Text>
                ) : null}
              </article>
            ))}
          </div>
        )}
      </section>

      <section className={styles.sectionStack}>
        <SectionHeader
          title="Post-run results"
          description="Overall outcome stays ahead of the per-AC verdicts, evidence details, and Jira feedback controls."
        />
        {!verdicts.length ? (
          state.pipelineError ? (
            <div className={styles.reviewList}>
              <article className={styles.reviewItem}>
                <div className={styles.reviewItemHeader}>
                  <Text as="h3" size="sm" weight="medium">
                    Pipeline run failed before verdicts were produced
                  </Text>
                  <Badge tone="error">Needs rerun</Badge>
                </div>
                <Text as="p" size="sm">
                  Resolve the pipeline failure and rerun the console to produce verdicts and Jira feedback.
                </Text>
              </article>
            </div>
          ) : (
            <EmptyState
              title="No results yet"
              description="Generate tests or run the full pipeline to populate verdicts and downstream Jira feedback."
            />
          )
        ) : (
          <div className={styles.sectionStack}>
            <div className={styles.detailList}>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Overall result
                </Text>
                <div className={styles.inlineCluster}>
                  <Text as="p" size="sm" weight="medium">
                    {failedCount ? `${failedCount} failing AC verdict${failedCount === 1 ? '' : 's'}` : 'All AC verdicts passed'}
                  </Text>
                  <Badge tone={failedCount ? 'warning' : 'success'}>
                    {passedCount}/{verdicts.length} passed
                  </Badge>
                </div>
              </div>
            </div>
            <div className={styles.reviewList}>
              {failuresFirstVerdicts.map((verdict, index) => (
                <article className={styles.reviewItem} key={`${verdict.ac_checkbox ?? index}`}>
                  <div className={styles.reviewItemHeader}>
                    <div>
                      <Text as="h3" size="sm" weight="medium">
                        AC {(verdict.ac_checkbox ?? verdict.ac_index ?? index) + 1}
                      </Text>
                      <Text as="p" size="sm" tone="muted">
                        {verdict.ac_text ?? 'Acceptance criterion verdict'}
                      </Text>
                    </div>
                    <Badge tone={verdict.passed ? 'success' : 'warning'}>
                      {verdict.passed ? 'Passed' : 'Failed'}
                    </Badge>
                  </div>
                  <Text as="p" size="sm">
                    {verdict.summary ?? 'Evidence summary pending.'}
                  </Text>
                  <div className={styles.reviewList}>
                    {(verdict.evidence ?? []).map((evidence) => (
                      <article className={styles.reviewItem} key={String(evidence.ref)}>
                        <div className={styles.reviewItemHeader}>
                          <Mono>{String(evidence.ref)}</Mono>
                          <Badge tone={evidence.passed ? 'success' : 'warning'}>
                            {evidence.verification_type ?? 'verification'}
                          </Badge>
                        </div>
                        <Text as="p" size="sm">
                          {String(evidence.details ?? evidence.description ?? 'No evidence details provided.')}
                        </Text>
                      </article>
                    ))}
                  </div>
                </article>
              ))}
            </div>
            <div className={styles.actionSurface}>
              <SectionHeader
                title="Jira feedback"
                description="Post the latest checkbox and evidence outcome back to Jira from the same post-run surface."
              />
              <div className={styles.actionRow}>
                <Button
                  disabled={!jiraConfigured || !verdicts.length}
                  loading={jiraUpdateMutation.isPending}
                  onClick={() => void handleSendJiraFeedback()}
                >
                  Send Jira feedback
                </Button>
              </div>
              {!jiraConfigured ? (
                <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
                  Jira is not configured for this environment, so checkbox and evidence updates are unavailable.
                </Text>
              ) : null}
              {state.jiraUpdateError ? (
                <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
                  {state.jiraUpdateError}
                </Text>
              ) : null}
              {state.jiraUpdateResult ? (
                <Text as="p" className={styles.actionMessage} data-state="success" size="sm">
                  {buildJiraResultMessage(state.jiraUpdateResult, jiraCount)}
                </Text>
              ) : null}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function resolveSessionApproval(
  session: StartNegotiationResponse | null,
): EarsApprovalResponse | null {
  if (!session?.approved) {
    return null;
  }

  return {
    approved: true,
    approved_at: session.approved_at ?? '',
    approved_by: session.approved_by ?? 'web_operator',
  };
}

function buildCompileResultFromPipeline(event: PipelineEvent | null): CompileSpecResponse | null {
  if (!event?.spec_content || !event.spec_path) {
    return null;
  }

  return {
    requirements: event.requirements,
    spec_content: event.spec_content,
    spec_path: event.spec_path,
    traceability: event.traceability,
  };
}

function buildGeneratedTestsFromPipeline(event: PipelineEvent | null): GenerateTestsResponse | null {
  if (!event?.test_content && !event?.verdicts?.length) {
    return null;
  }

  return {
    all_passed: event.all_passed,
    steps: [],
    test_content: event.test_content,
    test_path: event.test_path,
    verdicts: event.verdicts,
  };
}

function updatePipelineState(
  current: VerificationWorkspaceState,
  event: PipelineEvent,
): VerificationWorkspaceState {
  const next = {
    ...current,
    pipelineEvents: [...current.pipelineEvents, event],
  };

  if (event.type === 'done') {
    return {
      ...next,
      artifactView: event.test_content ? 'tests' : current.artifactView,
      pipelineError: null,
      pipelineRunning: false,
      pipelineSummary: event,
    };
  }

  if (event.type === 'error' || event.status === 'failed') {
    return {
      ...next,
      pipelineError: String(event.message ?? 'The pipeline failed.'),
      pipelineRunning: false,
    };
  }

  return next;
}

function resolvePipelineLabel(
  isRunning: boolean,
  pipelineError: string | null,
  summary: PipelineEvent | null,
) {
  if (isRunning) {
    return 'Running';
  }

  if (pipelineError) {
    return 'Failed';
  }

  if (summary) {
    return 'Complete';
  }

  return 'Idle';
}

function resolvePipelineTone(
  isRunning: boolean,
  pipelineError: string | null,
  summary: PipelineEvent | null,
): 'error' | 'success' | 'warning' {
  if (isRunning) {
    return 'warning';
  }

  if (pipelineError) {
    return 'error';
  }

  return summary ? 'success' : 'warning';
}

function resolveConsoleTone(status: unknown): 'error' | 'success' | 'warning' | 'neutral' {
  if (status === 'failed') {
    return 'error';
  }

  if (status === 'running') {
    return 'warning';
  }

  if (status === 'done') {
    return 'success';
  }

  return 'neutral';
}

function buildConsoleDetail(event: PipelineEvent) {
  if (event.type === 'done') {
    return event.all_passed
      ? 'All acceptance criteria passed their linked verification checks.'
      : 'The run completed with failing acceptance criteria.';
  }

  return event.step ? `Step: ${event.step}` : 'Pipeline event';
}

function countCheckboxes(result: JiraUpdateResponse | null) {
  if (!result) {
    return 0;
  }

  if (Array.isArray(result.checkboxes_ticked)) {
    return result.checkboxes_ticked.length;
  }

  return typeof result.checkboxes_ticked === 'number' ? result.checkboxes_ticked : 0;
}

function buildJiraResultMessage(result: JiraUpdateResponse, checkboxCount: number) {
  const evidencePosted = result.evidence_posted ?? result.comment_posted ?? false;

  return `${checkboxCount} checkbox${checkboxCount === 1 ? '' : 'es'} updated. Evidence ${evidencePosted ? 'posted' : 'not posted'}.`;
}

function resolveErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}
