import type {
  CompileSpecResponse,
  EarsApprovalResponse,
  GenerateTestsResponse,
  JiraUpdateResponse,
  PipelineEvent,
  StartNegotiationResponse,
} from '@/lib/api/types';

export type VerificationWorkspaceState = {
  approval: EarsApprovalResponse | null;
  approvalError: string | null;
  artifactView: 'spec' | 'tests';
  compileError: string | null;
  compileResult: CompileSpecResponse | null;
  generateError: string | null;
  generateResult: GenerateTestsResponse | null;
  jiraUpdateError: string | null;
  jiraUpdateResult: JiraUpdateResponse | null;
  pipelineError: string | null;
  pipelineEvents: PipelineEvent[];
  pipelineRunning: boolean;
  pipelineSummary: PipelineEvent | null;
};

export function buildInitialVerificationState(
  session: StartNegotiationResponse | null,
): VerificationWorkspaceState {
  return {
    approval: resolveSessionApproval(session),
    approvalError: null,
    artifactView: 'spec',
    compileError: null,
    compileResult: null,
    generateError: null,
    generateResult: null,
    jiraUpdateError: null,
    jiraUpdateResult: null,
    pipelineError: null,
    pipelineEvents: [],
    pipelineRunning: false,
    pipelineSummary: null,
  };
}

function resolveSessionApproval(session: StartNegotiationResponse | null): EarsApprovalResponse | null {
  if (!session?.approved) {
    return null;
  }

  return {
    approved: true,
    approved_at: session.approved_at ?? '',
    approved_by: session.approved_by ?? 'web_operator',
  };
}
