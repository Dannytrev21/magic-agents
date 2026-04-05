import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AppShell } from '@/components/layout/AppShell';

function renderShell() {
  const onMobilePaneChange = vi.fn();
  const onToggleLeftPane = vi.fn();
  const onToggleRightPane = vi.fn();

  render(
    <AppShell
      centerPane={<div>Center workspace</div>}
      layoutMode="desktop"
      leftPaneCollapsed={false}
      leftRail={<div>Story intake</div>}
      mobilePane="workspace"
      onMobilePaneChange={onMobilePaneChange}
      onToggleLeftPane={onToggleLeftPane}
      onToggleRightPane={onToggleRightPane}
      phaseLabel="Phase 2: Happy Path Contract"
      rightPaneCollapsed={false}
      rightRail={<div>Evidence inspector</div>}
      sessionState="active"
      statusLabel="Awaiting operator input"
      storyKey="MAG-22"
      storySummary="Port the operator workspace layout"
      workspaceLabel="Negotiation surface"
    />,
  );

  return {
    onMobilePaneChange,
    onToggleLeftPane,
    onToggleRightPane,
  };
}

afterEach(() => {
  cleanup();
  window.localStorage?.clear?.();
});

describe('AppShell', () => {
  it('renders a three-pane desktop layout with a dominant center pane', () => {
    renderShell();

    const grid = screen.getByTestId('workspace-grid');
    const main = screen.getByRole('main');

    expect(screen.getByRole('banner')).toHaveAttribute('data-sticky', 'true');
    expect(grid).toHaveAttribute('data-layout-mode', 'desktop');
    expect(grid).toHaveStyle({
      '--workspace-left-width': '18rem',
      '--workspace-right-width': '20rem',
    });
    expect(main).toHaveAttribute('data-pane-priority', 'primary');
    expect(main).toHaveAttribute('data-scroll-region', 'independent');
    expect(screen.getByRole('complementary', { name: /story intake/i })).toHaveAttribute(
      'data-scroll-region',
      'independent',
    );
    expect(screen.getByRole('complementary', { name: /evidence inspector/i })).toHaveAttribute(
      'data-scroll-region',
      'independent',
    );
  });

  it('shows top-bar story context and workspace controls', () => {
    renderShell();

    expect(screen.getByRole('heading', { name: /magic agents/i })).toBeInTheDocument();
    expect(screen.getByText('MAG-22')).toBeInTheDocument();
    expect(screen.getByText(/negotiation surface/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /toggle story intake panel/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /toggle evidence panel/i })).toBeInTheDocument();
    expect(screen.getByRole('status', { name: /session status/i })).toHaveTextContent(
      /awaiting operator input/i,
    );
  });

  it('supports collapsed panel state and mobile panel switching controls', async () => {
    const user = userEvent.setup();
    const onMobilePaneChange = vi.fn();
    const onToggleLeftPane = vi.fn();
    const onToggleRightPane = vi.fn();

    render(
      <AppShell
        centerPane={<div>Center workspace</div>}
        layoutMode="mobile"
        leftPaneCollapsed
        leftRail={<div>Story intake</div>}
        mobilePane="workspace"
        onMobilePaneChange={onMobilePaneChange}
        onToggleLeftPane={onToggleLeftPane}
        onToggleRightPane={onToggleRightPane}
        phaseLabel="Phase 2: Happy Path Contract"
        rightPaneCollapsed
        rightRail={<div>Evidence inspector</div>}
        sessionState="idle"
        statusLabel="No active session"
        storyKey={null}
        workspaceLabel="Workspace overview"
      />,
    );

    expect(screen.getByTestId('workspace-grid')).toHaveAttribute('data-layout-mode', 'mobile');
    expect(screen.getByRole('tablist', { name: /workspace panels/i })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: /evidence panel/i }));
    expect(onMobilePaneChange).toHaveBeenCalledWith('evidence');

    await user.click(screen.getByRole('button', { name: /toggle story intake panel/i }));
    expect(onToggleLeftPane).toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /toggle evidence panel/i }));
    expect(onToggleRightPane).toHaveBeenCalled();
  });
});
