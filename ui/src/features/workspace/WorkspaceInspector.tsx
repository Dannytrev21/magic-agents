import { Suspense, lazy, useDeferredValue, useEffect, useId, useState, type RefObject } from 'react';
import { Button } from '@/components/primitives/Button';
import { Badge } from '@/components/primitives/Badge';
import { Divider } from '@/components/primitives/Divider';
import { EmptyState } from '@/components/primitives/EmptyState';
import { Mono } from '@/components/primitives/Mono';
import { SectionHeader } from '@/components/primitives/SectionHeader';
import { Text } from '@/components/primitives/Text';
import {
  buildTraceabilityItems,
  formatScanSummary,
  requirementForAcceptanceCriterion,
  requirementTraceabilityRefs,
  type InspectorTraceabilityItem,
} from '@/features/workspace/workspaceInspectorModel';
import {
  inspectorViews,
  type WorkspaceInspectorView,
} from '@/features/workspace/workspaceModel';
import type {
  CompileSpecResponse,
  CompiledSpecRequirement,
  StartNegotiationResponse,
} from '@/lib/api/types';
import { useInspectorActions, useInspectorQueries } from '@/lib/query/sessionHooks';
import styles from '@/features/workspace/workspace.module.css';

const WorkspaceInspectorAnalysisView = lazy(
  () => import('@/features/workspace/WorkspaceInspectorAnalysisView'),
);

type WorkspaceInspectorProps = {
  activeSession: StartNegotiationResponse | null;
  activeView: WorkspaceInspectorView;
  focusRef: RefObject<HTMLElement | null>;
  onAcceptanceCriterionSelect?: (index: number) => void;
  onViewChange: (view: WorkspaceInspectorView) => void;
  selectedAcceptanceCriterionIndex: number | null;
};

type InspectorActions = ReturnType<typeof useInspectorActions>;

export function WorkspaceInspector({
  activeSession,
  activeView,
  focusRef,
  onAcceptanceCriterionSelect,
  onViewChange,
  selectedAcceptanceCriterionIndex,
}: WorkspaceInspectorProps) {
  const inspectorViewId = useId();
  const { isLoading, scanStatus, skills } = useInspectorQueries();
  const { compileMutation, critiqueMutation, planningMutation, scanMutation, specDiffMutation } =
    useInspectorActions();
  const [specView, setSpecView] = useState<'raw' | 'structured'>('structured');
  const [traceabilityMode, setTraceabilityMode] = useState<'browser' | 'matrix'>('browser');
  const contractState = activeSession ? 'Session-bound' : 'Waiting for session';
  const activeInspectorPanelId = `${inspectorViewId}-${activeView}-panel`;
  const activeInspectorTabId = `${inspectorViewId}-${activeView}-tab`;

  useEffect(() => {
    compileMutation.reset();
    critiqueMutation.reset();
    planningMutation.reset();
    specDiffMutation.reset();
    setSpecView('structured');
  }, [activeSession?.session_id]);

  return (
    <div className={styles.stack}>
      <SectionHeader
        title="Evidence inspector"
        description="Evidence, scan output, traceability, and analyst context stay visible without forcing a route change."
      />
      <div aria-label="Inspector views" className={styles.viewTabs} role="tablist">
        {inspectorViews.map((view) => (
          <button
            aria-controls={`${inspectorViewId}-${view.value}-panel`}
            aria-selected={activeView === view.value}
            className={styles.viewTab}
            id={`${inspectorViewId}-${view.value}-tab`}
            key={view.value}
            onClick={() => onViewChange(view.value)}
            role="tab"
            type="button"
          >
            {view.label}
          </button>
        ))}
      </div>
      <section
        aria-labelledby={activeInspectorTabId}
        className={styles.focusRegion}
        id={activeInspectorPanelId}
        ref={focusRef}
        role="tabpanel"
        tabIndex={-1}
      >
        <div className={styles.sectionStack}>
          <div className={styles.detailList}>
            <div className={styles.detailRow}>
              <Text as="p" size="xs" tone="muted">
                Contract state
              </Text>
              <div className={styles.inlineCluster}>
                <Text as="p" size="sm" weight="medium">
                  {contractState}
                </Text>
                <Badge tone={activeSession ? 'success' : 'warning'}>
                  {activeSession ? 'Phase surface mounted' : 'Awaiting intake'}
                </Badge>
              </div>
            </div>
          </div>
          <Divider />
          {activeView === 'evidence' ? (
            <EvidenceView
              activeSession={activeSession}
              compileMutation={compileMutation}
              onAcceptanceCriterionSelect={onAcceptanceCriterionSelect}
              selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
              specView={specView}
              onSpecViewChange={setSpecView}
            />
          ) : null}
          {activeView === 'scan' ? (
            <ScanView
              isLoading={isLoading}
              projectRoot={scanStatus.project_root}
              scanMutation={scanMutation}
              scanned={scanStatus.scanned}
              scanSummary={scanMutation.data?.summary ?? scanStatus.summary}
              skillCount={skills.length}
            />
          ) : null}
          {activeView === 'traceability' ? (
            <TraceabilityView
              activeSession={activeSession}
              mode={traceabilityMode}
              onAcceptanceCriterionSelect={onAcceptanceCriterionSelect}
              onModeChange={setTraceabilityMode}
              selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
            />
          ) : null}
          {activeView === 'analysis' ? (
            <Suspense fallback={<Text size="sm">Loading analysis tools</Text>}>
              <WorkspaceInspectorAnalysisView
                activeSession={activeSession}
                critiqueMutation={critiqueMutation}
                planningMutation={planningMutation}
                selectedAcceptanceCriterionIndex={selectedAcceptanceCriterionIndex}
                specDiffMutation={specDiffMutation}
              />
            </Suspense>
          ) : null}
        </div>
      </section>
    </div>
  );
}

type EvidenceViewProps = {
  activeSession: StartNegotiationResponse | null;
  compileMutation: InspectorActions['compileMutation'];
  onAcceptanceCriterionSelect?: (index: number) => void;
  onSpecViewChange: (view: 'raw' | 'structured') => void;
  selectedAcceptanceCriterionIndex: number | null;
  specView: 'raw' | 'structured';
};

function EvidenceView({
  activeSession,
  compileMutation,
  onAcceptanceCriterionSelect,
  onSpecViewChange,
  selectedAcceptanceCriterionIndex,
  specView,
}: EvidenceViewProps) {
  const selectedRequirement = resolveSelectedRequirement(
    compileMutation.data,
    selectedAcceptanceCriterionIndex,
  );

  return (
    <div className={styles.sectionStack}>
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Typed API handoff
          </Text>
          <div className={styles.codeList}>
            <Mono>/api/start</Mono>
            <Mono>/api/respond</Mono>
            <Mono>/api/compile</Mono>
          </div>
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Selected AC
          </Text>
          <Text as="p" size="sm">
            {selectedAcceptanceCriterionIndex !== null
              ? `AC ${selectedAcceptanceCriterionIndex + 1}`
              : 'Awaiting rail selection'}
          </Text>
        </div>
      </div>
      {!activeSession ? (
        <EmptyState
          title="No evidence yet"
          description="Run the next phase to populate traceability, specs, and generated verification artifacts."
        />
      ) : (
        <div className={styles.sectionStack}>
          <SectionHeader
            title="Spec contract viewer"
            description="Structured requirements stay beside the raw YAML artifact so operators can inspect routing without losing the compiled contract."
            action={
              <Button
                loading={compileMutation.isPending}
                onClick={() => compileMutation.mutate()}
                variant="secondary"
              >
                {compileMutation.data ? 'Refresh compiled spec' : 'Load compiled spec'}
              </Button>
            }
          />
          {compileMutation.isError ? (
            <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
              {resolveErrorMessage(compileMutation.error, 'Unable to compile the current spec.')}
            </Text>
          ) : null}
          {!compileMutation.data ? (
            <EmptyState
              title="Spec not yet compiled"
              description="Compile the current session to inspect immutable requirement IDs, verification routing, and the raw YAML contract."
            />
          ) : (
            <div className={styles.sectionStack}>
              <div aria-label="Spec contract views" className={styles.viewTabs} role="tablist">
                <button
                  aria-selected={specView === 'structured'}
                  className={styles.viewTab}
                  onClick={() => onSpecViewChange('structured')}
                  role="tab"
                  type="button"
                >
                  Structured contract
                </button>
                <button
                  aria-selected={specView === 'raw'}
                  className={styles.viewTab}
                  onClick={() => onSpecViewChange('raw')}
                  role="tab"
                  type="button"
                >
                  Raw YAML
                </button>
              </div>
              {specView === 'structured' ? (
                <StructuredContractView
                  compiledSpec={compileMutation.data}
                  onAcceptanceCriterionSelect={onAcceptanceCriterionSelect}
                  selectedRequirement={selectedRequirement}
                />
              ) : (
                <pre className={styles.rawPayloadPre}>{compileMutation.data.spec_content}</pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StructuredContractView({
  compiledSpec,
  onAcceptanceCriterionSelect,
  selectedRequirement,
}: {
  compiledSpec: CompileSpecResponse;
  onAcceptanceCriterionSelect?: (index: number) => void;
  selectedRequirement: CompiledSpecRequirement | null;
}) {
  if (!compiledSpec.requirements?.length) {
    return (
      <EmptyState
        title="No structured requirements"
        description="The compiled artifact returned raw YAML but no parsed requirements yet."
      />
    );
  }

  const activeRequirement = selectedRequirement ?? compiledSpec.requirements[0] ?? null;

  if (!activeRequirement) {
    return null;
  }

  const verificationRefs = requirementTraceabilityRefs(compiledSpec, activeRequirement);

  return (
    <div className={styles.sectionStack}>
      <div aria-label="Compiled requirements" className={styles.viewTabs} role="tablist">
        {compiledSpec.requirements.map((requirement) => (
          <button
            aria-selected={activeRequirement.id === requirement.id}
            className={styles.viewTab}
            key={requirement.id}
            onClick={() => {
              if (typeof requirement.ac_checkbox === 'number') {
                onAcceptanceCriterionSelect?.(requirement.ac_checkbox);
              }
            }}
            role="tab"
            type="button"
          >
            {requirement.id}
          </button>
        ))}
      </div>
      <article className={styles.reviewItem}>
        <div className={styles.reviewItemHeader}>
          <div>
            <Text as="h3" size="sm" weight="medium">
              {activeRequirement.title ?? activeRequirement.id}
            </Text>
            <Text as="p" size="sm" tone="muted">
              {activeRequirement.ac_text ?? 'Requirement traceability is pending.'}
            </Text>
          </div>
          <div className={styles.inlineCluster}>
            <Badge tone="neutral">{activeRequirement.type ?? 'unknown'}</Badge>
            {typeof activeRequirement.ac_checkbox === 'number' ? (
              <Button
                onClick={() => onAcceptanceCriterionSelect?.(activeRequirement.ac_checkbox ?? 0)}
                variant="ghost"
              >
                Focus AC {activeRequirement.ac_checkbox + 1}
              </Button>
            ) : null}
          </div>
        </div>
        <div className={styles.detailList}>
          <div className={styles.detailRow}>
            <Text as="p" size="xs" tone="muted">
              Interface
            </Text>
            <div className={styles.inlineCluster}>
              <Badge tone="info">{activeRequirement.contract?.interface?.method ?? 'method?'}</Badge>
              <Mono>{activeRequirement.contract?.interface?.path ?? '/unknown'}</Mono>
            </div>
          </div>
          <div className={styles.detailRow}>
            <Text as="p" size="xs" tone="muted">
              Verification routing
            </Text>
            <div className={styles.reviewList}>
              {activeRequirement.verification?.map((route, index) => (
                <article className={styles.reviewItem} key={`${route.skill ?? 'route'}-${index}`}>
                  <div className={styles.reviewItemHeader}>
                    <Badge tone="success">{route.skill ?? 'unrouted'}</Badge>
                    {route.output ? <Mono>{route.output}</Mono> : null}
                  </div>
                  <div className={styles.codeList}>
                    {route.refs?.map((ref) => (
                      <Mono key={ref}>{ref}</Mono>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
          <div className={styles.detailRow}>
            <Text as="p" size="xs" tone="muted">
              Traceability refs
            </Text>
            <div className={styles.reviewList}>
              {verificationRefs.map((ref) => (
                <article className={styles.reviewItem} key={ref.ref}>
                  <div className={styles.reviewItemHeader}>
                    <Mono>{ref.ref}</Mono>
                    <Badge tone="neutral">{ref.verification_type ?? 'ref'}</Badge>
                  </div>
                  <Text as="p" size="sm">
                    {ref.description ?? 'No traceability description provided.'}
                  </Text>
                </article>
              ))}
            </div>
          </div>
        </div>
      </article>
    </div>
  );
}

type ScanViewProps = {
  isLoading: boolean;
  projectRoot: string;
  scanMutation: InspectorActions['scanMutation'];
  scanned: boolean;
  scanSummary: Record<string, unknown> | string | undefined;
  skillCount: number;
};

function ScanView({
  isLoading,
  projectRoot,
  scanMutation,
  scanned,
  scanSummary,
  skillCount,
}: ScanViewProps) {
  const [projectRootInput, setProjectRootInput] = useState(projectRoot || 'dog-service');
  const summaryText = formatScanSummary(scanSummary);

  useEffect(() => {
    if (projectRoot) {
      setProjectRootInput(projectRoot);
    }
  }, [projectRoot]);

  if (isLoading) {
    return <Text size="sm">Loading scan output</Text>;
  }

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Codebase scan"
        description="Run a repository scan from the workspace and keep the resulting summary mounted beside the active phase review."
        action={
          <Button
            loading={scanMutation.isPending}
            onClick={() => scanMutation.mutate(projectRootInput || 'dog-service')}
            variant="secondary"
          >
            Run codebase scan
          </Button>
        }
      />
      <div className={styles.detailList}>
        <div className={styles.detailRow}>
          <Text as="label" htmlFor="scan-project-root" size="xs" tone="muted">
            Project root
          </Text>
          <input
            className={styles.inspectorInput}
            id="scan-project-root"
            onChange={(event) => setProjectRootInput(event.target.value)}
            value={projectRootInput}
          />
        </div>
        <div className={styles.detailRow}>
          <Text as="p" size="xs" tone="muted">
            Scan status
          </Text>
          <div className={styles.inlineCluster}>
            <Badge tone={resolveScanTone(scanMutation.isPending, scanMutation.isError, scanned)}>
              {resolveScanLabel(scanMutation.isPending, scanMutation.isError, scanned)}
            </Badge>
            <Text as="p" size="sm">
              {skillCount} skill descriptors available for routing context
            </Text>
          </div>
        </div>
      </div>
      {scanMutation.isError ? (
        <Text as="p" className={styles.actionMessage} data-state="error" size="sm">
          {resolveErrorMessage(scanMutation.error, 'The scan failed, but existing inspector data stays available.')}
        </Text>
      ) : null}
      {summaryText ? (
        <pre className={styles.rawPayloadPre}>{summaryText}</pre>
      ) : (
        <EmptyState
          title="Scan not started"
          description="Launch a scan to persist the latest repository summary in the inspector."
        />
      )}
    </div>
  );
}

type TraceabilityViewProps = {
  activeSession: StartNegotiationResponse | null;
  mode: 'browser' | 'matrix';
  onAcceptanceCriterionSelect?: (index: number) => void;
  onModeChange: (mode: 'browser' | 'matrix') => void;
  selectedAcceptanceCriterionIndex: number | null;
};

function TraceabilityView({
  activeSession,
  mode,
  onAcceptanceCriterionSelect,
  onModeChange,
  selectedAcceptanceCriterionIndex,
}: TraceabilityViewProps) {
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const traceabilityItems = useDeferredValue(buildTraceabilityItems(activeSession));

  if (!traceabilityItems.length) {
    return (
      <EmptyState
        title="Traceability will populate after synthesis"
        description="Complete more of the negotiation loop to browse per-AC evidence chains and matrix scanning views."
      />
    );
  }

  const activeItem =
    traceabilityItems.find((item) => item.acIndex === selectedAcceptanceCriterionIndex) ??
    traceabilityItems[0];

  async function handleCopyRefs(item: InspectorTraceabilityItem) {
    const text = item.verificationRefs.map((ref) => ref.ref).join('\n');

    if (!text || !navigator.clipboard?.writeText) {
      return;
    }

    await navigator.clipboard.writeText(text);
    setCopyStatus(`Copied ${item.requirementId} refs`);
  }

  return (
    <div className={styles.sectionStack}>
      <SectionHeader
        title="Traceability browser"
        description="Inspect each acceptance criterion as a linked chain of negotiated evidence without displacing the active phase workspace."
      />
      <div aria-label="Traceability modes" className={styles.viewTabs} role="tablist">
        <button
          aria-selected={mode === 'browser'}
          className={styles.viewTab}
          onClick={() => onModeChange('browser')}
          role="tab"
          type="button"
        >
          Per-AC browser
        </button>
        <button
          aria-selected={mode === 'matrix'}
          className={styles.viewTab}
          onClick={() => onModeChange('matrix')}
          role="tab"
          type="button"
        >
          Matrix view
        </button>
      </div>
      {copyStatus ? (
        <Text as="p" className={styles.actionMessage} data-state="success" size="sm">
          {copyStatus}
        </Text>
      ) : null}
      {mode === 'matrix' ? (
        <div className={styles.matrix}>
          <div className={styles.matrixHeader}>
            <Text as="p" size="xs" tone="muted">
              Acceptance criterion
            </Text>
            <Text as="p" size="xs" tone="muted">
              Classification & requirement
            </Text>
            <Text as="p" size="xs" tone="muted">
              Verification refs
            </Text>
          </div>
          {traceabilityItems.map((item) => (
            <button
              className={styles.matrixRowButton}
              key={item.requirementId}
              onClick={() => onAcceptanceCriterionSelect?.(item.acIndex)}
              type="button"
            >
              <Text as="p" size="sm">
                AC {item.acIndex + 1}: {item.acText}
              </Text>
              <Text as="p" size="sm">
                {item.classification} / {item.requirementId}
              </Text>
              <Text as="p" size="sm">
                {item.verificationRefs.length} refs
              </Text>
            </button>
          ))}
        </div>
      ) : (
        <div className={styles.sectionStack}>
          <div aria-label="Acceptance criteria browser" className={styles.viewTabs} role="tablist">
            {traceabilityItems.map((item) => (
              <button
                aria-selected={activeItem.acIndex === item.acIndex}
                className={styles.viewTab}
                key={item.requirementId}
                onClick={() => onAcceptanceCriterionSelect?.(item.acIndex)}
                role="tab"
                type="button"
              >
                AC {item.acIndex + 1}
              </button>
            ))}
          </div>
          <article className={styles.reviewItem}>
            <div className={styles.reviewItemHeader}>
              <div>
                <Text as="h3" size="sm" weight="medium">
                  {activeItem.requirementId}
                </Text>
                <Text as="p" size="sm" tone="muted">
                  {activeItem.acText}
                </Text>
              </div>
              <div className={styles.inlineCluster}>
                <Badge tone="info">{activeItem.classification}</Badge>
                <Button onClick={() => void handleCopyRefs(activeItem)} variant="ghost">
                  Copy refs
                </Button>
              </div>
            </div>
            <div className={styles.detailList}>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Preconditions
                </Text>
                <div className={styles.reviewList}>
                  {activeItem.preconditions?.map((precondition) => (
                    <div className={styles.reviewItem} key={precondition.id}>
                      <div className={styles.reviewItemHeader}>
                        <Mono>{precondition.id}</Mono>
                        <Badge tone="neutral">{precondition.category ?? 'precondition'}</Badge>
                      </div>
                      <Text as="p" size="sm">
                        {precondition.description ?? precondition.formal ?? 'No description'}
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Postconditions
                </Text>
                <div className={styles.reviewList}>
                  {activeItem.postconditions?.map((postcondition, index) => (
                    <div className={styles.reviewItem} key={`${postcondition.status ?? 'success'}-${index}`}>
                      <div className={styles.reviewItemHeader}>
                        <Badge tone="success">
                          {postcondition.status ? `HTTP ${postcondition.status}` : 'Success'}
                        </Badge>
                        {postcondition.content_type ? <Mono>{postcondition.content_type}</Mono> : null}
                      </div>
                      <Text as="p" size="sm">
                        {postcondition.schema ? 'Structured response schema captured for this AC.' : 'No response schema captured.'}
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Failure modes
                </Text>
                <div className={styles.reviewList}>
                  {activeItem.failureModes.map((failureMode) => (
                    <div className={styles.reviewItem} key={failureMode.id}>
                      <div className={styles.reviewItemHeader}>
                        <Mono>{failureMode.id}</Mono>
                        {failureMode.status ? <Badge tone="warning">HTTP {failureMode.status}</Badge> : null}
                      </div>
                      <Text as="p" size="sm">
                        {failureMode.description ?? 'No failure description'}
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
              <div className={styles.detailRow}>
                <Text as="p" size="xs" tone="muted">
                  Verification refs
                </Text>
                <div className={styles.reviewList}>
                  {activeItem.verificationRefs.map((ref) => (
                    <div className={styles.reviewItem} key={ref.ref}>
                      <div className={styles.reviewItemHeader}>
                        <Mono>{ref.ref}</Mono>
                        <Badge tone="neutral">{ref.verification_type ?? 'ref'}</Badge>
                      </div>
                      <Text as="p" size="sm">
                        {ref.description ?? 'No traceability description provided.'}
                      </Text>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </article>
        </div>
      )}
    </div>
  );
}

function resolveSelectedRequirement(
  compiledSpec: CompileSpecResponse | undefined,
  selectedAcceptanceCriterionIndex: number | null,
) {
  if (!compiledSpec?.requirements?.length) {
    return null;
  }

  if (selectedAcceptanceCriterionIndex !== null) {
    return requirementForAcceptanceCriterion(compiledSpec, selectedAcceptanceCriterionIndex);
  }

  return compiledSpec.requirements[0] ?? null;
}

function resolveErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

function resolveScanLabel(isPending: boolean, isError: boolean, scanned: boolean) {
  if (isPending) {
    return 'Scanning';
  }

  if (isError) {
    return 'Failed';
  }

  return scanned ? 'Indexed' : 'Pending';
}

function resolveScanTone(
  isPending: boolean,
  isError: boolean,
  scanned: boolean,
): 'error' | 'success' | 'warning' {
  if (isPending) {
    return 'warning';
  }

  if (isError) {
    return 'error';
  }

  return scanned ? 'success' : 'warning';
}
