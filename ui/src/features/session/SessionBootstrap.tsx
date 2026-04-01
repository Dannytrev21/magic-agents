import { useDeferredValue, useState, type ChangeEvent, type FormEvent } from 'react';
import styles from '@/features/session/session-bootstrap.module.css';
import { Badge } from '@/components/primitives/Badge';
import { Button } from '@/components/primitives/Button';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Skeleton } from '@/components/primitives/Skeleton';
import { Text } from '@/components/primitives/Text';
import type { JiraStory, StartNegotiationRequest, StartNegotiationResponse } from '@/lib/api/types';
import { useSessionBootstrapQueries, useStartNegotiationMutation } from '@/lib/query/sessionHooks';

type SessionBootstrapProps = {
  onSessionStarted?: (session: StartNegotiationResponse) => void;
};

type IntakeDraft = {
  jiraKey: string;
  jiraSummary: string;
  acceptanceCriteria: string;
  storyFilter: string;
};

const defaultDraft: IntakeDraft = {
  jiraKey: 'DEMO-UI',
  jiraSummary: 'Operator workspace foundation',
  acceptanceCriteria: [
    'Operator can review the new React shell without changing backend routes',
    'Story intake uses typed client helpers and query hooks',
    'Shared primitives expose visible focus and async loading states',
  ].join('\n'),
  storyFilter: '',
};

function criteriaFromText(text: string) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => ({
      index,
      text: line,
      checked: false,
    }));
}

function buildStartPayload(draft: IntakeDraft): StartNegotiationRequest {
  return {
    jira_key: draft.jiraKey,
    jira_summary: draft.jiraSummary,
    acceptance_criteria: criteriaFromText(draft.acceptanceCriteria),
  };
}

export function SessionBootstrap({ onSessionStarted }: SessionBootstrapProps) {
  const [draft, setDraft] = useState(defaultDraft);
  const deferredFilter = useDeferredValue(draft.storyFilter);
  const { configured, isError, isLoading, stories } = useSessionBootstrapQueries();
  const startMutation = useStartNegotiationMutation();

  const filteredStories = stories.filter((story) => {
    if (!deferredFilter.trim()) {
      return true;
    }

    const query = deferredFilter.toLowerCase();
    return `${story.key} ${story.summary}`.toLowerCase().includes(query);
  });

  function updateDraft(key: keyof IntakeDraft) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      setDraft((current) => ({ ...current, [key]: event.target.value }));
    };
  }

  function applyStory(story: JiraStory) {
    setDraft((current) => ({
      ...current,
      jiraKey: story.key,
      jiraSummary: story.summary,
    }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    startMutation.mutate(buildStartPayload(draft), {
      onSuccess: (session) => {
        onSessionStarted?.(session);
      },
    });
  }

  return (
    <div className={styles.stack}>
      <div className={styles.section}>
        <SectionHeader
          title="Story intake"
          description="Bootstrap the workspace with Jira availability and a manual session start form."
          action={<Badge tone={configured ? 'success' : 'warning'}>{configured ? 'Jira ready' : 'Manual mode'}</Badge>}
        />
        <div className={styles.metaRow}>
          <Badge tone="neutral">Parallel bootstrap</Badge>
          <Badge tone="info">{stories.length} stories visible</Badge>
        </div>
      </div>
      <Divider />
      <div className={styles.section}>
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
        {isLoading ? <Text size="sm">Loading workspace context</Text> : null}
        {isLoading ? <Skeleton aria-label="Loading panel" /> : null}
        {isError ? (
          <Text size="sm" tone="muted">
            Workspace bootstrap failed
          </Text>
        ) : null}
        {!isLoading && !filteredStories.length ? (
          <EmptyState
            title="No active Jira stories"
            description="Keep working from manual intake until the backend exposes in-progress tickets."
          />
        ) : null}
        {!isLoading && filteredStories.length ? (
          <div className={styles.list}>
            {filteredStories.map((story) => (
              <button className={styles.storyButton} key={story.key} onClick={() => applyStory(story)} type="button">
                <div className={styles.storyKey}>
                  <Mono>{story.key}</Mono>
                  <Badge tone="neutral">intake</Badge>
                </div>
                <Text as="span" size="sm">
                  {story.summary}
                </Text>
              </button>
            ))}
          </div>
        ) : null}
      </div>
      <Divider />
      <form className={styles.form} onSubmit={handleSubmit}>
        <SectionHeader
          title="Manual session start"
          description="Keep the working surface usable even when Jira or checkpoints are unavailable."
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
            onChange={updateDraft('acceptanceCriteria')}
            required
            value={draft.acceptanceCriteria}
          />
        </div>
        <Button loading={startMutation.isPending} type="submit">
          Start negotiation session
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
