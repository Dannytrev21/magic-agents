import { useState, type ReactNode } from 'react';
import styles from '@/features/workspace/workspace.module.css';

type WorkspaceDisclosureProps = {
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  defaultOpen?: boolean;
  meta?: ReactNode;
  title: ReactNode;
};

export function WorkspaceDisclosure({
  children,
  className,
  contentClassName,
  defaultOpen = false,
  meta,
  title,
}: WorkspaceDisclosureProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <details
      className={[styles.sectionDisclosure, className].filter(Boolean).join(' ')}
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      open={isOpen}
    >
      <summary className={styles.sectionDisclosureSummary}>
        <span>{title}</span>
        {meta ? <span className={styles.sectionDisclosureMeta}>{meta}</span> : null}
      </summary>
      <div className={[styles.sectionDisclosureContent, contentClassName].filter(Boolean).join(' ')}>
        {children}
      </div>
    </details>
  );
}
