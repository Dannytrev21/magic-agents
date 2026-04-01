import type {
  CompileSpecResponse,
  GenerateTestsResponse,
  JiraStory,
  JiraTicket,
  PhaseResponse,
  StartSessionRequest,
  UpdateJiraResponse,
  WorkspaceApi,
} from "@/lib/api/contracts";
import { jsonRequest } from "@/lib/api/client";

type RawAcceptanceCriterion = {
  index: number;
  text: string;
  checked: boolean;
};

type RawPhaseResponse = {
  done: boolean;
  session_id?: string | null;
  phase_title?: string;
  phase_number?: number;
  total_phases?: number;
  results?: Array<Record<string, unknown>>;
  questions?: string[];
  revised?: boolean;
};

function normalizePhaseResponse(response: RawPhaseResponse): PhaseResponse {
  return {
    done: response.done,
    sessionId: response.session_id ?? null,
    phaseTitle: response.phase_title ?? "Operator workspace",
    phaseNumber: response.phase_number ?? 0,
    totalPhases: response.total_phases ?? 0,
    results: response.results ?? [],
    questions: response.questions ?? [],
    revised: response.revised ?? false,
  };
}

function normalizeAcceptanceCriteria(criteria: RawAcceptanceCriterion[] = []) {
  return criteria.map((criterion) => ({
    index: criterion.index,
    text: criterion.text,
    checked: criterion.checked,
  }));
}

export const workspaceApi: WorkspaceApi = {
  async getJiraConfigured() {
    const response = await jsonRequest<{ configured: boolean }>("/api/jira/configured");
    return response.configured;
  },

  async getJiraStories() {
    const response = await jsonRequest<{ stories: JiraStory[] }>("/api/jira/stories");
    return response.stories ?? [];
  },

  async getJiraTicket(jiraKey) {
    const response = await jsonRequest<{
      key: string;
      summary: string;
      status: string;
      acceptance_criteria?: RawAcceptanceCriterion[];
    }>(`/api/jira/ticket/${jiraKey}`);

    const ticket: JiraTicket = {
      key: response.key,
      summary: response.summary,
      status: response.status,
      acceptanceCriteria: normalizeAcceptanceCriteria(response.acceptance_criteria),
    };

    return ticket;
  },

  async startSession(request: StartSessionRequest) {
    const response = await jsonRequest<RawPhaseResponse>("/api/start", {
      method: "POST",
      body: {
        jira_key: request.jiraKey,
        jira_summary: request.jiraSummary,
        acceptance_criteria: request.acceptanceCriteria,
        constitution: request.constitution,
      },
    });

    return normalizePhaseResponse(response);
  },

  async respondToSession(request) {
    const response = await jsonRequest<RawPhaseResponse>("/api/respond", {
      method: "POST",
      body: {
        session_id: request.sessionId,
        input: request.input,
      },
    });

    return normalizePhaseResponse(response);
  },

  async compileSpec(sessionId) {
    const response = await jsonRequest<{
      session_id?: string | null;
      spec_path: string;
      spec_content: string;
    }>("/api/compile", {
      method: "POST",
      body: sessionId ? { session_id: sessionId } : undefined,
    });

    const compileResponse: CompileSpecResponse = {
      sessionId: response.session_id ?? null,
      specPath: response.spec_path,
      specContent: response.spec_content,
    };

    return compileResponse;
  },

  async generateTests(sessionId) {
    const response = await jsonRequest<{
      steps: Array<Record<string, unknown>>;
      test_path: string;
      test_content: string;
      verdicts: Array<Record<string, unknown>>;
      all_passed: boolean;
    }>("/api/generate-tests", {
      method: "POST",
      body: sessionId ? { session_id: sessionId } : undefined,
    });

    const testsResponse: GenerateTestsResponse = {
      steps: response.steps,
      testPath: response.test_path,
      testContent: response.test_content,
      verdicts: response.verdicts,
      allPassed: response.all_passed,
    };

    return testsResponse;
  },

  async updateJira(sessionId) {
    const response = await jsonRequest<{
      status: string;
      jira_key: string;
      checkboxes_ticked: number;
      evidence_posted: boolean;
    }>("/api/jira/update", {
      method: "POST",
      body: sessionId ? { session_id: sessionId } : undefined,
    });

    const jiraResponse: UpdateJiraResponse = {
      status: response.status,
      jiraKey: response.jira_key,
      checkboxesTicked: response.checkboxes_ticked,
      evidencePosted: response.evidence_posted,
    };

    return jiraResponse;
  },
};
