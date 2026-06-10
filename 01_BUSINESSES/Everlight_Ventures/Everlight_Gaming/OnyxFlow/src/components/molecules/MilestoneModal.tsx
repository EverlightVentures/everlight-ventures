/**
 * MilestoneModal - Celebration screen for reaching milestones
 */

import React, { useState } from 'react';
import { View, StyleSheet, Modal } from 'react-native';
import Animated, { FadeIn, ZoomIn } from 'react-native-reanimated';
import { GradientBackground, Text, Button, Icon, ParticleEffect } from '@components/atoms';
import { theme } from '@config/theme';

interface MilestoneModalProps {
  visible: boolean;
  type: 'streak' | 'game' | 'score';
  milestone: number;
  reward?: {
    tokens?: number;
    shields?: number;
  };
  message: string;
  onContinue: () => void;
}

export const MilestoneModal: React.FC<MilestoneModalProps> = ({
  visible,
  type,
  milestone,
  reward,
  message,
  onContinue,
}) => {
  const [showParticles, setShowParticles] = useState(visible);

  React.useEffect(() => {
    if (visible) {
      setShowParticles(true);
    }
  }, [visible]);

  const getIcon = () => {
    switch (type) {
      case 'streak':
        return 'zap';
      case 'game':
        return 'award';
      case 'score':
        return 'target';
      default:
        return 'star';
    }
  };

  const getTitle = () => {
    switch (type) {
      case 'streak':
        return `${milestone}-Day Streak!`;
      case 'game':
        return `${milestone} Games!`;
      case 'score':
        return `${milestone.toLocaleString()} Points!`;
      default:
        return 'Milestone!';
    }
  };

  return (
    <Modal visible={visible} transparent animationType="fade">
      <GradientBackground variant="dark" style={styles.overlay}>
        <Animated.View entering={ZoomIn.duration(500)} style={styles.container}>
          {/* Icon */}
          <View style={styles.iconContainer}>
            <Icon name={getIcon()} size={64} color={theme.colors.champagneGold} />
          </View>

          {/* Title */}
          <Text variant="display" align="center" style={styles.title}>
            {getTitle()}
          </Text>

          {/* Message */}
          <Text variant="h4" color={theme.colors.fogText} align="center" style={styles.message}>
            {message}
          </Text>

          {/* Rewards */}
          {reward && (
            <View style={styles.rewards}>
              {reward.tokens && (
                <Animated.View entering={FadeIn.delay(300)} style={styles.rewardItem}>
                  <Icon name="dollar-sign" size={32} color={theme.colors.champagneGold} />
                  <Text variant="h3" color={theme.colors.champagneGold} style={{ marginTop: 8 }}>
                    +{reward.tokens}
                  </Text>
                  <Text variant="caption" color={theme.colors.fogText}>
                    Tokens
                  </Text>
                </Animated.View>
              )}
              {reward.shields && (
                <Animated.View entering={FadeIn.delay(400)} style={styles.rewardItem}>
                  <Icon name="shield" size={32} color={theme.colors.success} />
                  <Text variant="h3" color={theme.colors.success} style={{ marginTop: 8 }}>
                    +{reward.shields}
                  </Text>
                  <Text variant="caption" color={theme.colors.fogText}>
                    Shields
                  </Text>
                </Animated.View>
              )}
            </View>
          )}

          {/* Continue Button */}
          <Animated.View entering={FadeIn.delay(600)} style={styles.buttonContainer}>
            <Button
              title="Continue"
              variant="gold"
              size="large"
              fullWidth
              onPress={onContinue}
            />
          </Animated.View>
        </Animated.View>

        {/* Particle Effect */}
        {showParticles && (
          <ParticleEffect
            type="confetti"
            particleCount={40}
            duration={2500}
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
    width: '85%',
    padding: theme.spacing.xl,
    alignItems: 'center',
  },
  iconContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    backgroundColor: theme.colors.graphite,
    borderWidth: 4,
    borderColor: theme.colors.champagneGold,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: theme.spacing.lg,
  },
  title: {
    marginBottom: theme.spacing.md,
  },
  message: {
    marginBottom: theme.spacing.xl,
  },
  rewards: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: theme.spacing.xl,
  },
  rewardItem: {
    alignItems: 'center',
    marginHorizontal: theme.spacing.lg,
  },
  buttonContainer: {
    width: '100%',
  },
});

export default MilestoneModal;
