import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  approveEars,
  compileSpec,
  evaluatePhase,
  fetchPlan,
  fetchSpecDiff,
  fetchJiraConfigured,
  fetchJiraStories,
  fetchScanStatus,
  fetchSessionInfo,
  fetchSkills,
  generateTests,
  postJiraUpdate,
  respondToSession,
  runCodebaseScan,
  resumeSession,
  startNegotiation,
} from '@/lib/api/client';
import type { JiraStory, StartNegotiationRequest } from '@/lib/api/types';
import { queryKeys } from '@/lib/query/queryKeys';

export function useSessionBootstrapQueries() {
  const [configuredQuery, storiesQuery] = useQueries({
    queries: [
      {
        queryKey: queryKeys.jiraConfigured,
        queryFn: fetchJiraConfigured,
      },
      {
        queryKey: queryKeys.jiraStories,
        queryFn: fetchJiraStories,
      },
    ],
  });

  return {
    configured: configuredQuery.data?.configured ?? false,
    isError: configuredQuery.isError || storiesQuery.isError,
    isLoading: configuredQuery.isLoading || storiesQuery.isLoading,
    storiesError: storiesQuery.data?.error ?? null,
    stories: storiesQuery.data?.stories ?? [],
  };
}

export function useStorySessionQueries(stories: JiraStory[]) {
  const sessionQueries = useQueries({
    queries: stories.map((story) => ({
      enabled: Boolean(story.key),
      queryKey: queryKeys.sessionInfo(story.key),
      queryFn: () => fetchSessionInfo(story.key),
      staleTime: 15_000,
    })),
  });

  return stories.reduce<Record<string, (typeof sessionQueries)[number]['data']>>((acc, story, index) => {
    acc[story.key] = sessionQueries[index]?.data;
    return acc;
  }, {});
}

export function useInspectorQueries() {
  const [skillsQuery, scanStatusQuery] = useQueries({
    queries: [
      {
        queryKey: queryKeys.skills,
        queryFn: fetchSkills,
      },
      {
        queryKey: queryKeys.scanStatus,
        queryFn: fetchScanStatus,
      },
    ],
  });

  return {
    isLoading: skillsQuery.isLoading || scanStatusQuery.isLoading,
    scanStatus:
      scanStatusQuery.data ??
      ({
        project_root: '',
        scanned: false,
        status: undefined,
        summary: undefined,
      } as const),
    skills: skillsQuery.data ?? [],
  };
}

export function useStartNegotiationMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: StartNegotiationRequest) => startNegotiation(payload),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jiraStories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.scanStatus });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessionInfo(session.jira_key) });
    },
  });
}

export function useResumeSessionMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jiraKey: string) => resumeSession(jiraKey),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.scanStatus });
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessionInfo(session.jira_key) });
    },
  });
}

export function useInspectorActions() {
  const queryClient = useQueryClient();

  const scanMutation = useMutation({
    mutationFn: (projectRoot: string) => runCodebaseScan(projectRoot),
    onSuccess: (scanStatus) => {
      queryClient.setQueryData(queryKeys.scanStatus, scanStatus);
      void queryClient.invalidateQueries({ queryKey: queryKeys.scanStatus });
    },
  });

  const compileMutation = useMutation({
    mutationFn: () => compileSpec(),
  });

  const planningMutation = useMutation({
    mutationFn: () => fetchPlan(),
  });

  const critiqueMutation = useMutation({
    mutationFn: (phase: string) => evaluatePhase({ phase }),
  });

  const specDiffMutation = useMutation({
    mutationFn: () => fetchSpecDiff(),
  });

  return {
    compileMutation,
    critiqueMutation,
    planningMutation,
    scanMutation,
    specDiffMutation,
  };
}

export function useRespondMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: { input: string; session_id: string }) => respondToSession(payload),
    onSuccess: (session) => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessionInfo(session.jira_key) });
    },
  });
}

export function useVerificationQueries() {
  const jiraConfiguredQuery = useQuery({
    queryKey: queryKeys.jiraConfigured,
    queryFn: fetchJiraConfigured,
  });

  return {
    jiraConfigured: jiraConfiguredQuery.data?.configured ?? false,
    jiraConfiguredQuery,
  };
}

export function useVerificationActions(sessionId: string) {
  const approveMutation = useMutation({
    mutationFn: (approvedBy?: string) =>
      approveEars({
        approved_by: approvedBy ?? 'web_operator',
        session_id: sessionId,
      }),
  });

  const compileMutation = useMutation({
    mutationFn: () => compileSpec({ session_id: sessionId }),
  });

  const generateMutation = useMutation({
    mutationFn: () => generateTests({ session_id: sessionId }),
  });

  const jiraUpdateMutation = useMutation({
    mutationFn: () => postJiraUpdate({ session_id: sessionId }),
  });

  return {
    approveMutation,
    compileMutation,
    generateMutation,
    jiraUpdateMutation,
  };
}
