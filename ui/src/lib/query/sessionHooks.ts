import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query';
import {
  fetchJiraConfigured,
  fetchJiraStories,
  fetchScanStatus,
  fetchSkills,
  startNegotiation,
} from '@/lib/api/client';
import type { StartNegotiationRequest } from '@/lib/api/types';
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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.jiraStories });
      void queryClient.invalidateQueries({ queryKey: queryKeys.scanStatus });
    },
  });
}
