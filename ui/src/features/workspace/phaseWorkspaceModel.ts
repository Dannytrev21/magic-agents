import { useCallback, useLayoutEffect } from 'react';
import { useEventStoreController } from '@/lib/api/eventStore';
import { useSSE } from '@/lib/api/useSSE';

export function usePhaseWorkspaceModel(sessionId: string | null) {
  const { clear, clearForSession, dispatch } = useEventStoreController();
  const handleEvent = useCallback(
    (event: Record<string, unknown> & { type: string }) => {
      dispatch(event);
    },
    [dispatch],
  );
  const { status: connectionStatus, lastEvent } = useSSE(sessionId, {
    onEvent: handleEvent,
  });

  useLayoutEffect(() => {
    if (!sessionId) {
      clear();
      return;
    }

    clearForSession(sessionId);
  }, [clear, clearForSession, sessionId]);

  return {
    connectionStatus,
    lastEvent,
  };
}
