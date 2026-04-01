import type { StartNegotiationResponse } from '@/lib/api/types';

export const negotiationPhases = [
  'Interface & Actor Discovery',
  'Happy Path Contract',
  'Precondition Formalization',
  'Failure Mode Enumeration',
  'Invariant Extraction',
  'Routing & Completeness Sweep',
  'EARS Formalization',
] as const;

export const centerWorkspaceViews = [
  { value: 'overview', label: 'Overview' },
  { value: 'negotiation', label: 'Negotiation' },
  { value: 'traceability', label: 'Traceability' },
] as const;

export const inspectorViews = [
  { value: 'evidence', label: 'Evidence' },
  { value: 'scan', label: 'Scan output' },
  { value: 'traceability', label: 'Traceability' },
] as const;

export const mobileWorkspacePanes = [
  { value: 'story', label: 'Story panel' },
  { value: 'workspace', label: 'Workspace panel' },
  { value: 'evidence', label: 'Evidence panel' },
] as const;

export const workspacePanelStorageKey = 'magic-agents:workspace-panels';

export type WorkspaceLayoutMode = 'desktop' | 'tablet' | 'mobile';
export type WorkspacePaneId = (typeof mobileWorkspacePanes)[number]['value'];
export type WorkspaceSessionState = 'idle' | 'active' | 'revising' | 'complete';
export type WorkspaceCenterView = (typeof centerWorkspaceViews)[number]['value'];
export type WorkspaceInspectorView = (typeof inspectorViews)[number]['value'];

export function parseCenterWorkspaceView(value: string | null): WorkspaceCenterView {
  return centerWorkspaceViews.some((view) => view.value === value)
    ? (value as WorkspaceCenterView)
    : 'overview';
}

export function parseInspectorWorkspaceView(value: string | null): WorkspaceInspectorView {
  return inspectorViews.some((view) => view.value === value)
    ? (value as WorkspaceInspectorView)
    : 'evidence';
}

export function parseMobileWorkspacePane(value: string | null): WorkspacePaneId {
  return mobileWorkspacePanes.some((pane) => pane.value === value)
    ? (value as WorkspacePaneId)
    : 'workspace';
}

export function getWorkspaceLayoutMode(width: number): WorkspaceLayoutMode {
  if (width < 768) {
    return 'mobile';
  }

  if (width < 1024) {
    return 'tablet';
  }

  return 'desktop';
}

export function getWorkspaceSessionState(
  activeSession: StartNegotiationResponse | null,
): WorkspaceSessionState {
  if (!activeSession) {
    return 'idle';
  }

  if (activeSession.done) {
    return 'complete';
  }

  if (activeSession.revised) {
    return 'revising';
  }

  return 'active';
}

export function getWorkspaceStatusLabel(activeSession: StartNegotiationResponse | null): string {
  const sessionState = getWorkspaceSessionState(activeSession);

  switch (sessionState) {
    case 'complete':
      return 'Verification-ready session';
    case 'revising':
      return 'Revising phase output';
    case 'active':
      return 'Awaiting operator input';
    default:
      return 'No active session';
  }
}
