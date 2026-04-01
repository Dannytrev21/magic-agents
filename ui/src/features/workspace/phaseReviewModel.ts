import type {
  AcceptanceCriterionClassification,
  EarsStatementResult,
  FailureModeResult,
  InvariantResult,
  NegotiationLogEntry,
  PostconditionResult,
  PreconditionResult,
  RoutingChecklistItem,
  RoutingResult,
  SessionEvent,
  StartNegotiationResponse,
  VerificationRoutingResult,
} from '@/lib/api/types';
import { negotiationPhases } from '@/features/workspace/workspaceModel';

export type WorkspaceTranscriptRole = 'model' | 'operator' | 'system';

export type WorkspaceTranscriptEntry = {
  content: string;
  id: string;
  label: string;
  phaseNumber: number | null;
  role: WorkspaceTranscriptRole;
  timestamp?: string;
};

export type PhaseReviewItem = {
  body: string;
  extra?: Record<string, unknown>;
  id: string;
  label: string;
  meta?: string;
  title: string;
};

export type PhaseReviewGroup = {
  items: PhaseReviewItem[];
  title: string;
};

export type PhaseReview = {
  description: string;
  groups: PhaseReviewGroup[];
  phaseNumber: number;
  phaseTitle: string;
  questions: string[];
  rawPayload: unknown;
  state: 'active' | 'complete' | 'pending';
  summary: string;
  summaryLabel: string;
};

export function buildPhaseReview(
  session: StartNegotiationResponse,
  phaseNumber: number,
): PhaseReview {
  const phaseTitle = negotiationPhases[phaseNumber - 1] ?? session.phase_title;
  const state = getPhaseState(phaseNumber, session.phase_number);
  const questions = resolvePhaseQuestions(session, phaseNumber);

  switch (phaseNumber) {
    case 1:
      return {
        description: 'Actors, requirement types, and interfaces are explicit before contract design.',
        groups: [
          {
            title: 'Interface coverage',
            items: formatClassifications(session.classifications ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.classifications ?? [],
        state,
        summary:
          session.classifications?.length
            ? `${session.classifications.length} classification${session.classifications.length === 1 ? '' : 's'} map the operator-facing interface.`
            : 'Classification output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    case 2:
      return {
        description: 'Happy-path contracts stay readable before the dense response schema details.',
        groups: [
          {
            title: 'Response contracts',
            items: formatPostconditions(session.postconditions ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.postconditions ?? [],
        state,
        summary:
          session.postconditions?.length
            ? `${session.postconditions.length} happy-path contract${session.postconditions.length === 1 ? '' : 's'} define the API response shape.`
            : 'Contract output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    case 3:
      return {
        description: 'Required conditions stay concise while formal expressions remain secondary for inspection.',
        groups: [
          {
            title: 'Required conditions',
            items: formatPreconditions(session.preconditions ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.preconditions ?? [],
        state,
        summary:
          session.preconditions?.length
            ? `${session.preconditions.length} precondition${session.preconditions.length === 1 ? '' : 's'} protect the approved contract.`
            : 'Precondition output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    case 4:
      return {
        description: 'Failure paths lead with the operator-visible response before raw bodies and supporting fields.',
        groups: [
          {
            title: 'Failure responses',
            items: formatFailureModes(session.failure_modes ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.failure_modes ?? [],
        state,
        summary:
          session.failure_modes?.length
            ? `Failure responses are mapped to explicit broken-path decisions across ${session.failure_modes.length} scenario${session.failure_modes.length === 1 ? '' : 's'}.`
            : 'Failure-mode output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    case 5:
      return {
        description: 'Always-on rules stay legible without forcing the operator to inspect every derivation first.',
        groups: [
          {
            title: 'Always-on rules',
            items: formatInvariants(session.invariants ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.invariants ?? [],
        state,
        summary:
          session.invariants?.length
            ? `${session.invariants.length} invariant${session.invariants.length === 1 ? '' : 's'} lock the non-negotiable system behavior.`
            : 'Invariant output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    case 6: {
      const routing = session.verification_routing ?? ({} as VerificationRoutingResult);
      return {
        description: 'Completeness signals stay separate from proof-routing decisions so the operator can scan gaps quickly.',
        groups: [
          {
            title: 'Completeness checklist',
            items: formatChecklist(routing.checklist ?? []),
          },
          {
            title: 'Verification routes',
            items: formatRoutes(routing.routing ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: routing,
        state,
        summary:
          routing.routing?.length
            ? `${routing.routing.length} routing decision${routing.routing.length === 1 ? '' : 's'} connect the current scope to proof artifacts.`
            : 'Routing output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
    }
    case 7:
    default:
      return {
        description: 'Formalized EARS requirements stay summary-first while every trace ref remains visible for review.',
        groups: [
          {
            title: 'Formalized requirements',
            items: formatEarsStatements(session.ears_statements ?? []),
          },
        ],
        phaseNumber,
        phaseTitle,
        questions,
        rawPayload: session.ears_statements ?? [],
        state,
        summary:
          session.ears_statements?.length
            ? `${session.ears_statements.length} EARS statement${session.ears_statements.length === 1 ? '' : 's'} formalize the negotiated contract for approval.`
            : 'EARS output is waiting on backend confirmation.',
        summaryLabel: 'Primary decision',
      };
  }
}

export function buildTranscriptEntries(
  session: StartNegotiationResponse,
  phaseNumber: number,
): WorkspaceTranscriptEntry[] {
  const systemEntries = (session.session_events ?? []).map((entry, index) =>
    buildSystemTranscriptEntry(entry, index),
  );
  const logEntries = (session.negotiation_log ?? []).map((entry, index) =>
    buildNegotiationTranscriptEntry(entry, index),
  );

  return [...systemEntries, ...logEntries]
    .filter((entry) => entry.phaseNumber === null || entry.phaseNumber === phaseNumber)
    .sort((left, right) => {
      if (left.timestamp && right.timestamp) {
        return left.timestamp.localeCompare(right.timestamp);
      }

      return left.id.localeCompare(right.id);
    });
}

export function parsePhaseKeyToUiPhaseNumber(phaseKey: string | undefined): number | null {
  if (!phaseKey?.startsWith('phase_')) {
    return null;
  }

  const rawValue = Number(phaseKey.split('_', 2)[1]);
  if (Number.isNaN(rawValue)) {
    return null;
  }

  return Math.max(1, Math.min(negotiationPhases.length, rawValue + 1));
}

function getPhaseState(
  phaseNumber: number,
  activePhaseNumber: number,
): PhaseReview['state'] {
  if (phaseNumber < activePhaseNumber) {
    return 'complete';
  }

  if (phaseNumber === activePhaseNumber) {
    return 'active';
  }

  return 'pending';
}

function resolvePhaseQuestions(
  session: StartNegotiationResponse,
  phaseNumber: number,
): string[] {
  if (phaseNumber === session.phase_number && session.questions?.length) {
    return session.questions;
  }

  if (phaseNumber === 6 && session.verification_routing?.questions?.length) {
    return session.verification_routing.questions;
  }

  return [];
}

function buildNegotiationTranscriptEntry(
  entry: NegotiationLogEntry,
  index: number,
): WorkspaceTranscriptEntry {
  return {
    content: entry.content,
    id: `log-${index}`,
    label: entry.role === 'human' ? 'Operator' : entry.role === 'ai' ? 'Model' : 'System',
    phaseNumber: parsePhaseKeyToUiPhaseNumber(entry.phase),
    role: entry.role === 'human' ? 'operator' : entry.role === 'ai' ? 'model' : 'system',
    timestamp: entry.timestamp,
  };
}

function buildSystemTranscriptEntry(
  entry: SessionEvent,
  index: number,
): WorkspaceTranscriptEntry {
  return {
    content: entry.detail,
    id: `event-${index}`,
    label: 'System',
    phaseNumber: null,
    role: 'system',
    timestamp: entry.timestamp,
  };
}

function formatClassifications(
  items: AcceptanceCriterionClassification[],
): PhaseReviewItem[] {
  return items.map((item) => {
    const interfaceValue = asRecord(item.interface);
    const method = textValue(interfaceValue.method);
    const path = textValue(interfaceValue.path);

    return {
      body: method && path ? `${method} ${path}` : 'Non-endpoint classification',
      extra: omitKeys(item, ['ac_index', 'actor', 'interface', 'type']),
      id: `classification-${item.ac_index}`,
      label: `AC[${(item.ac_index ?? 0) + 1}]`,
      meta: item.actor,
      title: item.type ?? 'Unclassified',
    };
  });
}

function formatPostconditions(items: PostconditionResult[]): PhaseReviewItem[] {
  return items.map((item, index) => ({
    body: `${item.content_type ?? 'Unknown content type'} · ${item.constraints?.length ?? 0} constraint${item.constraints?.length === 1 ? '' : 's'}`,
    extra: omitKeys(item, ['ac_index', 'constraints', 'content_type', 'forbidden_fields', 'schema', 'status']),
    id: `postcondition-${index}`,
    label: `AC[${(item.ac_index ?? 0) + 1}]`,
    meta: item.forbidden_fields?.length ? `Forbidden: ${item.forbidden_fields.join(', ')}` : undefined,
    title: `HTTP ${item.status ?? '200'}`,
  }));
}

function formatPreconditions(items: PreconditionResult[]): PhaseReviewItem[] {
  return items.map((item) => ({
    body: item.description ?? 'No description provided.',
    extra: omitKeys(item, ['category', 'description', 'formal', 'id']),
    id: item.id,
    label: item.category ?? 'precondition',
    meta: item.formal,
    title: item.id,
  }));
}

function formatFailureModes(items: FailureModeResult[]): PhaseReviewItem[] {
  return items.map((item) => ({
    body: item.description ?? 'No failure description provided.',
    extra: omitKeys(item, ['body', 'description', 'id', 'status', 'violates']),
    id: item.id,
    label: `HTTP ${item.status ?? 'n/a'}`,
    meta: item.violates ? `Violates ${item.violates}` : undefined,
    title: item.id,
  }));
}

function formatInvariants(items: InvariantResult[]): PhaseReviewItem[] {
  return items.map((item) => ({
    body: item.rule ?? 'No invariant rule provided.',
    extra: omitKeys(item, ['id', 'rule', 'source', 'type']),
    id: item.id,
    label: item.type ?? 'invariant',
    meta: item.source,
    title: item.id,
  }));
}

function formatChecklist(items: RoutingChecklistItem[]): PhaseReviewItem[] {
  return items.map((item, index) => ({
    body: item.detail ?? 'No detail provided.',
    extra: omitKeys(item, ['category', 'detail', 'status']),
    id: `checklist-${index}`,
    label: item.status ?? 'unreviewed',
    title: item.category ?? `Checklist ${index + 1}`,
  }));
}

function formatRoutes(items: RoutingResult[]): PhaseReviewItem[] {
  return items.map((item, index) => ({
    body: item.refs?.length ? item.refs.join(', ') : 'No refs provided.',
    extra: omitKeys(item, ['refs', 'req_id', 'skill']),
    id: item.req_id ?? `route-${index}`,
    label: item.skill ?? 'unrouted',
    meta: item.refs?.length ? `${item.refs.length} refs` : undefined,
    title: item.req_id ?? `Route ${index + 1}`,
  }));
}

function formatEarsStatements(items: EarsStatementResult[]): PhaseReviewItem[] {
  return items.map((item) => ({
    body: item.statement ?? 'No EARS statement provided.',
    extra: omitKeys(item, ['id', 'pattern', 'statement', 'traces_to']),
    id: item.id,
    label: item.pattern ?? 'EARS',
    meta: item.traces_to,
    title: item.id,
  }));
}

function asRecord(value: unknown): Record<string, unknown> {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }

  return {};
}

function textValue(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

function omitKeys(
  value: Record<string, unknown>,
  keys: string[],
): Record<string, unknown> | undefined {
  const next = Object.fromEntries(
    Object.entries(value).filter(([key]) => !keys.includes(key)),
  );

  return Object.keys(next).length ? next : undefined;
}
