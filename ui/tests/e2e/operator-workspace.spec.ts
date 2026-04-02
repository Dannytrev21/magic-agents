import { expect, test, type Page } from '@playwright/test';

const phaseTitles = [
  'Interface & Actor Discovery',
  'Happy Path Contract',
  'Precondition Formalization',
  'Failure Mode Enumeration',
  'Invariant Extraction',
  'Routing & Completeness Sweep',
  'EARS Formalization',
] as const;

const approvePhaseButtonName = /^approve(?: phase)?$/i;

type MockWorkspaceOptions = {
  pipelineError?: string;
  startDone?: boolean;
};

test.describe('Operator workspace browser flow', () => {
  test('covers fallback intake, negotiation progress, approval, and pipeline execution', async ({
    page,
  }) => {
    await registerWorkspaceRoutes(page);

    await page.goto('/');

    await expect(page.getByText(/jira configuration required/i)).toBeVisible();

    await page.getByRole('button', { name: /use manual entry/i }).click();
    await expect(page.getByLabel(/jira key/i)).toBeVisible();
    await page.getByLabel(/jira key/i).fill('MAG-901');
    await page.getByLabel(/summary/i).fill('Browser journey coverage');
    await page
      .getByLabel(/acceptance criteria/i)
      .fill('Operator can continue from raw notes\nVerification stays inside the workspace');
    await page.getByRole('button', { name: /start session from manual story/i }).click();

    await expect(page.getByRole('status', { name: /session status/i })).toContainText(
      /awaiting operator input/i,
    );
    await expect(page.getByText(/browser journey coverage/i)).toBeVisible();

    for (let index = 0; index < 6; index += 1) {
      await page.getByRole('button', { name: approvePhaseButtonName }).click();
      await expect(page.locator('header')).toContainText(phaseTitles[index + 1]);
    }

    await page.getByRole('button', { name: approvePhaseButtonName }).click();
    await expect(page.getByText(/verification console/i)).toBeVisible();

    await page.getByRole('button', { name: /approve ears/i }).click();
    await expect(page.getByText(/approved by web_operator/i)).toBeVisible();

    await page.getByRole('button', { name: /run full pipeline/i }).click();

    await expect(page.getByRole('log', { name: /pipeline console/i })).toContainText(
      /compiling spec/i,
    );
    await expect(page.getByText(/pipeline complete/i)).toBeVisible();
    await expect(page.getByText(/1\/1 passed/i)).toBeVisible();
  });

  test('surfaces a deterministic pipeline failure path in mock mode', async ({ page }) => {
    await registerWorkspaceRoutes(page, {
      pipelineError: 'Pipeline stream failed in mock mode',
      startDone: true,
    });

    await page.goto('/');

    await page.getByRole('button', { name: /use manual entry/i }).click();
    await expect(page.getByLabel(/jira key/i)).toBeVisible();
    await page.getByLabel(/jira key/i).fill('MAG-902');
    await page.getByLabel(/summary/i).fill('Pipeline failure coverage');
    await page
      .getByLabel(/acceptance criteria/i)
      .fill('Pipeline failures remain visible in the active verification surface');
    await page.getByRole('button', { name: /start session from manual story/i }).click();

    await page.getByRole('tab', { name: /^verification$/i }).click();
    await page.getByRole('button', { name: /approve ears/i }).click();
    await page.getByRole('button', { name: /run full pipeline/i }).click();

    await expect(page.getByText(/pipeline stream failed in mock mode/i)).toBeVisible();
  });
});

async function registerWorkspaceRoutes(page: Page, options: MockWorkspaceOptions = {}) {
  let currentSession = buildSession({
    done: Boolean(options.startDone),
    jiraKey: 'MAG-901',
    jiraSummary: 'Browser journey coverage',
    phaseNumber: options.startDone ? 7 : 1,
  });

  await page.route('**/api/jira/configured', async (route) => {
    await route.fulfill({ json: { configured: false } });
  });

  await page.route('**/api/jira/stories', async (route) => {
    await route.fulfill({ json: { stories: [] } });
  });

  await page.route('**/api/skills', async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route('**/api/scan/status', async (route) => {
    await route.fulfill({
      json: {
        project_root: '/Users/dannytrevino/development/magic-agents',
        scanned: false,
        summary: 'No scan yet',
      },
    });
  });

  await page.route('**/api/start', async (route) => {
    const payload = route.request().postDataJSON() as {
      acceptance_criteria: Array<{ checked: boolean; index: number; text: string }>;
      jira_key: string;
      jira_summary: string;
    };

    currentSession = buildSession({
      acceptanceCriteria: payload.acceptance_criteria,
      done: Boolean(options.startDone),
      jiraKey: payload.jira_key,
      jiraSummary: payload.jira_summary,
      phaseNumber: options.startDone ? 7 : 1,
      sessionId: options.startDone ? 'session-e2e-done' : 'session-e2e-active',
    });

    await route.fulfill({ json: currentSession });
  });

  await page.route('**/api/respond', async (route) => {
    const payload = route.request().postDataJSON() as { input: string; session_id: string };

    if (payload.input !== 'approve') {
      currentSession = {
        ...currentSession,
        revised: true,
      };
      await route.fulfill({ json: currentSession });
      return;
    }

    if (currentSession.phase_number < 7) {
      currentSession = buildSession({
        acceptanceCriteria: currentSession.acceptance_criteria ?? [],
        jiraKey: currentSession.jira_key,
        jiraSummary: currentSession.jira_summary ?? '',
        phaseNumber: currentSession.phase_number + 1,
        sessionId: currentSession.session_id,
      });
    } else {
      currentSession = {
        ...currentSession,
        done: true,
        revised: false,
      };
    }

    await route.fulfill({ json: currentSession });
  });

  await page.route('**/api/ears-approve', async (route) => {
    await route.fulfill({
      json: {
        approved: true,
        approved_at: '2026-04-01T17:00:00Z',
        approved_by: 'web_operator',
      },
    });
  });

  await page.route('**/api/pipeline/stream', async (route) => {
    if (options.pipelineError) {
      await route.fulfill({
        body: options.pipelineError,
        status: 500,
      });
      return;
    }

    await route.fulfill({
      body:
        'data: {"type":"step","step":"compile","status":"running","message":"Compiling spec..."}\n\n' +
        'data: {"type":"done","all_passed":true,"message":"Pipeline complete","success":true,"verdicts":[{"ac_checkbox":0,"ac_text":"Operator can continue from raw notes","passed":true}]}\n\n',
      contentType: 'text/event-stream',
      status: 200,
    });
  });
}

function buildSession({
  acceptanceCriteria = [
    { checked: false, index: 0, text: 'Operator can continue from raw notes' },
    { checked: false, index: 1, text: 'Verification stays inside the workspace' },
  ],
  done = false,
  jiraKey,
  jiraSummary,
  phaseNumber,
  sessionId = 'session-e2e-active',
}: {
  acceptanceCriteria?: Array<{ checked: boolean; index: number; text: string }>;
  done?: boolean;
  jiraKey: string;
  jiraSummary: string;
  phaseNumber: number;
  sessionId?: string;
}) {
  return {
    acceptance_criteria: acceptanceCriteria,
    done,
    jira_key: jiraKey,
    jira_summary: jiraSummary,
    phase_number: phaseNumber,
    phase_title: phaseTitles[phaseNumber - 1],
    session_id: sessionId,
    total_phases: 7,
    verification_routing: {
      checklist: [],
      routing: [],
    },
    verdicts: [],
  };
}
