/**
 * ChecklistScreen - Checklist with 5-minute sprint timer
 */

import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { GradientBackground, Button, Text, Icon, Card } from '@components/atoms';
import { Checklist } from '@components/organisms';
import { useGameStore } from '@store';
import type { HomeStackParamList } from '@navigation/types';
import { theme } from '@config/theme';
import { GAME_CONFIG } from '@config/constants';

type ChecklistScreenNavigationProp = NativeStackNavigationProp<
  HomeStackParamList,
  'Checklist'
>;
type ChecklistScreenRouteProp = RouteProp<HomeStackParamList, 'Checklist'>;

export const ChecklistScreen = () => {
  const navigation = useNavigation<ChecklistScreenNavigationProp>();
  const route = useRoute<ChecklistScreenRouteProp>();
  const { sessionId } = route.params;

  const { session } = useGameStore();

  const [timerRunning, setTimerRunning] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState(GAME_CONFIG.sprintTimerDuration);
  const [allComplete, setAllComplete] = useState(false);

  useEffect(() => {
    let interval: NodeJS.Timeout;

    if (timerRunning && timeRemaining > 0) {
      interval = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            setTimerRunning(false);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [timerRunning, timeRemaining]);

  if (!session || session.id !== sessionId) {
    return (
      <GradientBackground variant="dark">
        <View style={styles.container}>
          <Text variant="h2">Session not found</Text>
        </View>
      </GradientBackground>
    );
  }

  const handleStartTimer = () => {
    setTimerRunning(true);
  };

  const handlePauseTimer = () => {
    setTimerRunning(false);
  };

  const handleResetTimer = () => {
    setTimerRunning(false);
    setTimeRemaining(GAME_CONFIG.sprintTimerDuration);
  };

  const handleAllComplete = () => {
    setAllComplete(true);
  };

  const handleFinish = () => {
    navigation.navigate('Home');
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <GradientBackground variant="dark">
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <Text variant="displayMedium" align="center">
              Your Checklist
            </Text>
            <Text variant="body" color={theme.colors.fogText} align="center">
              Complete these tasks in a 5-minute sprint
            </Text>
          </View>

          {/* 5-Minute Sprint Timer */}
          <Card variant="elevated" padding="lg" style={styles.timerCard}>
            <View style={styles.timerContent}>
              <Icon
                name="clock"
                size={32}
                color={
                  timeRemaining === 0
                    ? theme.colors.error
                    : timerRunning
                      ? theme.colors.success
                      : theme.colors.fogText
                }
              />
              <Text
                variant="timer"
                color={
                  timeRemaining === 0
                    ? theme.colors.error
                    : timeRemaining <= 60
                      ? theme.colors.warning
                      : theme.colors.white
                }
                style={{ marginLeft: theme.spacing.md }}
              >
                {formatTime(timeRemaining)}
              </Text>
            </View>

            <View style={styles.timerButtons}>
              {!timerRunning ? (
                <Button
                  title={timeRemaining === GAME_CONFIG.sprintTimerDuration ? 'Start Sprint' : 'Resume'}
                  variant="gold"
                  size="medium"
                  onPress={handleStartTimer}
                  style={{ flex: 1, marginRight: theme.spacing.sm }}
                />
              ) : (
                <Button
                  title="Pause"
                  variant="secondary"
                  size="medium"
                  onPress={handlePauseTimer}
                  style={{ flex: 1, marginRight: theme.spacing.sm }}
                />
              )}

              <Button
                title="Reset"
                variant="outline"
                size="medium"
                onPress={handleResetTimer}
                style={{ flex: 1 }}
              />
            </View>
          </Card>

          {/* Checklist */}
          <View style={styles.checklistContainer}>
            <Checklist
              items={session.checklist}
              onAllComplete={handleAllComplete}
            />
          </View>

          {/* Finish Button */}
          {allComplete && (
            <View style={styles.footer}>
              <Button
                title="Finish & Go Home"
                variant="primary"
                size="large"
                fullWidth
                onPress={handleFinish}
              />
            </View>
          )}
        </View>
      </ScrollView>
    </GradientBackground>
  );
};

const styles = StyleSheet.create({
  scrollContainer: {
    flexGrow: 1,
  },
  container: {
    flex: 1,
    padding: theme.spacing.lg,
  },
  header: {
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.lg,
  },
  timerCard: {
    marginBottom: theme.spacing.lg,
  },
  timerContent: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  timerButtons: {
    flexDirection: 'row',
    marginTop: theme.spacing.md,
  },
  checklistContainer: {
    flex: 1,
    marginBottom: theme.spacing.lg,
  },
  footer: {
    marginTop: theme.spacing.lg,
  },
});

export default ChecklistScreen;
