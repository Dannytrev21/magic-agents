import { describe, expect, it } from 'vitest';
import { buildPhaseReview } from '@/features/workspace/phaseReviewModel';
import type { StartNegotiationResponse } from '@/lib/api/types';

const fullSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'Authenticated users can view their profile',
    },
  ],
  classifications: [
    {
      ac_index: 0,
      actor: 'authenticated_user',
      confidence: 'high',
      interface: { method: 'GET', path: '/api/v1/users/me' },
      type: 'api_behavior',
    },
  ],
  current_phase: 'phase_6',
  done: false,
  ears_statements: [
    {
      confidence: 'high',
      id: 'EARS-001',
      pattern: 'EVENT_DRIVEN',
      statement:
        'WHEN GET /api/v1/users/me is requested with valid auth, the system SHALL respond with 200.',
      traces_to: 'REQ-001.success',
    },
  ],
  failure_modes: [
    {
      body: { error: 'unauthorized', message: 'Bearer token required' },
      id: 'FAIL-001',
      mitigations: ['Return the standard auth error envelope'],
      status: 401,
      violates: 'PRE-001',
    },
  ],
  invariants: [
    {
      id: 'INV-001',
      rule: 'Responses MUST NEVER include password or token fields.',
      source: 'constitution',
      type: 'security',
    },
  ],
  jira_key: 'MAG-410',
  jira_summary: 'Port the active phase workspace',
  negotiation_log: [
    {
      content: 'Interface & Actor Discovery: mapped one API behavior',
      phase: 'phase_0',
      role: 'ai',
      timestamp: '2026-04-01T10:00:00Z',
    },
    {
      content: 'Please tighten the 404 vs 410 decision.',
      phase: 'phase_3',
      role: 'human',
      timestamp: '2026-04-01T10:05:00Z',
    },
  ],
  phase_number: 7,
  phase_title: 'EARS Formalization',
  postconditions: [
    {
      ac_index: 0,
      constraints: ['response.id MUST equal jwt.sub'],
      content_type: 'application/json',
      forbidden_fields: ['password', 'token'],
      schema: {
        display_name: { required: true, type: 'string' },
        id: { required: true, type: 'string' },
      },
      status: 200,
    },
  ],
  preconditions: [
    {
      category: 'authentication',
      description: 'A valid bearer token is present.',
      formal: "request.headers['Authorization'].startsWith('Bearer ')",
      id: 'PRE-001',
    },
  ],
  questions: ['Should soft-deleted users return 404 or 410?'],
  session_events: [
    {
      detail: 'MAG-410',
      timestamp: '2026-04-01T09:59:00Z',
      title: 'session_created',
    },
  ],
  session_id: 'session-u4',
  total_phases: 7,
  traceability_map: {
    ac_mappings: [
      {
        ac_checkbox: 0,
        ears_refs: ['EARS-001'],
        req_id: 'REQ-001',
      },
    ],
  },
  usage: null,
  verification_routing: {
    checklist: [
      {
        category: 'authentication',
        detail: 'PRE-001 covers JWT validation.',
        status: 'covered',
      },
    ],
    questions: ['Should we add explicit rate-limiting checks?'],
    routing: [
      {
        refs: ['REQ-001.success', 'REQ-001.FAIL-001'],
        req_id: 'REQ-001',
        skill: 'pytest_unit_test',
      },
    ],
  },
  verdicts: [],
};

describe('phaseReviewModel', () => {
  it.each([
    {
      expectedGroup: 'Interface coverage',
      phaseNumber: 1,
      token: 'classification',
    },
    {
      expectedGroup: 'Response contracts',
      phaseNumber: 2,
      token: 'contract',
    },
    {
      expectedGroup: 'Required conditions',
      phaseNumber: 3,
      token: 'precondition',
    },
    {
      expectedGroup: 'Failure responses',
      phaseNumber: 4,
      token: 'failure',
    },
    {
      expectedGroup: 'Always-on rules',
      phaseNumber: 5,
      token: 'invariant',
    },
    {
      expectedGroup: 'Completeness checklist',
      phaseNumber: 6,
      token: 'routing',
    },
    {
      expectedGroup: 'Formalized requirements',
      phaseNumber: 7,
      token: 'ears',
    },
  ])('builds a structured phase review for phase $phaseNumber', ({
    expectedGroup,
    phaseNumber,
    token,
  }) => {
    const review = buildPhaseReview(fullSession, phaseNumber);

    expect(review.phaseNumber).toBe(phaseNumber);
    expect(review.summary.toLowerCase()).toContain(token);
    expect(review.groups[0]?.title).toBe(expectedGroup);
    expect(review.rawPayload).toBeTruthy();
  });

  it('keeps the raw payload available for fallback details without replacing the primary summary', () => {
    const review = buildPhaseReview(fullSession, 6);

    expect(review.summaryLabel).toBe('Primary decision');
    expect(review.summary).toMatch(/routing/i);
    expect(review.rawPayload).toEqual(
      expect.objectContaining({
        checklist: expect.any(Array),
        routing: expect.any(Array),
      }),
    );
  });
});
