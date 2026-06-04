import React from 'react';
import RetryPanel from './RetryPanel';
import { normalizeError } from '../lib/errors';

type ErrorBoundaryState = {
  error: Error | null;
};

class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Unhandled UI error', error, info);
  }

  handleReset = () => {
    this.setState({ error: null });
  };

  render() {
    if (this.state.error) {
      const appError = normalizeError(this.state.error, 'The interface could not be rendered.');
      return (
        <main className="app-main app-main-fallback">
          <RetryPanel
            title="We recovered the app shell"
            message={`${appError.message} You can retry the current view without losing your session.`}
            onRetry={this.handleReset}
            actionLabel="Try again"
          />
        </main>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
