import type { PropsWithChildren } from "react";

import styles from "@/components/layout/WorkspaceSection.module.css";

export function WorkspaceSection({ children }: PropsWithChildren) {
  return <section className={styles.section}>{children}</section>;
}
