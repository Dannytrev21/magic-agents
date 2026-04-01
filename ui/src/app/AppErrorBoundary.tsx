import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from '@/components/primitives/Button';
import { Panel } from '@/components/primitives/Panel';
import { Text } from '@/components/primitives/Text';

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  hasError: boolean;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  public constructor(props: AppErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  public static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  public componentDidCatch(error: Error, info: ErrorInfo) {
    void error;
    void info;
  }

  private reset = () => {
    this.setState({ hasError: false });
  };

  public render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main
        style={{
          minHeight: '100vh',
          display: 'grid',
          placeItems: 'center',
          padding: 'var(--space-6)',
          background: 'var(--color-bg)',
        }}
      >
        <Panel aria-labelledby="workspace-unavailable-title" tone="subtle">
          <div style={{ display: 'grid', gap: 'var(--space-3)', maxWidth: '32rem' }}>
            <Text as="p" size="sm" tone="signal">
              Operator workspace
            </Text>
            <Text as="h1" size="xl" weight="semibold" id="workspace-unavailable-title">
              Workspace unavailable
            </Text>
            <Text as="p" size="base" tone="muted">
              The shell caught a rendering failure before it could affect the active session state.
            </Text>
            <Button onClick={this.reset}>Retry shell render</Button>
          </div>
        </Panel>
      </main>
    );
  }
}
