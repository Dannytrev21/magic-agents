import { useState, useTransition } from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { type StartNegotiationResponse } from '@/lib/api/types';
import { SessionBootstrap } from '@/features/session/SessionBootstrap';
import { WorkspaceInspector } from '@/features/workspace/WorkspaceInspector';
import { WorkspaceOverview } from '@/features/workspace/WorkspaceOverview';

export function OperatorWorkspacePage() {
  const [activeSession, setActiveSession] = useState<StartNegotiationResponse | null>(null);
  const [shellStatus, setShellStatus] = useState('Foundation ready');
  const [isTransitionPending, startShellTransition] = useTransition();

  function handleSessionStarted(session: StartNegotiationResponse) {
    startShellTransition(() => {
      setActiveSession(session);
      setShellStatus('Session active');
    });
  }

  return (
    <AppShell
      centerPane={
        <WorkspaceOverview activeSession={activeSession} isTransitionPending={isTransitionPending} />
      }
      leftRail={<SessionBootstrap onSessionStarted={handleSessionStarted} />}
      phaseLabel={activeSession?.phase_title ?? 'Foundation bootstrap'}
      rightRail={<WorkspaceInspector activeSession={activeSession} />}
      sessionKey={activeSession?.jira_key}
      statusLabel={shellStatus}
    />
  );
}
