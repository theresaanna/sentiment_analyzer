import React, { Component } from 'react';

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null,
      errorInfo: null,
      errorCount: 0
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to error reporting service in production
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState(prevState => ({
      error,
      errorInfo,
      errorCount: prevState.errorCount + 1
    }));

    // In production, send to error tracking service
    if (process.env.NODE_ENV === 'production' && window.Sentry) {
      window.Sentry.captureException(error, {
        contexts: {
          react: {
            componentStack: errorInfo.componentStack
          }
        }
      });
    }
  }

  handleReset = () => {
    this.setState({ 
      hasError: false, 
      error: null, 
      errorInfo: null 
    });
    
    // Optional: reload the page if errors persist
    if (this.state.errorCount > 3) {
      window.location.reload();
    }
  };

  render() {
    if (this.state.hasError) {
      // Custom error fallback UI
      return (
        <div className="error-boundary-fallback">
          <div className="container">
            <div className="row justify-content-center">
              <div className="col-md-8">
                <div className="card shadow-lg border-0 mt-5">
                  <div className="card-body p-5 text-center">
                    <div className="mb-4">
                      <i className="fas fa-exclamation-triangle text-warning" style={{ fontSize: '4rem' }}></i>
                    </div>
                    <h2 className="mb-3">Oops! Something went wrong</h2>
                    <p className="text-muted mb-4">
                      We encountered an unexpected error. The application may still work if you try again.
                    </p>
                    
                    {process.env.NODE_ENV !== 'production' && this.state.error && (
                      <details className="text-left mb-4">
                        <summary className="cursor-pointer text-primary">
                          Show technical details
                        </summary>
                        <div className="mt-3 p-3 bg-light rounded">
                          <pre className="mb-0 text-danger">
                            {this.state.error.toString()}
                          </pre>
                          {this.state.errorInfo && (
                            <pre className="mb-0 mt-2 text-secondary small">
                              {this.state.errorInfo.componentStack}
                            </pre>
                          )}
                        </div>
                      </details>
                    )}
                    
                    <div className="d-flex gap-3 justify-content-center">
                      <button 
                        className="btn btn-primary btn-lg"
                        onClick={this.handleReset}
                      >
                        <i className="fas fa-redo mr-2"></i>
                        Try Again
                      </button>
                      <button 
                        className="btn btn-outline-secondary btn-lg"
                        onClick={() => window.location.href = '/'}
                      >
                        <i className="fas fa-home mr-2"></i>
                        Go Home
                      </button>
                    </div>
                    
                    {this.state.errorCount > 1 && (
                      <div className="alert alert-info mt-4">
                        <small>
                          Error occurred {this.state.errorCount} times. 
                          If the problem persists, please contact support.
                        </small>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;