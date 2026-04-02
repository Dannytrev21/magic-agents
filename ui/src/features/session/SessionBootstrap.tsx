import {
  useDeferredValue,
  useEffect,
  useId,
  useRef,
  useState,
  type ChangeEvent,
  type FormEvent,
} from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import styles from '@/features/session/session-bootstrap.module.css';
import { Badge } from '@/components/primitives/Badge';
import { Button } from '@/components/primitives/Button';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Skeleton } from '@/components/primitives/Skeleton';
import { Text } from '@/components/primitives/Text';
import {
  buildStartNegotiationPayload,
  defaultSessionIntakeDraft,
  filterStories,
  normalizeJiraTicket,
  normalizeManualStory,
  type SessionIntakeDraft,
  type SessionIntakeMode,
  type SessionIntakeStory,
} from '@/features/session/sessionIntakeModel';
import {
  buildAcceptanceCriteriaRailItems,
  buildSessionHealthSummary,
  buildSessionPhaseRailItems,
  getStoryCheckpointState,
  normalizeResumedStory,
} from '@/features/session/sessionWorkspaceModel';
import { fetchJiraTicket } from '@/lib/api/client';
import type { JiraStory, StartNegotiationResponse } from '@/lib/api/types';
import { queryKeys } from '@/lib/query/queryKeys';
import {
  useResumeSessionMutation,
  useSessionBootstrapQueries,
  useStartNegotiationMutation,
  useStorySessionQueries,
} from '@/lib/query/sessionHooks';

type SessionBootstrapProps = {
  activeSession?: StartNegotiationResponse | null;
  draftFeedback?: string;
  onAcceptanceCriterionSelect?: (index: number) => void;
  onDraftFeedbackChange?: (value: string) => void;
  onPhaseSelect?: (phaseNumber: number) => void;
  onSessionStarted?: (session: StartNegotiationResponse, story: SessionIntakeStory) => void;
  selectedAcceptanceCriterionIndex?: number | null;
  selectedPhaseNumber?: number | null;
};

export function SessionBootstrap({
  activeSession = null,
  draftFeedback = '',
  onAcceptanceCriterionSelect,
  onDraftFeedbackChange,
  onPhaseSelect,
  onSessionStarted,
  selectedAcceptanceCriterionIndex = null,
  selectedPhaseNumber = null,
}: SessionBootstrapProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [draft, setDraft] = useState(defaultSessionIntakeDraft);
  const [mode, setMode] = useState<SessionIntakeMode>('jira');
  const [selectedStoryKey, setSelectedStoryKey] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isHydratingStory, setIsHydratingStory] = useState(false);
  const queryClient = useQueryClient();
  const deferredFilter = useDeferredValue(draft.storyFilter);
  const { configured, isError, isLoading, stories, storiesError } = useSessionBootstrapQueries();
  const sessionInfoByStoryKey = useStorySessionQueries(stories);
  const startMutation = useStartNegotiationMutation();
  const resumeMutation = useResumeSessionMutation();
  const tabGroupId = useId();
  const jiraTabId = `${tabGroupId}-jira`;
  const manualTabId = `${tabGroupId}-manual`;
  const jiraPanelId = `${tabGroupId}-jira-panel`;
  const manualPanelId = `${tabGroupId}-manual-panel`;

  const filteredStories = filterStories(stories, deferredFilter);
  const selectedStory = stories.find((story) => story.key === selectedStoryKey) ?? null;
  const selectedStorySessionInfo = selectedStoryKey
    ? sessionInfoByStoryKey[selectedStoryKey]
    : undefined;
  const selectedCheckpoint = selectedStorySessionInfo?.has_checkpoint
    ? selectedStorySessionInfo.session ?? undefined
    : undefined;
  const selectedCheckpointState = getStoryCheckpointState(selectedCheckpoint);
  const selectedTicketQuery = useQuery({
    enabled: mode === 'jira' && Boolean(selectedStoryKey),
    queryKey: queryKeys.jiraTicket(selectedStoryKey ?? '__none__'),
    queryFn: () => fetchJiraTicket(selectedStoryKey ?? ''),
    staleTime: 30_000,
  });
  const previewStory = selectedTicketQuery.data ? normalizeJiraTicket(selectedTicketQuery.data) : null;
  const railStory =
    activeSession?.acceptance_criteria?.length || activeSession?.jira_summary
      ? normalizeResumedStory(activeSession)
      : mode === 'jira'
        ? previewStory
        : normalizeManualStory({
            acceptanceCriteriaText: draft.acceptanceCriteriaText,
            jiraKey: draft.jiraKey,
            jiraSummary: draft.jiraSummary,
          });
  const checklistItems = buildAcceptanceCriteriaRailItems(
    activeSession,
    railStory,
    selectedAcceptanceCriterionIndex,
  );
  const phaseItems = buildSessionPhaseRailItems(activeSession, selectedPhaseNumber);
  const healthSummary = buildSessionHealthSummary(activeSession?.usage);
  const showConfigurationFallback = !isLoading && !isError && (!configured || Boolean(storiesError));
  const showEmptyState =
    !isLoading && !isError && configured && !storiesError && stories.length === 0;
  const showNoMatches =
    !isLoading &&
    !isError &&
    configured &&
    !storiesError &&
    stories.length > 0 &&
    filteredStories.length === 0;
  const showStoryFilter =
    !isLoading && !isError && !showConfigurationFallback && stories.length > 0;
  const isSubmitting = startMutation.isPending || resumeMutation.isPending || isHydratingStory;
  const canResume = Boolean(selectedStory && selectedCheckpoint && mode === 'jira');
  const intakeStatus = resolveIntakeStatus({
    configured,
    hasStories: stories.length > 0,
    storiesError,
  });
  const intakeMeta = buildIntakeMeta({
    canResume,
    configured,
    hasStories: stories.length > 0,
    selectedStoryKey,
  });

  useEffect(() => {
    if (!activeSession?.session_id) {
      return;
    }

    const scrollContainer = rootRef.current?.parentElement;
    if (!scrollContainer) {
      return;
    }

    scrollContainer.scrollTop = 0;
  }, [activeSession?.session_id]);

  function updateDraft(key: keyof SessionIntakeDraft) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setDraft((current) => ({ ...current, [key]: event.target.value }));
    };
  }

  function handleModeChange(nextMode: SessionIntakeMode) {
    setMode(nextMode);
    setSubmitError(null);
  }

  function applyStory(story: JiraStory) {
    setSelectedStoryKey(story.key);
    setSubmitError(null);
  }

  async function resolveSelectedStory(): Promise<SessionIntakeStory> {
    if (mode === 'manual') {
      return normalizeManualStory({
        acceptanceCriteriaText: draft.acceptanceCriteriaText,
        jiraKey: draft.jiraKey,
        jiraSummary: draft.jiraSummary,
      });
    }

    if (!selectedStoryKey) {
      throw new Error('Select a Jira story before starting a session.');
    }

    if (selectedTicketQuery.data) {
      return normalizeJiraTicket(selectedTicketQuery.data);
    }

    setIsHydratingStory(true);

    try {
      const ticket = await queryClient.fetchQuery({
        queryKey: queryKeys.jiraTicket(selectedStoryKey),
        queryFn: () => fetchJiraTicket(selectedStoryKey),
        staleTime: 30_000,
      });

      return normalizeJiraTicket(ticket);
    } finally {
      setIsHydratingStory(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitError(null);

    try {
      const story = await resolveSelectedStory();
      const session = await startMutation.mutateAsync(buildStartNegotiationPayload(story));

      onSessionStarted?.(
        {
          ...session,
          acceptance_criteria: session.acceptance_criteria ?? story.acceptanceCriteria,
          jira_summary: session.jira_summary ?? story.summary,
          usage: session.usage ?? null,
        },
        story,
      );
    } catch (error) {
      setSubmitError(resolveIntakeError(error));
    }
  }

  async function handleResume() {
    if (!selectedStoryKey) {
      setSubmitError('Select a Jira story before resuming a session.');
      return;
    }

    setSubmitError(null);

    try {
      const session = await resumeMutation.mutateAsync(selectedStoryKey);
      const story = normalizeResumedStory(session);

      onSessionStarted?.(session, story);
    } catch (error) {
      setSubmitError(resolveResumeError(error));
    }
  }

  return (
    <div className={styles.stack} ref={rootRef}>
      <div className={styles.section}>
        <SectionHeader
          title="Story intake"
          description="Start from Jira or enter a story manually without leaving the rail."
          action={
            <div className={styles.intakeStatus} data-state={intakeStatus.state}>
              <span aria-hidden="true" className={styles.intakeStatusDot} />
              <Text as="span" size="xs" weight="medium">
                {intakeStatus.label}
              </Text>
            </div>
          }
        />
        <div className={styles.modeGroup}>
          {intakeMeta.length ? (
            <div className={styles.intakeMeta}>
              {intakeMeta.map((item) => (
                <Text as="p" className={styles.intakeMetaItem} key={item} size="xs" tone="muted">
                  {item}
                </Text>
              ))}
            </div>
          ) : null}
          <div aria-label="Story intake modes" className={styles.modeTabs} role="tablist">
            <button
              aria-controls={jiraPanelId}
              aria-selected={mode === 'jira'}
              className={styles.modeTab}
              id={jiraTabId}
              onClick={() => handleModeChange('jira')}
              role="tab"
              type="button"
            >
              Jira intake
            </button>
            <button
              aria-controls={manualPanelId}
              aria-selected={mode === 'manual'}
              className={styles.modeTab}
              id={manualTabId}
              onClick={() => handleModeChange('manual')}
              role="tab"
              type="button"
            >
              Manual entry
            </button>
          </div>
        </div>
      </div>
      <form className={styles.form} onSubmit={handleSubmit}>
        {mode === 'jira' ? (
          <section
            aria-labelledby={jiraTabId}
            className={styles.section}
            id={jiraPanelId}
            role="tabpanel"
          >
            <div className={styles.modeLead}>
              <Text as="p" className={styles.modeEyebrow} size="xs" tone="muted">
                From Jira
              </Text>
              <Text as="p" size="sm">
                Select an active story and hydrate its acceptance criteria into the workspace.
              </Text>
            </div>
            {showStoryFilter ? (
              <div className={styles.field}>
                <Text as="label" htmlFor="story-filter" size="xs" tone="muted">
                  Story search
                </Text>
                <input
                  className={styles.input}
                  id="story-filter"
                  name="story-filter"
                  onChange={updateDraft('storyFilter')}
                  placeholder="Filter by key or summary…"
                  type="search"
                  value={draft.storyFilter}
                />
              </div>
            ) : null}
            {isLoading ? <Text size="sm">Loading Jira intake</Text> : null}
            {isLoading ? <Skeleton aria-label="Loading Jira intake" /> : null}
            {isError ? (
              <div className={styles.inlineNotice} data-tone="warning">
                <div className={styles.inlineNoticeBody}>
                  <Text as="p" size="sm" weight="semibold">
                    Jira is temporarily unavailable
                  </Text>
                  <Text as="p" size="sm" tone="muted">
                    Refresh the workspace or continue in manual entry while the connection recovers.
                  </Text>
                </div>
                <Button onClick={() => handleModeChange('manual')} type="button" variant="secondary">
                  Use manual entry
                </Button>
              </div>
            ) : null}
            {showConfigurationFallback ? (
              <div className={styles.inlineNotice} data-tone="warning">
                <div className={styles.inlineNoticeBody}>
                  <Text as="p" size="sm" weight="semibold">
                    Jira configuration required
                  </Text>
                  <Text as="p" size="sm" tone="muted">
                    Jira is unavailable until credentials or access are restored. Manual entry
                    stays available in this rail.
                  </Text>
                </div>
                <Button onClick={() => handleModeChange('manual')} type="button" variant="secondary">
                  Use manual entry
                </Button>
              </div>
            ) : null}
            {showEmptyState ? (
              <div className={styles.inlineNotice}>
                <div className={styles.inlineNoticeBody}>
                  <Text as="p" size="sm" weight="semibold">
                    No active Jira stories
                  </Text>
                  <Text as="p" size="sm" tone="muted">
                    Switch to manual entry to keep working until the backend exposes active tickets.
                  </Text>
                </div>
                <Button onClick={() => handleModeChange('manual')} type="button" variant="secondary">
                  Use manual entry
                </Button>
              </div>
            ) : null}
            {showNoMatches ? (
              <div className={styles.inlineNotice}>
                <div className={styles.inlineNoticeBody}>
                  <Text as="p" size="sm" weight="semibold">
                    No stories match this filter
                  </Text>
                  <Text as="p" size="sm" tone="muted">
                    Try a different key or summary term to narrow the Jira list.
                  </Text>
                </div>
              </div>
            ) : null}
            {!isLoading && !isError && !showConfigurationFallback && filteredStories.length ? (
              <div className={styles.list}>
                {filteredStories.map((story) => {
                  const checkpointInfo = sessionInfoByStoryKey[story.key];
                  const checkpointState = checkpointInfo?.has_checkpoint
                    ? getStoryCheckpointState(checkpointInfo.session)
                    : 'new';

                  return (
                    <button
                      aria-label={`Select story ${story.key}`}
                      className={styles.storyButton}
                      data-selected={selectedStoryKey === story.key}
                      key={story.key}
                      onClick={() => applyStory(story)}
                      type="button"
                    >
                      <div className={styles.storyMeta}>
                        <div className={styles.storyKey}>
                          <Mono>{story.key}</Mono>
                          <Badge tone="neutral">{story.status || 'In Progress'}</Badge>
                        </div>
                        <Badge
                          tone={
                            checkpointState === 'complete'
                              ? 'success'
                              : checkpointState === 'resumable'
                                ? 'warning'
                                : 'neutral'
                          }
                        >
                          {checkpointState === 'complete'
                            ? 'Complete'
                            : checkpointState === 'resumable'
                              ? 'Resume ready'
                              : 'New'}
                        </Badge>
                      </div>
                      <Text as="span" size="sm">
                        {story.summary}
                      </Text>
                    </button>
                  );
                })}
              </div>
            ) : null}
            {selectedStory ? (
              <div className={styles.selectionSummary}>
                <Text as="p" size="xs" tone="muted">
                  Selected story
                </Text>
                <div className={styles.storyMeta}>
                  <Mono>{selectedStory.key}</Mono>
                  <Badge tone={canResume ? 'warning' : 'info'}>
                    {canResume
                      ? selectedCheckpointState === 'complete'
                        ? 'Complete session'
                        : 'Resume from checkpoint'
                      : 'Ready to hydrate'}
                  </Badge>
                </div>
                <Text as="p" size="sm">
                  {selectedStory.summary}
                </Text>
                {selectedCheckpoint ? (
                  <div className={styles.detailCluster}>
                    <Badge tone="info">Phase {selectedCheckpoint.phase_number ?? '\u2014'}</Badge>
                    <Text as="p" size="sm" weight="medium">
                      {selectedCheckpoint.phase_title ?? selectedCheckpoint.current_phase ?? 'Checkpointed'}
                    </Text>
                    <Text as="p" size="xs" tone="muted">
                      {selectedCheckpoint.log_entries ?? 0} log entries
                    </Text>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : (
          <section
            aria-labelledby={manualTabId}
            className={styles.section}
            id={manualPanelId}
            role="tabpanel"
          >
            <SectionHeader
              title="Manual entry"
              description="Capture story metadata and acceptance criteria when Jira is unavailable or the operator is working from raw notes."
            />
            <div className={styles.field}>
              <Text as="label" htmlFor="jira-key" size="xs" tone="muted">
                Jira key
              </Text>
              <input
                className={styles.input}
                id="jira-key"
                onChange={updateDraft('jiraKey')}
                required
                type="text"
                value={draft.jiraKey}
              />
            </div>
            <div className={styles.field}>
              <Text as="label" htmlFor="jira-summary" size="xs" tone="muted">
                Summary
              </Text>
              <input
                className={styles.input}
                id="jira-summary"
                onChange={updateDraft('jiraSummary')}
                required
                type="text"
                value={draft.jiraSummary}
              />
            </div>
            <div className={styles.field}>
              <Text as="label" htmlFor="acceptance-criteria" size="xs" tone="muted">
                Acceptance criteria
              </Text>
              <textarea
                className={styles.textarea}
                id="acceptance-criteria"
                onChange={updateDraft('acceptanceCriteriaText')}
                required
                value={draft.acceptanceCriteriaText}
              />
            </div>
          </section>
        )}
        {submitError ? (
          <Text as="p" size="sm" tone="muted">
            {submitError}
          </Text>
        ) : null}
        {canResume ? (
          <div className={styles.actionRow}>
            <Button loading={resumeMutation.isPending} onClick={handleResume} type="button">
              Resume session
            </Button>
            <Button disabled={!selectedStoryKey} loading={startMutation.isPending} type="submit" variant="secondary">
              Start fresh session
            </Button>
          </div>
        ) : mode === 'jira' ? (
          selectedStoryKey ? (
            <Button loading={isSubmitting} type="submit">
              Start session from Jira
            </Button>
          ) : null
        ) : (
          <Button loading={isSubmitting} type="submit">
            Start session from manual story
          </Button>
        )}
        {startMutation.data?.session_id ? (
          <div className={styles.sessionSummary}>
            <Text as="p" size="sm" weight="medium">
              Active session created
            </Text>
            <Mono>{startMutation.data.session_id}</Mono>
          </div>
        ) : null}
      </form>
      {(activeSession || checklistItems.length > 0) ? <Divider /> : null}
      {activeSession ? (
        <section className={styles.section}>
          <SectionHeader
            title="Session context"
            description="Backend-confirmed phase state stays authoritative while the operator keeps a local draft ready for the next interaction."
            action={<Badge tone={activeSession.resumed ? 'warning' : 'success'}>{activeSession.resumed ? 'Resumed' : 'Live session'}</Badge>}
          />
          <div className={styles.selectionSummary}>
            <div className={styles.storyMeta}>
              <Mono>{activeSession.session_id}</Mono>
              <Badge tone="info">Phase {activeSession.phase_number}</Badge>
            </div>
            <Text as="p" size="sm">
              {activeSession.phase_title}
            </Text>
          </div>
          <div className={styles.field}>
            <Text as="label" htmlFor="draft-feedback" size="xs" tone="muted">
              Draft feedback
            </Text>
            <textarea
              className={styles.textarea}
              id="draft-feedback"
              onChange={(event) => onDraftFeedbackChange?.(event.target.value)}
              value={draftFeedback}
            />
          </div>
        </section>
      ) : null}
      {checklistItems.length ? (
        <section className={styles.section}>
          <SectionHeader
            title="Acceptance criteria"
            description="Selection, classification, and verdict state stay scannable from the rail."
          />
          <ol aria-label="Story checklist" className={styles.criteriaList}>
            {checklistItems.map((item) => (
              <li key={item.index}>
                <button
                  className={styles.criteriaButton}
                  data-selected={item.selected}
                  data-state={item.state}
                  onClick={() => onAcceptanceCriterionSelect?.(item.index)}
                  title={item.fullText}
                  type="button"
                >
                  <div className={styles.criteriaHeader}>
                    <Mono>AC[{item.index + 1}]</Mono>
                    <div className={styles.storyKey}>
                      {item.classification ? <Badge tone="neutral">{item.classification}</Badge> : null}
                      <Badge
                        tone={
                          item.state === 'passed'
                            ? 'success'
                            : item.state === 'failed'
                              ? 'warning'
                              : 'neutral'
                        }
                      >
                        {item.state === 'passed'
                          ? 'Passed'
                          : item.state === 'failed'
                            ? 'Failed'
                            : 'Pending'}
                      </Badge>
                    </div>
                  </div>
                  <Text as="span" size="sm" className={styles.criteriaText}>
                    {item.text}
                  </Text>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {activeSession ? (
        <section className={styles.section}>
          <SectionHeader
            title="Phase progress"
            description="Seven-phase progress stays visible in the rail without implying backend state that has not been confirmed."
          />
          <ol aria-label="Left rail phase timeline" className={styles.timelineList}>
            {phaseItems.map((item) => (
              <li key={item.number}>
                <button
                  className={styles.timelineButton}
                  data-selected={item.selected}
                  data-state={item.state}
                  disabled={item.state !== 'complete'}
                  onClick={() => onPhaseSelect?.(item.number)}
                  type="button"
                >
                  <span aria-hidden="true" className={styles.timelineMarker}>
                    {item.number}
                  </span>
                  <div>
                    <Text as="p" size="xs" tone="muted">
                      Phase {item.number}
                    </Text>
                    <Text as="p" size="sm" weight="medium">
                      {item.label}
                    </Text>
                  </div>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ) : null}
      {activeSession ? (
        <section className={styles.section}>
          <SectionHeader
            title="Session health"
            description="Usage telemetry remains compact and secondary to the operator workflow."
          />
          {healthSummary ? (
            <div className={styles.healthPanel}>
              <div
                aria-label="Token budget utilization"
                aria-valuemax={100}
                aria-valuemin={0}
                aria-valuenow={healthSummary.percentUsed}
                className={styles.healthProgress}
                data-state={healthSummary.state}
                role="progressbar"
              >
                <div
                  className={styles.healthProgressFill}
                  style={{ width: `${healthSummary.percentUsed}%` }}
                />
              </div>
              <div className={styles.detailCluster}>
                <Text as="p" size="sm">
                  {healthSummary.apiCallsLabel}
                </Text>
                <Text as="p" size="sm">
                  {healthSummary.durationLabel}
                </Text>
                <Text as="p" size="sm">
                  {healthSummary.costLabel}
                </Text>
                <Text as="p" size="sm" weight="medium">
                  {formatHealthStateLabel(healthSummary.state)}
                </Text>
              </div>
            </div>
          ) : (
            <EmptyState
              title="Telemetry unavailable"
              description="Usage data is not available for this session yet, so the rail stays in a non-blocking fallback state."
            />
          )}
        </section>
      ) : null}
    </div>
  );
}

function resolveIntakeError(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to start the intake session.';
}

function resolveResumeError(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to resume the saved session.';
}

function resolveIntakeStatus({
  configured,
  hasStories,
  storiesError,
}: {
  configured: boolean;
  hasStories: boolean;
  storiesError: string | null;
}) {
  if (!configured || storiesError) {
    return { label: 'Manual fallback', state: 'fallback' as const };
  }

  if (!hasStories) {
    return { label: 'No active stories', state: 'fallback' as const };
  }

  return { label: 'Jira ready', state: 'ready' as const };
}

function buildIntakeMeta({
  canResume,
  configured,
  hasStories,
  selectedStoryKey,
}: {
  canResume: boolean;
  configured: boolean;
  hasStories: boolean;
  selectedStoryKey: string | null;
}) {
  const items: string[] = [];

  if (configured && hasStories) {
    items.push('Active Jira stories available');
  }

  if (selectedStoryKey) {
    items.push(`Selected ${selectedStoryKey}`);
  }

  if (canResume) {
    items.push('Checkpoint available');
  }

  return items;
}

function formatHealthStateLabel(state: string) {
  switch (state) {
    case 'warning':
      return 'Warning state';
    case 'blocked':
      return 'Blocked state';
    case 'healthy':
      return 'Healthy state';
    default:
      return 'Unavailable state';
  }
}
