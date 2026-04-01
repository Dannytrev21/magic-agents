import clsx from 'clsx';
import type { HTMLAttributes } from 'react';
import styles from '@/components/primitives/primitives.module.css';

export function Divider({ className, ...props }: HTMLAttributes<HTMLHRElement>) {
  return <hr {...props} className={clsx(styles.divider, className)} />;
}
