import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Generic rendering-failure boundary. Presentation only — no knowledge of
 * what it wraps. Scoped around route content (see AppLayout) so a crash in
 * one page's render doesn't take down the header/nav chrome with it.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled rendering error", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary" role="alert">
          <h2>Something went wrong</h2>
          <p>This page failed to render. Try navigating elsewhere or reloading.</p>
        </div>
      );
    }

    return this.props.children;
  }
}
