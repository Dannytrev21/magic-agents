export type AcceptanceCriterionInput = {
  checked: boolean;
  index: number;
  text: string;
};

export type JiraConfiguredResponse = {
  configured: boolean;
};

export type JiraStory = {
  key: string;
  summary: string;
  status?: string;
};

export type JiraStoriesResponse = {
  error?: string;
  stories: JiraStory[];
};

export type JiraTicketResponse = {
  acceptance_criteria: AcceptanceCriterionInput[];
  error?: string;
  key: string;
  status?: string;
  summary: string;
};

export type SkillDescriptor = {
  name?: string;
  path?: string;
  status?: string;
  [key: string]: unknown;
};

export type ScanStatusResponse = {
  project_root: string;
  scanned: boolean;
  summary?: string;
};

export type StartNegotiationRequest = {
  acceptance_criteria: AcceptanceCriterionInput[];
  jira_key: string;
  jira_summary: string;
};

export type AcceptanceCriterionClassification = {
  ac_index: number;
  actor?: string;
  type?: string;
  [key: string]: unknown;
};

export type PostconditionResult = {
  ac_index: number;
  constraints?: string[];
  content_type?: string;
  forbidden_fields?: string[];
  schema?: Record<string, unknown>;
  status?: number;
  [key: string]: unknown;
};

export type PreconditionResult = {
  category?: string;
  description?: string;
  formal?: string;
  id: string;
  [key: string]: unknown;
};

export type FailureModeResult = {
  body?: Record<string, unknown>;
  description?: string;
  id: string;
  status?: number;
  violates?: string;
  [key: string]: unknown;
};

export type InvariantResult = {
  id: string;
  rule?: string;
  source?: string;
  type?: string;
  [key: string]: unknown;
};

export type RoutingChecklistItem = {
  category?: string;
  detail?: string;
  status?: string;
  [key: string]: unknown;
};

export type RoutingResult = {
  refs?: string[];
  req_id?: string;
  skill?: string;
  [key: string]: unknown;
};

export type VerificationRoutingResult = {
  checklist?: RoutingChecklistItem[];
  questions?: string[];
  routing?: RoutingResult[];
  [key: string]: unknown;
};

export type EarsStatementResult = {
  id: string;
  pattern?: string;
  statement?: string;
  traces_to?: string;
  [key: string]: unknown;
};

export type TraceabilityMap = {
  [key: string]: unknown;
  ac_mappings?: Array<Record<string, unknown>>;
};

export type NegotiationLogEntry = {
  content: string;
  phase?: string;
  role: string;
  timestamp?: string;
  [key: string]: unknown;
};

export type SessionEvent = {
  detail: string;
  title: string;
  timestamp?: string;
  data?: Record<string, unknown>;
};

export type AcceptanceCriterionVerdict = {
  ac_checkbox?: number;
  ac_index?: number;
  ac_text?: string;
  passed?: boolean;
  status?: 'pass' | 'fail' | 'pending';
  [key: string]: unknown;
};

export type SessionUsageSummary = {
  api_calls?: number;
  budget_state?: 'healthy' | 'warning' | 'blocked';
  cost_usd?: number;
  max_api_calls?: number;
  max_tokens?: number;
  tokens_used?: number;
  wall_clock_seconds?: number;
};

export type StartNegotiationResponse = {
  acceptance_criteria?: AcceptanceCriterionInput[];
  approved?: boolean;
  classifications?: AcceptanceCriterionClassification[];
  current_phase?: string;
  done: boolean;
  ears_statements?: EarsStatementResult[];
  failure_modes?: FailureModeResult[];
  invariants?: InvariantResult[];
  jira_key: string;
  jira_summary?: string;
  log_entries?: number;
  negotiation_log?: NegotiationLogEntry[];
  phase_number: number;
  phase_title: string;
  postconditions?: PostconditionResult[];
  preconditions?: PreconditionResult[];
  questions?: string[];
  results?: unknown;
  revised?: boolean;
  resumed?: boolean;
  session_id: string;
  session_events?: SessionEvent[];
  summary?: Record<string, unknown>;
  total_phases: number;
  traceability_map?: TraceabilityMap;
  usage?: SessionUsageSummary | null;
  verdicts?: AcceptanceCriterionVerdict[];
  verification_routing?: VerificationRoutingResult;
};

export type SessionCheckpointSummary = {
  acceptance_criteria_count?: number;
  approved?: boolean;
  checkpoint_path?: string;
  current_phase?: string;
  jira_key?: string;
  jira_summary?: string;
  log_entries?: number;
  phase_number?: number;
  phase_title?: string;
  session_id?: string;
  usage?: SessionUsageSummary | null;
};

export type SessionInfoResponse = {
  has_checkpoint: boolean;
  session?: SessionCheckpointSummary;
};

export type PipelineEvent = {
  [key: string]: unknown;
  type: string;
};
