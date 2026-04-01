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

export type StartNegotiationResponse = {
  done: boolean;
  jira_key: string;
  phase_number: number;
  phase_title: string;
  revised?: boolean;
  session_id: string;
  total_phases: number;
};

export type SessionInfoResponse = {
  has_checkpoint: boolean;
  session?: {
    current_phase?: string;
    jira_key?: string;
    jira_summary?: string;
  };
};

export type PipelineEvent = {
  [key: string]: unknown;
  type: string;
};
