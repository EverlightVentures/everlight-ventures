/**
 * Animation Configurations - Reusable animation presets
 * Ensures consistent animation feel across the app
 */

import { Easing } from 'react-native-reanimated';

export const ANIMATION_DURATIONS = {
  instant: 100,
  fast: 200,
  normal: 300,
  slow: 500,
  verySlow: 800,
};

export const SPRING_CONFIGS = {
  // Bouncy spring for playful interactions
  bouncy: {
    damping: 10,
    stiffness: 100,
  },
  // Smooth spring for premium feel
  smooth: {
    damping: 15,
    stiffness: 150,
  },
  // Snappy spring for quick responses
  snappy: {
    damping: 20,
    stiffness: 400,
  },
  // Gentle spring for subtle movements
  gentle: {
    damping: 25,
    stiffness: 200,
  },
};

export const TIMING_CONFIGS = {
  // Quick linear for simple fades
  linear: {
    duration: ANIMATION_DURATIONS.fast,
    easing: Easing.linear,
  },
  // Ease out for natural deceleration
  easeOut: {
    duration: ANIMATION_DURATIONS.normal,
    easing: Easing.out(Easing.quad),
  },
  // Ease in for natural acceleration
  easeIn: {
    duration: ANIMATION_DURATIONS.normal,
    easing: Easing.in(Easing.quad),
  },
  // Ease in-out for smooth transitions
  easeInOut: {
    duration: ANIMATION_DURATIONS.normal,
    easing: Easing.inOut(Easing.quad),
  },
  // Bezier curve for premium feel
  luxury: {
    duration: ANIMATION_DURATIONS.slow,
    easing: Easing.bezier(0.25, 0.1, 0.25, 1),
  },
};

export const ENTRANCE_ANIMATIONS = {
  fadeIn: {
    duration: ANIMATION_DURATIONS.normal,
  },
  fadeInUp: {
    delay: 0,
    duration: ANIMATION_DURATIONS.normal,
  },
  fadeInDown: {
    delay: 0,
    duration: ANIMATION_DURATIONS.normal,
  },
  zoomIn: {
    duration: ANIMATION_DURATIONS.slow,
  },
  slideInRight: {
    duration: ANIMATION_DURATIONS.fast,
  },
  slideInLeft: {
    duration: ANIMATION_DURATIONS.fast,
  },
};

// Stagger delay for list items
export const getStaggerDelay = (index: number, baseDelay: number = 50) => {
  return index * baseDelay;
};

// Scale animation values
export const SCALE_VALUES = {
  press: 0.95,
  pressLight: 0.98,
  pressHeavy: 0.92,
  pop: 1.1,
  expand: 1.05,
};
