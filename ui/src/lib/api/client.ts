import type {
  JiraConfiguredResponse,
  JiraStoriesResponse,
  JiraTicketResponse,
  PipelineEvent,
  ScanStatusResponse,
  SessionInfoResponse,
  SkillDescriptor,
  StartNegotiationRequest,
  StartNegotiationResponse,
} from '@/lib/api/types';
import { parseSseChunk } from '@/lib/api/sse';

class ApiError extends Error {
  public constructor(message: string, public readonly status: number) {
    super(message);
    this.name = 'ApiError';
  }
}

async function requestJson<T>(input: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(input, {
    credentials: 'same-origin',
    ...init,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new ApiError(message || `Request failed for ${input}`, response.status);
  }

  return (await response.json()) as T;
}

function jsonRequest<TBody>(body?: TBody): RequestInit {
  if (!body) {
    return {};
  }

  return {
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
    body: JSON.stringify(body),
  };
}

export function fetchJiraConfigured() {
  return requestJson<JiraConfiguredResponse>('/api/jira/configured');
}

export function fetchJiraStories() {
  return requestJson<JiraStoriesResponse>('/api/jira/stories');
}

export function fetchJiraTicket(jiraKey: string) {
  return requestJson<JiraTicketResponse>(`/api/jira/ticket/${jiraKey}`);
}

export function fetchSkills() {
  return requestJson<SkillDescriptor[]>('/api/skills');
}

export function fetchScanStatus() {
  return requestJson<ScanStatusResponse>('/api/scan/status');
}

export function fetchSessionInfo(jiraKey: string) {
  return requestJson<SessionInfoResponse>(`/api/session/${jiraKey}`);
}

export function startNegotiation(payload: StartNegotiationRequest) {
  return requestJson<StartNegotiationResponse>('/api/start', jsonRequest(payload));
}

export async function streamPipelineEvents(sessionId: string, onEvent: (event: PipelineEvent) => void) {
  const response = await fetch('/api/pipeline/stream', jsonRequest({ session_id: sessionId }));

  if (!response.ok) {
    throw new ApiError(await response.text(), response.status);
  }

  if (!response.body) {
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      for (const event of parseSseChunk(part)) {
        onEvent(event);
      }
    }
  }

  if (buffer.trim()) {
    for (const event of parseSseChunk(buffer)) {
      onEvent(event);
    }
  }
}
