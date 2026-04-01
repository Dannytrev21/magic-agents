import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import {
  fetchJiraConfigured,
  fetchJiraStories,
  fetchScanStatus,
  fetchSessionInfo,
  fetchSkills,
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
