import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/**
 * Catches render-time errors anywhere in the subtree and shows a recoverable
 * fallback instead of a blank page. React Query handles async errors, but
 * synchronous render throws (e.g. malformed data in the d3 graph) need this.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ error: null });
    window.location.reload();
  };

  render() {
    if (this.state.error) {
      return (
        <div role="alert" style={{ padding: '2rem', maxWidth: 560, margin: '4rem auto', textAlign: 'center' }}>
          <h1 style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>Something went wrong</h1>
          <p style={{ color: 'var(--text-muted, #666)', marginBottom: '1.5rem' }}>
            An unexpected error occurred while rendering this view. Your data is safe.
          </p>
          <button className="btn btn--primary" onClick={this.handleReload}>
            Reload the app
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
