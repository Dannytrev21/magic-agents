import type { PhaseResponse } from "@/lib/api/contracts";

export const NEGOTIATION_PHASES = [
  { id: "phase_1", label: "Interface & Actor Discovery", shortLabel: "P1" },
  { id: "phase_2", label: "Happy Path Contract", shortLabel: "P2" },
  { id: "phase_3", label: "Precondition Formalization", shortLabel: "P3" },
  { id: "phase_4", label: "Failure Mode Enumeration", shortLabel: "P4" },
  { id: "phase_5", label: "Invariant Extraction", shortLabel: "P5" },
  { id: "phase_6", label: "Completeness Sweep", shortLabel: "P6" },
  { id: "phase_7", label: "EARS Formalization", shortLabel: "P7" },
] as const;

export const WORKSPACE_LAYOUT_STORAGE_KEY = "magic-agents.workspace.layout";
export const WORKSPACE_COMPACT_BREAKPOINT = 1180;

export type PanelVisibility = {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
};

export type SessionStateLabel = "Idle" | "Running" | "Revised" | "Complete";

export const DEFAULT_PANEL_VISIBILITY: PanelVisibility = {
  leftCollapsed: false,
  rightCollapsed: false,
};

type StorageLike = Pick<Storage, "getItem" | "setItem">;

export function normalizePhaseState(phase: PhaseResponse): PhaseResponse {
  return {
    ...phase,
    totalPhases: NEGOTIATION_PHASES.length,
  };
}

export function deriveSessionStateLabel(phase: PhaseResponse): SessionStateLabel {
  if (phase.done) {
    return "Complete";
  }

  if (phase.revised) {
    return "Revised";
  }

  if (phase.sessionId) {
    return "Running";
  }

  return "Idle";
}

export function extractPhaseSummary(phaseTitle: string): string {
  const normalized = phaseTitle.replace(/\s+/g, " ").trim();
  const numberedMatch = normalized.match(/^Phase\s+\d+\s+of\s+\d+:\s*(.+)$/i);

  if (numberedMatch?.[1]) {
    return numberedMatch[1].trim();
  }

  return normalized;
}

export function readPanelVisibility(storage: StorageLike | null | undefined): PanelVisibility {
  if (!storage) {
    return DEFAULT_PANEL_VISIBILITY;
  }

  const raw = storage.getItem(WORKSPACE_LAYOUT_STORAGE_KEY);

  if (!raw) {
    return DEFAULT_PANEL_VISIBILITY;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<PanelVisibility>;
    return {
      leftCollapsed: Boolean(parsed.leftCollapsed),
      rightCollapsed: Boolean(parsed.rightCollapsed),
    };
  } catch {
    return DEFAULT_PANEL_VISIBILITY;
  }
}

export function writePanelVisibility(
  storage: StorageLike | null | undefined,
  visibility: PanelVisibility,
) {
  if (!storage) {
    return;
  }

  storage.setItem(WORKSPACE_LAYOUT_STORAGE_KEY, JSON.stringify(visibility));
}
