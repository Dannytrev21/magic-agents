import type {
  AcceptanceCriterionClassification,
  AcceptanceCriterionVerdict,
  SessionCheckpointSummary,
  SessionUsageSummary,
  StartNegotiationResponse,
} from '@/lib/api/types';
import type { SessionIntakeStory } from '@/features/session/sessionIntakeModel';
import { negotiationPhases } from '@/features/workspace/workspaceModel';

export type StoryCheckpointState = 'new' | 'resumable' | 'complete';
export type AcceptanceCriterionRailState = 'passed' | 'failed' | 'pending';
export type SessionPhaseRailState = 'complete' | 'active' | 'pending' | 'failed';
export type SessionHealthState = 'healthy' | 'warning' | 'blocked' | 'unavailable';

export type AcceptanceCriterionRailItem = {
  classification: string | null;
  fullText: string;
  index: number;
  selected: boolean;
  state: AcceptanceCriterionRailState;
  text: string;
};

export type SessionPhaseRailItem = {
  label: string;
  number: number;
  selected: boolean;
  state: SessionPhaseRailState;
};

export type SessionHealthSummary = {
  apiCallsLabel: string;
  costLabel: string;
  durationLabel: string;
  percentUsed: number;
  state: SessionHealthState;
};

export function getStoryCheckpointState(sessionInfo?: SessionCheckpointSummary): StoryCheckpointState {
  if (!sessionInfo) {
    return 'new';
  }

  if (sessionInfo.approved) {
    return 'complete';
  }

  return 'resumable';
}

export function normalizeResumedStory(session: StartNegotiationResponse): SessionIntakeStory {
  return {
    acceptanceCriteria: session.acceptance_criteria ?? [],
    key: session.jira_key,
    source: 'jira',
    status: session.resumed ? 'Checkpointed' : 'In Progress',
    summary: session.jira_summary ?? session.jira_key,
  };
}

export function buildAcceptanceCriteriaRailItems(
  activeSession: StartNegotiationResponse | null,
  activeStory: SessionIntakeStory | null,
  selectedIndex: number | null,
): AcceptanceCriterionRailItem[] {
  const acceptanceCriteria = activeSession?.acceptance_criteria ?? activeStory?.acceptanceCriteria ?? [];

  return acceptanceCriteria.map((criterion) => ({
    classification: findClassificationLabel(activeSession?.classifications, criterion.index),
    fullText: criterion.text,
    index: criterion.index,
    selected: selectedIndex === criterion.index,
    state: findCriterionState(activeSession?.verdicts, criterion.index),
    text: criterion.text,
  }));
}

export function buildSessionPhaseRailItems(
  activeSession: StartNegotiationResponse | null,
  selectedPhaseNumber: number | null,
): SessionPhaseRailItem[] {
  const activePhase = activeSession?.phase_number ?? 0;

  return negotiationPhases.map((label, index) => {
    const number = index + 1;
    let state: SessionPhaseRailState = 'pending';

    if (number < activePhase) {
      state = 'complete';
    } else if (number === activePhase) {
      state = 'active';
    }

    return {
      label,
      number,
      selected: selectedPhaseNumber === number,
      state,
    };
  });
}

export function buildSessionHealthSummary(
  usage: SessionUsageSummary | null | undefined,
): SessionHealthSummary | null {
  if (!usage) {
    return null;
  }

  const percentUsed =
    usage.max_tokens && usage.max_tokens > 0 && usage.tokens_used !== undefined
      ? Math.round((usage.tokens_used / usage.max_tokens) * 100)
      : 0;

  return {
    apiCallsLabel:
      usage.api_calls !== undefined
        ? `${usage.api_calls}${usage.max_api_calls ? ` / ${usage.max_api_calls}` : ''} calls`
        : '\u2014',
    costLabel:
      usage.cost_usd !== undefined ? `$${usage.cost_usd.toFixed(2)}` : '\u2014',
    durationLabel:
      usage.wall_clock_seconds !== undefined ? formatDuration(usage.wall_clock_seconds) : '\u2014',
    percentUsed,
    state: usage.budget_state ?? 'healthy',
  };
}

function findClassificationLabel(
  classifications: AcceptanceCriterionClassification[] | undefined,
  index: number,
) {
  const match = classifications?.find((classification) => classification.ac_index === index);
  return match?.type ?? null;
}

function findCriterionState(
  verdicts: AcceptanceCriterionVerdict[] | undefined,
  index: number,
): AcceptanceCriterionRailState {
  const match = verdicts?.find(
    (verdict) => verdict.ac_checkbox === index || verdict.ac_index === index,
  );

  if (!match) {
    return 'pending';
  }

  if (match.status) {
    return match.status === 'pass' ? 'passed' : match.status === 'fail' ? 'failed' : 'pending';
  }

  if (match.passed === true) {
    return 'passed';
  }

  if (match.passed === false) {
    return 'failed';
  }

  return 'pending';
}

function formatDuration(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}m ${seconds.toString().padStart(2, '0')}s`;
}
