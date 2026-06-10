/**
 * AchievementsScreen - Display all achievements with unlock animations
 */

import React, { useState } from 'react';
import { View, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import Animated, { FadeIn, ZoomIn } from 'react-native-reanimated';
import { GradientBackground, Text, Card, Icon } from '@components/atoms';
import { useUserStore } from '@store';
import { theme } from '@config/theme';

type CategoryFilter = 'all' | 'games' | 'streaks' | 'score' | 'special';

export const AchievementsScreen = () => {
  const { achievements } = useUserStore();
  const [selectedCategory, setSelectedCategory] = useState<CategoryFilter>('all');

  const categories = [
    { id: 'all' as CategoryFilter, label: 'All', icon: 'grid' },
    { id: 'games' as CategoryFilter, label: 'Games', icon: 'play-circle' },
    { id: 'streaks' as CategoryFilter, label: 'Streaks', icon: 'zap' },
    { id: 'score' as CategoryFilter, label: 'Score', icon: 'target' },
    { id: 'special' as CategoryFilter, label: 'Special', icon: 'star' },
  ];

  const filteredAchievements =
    selectedCategory === 'all'
      ? achievements
      : achievements.filter(a => a.category === selectedCategory);

  const unlockedCount = achievements.filter(a => a.unlockedAt).length;
  const totalCount = achievements.length;

  return (
    <GradientBackground variant="dark">
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <Text variant="displayMedium" align="center">
              Achievements
            </Text>
            <Text variant="h4" color={theme.colors.champagneGold} align="center">
              {unlockedCount} / {totalCount} Unlocked
            </Text>
          </View>

          {/* Category Filter */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categoryScroll}
            style={styles.categoryContainer}
          >
            {categories.map(category => (
              <TouchableOpacity
                key={category.id}
                onPress={() => setSelectedCategory(category.id)}
                activeOpacity={0.7}
              >
                <Card
                  variant={selectedCategory === category.id ? 'gradient' : 'outlined'}
                  padding="sm"
                  style={styles.categoryChip}
                >
                  <Icon
                    name={category.icon}
                    size={16}
                    color={
                      selectedCategory === category.id
                        ? theme.colors.white
                        : theme.colors.fogText
                    }
                  />
                  <Text
                    variant="caption"
                    color={
                      selectedCategory === category.id
                        ? theme.colors.white
                        : theme.colors.fogText
                    }
                    style={{ marginLeft: theme.spacing.xs }}
                  >
                    {category.label}
                  </Text>
                </Card>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Achievements List */}
          <View style={styles.achievementsList}>
            {filteredAchievements.map((achievement, index) => {
              const isUnlocked = !!achievement.unlockedAt;
              const progress = achievement.progress || 0;
              const progressPercent = (progress / achievement.target) * 100;

              return (
                <Animated.View
                  key={achievement.id}
                  entering={FadeIn.delay(index * 50)}
                >
                  <Card
                    variant={isUnlocked ? 'elevated' : 'outlined'}
                    padding="md"
                    style={[
                      styles.achievementCard,
                      !isUnlocked && styles.achievementCardLocked,
                    ]}
                  >
                    <View style={styles.achievementContent}>
                      {/* Icon */}
                      <View
                        style={[
                          styles.achievementIcon,
                          isUnlocked && styles.achievementIconUnlocked,
                        ]}
                      >
                        {isUnlocked ? (
                          <Animated.View entering={ZoomIn}>
                            <Icon
                              name={achievement.icon}
                              size={32}
                              color={theme.colors.champagneGold}
                            />
                          </Animated.View>
                        ) : (
                          <Icon
                            name={achievement.icon}
                            size={32}
                            color={theme.colors.fogText}
                          />
                        )}
                      </View>

                      {/* Details */}
                      <View style={styles.achievementDetails}>
                        <Text
                          variant="h4"
                          color={isUnlocked ? theme.colors.white : theme.colors.fogText}
                        >
                          {achievement.title}
                        </Text>
                        <Text
                          variant="caption"
                          color={theme.colors.fogText}
                          style={{ marginTop: theme.spacing.xs }}
                        >
                          {achievement.description}
                        </Text>

                        {/* Progress Bar (for locked achievements) */}
                        {!isUnlocked && progress > 0 && (
                          <View style={styles.progressContainer}>
                            <View style={styles.progressBarBg}>
                              <View
                                style={[
                                  styles.progressBarFill,
                                  { width: `${progressPercent}%` },
                                ]}
                              />
                            </View>
                            <Text variant="caption" color={theme.colors.fogText}>
                              {progress} / {achievement.target}
                            </Text>
                          </View>
                        )}

                        {/* Rewards */}
                        {achievement.reward && (
                          <View style={styles.rewards}>
                            {achievement.reward.tokens && (
                              <View style={styles.reward}>
                                <Icon
                                  name="dollar-sign"
                                  size={12}
                                  color={theme.colors.champagneGold}
                                />
                                <Text variant="caption" color={theme.colors.champagneGold}>
                                  {achievement.reward.tokens}
                                </Text>
                              </View>
                            )}
                            {achievement.reward.shield && (
                              <View style={styles.reward}>
                                <Icon
                                  name="shield"
                                  size={12}
                                  color={theme.colors.success}
                                />
                                <Text variant="caption" color={theme.colors.success}>
                                  {achievement.reward.shield}
                                </Text>
                              </View>
                            )}
                          </View>
                        )}

                        {/* Unlocked Date */}
                        {isUnlocked && achievement.unlockedAt && (
                          <Text
                            variant="caption"
                            color={theme.colors.fogText}
                            style={{ marginTop: theme.spacing.xs }}
                          >
                            Unlocked {new Date(achievement.unlockedAt).toLocaleDateString()}
                          </Text>
                        )}
                      </View>
                    </View>
                  </Card>
                </Animated.View>
              );
            })}
          </View>
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
  categoryContainer: {
    marginBottom: theme.spacing.lg,
  },
  categoryScroll: {
    paddingRight: theme.spacing.lg,
  },
  categoryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: theme.spacing.sm,
    paddingHorizontal: theme.spacing.md,
  },
  achievementsList: {
    flex: 1,
  },
  achievementCard: {
    marginBottom: theme.spacing.md,
  },
  achievementCardLocked: {
    opacity: 0.6,
  },
  achievementContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  achievementIcon: {
    width: 56,
    height: 56,
    borderRadius: theme.borderRadius.lg,
    backgroundColor: theme.colors.darkGray,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  achievementIconUnlocked: {
    backgroundColor: theme.colors.graphite,
    borderWidth: 2,
    borderColor: theme.colors.champagneGold,
  },
  achievementDetails: {
    flex: 1,
  },
  progressContainer: {
    marginTop: theme.spacing.sm,
  },
  progressBarBg: {
    height: 6,
    backgroundColor: theme.colors.darkGray,
    borderRadius: theme.borderRadius.full,
    overflow: 'hidden',
    marginBottom: theme.spacing.xs,
  },
  progressBarFill: {
    height: '100%',
    backgroundColor: theme.colors.champagneGold,
    borderRadius: theme.borderRadius.full,
  },
  rewards: {
    flexDirection: 'row',
    marginTop: theme.spacing.sm,
  },
  reward: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
});

export default AchievementsScreen;
