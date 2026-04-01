export type AcceptanceCriterion = {
  index: number;
  text: string;
  checked: boolean;
};

export type JiraStory = {
  key: string;
  summary: string;
  status: string;
};

export type JiraTicket = {
  key: string;
  summary: string;
  status: string;
  acceptanceCriteria: AcceptanceCriterion[];
};

export type PhaseResult = Record<string, unknown>;

export type PhaseResponse = {
  done: boolean;
  sessionId: string | null;
  phaseTitle: string;
  phaseNumber: number;
  totalPhases: number;
  results: PhaseResult[];
  questions: string[];
  revised: boolean;
};

export type CompileSpecResponse = {
  sessionId: string | null;
  specPath: string;
  specContent: string;
};

export type GenerateTestsResponse = {
  steps: Array<Record<string, unknown>>;
  testPath: string;
  testContent: string;
  verdicts: Array<Record<string, unknown>>;
  allPassed: boolean;
};

export type UpdateJiraResponse = {
  status: string;
  jiraKey: string;
  checkboxesTicked: number;
  evidencePosted: boolean;
};

export type StartSessionRequest = {
  jiraKey: string;
  jiraSummary: string;
  acceptanceCriteria: AcceptanceCriterion[];
  constitution?: Record<string, unknown>;
};

export type SessionResponseRequest = {
  sessionId?: string | null;
  input: string;
};

export interface WorkspaceApi {
  getJiraConfigured(): Promise<boolean>;
  getJiraStories(): Promise<JiraStory[]>;
  getJiraTicket(jiraKey: string): Promise<JiraTicket>;
  startSession(request: StartSessionRequest): Promise<PhaseResponse>;
  respondToSession(request: SessionResponseRequest): Promise<PhaseResponse>;
  compileSpec(sessionId?: string | null): Promise<CompileSpecResponse>;
  generateTests(sessionId?: string | null): Promise<GenerateTestsResponse>;
  updateJira(sessionId?: string | null): Promise<UpdateJiraResponse>;
}
