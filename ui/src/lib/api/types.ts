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
  status?: string;
  summary?: Record<string, unknown> | string;
};

export type ScanRunResponse = ScanStatusResponse;

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
  ac_mappings?: TraceabilityMapping[];
};

export type TraceabilityVerificationRef = {
  description?: string;
  ref: string;
  verification_type?: string;
  [key: string]: unknown;
};

export type TraceabilityMapping = {
  ac_checkbox?: number;
  ac_text?: string;
  pass_condition?: string;
  required_verifications?: TraceabilityVerificationRef[];
  [key: string]: unknown;
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
  evidence?: Array<{
    description?: string;
    details?: string;
    passed?: boolean;
    ref?: string;
    verification_type?: string;
    [key: string]: unknown;
  }>;
  pass_condition?: string;
  passed?: boolean;
  status?: 'pass' | 'fail' | 'pending';
  summary?: string;
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
  approved_at?: string;
  approved_by?: string;
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

export type PlanningGroup = {
  ac_indices: number[];
  endpoint: string;
  methods: string[];
};

export type PlanResponse = {
  ac_groups: PlanningGroup[];
  cross_ac_dependencies?: string[];
  estimated_complexity?: string;
};

export type PhaseCritiqueResponse = {
  has_issues: boolean;
  issues: string[];
  suggestions: string[];
};

export type SpecDiffResponse = {
  diff: string | null;
  has_old_spec: boolean;
  jira_key: string;
};

export type CompiledSpecVerification = {
  output?: string;
  refs?: string[];
  skill?: string;
  [key: string]: unknown;
};

export type CompiledSpecContract = {
  failures?: FailureModeResult[];
  interface?: {
    auth?: string;
    method?: string;
    path?: string;
    [key: string]: unknown;
  };
  invariants?: InvariantResult[];
  preconditions?: PreconditionResult[];
  success?: {
    content_type?: string;
    required?: string[];
    schema?: Record<string, unknown>;
    status?: number;
    [key: string]: unknown;
  };
  [key: string]: unknown;
};

export type CompiledSpecRequirement = {
  ac_checkbox?: number;
  ac_text?: string;
  contract?: CompiledSpecContract;
  id: string;
  title?: string;
  type?: string;
  verification?: CompiledSpecVerification[];
  [key: string]: unknown;
};

export type CompileSpecResponse = {
  requirements?: CompiledSpecRequirement[];
  spec_content: string;
  spec_path: string;
  traceability?: TraceabilityMap;
};

export type EarsApprovalResponse = {
  approved: boolean;
  approved_at: string;
  approved_by: string;
};

export type GenerateTestsStep = {
  all_passed?: boolean;
  message?: string;
  passed?: number;
  path?: string;
  status?: string;
  step: string;
  total?: number;
  [key: string]: unknown;
};

export type GenerateTestsResponse = {
  all_passed?: boolean;
  error?: string;
  steps: GenerateTestsStep[];
  test_content?: string;
  test_path?: string;
  verdicts?: AcceptanceCriterionVerdict[];
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
  all_passed?: boolean;
  message?: string;
  requirements?: CompiledSpecRequirement[];
  session_id?: string;
  spec_content?: string;
  spec_path?: string;
  status?: string;
  step?: string;
  success?: boolean;
  test_content?: string;
  test_path?: string;
  traceability?: TraceabilityMap;
  verdicts?: AcceptanceCriterionVerdict[];
  [key: string]: unknown;
  type: string;
};

export type JiraUpdateResponse = {
  all_passed?: boolean;
  checkboxes_ticked?: number | number[];
  comment_posted?: boolean;
  evidence_posted?: boolean;
  jira_key?: string;
  status?: string;
  [key: string]: unknown;
};
