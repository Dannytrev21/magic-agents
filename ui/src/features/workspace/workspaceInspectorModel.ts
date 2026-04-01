import type {
  CompileSpecResponse,
  CompiledSpecRequirement,
  FailureModeResult,
  StartNegotiationResponse,
  TraceabilityVerificationRef,
} from '@/lib/api/types';

export type InspectorTraceabilityItem = {
  acIndex: number;
  acText: string;
  classification: string;
  failureModes: FailureModeResult[];
  postconditions: StartNegotiationResponse['postconditions'];
  preconditions: StartNegotiationResponse['preconditions'];
  requirementId: string;
  verificationRefs: TraceabilityVerificationRef[];
};

export function buildTraceabilityItems(
  activeSession: StartNegotiationResponse | null,
): InspectorTraceabilityItem[] {
  if (!activeSession?.acceptance_criteria?.length) {
    return [];
  }

  return activeSession.acceptance_criteria.map((criterion) => {
    const mapping =
      activeSession.traceability_map?.ac_mappings?.find(
        (candidate) => candidate.ac_checkbox === criterion.index,
      ) ?? null;
    const verificationRefs = mapping?.required_verifications ?? [];
    const failureIds = new Set(
      verificationRefs
        .map((ref) => ref.ref.split('.').at(-1))
        .filter((refId): refId is string => Boolean(refId?.startsWith('FAIL-'))),
    );
    const matchingPostconditions =
      activeSession.postconditions?.filter((result) => result.ac_index === criterion.index) ?? [];

    return {
      acIndex: criterion.index,
      acText: criterion.text,
      classification:
        activeSession.classifications?.find((classification) => classification.ac_index === criterion.index)
          ?.type ?? 'unclassified',
      failureModes:
        activeSession.failure_modes?.filter((failureMode) =>
          failureIds.size > 0 ? failureIds.has(failureMode.id) : true,
        ) ?? [],
      postconditions:
        matchingPostconditions.length > 0 ? matchingPostconditions : activeSession.postconditions ?? [],
      preconditions: activeSession.preconditions ?? [],
      requirementId: buildRequirementId(criterion.index, verificationRefs),
      verificationRefs,
    };
  });
}

export function buildRequirementId(acIndex: number, refs: TraceabilityVerificationRef[]) {
  const prefixedRef = refs[0]?.ref.split('.')[0];

  if (prefixedRef) {
    return prefixedRef;
  }

  return `REQ-${String(acIndex + 1).padStart(3, '0')}`;
}

export function formatScanSummary(summary: Record<string, unknown> | string | undefined) {
  if (!summary) {
    return '';
  }

  if (typeof summary === 'string') {
    return summary;
  }

  return Object.entries(summary)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join('\n');
}

export function phaseKeyFromNumber(phaseNumber: number) {
  return `phase_${Math.max(1, phaseNumber)}`;
}

export function requirementForAcceptanceCriterion(
  compiledSpec: CompileSpecResponse | undefined,
  acIndex: number,
) {
  return compiledSpec?.requirements?.find((requirement) => requirement.ac_checkbox === acIndex) ?? null;
}

export function requirementTraceabilityRefs(
  compiledSpec: CompileSpecResponse | undefined,
  requirement: CompiledSpecRequirement,
) {
  return (
    compiledSpec?.traceability?.ac_mappings?.find(
      (mapping) => mapping.ac_checkbox === requirement.ac_checkbox,
    )?.required_verifications ?? []
  );
}
