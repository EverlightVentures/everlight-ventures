/**
 * AchievementToast - Notification when achievement is unlocked
 */

import React, { useEffect } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withDelay,
  withTiming,
  runOnJS,
} from 'react-native-reanimated';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { Icon, Text, Card } from '@components/atoms';
import { theme } from '@config/theme';
import type { Achievement } from '@types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface AchievementToastProps {
  achievement: Achievement;
  onDismiss?: () => void;
  duration?: number;
}

export const AchievementToast: React.FC<AchievementToastProps> = ({
  achievement,
  onDismiss,
  duration = 3000,
}) => {
  const translateY = useSharedValue(-200);
  const opacity = useSharedValue(0);

  useEffect(() => {
    // Haptic feedback
    ReactNativeHapticFeedback.trigger('notificationSuccess', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });

    // Slide in
    translateY.value = withSpring(0, { damping: 15, stiffness: 100 });
    opacity.value = withTiming(1, { duration: 300 });

    // Slide out after duration
    const timeout = setTimeout(() => {
      translateY.value = withTiming(-200, { duration: 300 });
      opacity.value = withTiming(0, { duration: 300 }, () => {
        if (onDismiss) {
          runOnJS(onDismiss)();
        }
      });
    }, duration);

    return () => clearTimeout(timeout);
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));

  return (
    <Animated.View style={[styles.container, animatedStyle]}>
      <Card variant="elevated" padding="md" style={styles.card}>
        <View style={styles.content}>
          {/* Icon */}
          <View style={styles.iconContainer}>
            <Icon name={achievement.icon} size={32} color={theme.colors.champagneGold} />
          </View>

          {/* Text */}
          <View style={styles.textContainer}>
            <Text variant="caption" color={theme.colors.champagneGold}>
              Achievement Unlocked!
            </Text>
            <Text variant="h4" style={{ marginTop: 2 }}>
              {achievement.title}
            </Text>
            {achievement.reward?.tokens && (
              <View style={styles.reward}>
                <Icon name="dollar-sign" size={12} color={theme.colors.champagneGold} />
                <Text variant="caption" color={theme.colors.champagneGold}>
                  +{achievement.reward.tokens} tokens
                </Text>
              </View>
            )}
          </View>

          {/* Trophy */}
          <Icon name="award" size={24} color={theme.colors.champagneGold} />
        </View>
      </Card>
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 60,
    left: theme.spacing.md,
    right: theme.spacing.md,
    zIndex: 9999,
  },
  card: {
    ...theme.shadows.gold,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.darkGray,
    borderWidth: 2,
    borderColor: theme.colors.champagneGold,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: theme.spacing.md,
  },
  textContainer: {
    flex: 1,
  },
  reward: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: theme.spacing.xs,
  },
});

export default AchievementToast;
