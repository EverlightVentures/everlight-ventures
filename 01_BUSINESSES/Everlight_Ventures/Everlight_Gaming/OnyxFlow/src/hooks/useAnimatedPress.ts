/**
 * useAnimatedPress - Premium button press animation hook
 * Provides smooth scale and opacity feedback
 */

import { useSharedValue, useAnimatedStyle, withSpring, withTiming } from 'react-native-reanimated';

interface UseAnimatedPressConfig {
  scaleAmount?: number;
  springConfig?: {
    damping?: number;
    stiffness?: number;
  };
}

export const useAnimatedPress = (config: UseAnimatedPressConfig = {}) => {
  const {
    scaleAmount = 0.95,
    springConfig = { damping: 15, stiffness: 400 },
  } = config;

  const scale = useSharedValue(1);
  const opacity = useSharedValue(1);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const onPressIn = () => {
    scale.value = withSpring(scaleAmount, springConfig);
    opacity.value = withTiming(0.8, { duration: 100 });
  };

  const onPressOut = () => {
    scale.value = withSpring(1, springConfig);
    opacity.value = withTiming(1, { duration: 150 });
  };

  return {
    animatedStyle,
    onPressIn,
    onPressOut,
  };
};

export default useAnimatedPress;
