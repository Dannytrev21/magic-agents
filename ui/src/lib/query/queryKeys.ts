export const queryKeys = {
  jiraConfigured: ['jira-configured'] as const,
  jiraStories: ['jira-stories'] as const,
  jiraTicket: (jiraKey: string) => ['jira-ticket', jiraKey] as const,
  scanStatus: ['scan-status'] as const,
  sessionInfo: (jiraKey: string) => ['session-info', jiraKey] as const,
  skills: ['skills'] as const,
};
