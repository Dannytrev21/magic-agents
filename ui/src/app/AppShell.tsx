import type { ReactNode } from "react";

import { Badge } from "@/components/primitives/Badge";

import styles from "@/app/AppShell.module.css";

type AppShellProps = {
  sessionLabel: string;
  phaseLabel: string;
  leftRail: ReactNode;
  centerPane: ReactNode;
  rightPane: ReactNode;
};

export function AppShell({
  sessionLabel,
  phaseLabel,
  leftRail,
  centerPane,
  rightPane,
}: AppShellProps) {
  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.topBar}>
          <div className={styles.identity}>
            <span className={styles.product}>Magic Agents</span>
            <h1 className={styles.heading}>Operator workspace</h1>
          </div>
          <div className={styles.status}>
            <Badge tone="muted">{sessionLabel}</Badge>
            <Badge>{phaseLabel}</Badge>
          </div>
        </header>
        <div className={styles.workspace}>
          <aside aria-label="Story intake">{leftRail}</aside>
          <main className={styles.center}>{centerPane}</main>
          <aside aria-label="Evidence inspector">{rightPane}</aside>
        </div>
      </div>
    </div>
  );
}
