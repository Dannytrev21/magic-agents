import clsx from 'clsx';
import type { HTMLAttributes } from 'react';
import styles from '@/components/primitives/primitives.module.css';

export function Mono({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <code {...props} className={clsx(styles.mono, className)}>
      {children}
    </code>
  );
}
