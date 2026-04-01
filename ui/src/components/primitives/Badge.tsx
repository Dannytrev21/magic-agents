import clsx from 'clsx';
import type { HTMLAttributes } from 'react';
import styles from '@/components/primitives/primitives.module.css';

type BadgeTone = 'info' | 'success' | 'warning' | 'error' | 'neutral';

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
};

function toneClassName(tone: BadgeTone) {
  switch (tone) {
    case 'success':
      return styles.badgeSuccess;
    case 'warning':
      return styles.badgeWarning;
    case 'error':
      return styles.badgeError;
    case 'neutral':
      return styles.badgeNeutral;
    default:
      return styles.badgeInfo;
  }
}

export function Badge({ children, className, tone = 'info', ...props }: BadgeProps) {
  return (
    <span {...props} className={clsx(styles.badge, toneClassName(tone), className)}>
      {children}
    </span>
  );
}
