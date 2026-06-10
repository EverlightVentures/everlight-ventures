import { Component } from 'react'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.state = { hasError: true, error, errorInfo }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          background: 'linear-gradient(to bottom, #0a0a0a, #1a1a1a)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            maxWidth: '800px',
            background: '#1a1a1a',
            border: '1px solid #ef4444',
            borderRadius: '12px',
            padding: '32px',
            color: 'white'
          }}>
            <h1 style={{ color: '#ef4444', fontSize: '24px', fontWeight: 'bold', marginBottom: '16px' }}>
              ⚠️ Something went wrong
            </h1>
            <p style={{ color: '#9ca3af', marginBottom: '24px' }}>
              The application encountered an error. Details below:
            </p>
            <div style={{
              background: '#0a0a0a',
              border: '1px solid #2d2d2d',
              borderRadius: '8px',
              padding: '16px',
              fontFamily: 'monospace',
              fontSize: '14px',
              overflow: 'auto'
            }}>
              <p style={{ color: '#ef4444', marginBottom: '12px' }}>
                <strong>Error:</strong> {this.state.error?.toString()}
              </p>
              <pre style={{ color: '#9ca3af', whiteSpace: 'pre-wrap', margin: 0 }}>
                {this.state.errorInfo?.componentStack}
              </pre>
            </div>
            <button
              onClick={() => window.location.reload()}
              style={{
                marginTop: '24px',
                padding: '12px 24px',
                background: '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                fontSize: '16px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
