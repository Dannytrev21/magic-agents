import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { WorkspaceApi } from "@/lib/api/contracts";
import { workspaceApi } from "@/lib/api/workspaceApi";

export const WORKSPACE_QUERY_KEYS = {
  jiraConfigured: () => ["workspace", "jira-configured"] as const,
  jiraStories: () => ["workspace", "jira-stories"] as const,
  jiraTicket: (jiraKey: string) => ["workspace", "jira-ticket", jiraKey] as const,
  sessionState: () => ["workspace", "session-state"] as const,
};

export function useJiraConfiguredQuery(api: WorkspaceApi = workspaceApi) {
  return useQuery({
    queryKey: WORKSPACE_QUERY_KEYS.jiraConfigured(),
    queryFn: () => api.getJiraConfigured(),
  });
}

export function useJiraStoriesQuery(api: WorkspaceApi = workspaceApi) {
  return useQuery({
    queryKey: WORKSPACE_QUERY_KEYS.jiraStories(),
    queryFn: () => api.getJiraStories(),
  });
}

export function useStartSessionMutation(api: WorkspaceApi = workspaceApi) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.startSession,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: WORKSPACE_QUERY_KEYS.jiraStories() }),
        queryClient.invalidateQueries({ queryKey: WORKSPACE_QUERY_KEYS.sessionState() }),
      ]);
    },
  });
}
