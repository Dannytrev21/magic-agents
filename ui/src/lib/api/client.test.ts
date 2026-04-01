import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fetchJiraConfigured,
  fetchJiraStories,
  fetchSessionInfo,
  startNegotiation,
} from '@/lib/api/client';
import { parseSseChunk } from '@/lib/api/sse';

const fetchMock = vi.fn<typeof fetch>();

describe('API client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
  });

  it('requests jira configuration through a typed helper', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ configured: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchJiraConfigured()).resolves.toEqual({ configured: true });
    expect(fetchMock).toHaveBeenCalledWith('/api/jira/configured', expect.any(Object));
  });

  it('requests jira stories without leaking URLs into components', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ stories: [{ key: 'MAG-1', summary: 'Story' }] }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchJiraStories()).resolves.toEqual({
      stories: [{ key: 'MAG-1', summary: 'Story' }],
    });
  });

  it('posts typed negotiation payloads for story intake', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ session_id: 'session-1', done: false, phase_number: 1, total_phases: 7 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await startNegotiation({
      jira_key: 'MAG-10',
      jira_summary: 'Port the shell',
      acceptance_criteria: [{ index: 0, text: 'Render the shell', checked: false }],
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/start',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    );
  });

  it('reads persisted session state through a typed endpoint adapter', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ has_checkpoint: true, session: { jira_key: 'MAG-10' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchSessionInfo('MAG-10')).resolves.toEqual({
      has_checkpoint: true,
      session: { jira_key: 'MAG-10' },
    });
  });
});

describe('SSE adapter', () => {
  it('parses event stream chunks into structured pipeline events', () => {
    const events = parseSseChunk(
      'data: {"type":"step","step":"compile","status":"running"}\n\n' +
        'data: {"type":"done","success":true}\n\n',
    );

    expect(events).toEqual([
      { type: 'step', step: 'compile', status: 'running' },
      { type: 'done', success: true },
    ]);
  });
});
