/**
 * SwipeCard - Swipeable card with Reanimated animations
 */

import React, { useCallback } from 'react';
import { Dimensions, StyleSheet } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
  runOnJS,
  interpolate,
  Extrapolate,
} from 'react-native-reanimated';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { Card as BaseCard, Text } from '@components/atoms';
import type { Card, SwipeDirection, TaskCardContent } from '@types';
import { theme } from '@config/theme';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.3; // 30% of screen width
const HOLD_DURATION = 800; // milliseconds

interface SwipeCardProps {
  card: Card;
  onSwipe: (direction: SwipeDirection) => void;
  isTopCard: boolean;
}

export const SwipeCard: React.FC<SwipeCardProps> = ({ card, onSwipe, isTopCard }) => {
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const scale = useSharedValue(isTopCard ? 1 : 0.95);
  const holdProgress = useSharedValue(0);

  const triggerHaptic = useCallback(() => {
    ReactNativeHapticFeedback.trigger('impactMedium', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });
  }, []);

  const triggerHoldHaptic = useCallback(() => {
    ReactNativeHapticFeedback.trigger('impactHeavy', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });
  }, []);

  // Long press gesture for "hold"
  const longPress = Gesture.LongPress()
    .minDuration(HOLD_DURATION)
    .onStart(() => {
      runOnJS(triggerHoldHaptic)();
      holdProgress.value = withTiming(1, { duration: 200 });
    })
    .onEnd(() => {
      holdProgress.value = withTiming(0, { duration: 200 });
      translateX.value = withSpring(0);
      translateY.value = withSpring(0);
      runOnJS(onSwipe)('hold');
    });

  // Pan gesture for swipe
  const pan = Gesture.Pan()
    .onUpdate(event => {
      translateX.value = event.translationX;
      translateY.value = event.translationY * 0.2; // Subtle vertical movement
    })
    .onEnd(event => {
      const direction = event.translationX > 0 ? 'right' : 'left';
      const absX = Math.abs(event.translationX);

      if (absX > SWIPE_THRESHOLD) {
        // Swipe confirmed
        runOnJS(triggerHaptic)();

        // Animate off screen
        translateX.value = withTiming(
          event.translationX > 0 ? SCREEN_WIDTH : -SCREEN_WIDTH,
          { duration: 300 },
          () => {
            runOnJS(onSwipe)(direction);
          }
        );
      } else {
        // Return to center
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
      }
    });

  const composed = Gesture.Race(longPress, pan);

  // Animated styles
  const cardAnimatedStyle = useAnimatedStyle(() => {
    const rotate = interpolate(
      translateX.value,
      [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
      [-15, 0, 15],
      Extrapolate.CLAMP
    );

    const opacity = interpolate(
      Math.abs(translateX.value),
      [0, SWIPE_THRESHOLD, SCREEN_WIDTH],
      [1, 1, 0],
      Extrapolate.CLAMP
    );

    return {
      transform: [
        { translateX: translateX.value },
        { translateY: translateY.value },
        { rotate: `${rotate}deg` },
        { scale: scale.value },
      ],
      opacity,
    };
  });

  // Left indicator (Delete)
  const leftIndicatorStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      translateX.value,
      [-SWIPE_THRESHOLD, 0, SWIPE_THRESHOLD],
      [0, 0, 1],
      Extrapolate.CLAMP
    );

    return { opacity };
  });

  // Right indicator (Keep)
  const rightIndicatorStyle = useAnimatedStyle(() => {
    const opacity = interpolate(
      translateX.value,
      [-SWIPE_THRESHOLD, 0, SWIPE_THRESHOLD],
      [1, 0, 0],
      Extrapolate.CLAMP
    );

    return { opacity };
  });

  // Hold indicator
  const holdIndicatorStyle = useAnimatedStyle(() => {
    return {
      opacity: holdProgress.value,
      transform: [{ scale: holdProgress.value }],
    };
  });

  // Render card content based on type
  const renderContent = () => {
    if (card.type === 'task') {
      const content = card.content as TaskCardContent;
      return (
        <>
          <Text variant="h3" style={styles.cardTitle}>
            {content.title}
          </Text>
          {content.description && (
            <Text variant="body" color={theme.colors.fogText} style={styles.cardDescription}>
              {content.description}
            </Text>
          )}
          {content.estimatedMinutes && (
            <Text variant="caption" color={theme.colors.champagneGold} style={styles.cardTime}>
              ~{content.estimatedMinutes} min
            </Text>
          )}
        </>
      );
    }

    return (
      <Text variant="h3" align="center">
        Swipe me!
      </Text>
    );
  };

  if (!isTopCard) {
    // Background card (next in stack)
    return (
      <Animated.View style={[styles.card, { transform: [{ scale: 0.95 }], opacity: 0.8 }]}>
        <BaseCard variant="elevated" padding="xl" borderRadius="xl" style={styles.cardInner}>
          <Text variant="body" color={theme.colors.fogText} align="center">
            Next card...
          </Text>
        </BaseCard>
      </Animated.View>
    );
  }

  return (
    <GestureDetector gesture={composed}>
      <Animated.View style={[styles.card, cardAnimatedStyle]}>
        {/* Swipe Indicators */}
        <Animated.View style={[styles.indicator, styles.leftIndicator, rightIndicatorStyle]}>
          <Text variant="h2" color={theme.colors.swipeLeft}>
            DELETE
          </Text>
        </Animated.View>

        <Animated.View style={[styles.indicator, styles.rightIndicator, leftIndicatorStyle]}>
          <Text variant="h2" color={theme.colors.swipeRight}>
            KEEP
          </Text>
        </Animated.View>

        <Animated.View style={[styles.indicator, styles.holdIndicator, holdIndicatorStyle]}>
          <Text variant="h2" color={theme.colors.champagneGold}>
            HOLD
          </Text>
        </Animated.View>

        {/* Card Content */}
        <BaseCard variant="elevated" padding="xl" borderRadius="xl" style={styles.cardInner}>
          {renderContent()}
        </BaseCard>
      </Animated.View>
    </GestureDetector>
  );
};

const styles = StyleSheet.create({
  card: {
    position: 'absolute',
    width: SCREEN_WIDTH * 0.9,
    height: SCREEN_HEIGHT * 0.65,
    alignSelf: 'center',
  },
  cardInner: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardTitle: {
    marginBottom: theme.spacing.md,
    textAlign: 'center',
  },
  cardDescription: {
    marginBottom: theme.spacing.sm,
    textAlign: 'center',
  },
  cardTime: {
    marginTop: theme.spacing.md,
  },
  indicator: {
    position: 'absolute',
    top: '40%',
    zIndex: 10,
  },
  leftIndicator: {
    left: theme.spacing.xl,
  },
  rightIndicator: {
    right: theme.spacing.xl,
  },
  holdIndicator: {
    alignSelf: 'center',
    top: '50%',
  },
});

export default SwipeCard;
