import type { PropsWithChildren, ReactNode } from "react";

import styles from "@/components/layout/ArtifactPanel.module.css";

type ArtifactPanelProps = PropsWithChildren<{
  title: ReactNode;
}>;

export function ArtifactPanel({ title, children }: ArtifactPanelProps) {
  return (
    <section className={styles.panel}>
      <strong>{title}</strong>
      {children}
    </section>
  );
}
