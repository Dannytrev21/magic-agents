import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRef, type ComponentProps, type ReactNode } from 'react';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { WorkspaceInspector } from '@/features/workspace/WorkspaceInspector';
import * as api from '@/lib/api/client';
import type {
  CompileSpecResponse,
  StartNegotiationResponse,
  TraceabilityMap,
} from '@/lib/api/types';

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

const traceabilityMap: TraceabilityMap = {
  ac_mappings: [
    {
      ac_checkbox: 0,
      ac_text: 'User can review planner output without losing the active draft',
      required_verifications: [
        {
          description: 'Happy path: HTTP 200',
          ref: 'REQ-001.success',
          verification_type: 'test_result',
        },
        {
          description: 'Failure: Missing auth',
          ref: 'REQ-001.FAIL-001',
          verification_type: 'test_result',
        },
      ],
    },
    {
      ac_checkbox: 1,
      ac_text: 'Workspace shows the 401 failure path clearly',
      required_verifications: [
        {
          description: 'Failure: Missing auth',
          ref: 'REQ-002.FAIL-001',
          verification_type: 'test_result',
        },
      ],
    },
  ],
};

const activeSession: StartNegotiationResponse = {
  acceptance_criteria: [
    {
      checked: false,
      index: 0,
      text: 'User can review planner output without losing the active draft',
    },
    {
      checked: false,
      index: 1,
      text: 'Workspace shows the 401 failure path clearly',
    },
  ],
  classifications: [
    { ac_index: 0, type: 'api_behavior' },
    { ac_index: 1, type: 'failure_mode' },
  ],
  done: false,
  failure_modes: [
    {
      description: 'No auth header provided',
      id: 'FAIL-001',
      status: 401,
      violates: 'PRE-001',
    },
  ],
  jira_key: 'MAG-501',
  jira_summary: 'Inspector and evidence workspace',
  phase_number: 4,
  phase_title: 'Failure Mode Enumeration',
  postconditions: [
    {
      ac_index: 0,
      content_type: 'application/json',
      schema: { type: 'object' },
      status: 200,
    },
  ],
  preconditions: [
    {
      category: 'authentication',
      description: 'Valid JWT bearer token is present',
      id: 'PRE-001',
    },
  ],
  session_id: 'session-u5',
  total_phases: 7,
  traceability_map: traceabilityMap,
};

const compiledSpec: CompileSpecResponse = {
  requirements: [
    {
      ac_checkbox: 0,
      ac_text: 'User can review planner output without losing the active draft',
      contract: {
        interface: {
          method: 'GET',
          path: '/api/v1/review',
        },
      },
      id: 'REQ-001',
      title: 'Planner review surface',
      type: 'api_behavior',
      verification: [
        {
          output: 'tests/test_planner_review.py',
          refs: ['success', 'FAIL-001'],
          skill: 'pytest_unit_test',
        },
      ],
    },
    {
      ac_checkbox: 1,
      ac_text: 'Workspace shows the 401 failure path clearly',
      contract: {
        interface: {
          method: 'GET',
          path: '/api/v1/review',
        },
      },
      id: 'REQ-002',
      title: 'Unauthorized review path',
      type: 'api_failure',
      verification: [
        {
          output: 'tests/test_planner_review.py',
          refs: ['FAIL-001'],
          skill: 'pytest_unit_test',
        },
      ],
    },
  ],
  spec_content: 'requirements:\n  - id: REQ-001\ntraceability:\n  ac_mappings: []\n',
  spec_path: 'specs/MAG-501.yaml',
  traceability: traceabilityMap,
};

beforeEach(() => {
  vi.spyOn(api, 'fetchSkills').mockResolvedValue([
    { name: 'pytest_unit_test' },
    { name: 'gherkin_scenario' },
  ]);
  vi.spyOn(api, 'fetchScanStatus').mockResolvedValue({
    project_root: 'dog-service',
    scanned: false,
    summary: '',
  });
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderInspector(
  props: Partial<ComponentProps<typeof WorkspaceInspector>> = {},
) {
  const onAcceptanceCriterionSelect = vi.fn();
  const onViewChange = vi.fn();

  render(
    <WorkspaceInspector
      activeSession={activeSession}
      activeView="evidence"
      focusRef={createRef<HTMLElement>()}
      onAcceptanceCriterionSelect={onAcceptanceCriterionSelect}
      onViewChange={onViewChange}
      selectedAcceptanceCriterionIndex={0}
      {...props}
    />,
    { wrapper: createWrapper() },
  );

  return {
    onAcceptanceCriterionSelect,
    onViewChange,
  };
}

describe('WorkspaceInspector', () => {
  it('renders scan, traceability, and planning tabs with clear selection state', async () => {
    const user = userEvent.setup();
    const { onViewChange } = renderInspector();

    const tablist = screen.getByRole('tablist', { name: /inspector views/i });

    expect(within(tablist).getByRole('tab', { name: /evidence/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(within(tablist).getByRole('tab', { name: /^scan$/i })).toBeInTheDocument();
    expect(within(tablist).getByRole('tab', { name: /^links$/i })).toBeInTheDocument();

    const analysisTab = within(tablist).getByRole('tab', { name: /^tools$/i });
    expect(analysisTab).toHaveAttribute('aria-selected', 'false');

    await user.click(analysisTab);

    expect(onViewChange).toHaveBeenCalledWith('analysis');
  });

  it('mounts planning and critique content only when the analyst tab is selected', async () => {
    const { rerender } = render(
      <WorkspaceInspector
        activeSession={activeSession}
        activeView="evidence"
        focusRef={createRef<HTMLElement>()}
        onAcceptanceCriterionSelect={vi.fn()}
        onViewChange={vi.fn()}
        selectedAcceptanceCriterionIndex={0}
      />,
      { wrapper: createWrapper() },
    );

    expect(screen.queryByText(/planner output/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/phase critique/i)).not.toBeInTheDocument();

    rerender(
      <WorkspaceInspector
        activeSession={activeSession}
        activeView="analysis"
        focusRef={createRef<HTMLElement>()}
        onAcceptanceCriterionSelect={vi.fn()}
        onViewChange={vi.fn()}
        selectedAcceptanceCriterionIndex={0}
      />,
    );

    expect(await screen.findByRole('heading', { name: 'Plan' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Critique' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Diff' })).toBeInTheDocument();
  });

  it('rehydrates scan output and preserves the previous summary when a rerun fails', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'fetchScanStatus').mockResolvedValue({
      project_root: 'dog-service',
      scanned: true,
      summary: {
        controllers: 4,
        language: 'java',
      },
    });
    vi.spyOn(api, 'runCodebaseScan').mockRejectedValue(new Error('scanner offline'));

    renderInspector({ activeView: 'scan' });

    expect(await screen.findByText(/language: java/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('dog-service')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /run scan/i }));

    expect(await screen.findByText(/scanner offline/i)).toBeInTheDocument();
    expect(screen.getByText(/controllers: 4/i)).toBeInTheDocument();
  });

  it('renders per-ac traceability details and exposes a denser matrix view', async () => {
    const user = userEvent.setup();
    const { onAcceptanceCriterionSelect } = renderInspector({
      activeView: 'traceability',
      selectedAcceptanceCriterionIndex: 1,
    });

    expect(await screen.findByRole('heading', { name: 'REQ-002' })).toBeInTheDocument();
    expect(screen.getByText(/Workspace shows the 401 failure path clearly/i)).toBeInTheDocument();
    expect(screen.getByText(/^before$/i)).toBeInTheDocument();
    expect(screen.getByText(/^failures$/i)).toBeInTheDocument();

    await user.click(screen.getByText(/^refs$/i));

    expect(screen.getByText(/REQ-002.FAIL-001/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /^table$/i }));

    expect(screen.getByText(/Type \/ Req/i)).toBeInTheDocument();
    expect(screen.getByText(/api_behavior \/ REQ-001/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /AC 1: User can review planner output/i }));

    expect(onAcceptanceCriterionSelect).toHaveBeenCalledWith(0);
  });

  it('runs planner, critique, and spec-diff requests from the analyst tab', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'fetchPlan').mockResolvedValue({
      ac_groups: [{ ac_indices: [0, 1], endpoint: '/api/v1/review', methods: ['GET'] }],
      estimated_complexity: 'medium',
    });
    vi.spyOn(api, 'evaluatePhase').mockResolvedValue({
      has_issues: true,
      issues: ['No failure modes enumerated'],
      suggestions: ['Review edge-case coverage'],
    });
    vi.spyOn(api, 'fetchSpecDiff').mockResolvedValue({
      diff: null,
      has_old_spec: false,
      jira_key: 'MAG-501',
    });

    renderInspector({ activeView: 'analysis' });

    await user.click(await screen.findByRole('button', { name: /load plan/i }));
    await user.click(screen.getByRole('button', { name: /run critique/i }));
    await user.click(screen.getByRole('button', { name: /compare specs/i }));

    expect(await screen.findByText(/Estimated complexity/i)).toBeInTheDocument();
    expect(screen.getByText('/api/v1/review')).toBeInTheDocument();
    expect(await screen.findByText(/Issues found/i)).toBeInTheDocument();
    expect(screen.getByText(/No failure modes enumerated/i)).toBeInTheDocument();
    expect(await screen.findByText(/Nothing to compare yet/i)).toBeInTheDocument();
  });

  it('loads a structured spec contract view, toggles raw yaml, and links back to the originating ac', async () => {
    const user = userEvent.setup();

    vi.spyOn(api, 'compileSpec').mockResolvedValue(compiledSpec);

    const { onAcceptanceCriterionSelect } = renderInspector({
      activeView: 'evidence',
      selectedAcceptanceCriterionIndex: 0,
    });

    expect(screen.getByText(/No spec yet/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /load spec/i }));

    expect(await screen.findByRole('tab', { name: 'REQ-001' })).toBeInTheDocument();
    expect(screen.getByText(/Planner review surface/i)).toBeInTheDocument();
    expect(screen.getByText(/^checks$/i)).toBeInTheDocument();
    expect(screen.getByText(/pytest_unit_test/i)).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'REQ-002' }));

    expect(onAcceptanceCriterionSelect).toHaveBeenCalledWith(1);

    await user.click(screen.getByRole('tab', { name: /^yaml$/i }));

    await waitFor(() => {
      expect(screen.getByText(/requirements:/i)).toBeInTheDocument();
    });
  });
});
