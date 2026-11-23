import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-paper-100 p-phi-5">
          <div className="w-full max-w-phi-modal-sm rounded-phi-lg border border-[rgba(25,24,22,0.1)] bg-paper-50 p-phi-5 shadow-card">
            <div className="mb-phi-4 inline-flex h-phi-6 w-phi-6 items-center justify-center rounded-phi-md bg-semantic-negativeBg text-semantic-negative">
              <AlertTriangle className="h-5 w-5" strokeWidth={1.5} />
            </div>

            <h1 className="font-serif text-phi-lg font-normal text-ink-primary">
              Something went wrong
            </h1>
            <p className="mt-phi-2 text-phi-sm leading-phi text-ink-secondary">
              The application encountered an unexpected error. Refresh the page or try again.
            </p>

            {this.state.error && (
              <div className="mt-phi-5 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-200/70 p-phi-4 text-left">
                <p className="text-phi-xs font-medium text-semantic-negative">Error details</p>
                <p className="mt-phi-1 break-all font-mono text-phi-xs text-ink-secondary">
                  {this.state.error.message}
                </p>
              </div>
            )}

            <div className="mt-phi-5 flex items-center gap-phi-3">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className="btn-primary h-phi-ctrl flex-1"
              >
                Refresh page
              </button>
              <button
                type="button"
                onClick={() => {
                  this.setState({ hasError: false, error: undefined, errorInfo: undefined });
                }}
                className="btn-secondary h-phi-ctrl"
              >
                Try again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
