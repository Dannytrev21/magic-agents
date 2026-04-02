import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  compileSpec,
  fetchJiraConfigured,
  fetchJiraStories,
  fetchJiraTicket,
  fetchSessionInfo,
  generateTests,
  postJiraUpdate,
  respondToSession,
  startNegotiation,
  streamPipelineEvents,
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

  it('requests Jira ticket detail through a typed helper', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          acceptance_criteria: [{ checked: false, index: 0, text: 'Hydrate ACs from Jira' }],
          key: 'MAG-1',
          summary: 'Story',
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchJiraTicket('MAG-1')).resolves.toEqual({
      acceptance_criteria: [{ checked: false, index: 0, text: 'Hydrate ACs from Jira' }],
      key: 'MAG-1',
      summary: 'Story',
    });
    expect(fetchMock).toHaveBeenCalledWith('/api/jira/ticket/MAG-1', expect.any(Object));
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

  it('posts approve and revise responses through a typed session helper', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          done: false,
          jira_key: 'MAG-10',
          phase_number: 2,
          phase_title: 'Happy Path Contract',
          session_id: 'session-1',
          total_phases: 7,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      respondToSession({
        input: 'approve',
        session_id: 'session-1',
      }),
    ).resolves.toEqual({
      done: false,
      jira_key: 'MAG-10',
      phase_number: 2,
      phase_title: 'Happy Path Contract',
      session_id: 'session-1',
      total_phases: 7,
    });
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/respond',
      expect.objectContaining({
        body: JSON.stringify({
          input: 'approve',
          session_id: 'session-1',
        }),
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        method: 'POST',
      }),
    );
  });

  it('pins the compiled spec contract shape used by the verification workspace', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          requirements: [{ ac_checkbox: 0, id: 'REQ-001', title: 'Approval gate' }],
          spec_content: 'requirements:\n  - id: REQ-001\n',
          spec_path: 'specs/MAG-10.yaml',
          traceability: { ac_mappings: [{ ac_checkbox: 0, ac_text: 'Approve the contract' }] },
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(compileSpec({ session_id: 'session-1' })).resolves.toEqual({
      requirements: [{ ac_checkbox: 0, id: 'REQ-001', title: 'Approval gate' }],
      spec_content: 'requirements:\n  - id: REQ-001\n',
      spec_path: 'specs/MAG-10.yaml',
      traceability: { ac_mappings: [{ ac_checkbox: 0, ac_text: 'Approve the contract' }] },
    });
  });

  it('pins the generated test contract shape used by artifact viewers and verdict summaries', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          all_passed: false,
          steps: [{ step: 'generate', status: 'ok', path: 'tests/test_mag_10.py' }],
          test_content: 'def test_req_001_success():\n    assert True\n',
          test_path: 'tests/test_mag_10.py',
          verdicts: [{ ac_checkbox: 0, ac_text: 'Approve the contract', passed: false }],
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(generateTests({ session_id: 'session-1' })).resolves.toEqual({
      all_passed: false,
      steps: [{ step: 'generate', status: 'ok', path: 'tests/test_mag_10.py' }],
      test_content: 'def test_req_001_success():\n    assert True\n',
      test_path: 'tests/test_mag_10.py',
      verdicts: [{ ac_checkbox: 0, ac_text: 'Approve the contract', passed: false }],
    });
  });

  it('pins the jira feedback contract shape used by the post-run workspace surface', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          comment_id: 'jira-comment-1',
          issue_key: 'MAG-10',
          message: 'Updated Jira with verification evidence',
          transitioned: false,
          updated: true,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(postJiraUpdate({ session_id: 'session-1' })).resolves.toEqual({
      comment_id: 'jira-comment-1',
      issue_key: 'MAG-10',
      message: 'Updated Jira with verification evidence',
      transitioned: false,
      updated: true,
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

  it('streams pipeline events through the typed API helper', async () => {
    const events: Array<Record<string, unknown>> = [];
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(
          new TextEncoder().encode(
            'data: {"type":"step","step":"compile","status":"running"}\n\n' +
              'data: {"type":"done","success":true,"message":"Pipeline complete"}\n\n',
          ),
        );
        controller.close();
      },
    });

    fetchMock.mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await streamPipelineEvents('session-1', (event) => {
      events.push(event as Record<string, unknown>);
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/pipeline/stream',
      expect.objectContaining({
        body: JSON.stringify({ session_id: 'session-1' }),
        method: 'POST',
      }),
    );
    expect(events).toEqual([
      { type: 'step', step: 'compile', status: 'running' },
      { message: 'Pipeline complete', success: true, type: 'done' },
    ]);
  });
});
