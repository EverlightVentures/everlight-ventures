/**
 * DailyRewardModal - Shows daily reward calendar and claim UI
 */

import React, { useState } from 'react';
import { View, StyleSheet, Modal, ScrollView, TouchableOpacity } from 'react-native';
import Animated, { FadeIn, ZoomIn, FadeInDown } from 'react-native-reanimated';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { GradientBackground, Text, Button, Icon, Card, ParticleEffect } from '@components/atoms';
import { theme } from '@config/theme';
import type { DailyReward } from '@types';

interface DailyRewardModalProps {
  visible: boolean;
  rewards: DailyReward[];
  onClaim: () => void;
  onClose: () => void;
  timeUntilNext?: number;
  isPlusSubscriber?: boolean;
}

export const DailyRewardModal: React.FC<DailyRewardModalProps> = ({
  visible,
  rewards,
  onClaim,
  onClose,
  timeUntilNext,
  isPlusSubscriber = false,
}) => {
  const [claiming, setClaiming] = useState(false);
  const [showParticles, setShowParticles] = useState(false);
  const availableReward = rewards.find(r => r.isAvailable);
  const hasAvailableReward = !!availableReward && !availableReward.isClaimed;

  const handleClaim = () => {
    if (!hasAvailableReward || claiming) return;

    setClaiming(true);
    setShowParticles(true);
    ReactNativeHapticFeedback.trigger('notificationSuccess', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });

    setTimeout(() => {
      onClaim();
      setClaiming(false);
    }, 500);
  };

  const getDayIcon = (reward: DailyReward): string => {
    if (reward.isClaimed) return 'check-circle';
    if (reward.isAvailable) return 'gift';
    return 'circle';
  };

  const getDayColor = (reward: DailyReward): string => {
    if (reward.isClaimed) return theme.colors.success;
    if (reward.isAvailable) return theme.colors.champagneGold;
    return theme.colors.mediumGray;
  };

  const formatTimeRemaining = (ms?: number): string => {
    if (!ms) return '';
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <Modal visible={visible} transparent animationType="fade">
      <GradientBackground variant="dark" style={styles.overlay}>
        <Animated.View entering={ZoomIn.duration(400)} style={styles.container}>
          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Header */}
            <View style={styles.header}>
              <View style={styles.headerContent}>
                <Icon name="gift" size={32} color={theme.colors.champagneGold} />
                <Text variant="h2" style={{ marginTop: theme.spacing.sm }}>
                  Daily Rewards
                </Text>
                <Text variant="body" color={theme.colors.fogText} align="center">
                  Check in every day for amazing rewards!
                </Text>
                {isPlusSubscriber && (
                  <View style={styles.plusBadge}>
                    <Icon name="star" size={14} color={theme.colors.champagneGold} />
                    <Text
                      variant="caption"
                      color={theme.colors.champagneGold}
                      style={{ marginLeft: 4 }}
                    >
                      OnyxFlow+ 50% Bonus
                    </Text>
                  </View>
                )}
              </View>
              <TouchableOpacity onPress={onClose} style={styles.closeButton}>
                <Icon name="x" size={24} color={theme.colors.fogText} />
              </TouchableOpacity>
            </View>

            {/* Reward Calendar */}
            <View style={styles.calendar}>
              {rewards.map((reward, index) => (
                <Animated.View
                  key={reward.day}
                  entering={FadeInDown.delay(index * 50).duration(400)}
                >
                  <Card
                    variant={reward.isAvailable ? 'gradient' : reward.isClaimed ? 'elevated' : 'outlined'}
                    padding="md"
                    borderRadius="lg"
                    style={styles.dayCard}
                  >
                    <View style={styles.dayHeader}>
                      <Text
                        variant="caption"
                        color={reward.isAvailable ? theme.colors.white : theme.colors.fogText}
                      >
                        Day {reward.day}
                      </Text>
                      <Icon name={getDayIcon(reward)} size={16} color={getDayColor(reward)} />
                    </View>

                    {/* Rewards */}
                    <View style={styles.rewardItems}>
                      <View style={styles.rewardRow}>
                        <Icon name="dollar-sign" size={20} color={theme.colors.champagneGold} />
                        <Text
                          variant="h4"
                          color={theme.colors.champagneGold}
                          style={{ marginLeft: theme.spacing.xs }}
                        >
                          {reward.tokens}
                        </Text>
                      </View>

                      {reward.shields && (
                        <View style={styles.rewardRow}>
                          <Icon name="shield" size={20} color={theme.colors.success} />
                          <Text
                            variant="body"
                            color={theme.colors.success}
                            style={{ marginLeft: theme.spacing.xs }}
                          >
                            +{reward.shields}
                          </Text>
                        </View>
                      )}

                      {reward.bonus && (
                        <View style={styles.bonusTag}>
                          <Icon name="star" size={12} color={theme.colors.champagneGold} />
                          <Text variant="caption" color={theme.colors.champagneGold}>
                            Bonus!
                          </Text>
                        </View>
                      )}
                    </View>

                    {reward.day === 7 && (
                      <Text
                        variant="caption"
                        color={theme.colors.champagneGold}
                        align="center"
                        style={{ marginTop: theme.spacing.xs }}
                      >
                        Grand Prize
                      </Text>
                    )}
                  </Card>
                </Animated.View>
              ))}
            </View>

            {/* Action Button */}
            {hasAvailableReward ? (
              <Animated.View entering={FadeIn.delay(400)}>
                <Button
                  title={claiming ? 'Claiming...' : 'Claim Reward'}
                  variant="gold"
                  size="large"
                  fullWidth
                  icon="gift"
                  onPress={handleClaim}
                  loading={claiming}
                  style={{ marginTop: theme.spacing.lg }}
                />
              </Animated.View>
            ) : (
              <Animated.View entering={FadeIn.delay(400)}>
                <Card variant="outlined" padding="md" style={{ marginTop: theme.spacing.lg }}>
                  <Text variant="body" align="center" color={theme.colors.fogText}>
                    {timeUntilNext
                      ? `Next reward in ${formatTimeRemaining(timeUntilNext)}`
                      : 'All rewards claimed for today!'}
                  </Text>
                </Card>
                <Button
                  title="Close"
                  variant="secondary"
                  size="large"
                  fullWidth
                  onPress={onClose}
                  style={{ marginTop: theme.spacing.md }}
                />
              </Animated.View>
            )}
          </ScrollView>
        </Animated.View>

        {/* Particle Effect */}
        {showParticles && (
          <ParticleEffect
            type="sparkles"
            particleCount={25}
            duration={2000}
            onComplete={() => setShowParticles(false)}
          />
        )}
      </GradientBackground>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
  },
  container: {
    width: '90%',
    maxHeight: '85%',
    padding: theme.spacing.lg,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: theme.spacing.lg,
  },
  headerContent: {
    flex: 1,
    alignItems: 'center',
  },
  closeButton: {
    padding: theme.spacing.xs,
  },
  plusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.graphite,
    borderWidth: 1,
    borderColor: theme.colors.champagneGold,
    borderRadius: theme.borderRadius.full,
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: theme.spacing.xs,
    marginTop: theme.spacing.sm,
  },
  calendar: {
    gap: theme.spacing.sm,
  },
  dayCard: {
    minHeight: 100,
  },
  dayHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: theme.spacing.sm,
  },
  rewardItems: {
    gap: theme.spacing.xs,
  },
  rewardRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  bonusTag: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.darkGray,
    borderWidth: 1,
    borderColor: theme.colors.champagneGold,
    borderRadius: theme.borderRadius.sm,
    paddingHorizontal: theme.spacing.xs,
    paddingVertical: 2,
    marginTop: theme.spacing.xs,
    gap: 4,
  },
});

export default DailyRewardModal;
