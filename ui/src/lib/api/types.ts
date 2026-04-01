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
  jira_key: string;
  jira_summary?: string;
  log_entries?: number;
  phase_number: number;
  phase_title: string;
  revised?: boolean;
  resumed?: boolean;
  session_id: string;
  total_phases: number;
  usage?: SessionUsageSummary | null;
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
  [key: string]: unknown;
  type: string;
};
