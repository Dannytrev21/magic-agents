import type { ReactNode } from 'react';
import styles from '@/components/primitives/primitives.module.css';
import { Text } from '@/components/primitives/Text';

type SectionHeaderProps = {
  action?: ReactNode;
  description?: ReactNode;
  title: ReactNode;
};

export function SectionHeader({ action, description, title }: SectionHeaderProps) {
  return (
    <div className={styles.sectionHeader}>
      <div className={styles.sectionHeaderRow}>
        <Text as="h2" size="sm" weight="semibold">
          {title}
        </Text>
        {action}
      </div>
      {description ? (
        <Text as="p" className={styles.sectionHeaderDescription} size="sm">
          {description}
        </Text>
      ) : null}
    </div>
  );
}
