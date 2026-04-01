import { useEffect, useRef, useState } from 'react';
import { Badge } from '@/components/primitives/Badge';
import { Text } from '@/components/primitives/Text';
import type { WorkspaceTranscriptEntry } from '@/features/workspace/phaseReviewModel';
import styles from '@/features/workspace/workspace.module.css';

type PhaseTranscriptProps = {
  entries: WorkspaceTranscriptEntry[];
};

export function PhaseTranscript({ entries }: PhaseTranscriptProps) {
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);

  useEffect(() => {
    const node = transcriptRef.current;
    if (!node || !isPinnedToBottom) {
      return;
    }

    if (typeof node.scrollTo === 'function') {
      node.scrollTo({ top: node.scrollHeight });
      return;
    }

    node.scrollTop = node.scrollHeight;
  }, [entries, isPinnedToBottom]);

  function handleScroll() {
    const node = transcriptRef.current;
    if (!node) {
      return;
    }

    const remainingDistance = node.scrollHeight - node.clientHeight - node.scrollTop;
    setIsPinnedToBottom(remainingDistance <= 24);
  }

  return (
    <div
      aria-label="Phase transcript"
      className={styles.transcript}
      onScroll={handleScroll}
      ref={transcriptRef}
      role="log"
    >
      {entries.length ? (
        entries.map((entry) => (
          <article className={styles.transcriptEntry} data-role={entry.role} key={entry.id}>
            <div className={styles.transcriptMeta}>
              <Badge tone={badgeToneForRole(entry.role)}>{entry.label}</Badge>
              {entry.timestamp ? (
                <Text as="p" size="xs" tone="muted">
                  {entry.timestamp}
                </Text>
              ) : null}
            </div>
            <Text as="p" size="sm">
              {entry.content}
            </Text>
          </article>
        ))
      ) : (
        <Text as="p" size="sm" tone="muted">
          Transcript activity will appear here once the active phase begins emitting history.
        </Text>
      )}
    </div>
  );
}

function badgeToneForRole(role: WorkspaceTranscriptEntry['role']) {
  switch (role) {
    case 'operator':
      return 'warning';
    case 'model':
      return 'info';
    default:
      return 'neutral';
  }
}
