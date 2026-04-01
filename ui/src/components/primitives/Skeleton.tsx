import clsx from 'clsx';
import type { HTMLAttributes } from 'react';
import styles from '@/components/primitives/primitives.module.css';

export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={clsx(styles.skeleton, className)} />;
}
