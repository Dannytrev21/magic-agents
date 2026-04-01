import {
  startTransition,
  useDeferredValue,
  useId,
  useState,
  type ChangeEvent,
  type FormEvent,
} from 'react';
import { useQueryClient } from '@tanstack/react-query';
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
import { fetchJiraTicket } from '@/lib/api/client';
import type { JiraStory, StartNegotiationResponse } from '@/lib/api/types';
import { queryKeys } from '@/lib/query/queryKeys';
import { useSessionBootstrapQueries, useStartNegotiationMutation } from '@/lib/query/sessionHooks';

type SessionBootstrapProps = {
  onSessionStarted?: (session: StartNegotiationResponse, story: SessionIntakeStory) => void;
};

export function SessionBootstrap({ onSessionStarted }: SessionBootstrapProps) {
  const [draft, setDraft] = useState(defaultSessionIntakeDraft);
  const [mode, setMode] = useState<SessionIntakeMode>('jira');
  const [selectedStoryKey, setSelectedStoryKey] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isHydratingStory, setIsHydratingStory] = useState(false);
  const queryClient = useQueryClient();
  const deferredFilter = useDeferredValue(draft.storyFilter);
  const { configured, isError, isLoading, stories, storiesError } = useSessionBootstrapQueries();
  const startMutation = useStartNegotiationMutation();
  const tabGroupId = useId();
  const jiraTabId = `${tabGroupId}-jira`;
  const manualTabId = `${tabGroupId}-manual`;
  const jiraPanelId = `${tabGroupId}-jira-panel`;
  const manualPanelId = `${tabGroupId}-manual-panel`;

  const filteredStories = filterStories(stories, deferredFilter);
  const selectedStory = stories.find((story) => story.key === selectedStoryKey) ?? null;
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
  const isSubmitting = startMutation.isPending || isHydratingStory;

  function updateDraft(key: keyof SessionIntakeDraft) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setDraft((current) => ({ ...current, [key]: event.target.value }));
    };
  }

  function handleModeChange(nextMode: SessionIntakeMode) {
    startTransition(() => {
      setMode(nextMode);
      setSubmitError(null);
    });
  }

  function applyStory(story: JiraStory) {
    startTransition(() => {
      setSelectedStoryKey(story.key);
      setSubmitError(null);
    });
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

      onSessionStarted?.(session, story);
    } catch (error) {
      setSubmitError(resolveIntakeError(error));
    }
  }

  return (
    <div className={styles.stack}>
      <div className={styles.section}>
        <SectionHeader
          title="Story intake"
          description="Choose Jira intake or manual entry without leaving the left rail."
          action={
            <Badge tone={configured && !storiesError ? 'success' : 'warning'}>
              {configured && !storiesError ? 'Jira ready' : 'Manual fallback'}
            </Badge>
          }
        />
        <div className={styles.metaRow}>
          <Badge tone="neutral">Parallel bootstrap</Badge>
          <Badge tone="info">{stories.length} Jira stories</Badge>
          {selectedStory ? <Badge tone="success">Selection ready</Badge> : null}
        </div>
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
      <Divider />
      <form className={styles.form} onSubmit={handleSubmit}>
        {mode === 'jira' ? (
          <section
            aria-labelledby={jiraTabId}
            className={styles.section}
            id={jiraPanelId}
            role="tabpanel"
          >
            <SectionHeader
              title="Jira intake"
              description="Select an active Jira story and hydrate its acceptance criteria into the workspace session."
            />
            <div className={styles.field}>
              <Text as="label" htmlFor="story-filter" size="xs" tone="muted">
                Story search
              </Text>
              <input
                className={styles.input}
                id="story-filter"
                onChange={updateDraft('storyFilter')}
                placeholder="Filter by key or summary"
                type="search"
                value={draft.storyFilter}
              />
            </div>
            {isLoading ? <Text size="sm">Loading Jira intake</Text> : null}
            {isLoading ? <Skeleton aria-label="Loading Jira intake" /> : null}
            {isError ? (
              <EmptyState
                title="Jira intake is temporarily unavailable"
                description="Refresh the workspace or continue in manual entry while the bootstrap query recovers."
              />
            ) : null}
            {showConfigurationFallback ? (
              <EmptyState
                title="Jira configuration required"
                description="Jira credentials or access are unavailable. Manual entry remains available in this rail."
              />
            ) : null}
            {showEmptyState ? (
              <EmptyState
                title="No in-progress Jira stories"
                description="Choose manual entry to keep working until the backend exposes active tickets."
              />
            ) : null}
            {showNoMatches ? (
              <EmptyState
                title="No stories match this filter"
                description="Try a different key or summary term to narrow the Jira list."
              />
            ) : null}
            {!isLoading && !isError && !showConfigurationFallback && filteredStories.length ? (
              <div className={styles.list}>
                {filteredStories.map((story) => (
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
                      {selectedStoryKey === story.key ? <Badge tone="success">Selected</Badge> : null}
                    </div>
                    <Text as="span" size="sm">
                      {story.summary}
                    </Text>
                  </button>
                ))}
              </div>
            ) : null}
            {selectedStory ? (
              <div className={styles.selectionSummary}>
                <Text as="p" size="xs" tone="muted">
                  Selected story
                </Text>
                <div className={styles.storyMeta}>
                  <Mono>{selectedStory.key}</Mono>
                  <Badge tone="info">Ready to hydrate</Badge>
                </div>
                <Text as="p" size="sm">
                  {selectedStory.summary}
                </Text>
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
        <Button
          disabled={mode === 'jira' && !selectedStoryKey}
          loading={isSubmitting}
          type="submit"
        >
          {mode === 'jira' ? 'Start session from Jira' : 'Start session from manual story'}
        </Button>
        {startMutation.data?.session_id ? (
          <div className={styles.sessionSummary}>
            <Text as="p" size="sm" weight="medium">
              Active session created
            </Text>
            <Mono>{startMutation.data.session_id}</Mono>
          </div>
        ) : null}
      </form>
    </div>
  );
}

function resolveIntakeError(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Unable to start the intake session.';
}
