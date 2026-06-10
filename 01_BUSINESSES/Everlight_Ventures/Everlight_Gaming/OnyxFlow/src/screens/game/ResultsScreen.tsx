/**
 * ResultsScreen - Game completion summary
 */

import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import Animated, { FadeIn, FadeInDown, ZoomIn, FadeInUp } from 'react-native-reanimated';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { GradientBackground, Button, Card, Text, Icon } from '@components/atoms';
import { useGameStore, useUserStore } from '@store';
import type { HomeStackParamList } from '@navigation/types';
import type { GameSession } from '@types';
import { theme } from '@config/theme';

type ResultsScreenNavigationProp = NativeStackNavigationProp<HomeStackParamList, 'Results'>;
type ResultsScreenRouteProp = RouteProp<HomeStackParamList, 'Results'>;

export const ResultsScreen = () => {
  const navigation = useNavigation<ResultsScreenNavigationProp>();
  const route = useRoute<ResultsScreenRouteProp>();
  const { sessionId } = route.params;

  const { session } = useGameStore();
  const { profile } = useUserStore();

  const [displayedSession, setDisplayedSession] = useState<GameSession | null>(null);

  useEffect(() => {
    if (session && session.id === sessionId) {
      setDisplayedSession(session);
      // Haptic feedback for completion
      ReactNativeHapticFeedback.trigger('notificationSuccess', {
        enableVibrateFallback: true,
        ignoreAndroidSystemSettings: false,
      });
    }
  }, [session, sessionId]);

  const handleViewRoulette = () => {
    if (displayedSession) {
      navigation.navigate('Roulette', { sessionId: displayedSession.id });
    }
  };

  const handlePlayAgain = () => {
    if (displayedSession) {
      navigation.navigate('Game', { deckId: displayedSession.deckId });
    }
  };

  const handleGoHome = () => {
    navigation.navigate('Home');
  };

  if (!displayedSession || !profile) {
    return (
      <GradientBackground variant="dark">
        <View style={styles.container}>
          <Text variant="h2">Loading results...</Text>
        </View>
      </GradientBackground>
    );
  }

  const {
    score,
    baseScore,
    multiplier,
    cardsProcessed,
    maxCombo,
    selectedAction,
    checklist,
  } = displayedSession;

  return (
    <GradientBackground variant="dark">
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.container}>
          {/* Header */}
          <Animated.View entering={ZoomIn.duration(600)} style={styles.header}>
            <Icon name="check-circle" size={64} color={theme.colors.success} />
            <Text variant="display" style={styles.title}>
              Flow Complete!
            </Text>
            <Text variant="body" color={theme.colors.fogText} align="center">
              Great work! Here's your summary
            </Text>
          </Animated.View>

          {/* Score Card */}
          <Animated.View entering={FadeInUp.delay(200).duration(500)}>
          <Card variant="elevated" padding="lg" style={styles.scoreCard}>
            <Text variant="score" align="center" style={{ marginBottom: theme.spacing.sm }}>
              {score.toLocaleString()}
            </Text>
            <Text variant="caption" color={theme.colors.fogText} align="center">
              Final Score
            </Text>

            <View style={styles.statsRow}>
              <View style={styles.stat}>
                <Text variant="h3" color={theme.colors.champagneGold}>
                  {cardsProcessed}
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  Cards
                </Text>
              </View>

              <View style={styles.stat}>
                <Text variant="h3" color={theme.colors.champagneGold}>
                  {maxCombo}x
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  Max Combo
                </Text>
              </View>

              <View style={styles.stat}>
                <Text variant="h3" color={theme.colors.champagneGold}>
                  {multiplier.toFixed(1)}x
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  Multiplier
                </Text>
              </View>
            </View>
          </Card>
          </Animated.View>

          {/* Roulette Action Preview */}
          {selectedAction && (
            <Animated.View entering={FadeInDown.delay(400).duration(500)}>
            <Card variant="gradient" padding="lg" style={styles.actionCard}>
              <Icon name="target" size={32} color={theme.colors.champagneGold} />
              <Text variant="caption" color={theme.colors.fogText} align="center" style={{ marginTop: theme.spacing.sm }}>
                Decision Roulette Selected
              </Text>
              <Text variant="h4" align="center" style={{ marginTop: theme.spacing.xs }}>
                {selectedAction}
              </Text>
              <Button
                title="View Roulette Animation"
                variant="ghost"
                size="small"
                onPress={handleViewRoulette}
                style={{ marginTop: theme.spacing.md }}
              />
            </Card>
            </Animated.View>
          )}

          {/* Checklist Preview */}
          <Animated.View entering={FadeInDown.delay(selectedAction ? 600 : 400).duration(500)}>
          <Card variant="outlined" padding="lg" style={styles.checklistCard}>
            <Text variant="h4" style={{ marginBottom: theme.spacing.md }}>
              Your 3-Item Checklist
            </Text>
            {checklist.slice(0, 3).map((item, index) => (
              <View key={item.id} style={styles.checklistItem}>
                <Icon
                  name="circle"
                  size={20}
                  color={theme.colors.fogText}
                />
                <Text variant="body" style={{ marginLeft: theme.spacing.sm, flex: 1 }}>
                  {item.text}
                </Text>
              </View>
            ))}
          </Card>
          </Animated.View>

          {/* Actions */}
          <Animated.View entering={FadeIn.delay(selectedAction ? 800 : 600).duration(500)} style={styles.actions}>
            <Button
              title="Start 5-Min Sprint"
              variant="gold"
              size="large"
              fullWidth
              onPress={handleViewRoulette}
              icon={<Icon name="zap" size={20} color={theme.colors.onyxBlack} style={{ marginRight: 8 }} />}
              style={{ marginBottom: theme.spacing.md }}
            />
            <Button
              title="Play Again"
              variant="primary"
              size="medium"
              fullWidth
              onPress={handlePlayAgain}
              style={{ marginBottom: theme.spacing.sm }}
            />
            <Button
              title="Go Home"
              variant="ghost"
              size="small"
              fullWidth
              onPress={handleGoHome}
            />
          </Animated.View>
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
    alignItems: 'center',
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.xl,
  },
  title: {
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  scoreCard: {
    marginBottom: theme.spacing.lg,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: theme.spacing.lg,
  },
  stat: {
    alignItems: 'center',
  },
  actionCard: {
    marginBottom: theme.spacing.lg,
  },
  checklistCard: {
    marginBottom: theme.spacing.lg,
  },
  checklistItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  actions: {
    marginTop: theme.spacing.lg,
  },
});

export default ResultsScreen;
