import type {
  AcceptanceCriterionInput,
  JiraStory,
  JiraTicketResponse,
  StartNegotiationRequest,
} from '@/lib/api/types';

export type SessionIntakeMode = 'jira' | 'manual';
export type SessionIntakeSource = SessionIntakeMode;

export type SessionIntakeStory = {
  acceptanceCriteria: AcceptanceCriterionInput[];
  key: string;
  source: SessionIntakeSource;
  status: string;
  summary: string;
};

export type ManualStoryDraft = {
  acceptanceCriteriaText: string;
  jiraKey: string;
  jiraSummary: string;
};

export type SessionIntakeDraft = ManualStoryDraft & {
  storyFilter: string;
};

export const defaultSessionIntakeDraft: SessionIntakeDraft = {
  acceptanceCriteriaText: [
    'Operator can review the new React shell without changing backend routes',
    'Story intake uses typed client helpers and query hooks',
    'Shared primitives expose visible focus and async loading states',
  ].join('\n'),
  jiraKey: 'DEMO-UI',
  jiraSummary: 'Operator workspace foundation',
  storyFilter: '',
};

export function parseAcceptanceCriteria(text: string): AcceptanceCriterionInput[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => ({
      checked: false,
      index,
      text: line,
    }));
}

export function normalizeManualStory(draft: ManualStoryDraft): SessionIntakeStory {
  return {
    acceptanceCriteria: parseAcceptanceCriteria(draft.acceptanceCriteriaText),
    key: draft.jiraKey.trim(),
    source: 'manual',
    status: 'Draft',
    summary: draft.jiraSummary.trim(),
  };
}

export function normalizeJiraTicket(ticket: JiraTicketResponse): SessionIntakeStory {
  return {
    acceptanceCriteria: ticket.acceptance_criteria,
    key: ticket.key,
    source: 'jira',
    status: ticket.status || 'In Progress',
    summary: ticket.summary,
  };
}

export function buildStartNegotiationPayload(
  story: SessionIntakeStory,
): StartNegotiationRequest {
  return {
    acceptance_criteria: story.acceptanceCriteria,
    jira_key: story.key,
    jira_summary: story.summary,
  };
}

export function filterStories(stories: JiraStory[], query: string): JiraStory[] {
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return stories;
  }

  return stories.filter((story) =>
    `${story.key} ${story.summary}`.toLowerCase().includes(normalizedQuery),
  );
}
