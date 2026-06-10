/**
 * StatsScreen - Detailed statistics and progress visualization
 */

import React from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { GradientBackground, Text, Card, Icon, Button } from '@components/atoms';
import { StreakCounter } from '@components/molecules';
import { useUserStore } from '@store';
import { theme } from '@config/theme';
import StreakManager from '@services/game/StreakManager';

export const StatsScreen = () => {
  const navigation = useNavigation();
  const { profile, achievements } = useUserStore();

  if (!profile) {
    return (
      <GradientBackground variant="dark">
        <View style={styles.container}>
          <Text variant="h2">Loading stats...</Text>
        </View>
      </GradientBackground>
    );
  }

  const unlockedCount = achievements.filter(a => a.unlockedAt).length;
  const totalAchievements = achievements.length;
  const achievementProgress = (unlockedCount / totalAchievements) * 100;

  const averageScore = profile.totalGamesPlayed > 0
    ? Math.round(profile.totalScore / profile.totalGamesPlayed)
    : 0;

  const streakMessage = StreakManager.getStreakMessage(profile.currentStreak);

  return (
    <GradientBackground variant="dark">
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <Text variant="displayMedium" align="center">
              Your Stats
            </Text>
            <Text variant="body" color={theme.colors.fogText} align="center">
              Track your progress and achievements
            </Text>
          </View>

          {/* Streak Overview */}
          <Card variant="elevated" padding="lg" style={styles.streakCard}>
            <StreakCounter
              streak={profile.currentStreak}
              hasShield={profile.streakShields > 0}
            />
            <Text variant="body" color={theme.colors.fogText} align="center" style={{ marginTop: theme.spacing.md }}>
              {streakMessage}
            </Text>
            {profile.longestStreak > profile.currentStreak && (
              <View style={styles.longestStreak}>
                <Icon name="award" size={16} color={theme.colors.champagneGold} />
                <Text variant="caption" color={theme.colors.fogText} style={{ marginLeft: theme.spacing.xs }}>
                  Longest: {profile.longestStreak} days
                </Text>
              </View>
            )}
          </Card>

          {/* Game Stats Grid */}
          <View style={styles.statsGrid}>
            <Card variant="gradient" padding="md" style={styles.statCard}>
              <Icon name="play-circle" size={32} color={theme.colors.champagneGold} />
              <Text variant="h2" color={theme.colors.white} style={{ marginTop: theme.spacing.sm }}>
                {profile.totalGamesPlayed}
              </Text>
              <Text variant="caption" color={theme.colors.fogText}>
                Games Played
              </Text>
            </Card>

            <Card variant="gradient" padding="md" style={styles.statCard}>
              <Icon name="trending-up" size={32} color={theme.colors.champagneGold} />
              <Text variant="h2" color={theme.colors.white} style={{ marginTop: theme.spacing.sm }}>
                {profile.highestScore.toLocaleString()}
              </Text>
              <Text variant="caption" color={theme.colors.fogText}>
                High Score
              </Text>
            </Card>

            <Card variant="gradient" padding="md" style={styles.statCard}>
              <Icon name="bar-chart-2" size={32} color={theme.colors.champagneGold} />
              <Text variant="h2" color={theme.colors.white} style={{ marginTop: theme.spacing.sm }}>
                {averageScore.toLocaleString()}
              </Text>
              <Text variant="caption" color={theme.colors.fogText}>
                Avg Score
              </Text>
            </Card>

            <Card variant="gradient" padding="md" style={styles.statCard}>
              <Icon name="dollar-sign" size={32} color={theme.colors.champagneGold} />
              <Text variant="h2" color={theme.colors.white} style={{ marginTop: theme.spacing.sm }}>
                {profile.tokens.toLocaleString()}
              </Text>
              <Text variant="caption" color={theme.colors.fogText}>
                Tokens
              </Text>
            </Card>
          </View>

          {/* Achievements Progress */}
          <Card variant="elevated" padding="lg" style={styles.achievementsCard}>
            <View style={styles.achievementsHeader}>
              <Text variant="h3">Achievements</Text>
              <Text variant="h4" color={theme.colors.champagneGold}>
                {unlockedCount}/{totalAchievements}
              </Text>
            </View>

            <View style={styles.progressBarContainer}>
              <View style={[styles.progressBar, { width: `${achievementProgress}%` }]} />
            </View>

            <Text variant="caption" color={theme.colors.fogText} align="center" style={{ marginTop: theme.spacing.sm }}>
              {Math.round(achievementProgress)}% Complete
            </Text>

            <Button
              title="View All Achievements"
              variant="ghost"
              size="small"
              onPress={() => navigation.navigate('Achievements' as never)}
              style={{ marginTop: theme.spacing.md }}
            />
          </Card>

          {/* Streak Shields */}
          {profile.streakShields > 0 && (
            <Card variant="outlined" padding="md" style={styles.shieldsCard}>
              <View style={styles.shieldsContent}>
                <Icon name="shield" size={24} color={theme.colors.success} />
                <View style={{ marginLeft: theme.spacing.md, flex: 1 }}>
                  <Text variant="h4">{profile.streakShields} Streak Shields</Text>
                  <Text variant="caption" color={theme.colors.fogText}>
                    Protect your streak if you miss a day
                  </Text>
                </View>
              </View>
            </Card>
          )}

          {/* Total Score */}
          <Card variant="gradient" padding="lg" style={styles.totalScoreCard}>
            <Text variant="caption" color={theme.colors.fogText} align="center">
              Total Career Score
            </Text>
            <Text variant="score" align="center" style={{ marginTop: theme.spacing.sm }}>
              {profile.totalScore.toLocaleString()}
            </Text>
          </Card>
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
  streakCard: {
    marginBottom: theme.spacing.lg,
    alignItems: 'center',
  },
  longestStreak: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.sm,
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.lg,
  },
  statCard: {
    width: '48%',
    marginBottom: theme.spacing.md,
    alignItems: 'center',
  },
  achievementsCard: {
    marginBottom: theme.spacing.lg,
  },
  achievementsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  progressBarContainer: {
    height: 12,
    backgroundColor: theme.colors.darkGray,
    borderRadius: theme.borderRadius.full,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: theme.colors.champagneGold,
    borderRadius: theme.borderRadius.full,
  },
  shieldsCard: {
    marginBottom: theme.spacing.lg,
  },
  shieldsContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  totalScoreCard: {
    marginBottom: theme.spacing.lg,
  },
});

export default StatsScreen;
