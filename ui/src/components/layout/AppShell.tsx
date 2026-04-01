import type { ReactNode } from 'react';
import styles from '@/components/layout/AppShell.module.css';
import { Badge } from '@/components/primitives/Badge';
import { Mono } from '@/components/primitives/Mono';
import { Panel } from '@/components/primitives/Panel';
import { Text } from '@/components/primitives/Text';

type AppShellProps = {
  leftRail: ReactNode;
  centerPane: ReactNode;
  rightRail: ReactNode;
  phaseLabel: string;
  sessionKey?: string | null;
  statusLabel: string;
};

export function AppShell({
  leftRail,
  centerPane,
  rightRail,
  phaseLabel,
  sessionKey,
  statusLabel,
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <a className={styles.skipLink} href="#workspace-main">
        Skip to active workspace
      </a>
      <header className={styles.topBar}>
        <div className={styles.brandBlock}>
          <Text as="p" size="xs" tone="muted" className={styles.kicker}>
            Acceptance criteria to proof
          </Text>
          <div className={styles.brandName}>
            <Text as="h1" size="lg" weight="semibold">
              Magic Agents
            </Text>
            <Badge tone="neutral">Operator workspace</Badge>
          </div>
        </div>
        <div className={styles.headerMeta}>
          <div className={styles.metaColumn}>
            <Text as="p" size="xs" tone="muted">
              Active phase
            </Text>
            <Text as="p" size="sm" weight="medium">
              {phaseLabel}
            </Text>
          </div>
          <div className={styles.metaColumn}>
            <Text as="p" size="xs" tone="muted">
              Session
            </Text>
            {sessionKey ? <Mono>{sessionKey}</Mono> : <Text size="sm">No active session</Text>}
          </div>
          <Badge tone="info">{statusLabel}</Badge>
        </div>
      </header>
      <div className={styles.workspaceGrid}>
        <aside aria-label="Story intake" className={styles.pane} role="complementary">
          <Panel className={styles.paneSurface}>{leftRail}</Panel>
        </aside>
        <main className={`${styles.pane} ${styles.mainPane}`} id="workspace-main">
          <Panel className={styles.paneSurface}>{centerPane}</Panel>
        </main>
        <aside
          aria-label="Evidence inspector"
          className={`${styles.pane} ${styles.inspectorPane ?? ''}`}
          role="complementary"
        >
          <Panel className={styles.paneSurface}>{rightRail}</Panel>
        </aside>
      </div>
    </div>
  );
}
