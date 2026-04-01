import type { ReactNode } from "react";

import styles from "@/components/layout/Rail.module.css";

type RailProps = {
  ariaLabel: string;
  label: string;
  title: string;
  description?: string;
  children: ReactNode;
};

export function Rail({ ariaLabel, label, title, description, children }: RailProps) {
  return (
    <section className={styles.rail} aria-label={ariaLabel}>
      <header className={styles.header}>
        <span className={styles.label}>{label}</span>
        <h2 className={styles.title}>{title}</h2>
        {description ? <p className={styles.description}>{description}</p> : null}
      </header>
      {children}
    </section>
  );
}
