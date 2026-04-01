import clsx from 'clsx';
import type { HTMLAttributes } from 'react';
import styles from '@/components/primitives/primitives.module.css';

type PanelProps = HTMLAttributes<HTMLElement> & {
  tone?: 'default' | 'subtle';
};

export function Panel({ children, className, tone = 'default', ...props }: PanelProps) {
  return (
    <section
      {...props}
      className={clsx(styles.panel, tone === 'subtle' ? styles.panelSubtle : undefined, className)}
    >
      {children}
    </section>
  );
}
