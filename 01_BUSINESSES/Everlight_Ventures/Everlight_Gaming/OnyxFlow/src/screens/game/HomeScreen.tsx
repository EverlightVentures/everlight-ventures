import React, { useEffect, useState } from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import Animated, { FadeIn, FadeInDown } from 'react-native-reanimated';
import { GradientBackground, Text, Button, Card, Icon } from '@components/atoms';
import { StreakCounter, TokenDisplay, AchievementToast, AdBanner } from '@components/molecules';
import { DailyRewardModal } from '@components/organisms';
import { useUserStore } from '@store';
import type { HomeStackParamList } from '@navigation/types';
import type { Achievement } from '@types';
import { theme } from '@config/theme';
import { DECK_IDS } from '@config/constants';

type HomeScreenNavigationProp = NativeStackNavigationProp<HomeStackParamList, 'Home'>;

export const HomeScreen = () => {
  const navigation = useNavigation<HomeScreenNavigationProp>();
  const {
    profile,
    initializeUser,
    achievements,
    claimDailyReward,
    getDailyRewards,
    isDailyRewardAvailable,
    getTimeUntilNextReward,
  } = useUserStore();
  const [showAchievementToast, setShowAchievementToast] = useState<Achievement | null>(null);
  const [showDailyRewardModal, setShowDailyRewardModal] = useState(false);

  useEffect(() => {
    if (!profile) {
      initializeUser();
    }
  }, [profile, initializeUser]);

  const handleStartGame = () => {
    navigation.navigate('Game', { deckId: DECK_IDS.home });
  };

  const handleClaimDailyReward = () => {
    const reward = claimDailyReward();
    if (reward) {
      // Show success feedback (could trigger achievement toast if needed)
      console.log('Claimed daily reward:', reward);
    }
  };

  const dailyRewards = getDailyRewards();
  const hasAvailableReward = isDailyRewardAvailable();
  const timeUntilNext = getTimeUntilNextReward();

  const recentAchievements = achievements
    .filter(a => a.unlockedAt)
    .sort((a, b) => (b.unlockedAt || 0) - (a.unlockedAt || 0))
    .slice(0, 3);

  const averageScore = profile?.totalGamesPlayed
    ? Math.round(profile.totalScore / profile.totalGamesPlayed)
    : 0;

  const isNewUser = !profile || profile.totalGamesPlayed === 0;

  return (
    <GradientBackground variant="dark">
      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <View style={styles.container}>
          {/* Header with Token Display */}
          <Animated.View entering={FadeIn.duration(600)} style={styles.header}>
            <View style={styles.titleRow}>
              <Text variant="display">OnyxFlow</Text>
              <TokenDisplay
                tokens={profile?.tokens || 0}
                size="medium"
                showLabel={false}
              />
            </View>
            <Text variant="caption" align="center" color={theme.colors.fogText}>
              Swipe into focus — luxury in a minute
            </Text>
          </Animated.View>

          {/* Streak Display */}
          <Animated.View entering={FadeInDown.delay(100).duration(600)} style={styles.streakSection}>
            <Card variant="gradient" padding="md" borderRadius="lg">
              <StreakCounter
                streak={profile?.currentStreak || 0}
                hasShield={(profile?.streakShields || 0) > 0}
              />
            </Card>
          </Animated.View>

          {/* Stats Grid */}
          {!isNewUser && (
            <Animated.View entering={FadeInDown.delay(200).duration(600)} style={styles.statsGrid}>
              <Card variant="elevated" padding="md" borderRadius="lg" style={styles.statCard}>
                <Icon name="play-circle" size={24} color={theme.colors.champagneGold} />
                <Text variant="h3" style={{ marginTop: theme.spacing.xs }}>
                  {profile.totalGamesPlayed}
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  Games
                </Text>
              </Card>

              <Card variant="elevated" padding="md" borderRadius="lg" style={styles.statCard}>
                <Icon name="award" size={24} color={theme.colors.champagneGold} />
                <Text variant="h3" style={{ marginTop: theme.spacing.xs }}>
                  {profile.highestScore.toLocaleString()}
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  High Score
                </Text>
              </Card>

              <Card variant="elevated" padding="md" borderRadius="lg" style={styles.statCard}>
                <Icon name="trending-up" size={24} color={theme.colors.champagneGold} />
                <Text variant="h3" style={{ marginTop: theme.spacing.xs }}>
                  {averageScore.toLocaleString()}
                </Text>
                <Text variant="caption" color={theme.colors.fogText}>
                  Avg Score
                </Text>
              </Card>
            </Animated.View>
          )}

          {/* Recent Achievements */}
          {recentAchievements.length > 0 && (
            <Animated.View entering={FadeInDown.delay(300).duration(600)} style={styles.achievementsSection}>
              <View style={styles.sectionHeader}>
                <Text variant="h4">Recent Achievements</Text>
                <TouchableOpacity onPress={() => navigation.navigate('Stats')}>
                  <Text variant="caption" color={theme.colors.champagneGold}>
                    View All →
                  </Text>
                </TouchableOpacity>
              </View>

              <View style={styles.achievementsList}>
                {recentAchievements.map((achievement, index) => (
                  <Card
                    key={achievement.id}
                    variant="outlined"
                    padding="sm"
                    borderRadius="md"
                    style={styles.achievementCard}
                  >
                    <View style={styles.achievementIconContainer}>
                      <Icon name={achievement.icon} size={20} color={theme.colors.champagneGold} />
                    </View>
                    <View style={styles.achievementText}>
                      <Text variant="body" numberOfLines={1}>{achievement.title}</Text>
                      <Text variant="caption" color={theme.colors.fogText} numberOfLines={1}>
                        {achievement.description}
                      </Text>
                    </View>
                  </Card>
                ))}
              </View>
            </Animated.View>
          )}

          {/* Main CTA */}
          <Animated.View entering={FadeInDown.delay(400).duration(600)} style={styles.ctaSection}>
            <Card variant="elevated" padding="lg" borderRadius="xl">
              <Text variant="h3" align="center" style={{ marginBottom: theme.spacing.md }}>
                {isNewUser ? 'Ready to Flow?' : 'Start Your Session'}
              </Text>
              <Text variant="body" align="center" color={theme.colors.fogText}>
                {isNewUser
                  ? 'Play your first 60-second session and discover luxury productivity'
                  : 'Take 60 seconds to swipe into focus'
                }
              </Text>
            </Card>

            <Button
              title="Play 60s"
              variant="primary"
              size="large"
              fullWidth
              icon="play"
              onPress={handleStartGame}
              style={{ marginTop: theme.spacing.lg }}
            />

            {!isNewUser && (
              <View style={styles.quickActions}>
                <TouchableOpacity
                  style={styles.quickAction}
                  onPress={() => navigation.navigate('Stats')}
                >
                  <Icon name="bar-chart-2" size={20} color={theme.colors.fogText} />
                  <Text variant="caption" color={theme.colors.fogText} style={{ marginTop: 4 }}>
                    Stats
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.quickAction}
                  onPress={() => navigation.navigate('Stats')}
                >
                  <Icon name="award" size={20} color={theme.colors.fogText} />
                  <Text variant="caption" color={theme.colors.fogText} style={{ marginTop: 4 }}>
                    Achievements
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.quickAction}
                  onPress={() => setShowDailyRewardModal(true)}
                >
                  <View>
                    <Icon
                      name="gift"
                      size={20}
                      color={hasAvailableReward ? theme.colors.champagneGold : theme.colors.fogText}
                    />
                    {hasAvailableReward && <View style={styles.availableBadge} />}
                  </View>
                  <Text
                    variant="caption"
                    color={hasAvailableReward ? theme.colors.champagneGold : theme.colors.fogText}
                    style={{ marginTop: 4 }}
                  >
                    Daily Reward
                  </Text>
                </TouchableOpacity>
              </View>
            )}
          </Animated.View>
        </View>
      </ScrollView>

      {/* Achievement Toast Overlay */}
      {showAchievementToast && (
        <AchievementToast
          achievement={showAchievementToast}
          onDismiss={() => setShowAchievementToast(null)}
        />
      )}

      {/* Daily Reward Modal */}
      <DailyRewardModal
        visible={showDailyRewardModal}
        rewards={dailyRewards}
        onClaim={handleClaimDailyReward}
        onClose={() => setShowDailyRewardModal(false)}
        timeUntilNext={timeUntilNext}
        isPlusSubscriber={profile?.isPlusSubscriber}
      />

      {/* Ad Banner (only for free users) */}
      <AdBanner position="bottom" />
    </GradientBackground>
  );
};

const styles = StyleSheet.create({
  scrollView: {
    flex: 1,
  },
  container: {
    padding: theme.spacing.lg,
    paddingBottom: theme.spacing.xxxl,
  },
  header: {
    marginTop: theme.spacing.xl,
    marginBottom: theme.spacing.lg,
  },
  titleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.xs,
  },
  streakSection: {
    marginBottom: theme.spacing.lg,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: theme.spacing.lg,
  },
  statCard: {
    flex: 1,
    marginHorizontal: theme.spacing.xs,
    alignItems: 'center',
  },
  achievementsSection: {
    marginBottom: theme.spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.md,
  },
  achievementsList: {
    gap: theme.spacing.sm,
  },
  achievementCard: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  achievementIconContainer: {
    width: 40,
    height: 40,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.darkGray,
    borderWidth: 1,
    borderColor: theme.colors.champagneGold,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.sm,
  },
  achievementText: {
    flex: 1,
  },
  ctaSection: {
    marginTop: theme.spacing.md,
  },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: theme.spacing.lg,
  },
  quickAction: {
    alignItems: 'center',
    padding: theme.spacing.md,
  },
  availableBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.champagneGold,
    borderWidth: 2,
    borderColor: theme.colors.onyxBlack,
  },
});

export default HomeScreen;
