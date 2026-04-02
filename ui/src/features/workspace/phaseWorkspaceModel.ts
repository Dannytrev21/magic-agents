import { useCallback, useLayoutEffect } from 'react';
import { useEventStoreController } from '@/lib/api/eventStore';
import { useSSE, type SSEConnectionStatus } from '@/lib/api/useSSE';

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
    connectionLabel: formatConnectionLabel(connectionStatus, sessionId),
    connectionStatus,
    lastEvent,
  };
}

function formatConnectionLabel(status: SSEConnectionStatus, sessionId: string | null) {
  if (!sessionId) {
    return 'Live updates idle';
  }

  switch (status) {
    case 'connected':
      return 'Live updates connected';
    case 'reconnecting':
      return 'Reconnecting live updates';
    case 'disconnected':
      return 'Live updates disconnected';
    default:
      return 'Connecting live updates';
  }
}
