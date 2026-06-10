/**
 * DecisionRoulette - Spinning wheel animation to select action
 */

import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withSpring,
  Easing,
  runOnJS,
} from 'react-native-reanimated';
import { Canvas, Circle, Group, Text as SkiaText, useFont } from '@shopify/react-native-skia';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { Text, Card } from '@components/atoms';
import { theme } from '@config/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const WHEEL_SIZE = SCREEN_WIDTH * 0.8;
const SEGMENT_COUNT = 6;

interface DecisionRouletteProps {
  actions: string[];
  selectedAction?: string;
  onSpinComplete?: (action: string) => void;
  autoSpin?: boolean;
}

export const DecisionRoulette: React.FC<DecisionRouletteProps> = ({
  actions,
  selectedAction,
  onSpinComplete,
  autoSpin = false,
}) => {
  const rotation = useSharedValue(0);
  const scale = useSharedValue(1);
  const [isSpinning, setIsSpinning] = useState(false);
  const [finalAction, setFinalAction] = useState<string | null>(null);

  useEffect(() => {
    if (autoSpin && !isSpinning) {
      setTimeout(() => {
        spin();
      }, 500);
    }
  }, [autoSpin]);

  const triggerHaptic = () => {
    ReactNativeHapticFeedback.trigger('impactMedium', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });
  };

  const triggerSuccessHaptic = () => {
    ReactNativeHapticFeedback.trigger('notificationSuccess', {
      enableVibrateFallback: true,
      ignoreAndroidSystemSettings: false,
    });
  };

  const spin = () => {
    if (isSpinning) return;

    setIsSpinning(true);
    setFinalAction(null);

    // Determine which action to land on
    const selectedIndex = selectedAction
      ? actions.indexOf(selectedAction)
      : Math.floor(Math.random() * Math.min(actions.length, SEGMENT_COUNT));

    // Calculate rotation needed
    const segmentAngle = 360 / SEGMENT_COUNT;
    const targetAngle = 360 * 3 + selectedIndex * segmentAngle; // 3 full spins + target

    // Spin animation with haptic feedback at intervals
    rotation.value = withTiming(
      targetAngle,
      {
        duration: 3000,
        easing: Easing.bezier(0.25, 0.1, 0.25, 1), // Ease out
      },
      (finished) => {
        if (finished) {
          runOnJS(triggerSuccessHaptic)();
          runOnJS(setFinalAction)(actions[selectedIndex]);
          runOnJS(setIsSpinning)(false);
          if (onSpinComplete) {
            runOnJS(onSpinComplete)(actions[selectedIndex]);
          }
        }
      }
    );

    // Scale pulse during spin
    scale.value = withSpring(1.05, { damping: 10 }, () => {
      scale.value = withSpring(1);
    });

    // Trigger haptic at start
    triggerHaptic();

    // Haptic feedback during spin
    const hapticInterval = setInterval(() => {
      triggerHaptic();
    }, 300);

    setTimeout(() => {
      clearInterval(hapticInterval);
    }, 3000);
  };

  const wheelAnimatedStyle = useAnimatedStyle(() => {
    return {
      transform: [{ rotate: `${rotation.value}deg` }, { scale: scale.value }],
    };
  });

  // Prepare actions for display (max 6)
  const displayActions = actions.slice(0, SEGMENT_COUNT);

  return (
    <View style={styles.container}>
      {/* Wheel Container */}
      <View style={styles.wheelContainer}>
        <Animated.View style={[styles.wheel, wheelAnimatedStyle]}>
          {/* Simple colored wheel using gradient cards */}
          <View style={styles.wheelCircle}>
            {displayActions.map((action, index) => {
              const segmentAngle = 360 / SEGMENT_COUNT;
              const startAngle = index * segmentAngle;

              return (
                <View
                  key={index}
                  style={[
                    styles.segment,
                    {
                      transform: [{ rotate: `${startAngle}deg` }],
                      backgroundColor:
                        index % 2 === 0 ? theme.colors.graphite : theme.colors.darkGray,
                    },
                  ]}
                >
                  <View style={styles.segmentText}>
                    <Text
                      variant="caption"
                      color={theme.colors.white}
                      style={{ textAlign: 'center' }}
                    >
                      {action.substring(0, 20)}
                      {action.length > 20 ? '...' : ''}
                    </Text>
                  </View>
                </View>
              );
            })}
          </View>

          {/* Center circle */}
          <View style={styles.centerCircle}>
            <Text variant="h4" color={theme.colors.champagneGold} align="center">
              {isSpinning ? '...' : 'SPIN'}
            </Text>
          </View>
        </Animated.View>

        {/* Pointer */}
        <View style={styles.pointer} />
      </View>

      {/* Selected Action Display */}
      {finalAction && (
        <Card variant="elevated" padding="lg" style={styles.resultCard}>
          <Text variant="caption" color={theme.colors.fogText} align="center">
            Your Action
          </Text>
          <Text variant="h3" align="center" style={{ marginTop: theme.spacing.sm }}>
            {finalAction}
          </Text>
        </Card>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  wheelContainer: {
    width: WHEEL_SIZE,
    height: WHEEL_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  wheel: {
    width: WHEEL_SIZE,
    height: WHEEL_SIZE,
    justifyContent: 'center',
    alignItems: 'center',
  },
  wheelCircle: {
    width: WHEEL_SIZE,
    height: WHEEL_SIZE,
    borderRadius: WHEEL_SIZE / 2,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 4,
    borderColor: theme.colors.champagneGold,
  },
  segment: {
    position: 'absolute',
    width: WHEEL_SIZE / 2,
    height: WHEEL_SIZE,
    left: WHEEL_SIZE / 2,
    top: 0,
    transformOrigin: 'left center',
  },
  segmentText: {
    position: 'absolute',
    top: '45%',
    left: '20%',
    width: '60%',
  },
  centerCircle: {
    position: 'absolute',
    width: WHEEL_SIZE * 0.3,
    height: WHEEL_SIZE * 0.3,
    borderRadius: (WHEEL_SIZE * 0.3) / 2,
    backgroundColor: theme.colors.onyxBlack,
    borderWidth: 3,
    borderColor: theme.colors.champagneGold,
    justifyContent: 'center',
    alignItems: 'center',
  },
  pointer: {
    position: 'absolute',
    top: -10,
    width: 0,
    height: 0,
    borderLeftWidth: 15,
    borderRightWidth: 15,
    borderTopWidth: 30,
    borderLeftColor: 'transparent',
    borderRightColor: 'transparent',
    borderTopColor: theme.colors.champagneGold,
  },
  resultCard: {
    marginTop: theme.spacing.xl,
    width: SCREEN_WIDTH * 0.9,
  },
});

export default DecisionRoulette;
