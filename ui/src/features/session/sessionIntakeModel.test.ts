import { describe, expect, it } from 'vitest';
import {
  buildStartNegotiationPayload,
  filterStories,
  normalizeJiraTicket,
  normalizeManualStory,
} from '@/features/session/sessionIntakeModel';

describe('session intake model', () => {
  it('normalizes manual and Jira intake into the same shared story shape', () => {
    const manualStory = normalizeManualStory({
      jiraKey: 'OPS-44',
      jiraSummary: 'Capture manual intake',
      acceptanceCriteriaText: 'Operator can enter a story\nOperator can keep working without Jira',
    });
    const jiraStory = normalizeJiraTicket({
      key: 'MAG-88',
      summary: 'Hydrate Jira intake',
      status: 'In Progress',
      acceptance_criteria: [{ checked: false, index: 0, text: 'Read Jira acceptance criteria' }],
    });

    expect(manualStory).toEqual({
      acceptanceCriteria: [
        { checked: false, index: 0, text: 'Operator can enter a story' },
        { checked: false, index: 1, text: 'Operator can keep working without Jira' },
      ],
      key: 'OPS-44',
      source: 'manual',
      status: 'Draft',
      summary: 'Capture manual intake',
    });
    expect(jiraStory).toEqual({
      acceptanceCriteria: [{ checked: false, index: 0, text: 'Read Jira acceptance criteria' }],
      key: 'MAG-88',
      source: 'jira',
      status: 'In Progress',
      summary: 'Hydrate Jira intake',
    });
  });

  it('builds the start payload from the shared story shape', () => {
    const story = normalizeManualStory({
      jiraKey: 'OPS-44',
      jiraSummary: 'Capture manual intake',
      acceptanceCriteriaText: 'Operator can enter a story',
    });

    expect(buildStartNegotiationPayload(story)).toEqual({
      acceptance_criteria: [{ checked: false, index: 0, text: 'Operator can enter a story' }],
      jira_key: 'OPS-44',
      jira_summary: 'Capture manual intake',
    });
  });

  it('filters Jira stories by key and summary with whitespace-safe queries', () => {
    const stories = [
      { key: 'MAG-10', summary: 'Port workspace shell' },
      { key: 'MAG-11', summary: 'Add session checkpoint rail' },
    ];

    expect(filterStories(stories, '  checkpoint ')).toEqual([
      { key: 'MAG-11', summary: 'Add session checkpoint rail' },
    ]);
    expect(filterStories(stories, '')).toEqual(stories);
  });
});
