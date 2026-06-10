/**
 * Game Error Boundary
 * Specialized error boundary for game screens with recovery options
 */

import React, { Component, ReactNode } from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from '@components/atoms/Text';
import { Button } from '@components/atoms/Button';
import { theme } from '@config/theme';

interface Props {
  children: ReactNode;
  onGameReset?: () => void;
  onNavigateHome?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class GameErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    if (__DEV__) {
      console.error('Game Error Boundary caught an error:', error, errorInfo);
    }

    // TODO: Log to analytics/crash reporting
    // Example: logGameError(error, errorInfo);
  }

  handleRestart = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });

    if (this.props.onGameReset) {
      this.props.onGameReset();
    }
  };

  handleGoHome = (): void => {
    this.setState({
      hasError: false,
      error: null,
    });

    if (this.props.onNavigateHome) {
      this.props.onNavigateHome();
    }
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <View style={styles.content}>
            <Text variant="h1" style={styles.icon}>
              ⚠️
            </Text>
            <Text variant="h2" style={styles.title}>
              Game Error
            </Text>
            <Text variant="body" style={styles.message}>
              The game encountered an error and needs to restart.
              Don't worry, your progress has been saved!
            </Text>
            {__DEV__ && this.state.error && (
              <View style={styles.errorDetails}>
                <Text variant="caption" style={styles.errorText}>
                  {this.state.error.toString()}
                </Text>
                {this.state.error.stack && (
                  <Text variant="caption" style={styles.errorStack}>
                    {this.state.error.stack.split('\n').slice(0, 3).join('\n')}
                  </Text>
                )}
              </View>
            )}
            <View style={styles.buttons}>
              <Button
                title="Restart Game"
                variant="primary"
                onPress={this.handleRestart}
                style={styles.button}
              />
              <Button
                title="Go to Home"
                variant="outline"
                onPress={this.handleGoHome}
                style={styles.button}
              />
            </View>
          </View>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.onyxBlack,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  content: {
    maxWidth: 400,
    alignItems: 'center',
  },
  icon: {
    fontSize: 64,
    marginBottom: 16,
  },
  title: {
    color: theme.colors.white,
    textAlign: 'center',
    marginBottom: 16,
  },
  message: {
    color: theme.colors.fogText,
    textAlign: 'center',
    marginBottom: 24,
    lineHeight: 24,
  },
  errorDetails: {
    backgroundColor: theme.colors.darkGray,
    padding: 12,
    borderRadius: 8,
    marginBottom: 24,
    width: '100%',
  },
  errorText: {
    color: theme.colors.error,
    fontFamily: 'monospace',
    fontSize: 12,
    marginBottom: 8,
  },
  errorStack: {
    color: theme.colors.mediumGray,
    fontFamily: 'monospace',
    fontSize: 10,
  },
  buttons: {
    width: '100%',
    gap: 12,
  },
  button: {
    width: '100%',
  },
});
