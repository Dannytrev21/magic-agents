import type { ErrorInfo, ReactNode } from "react";
import { Component } from "react";

import styles from "@/app/AppErrorBoundary.module.css";
import { Button } from "@/components/primitives/Button";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  hasError: boolean;
};

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(_error: Error, _errorInfo: ErrorInfo) {}

  private handleReset = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className={styles.fallback}>
          <section className={styles.panel}>
            <h1 className={styles.title}>Workspace unavailable</h1>
            <p className={styles.message}>
              The shell caught a top-level rendering failure and kept the workspace in a controlled
              state.
            </p>
            <Button variant="secondary" onClick={this.handleReset}>
              Retry shell
            </Button>
          </section>
        </div>
      );
    }

    return this.props.children;
  }
}
