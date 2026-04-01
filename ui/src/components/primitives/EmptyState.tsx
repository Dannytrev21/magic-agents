import type { ReactNode } from 'react';
import styles from '@/components/primitives/primitives.module.css';
import { Text } from '@/components/primitives/Text';

type EmptyStateProps = {
  action?: ReactNode;
  description: ReactNode;
  title: ReactNode;
};

export function EmptyState({ action, description, title }: EmptyStateProps) {
  return (
    <div className={styles.emptyState}>
      <div className={styles.emptyStateBody}>
        <Text as="h2" size="lg" weight="semibold">
          {title}
        </Text>
        <Text as="p" size="sm" tone="muted">
          {description}
        </Text>
      </div>
      {action}
    </div>
  );
}
