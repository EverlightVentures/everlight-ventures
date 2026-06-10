/**
 * OnyxFlow Design System
 * Luxury-branded theme with onyx black, graphite, and champagne gold
 */

export const colors = {
  // Primary Brand Colors
  onyxBlack: '#0A0A0A',
  graphite: '#2C2C2E',
  champagneGold: '#D4AF37',
  fogText: '#8E8E93',

  // Neutrals
  white: '#FFFFFF',
  softWhite: '#F5F5F7',
  darkGray: '#1C1C1E',
  mediumGray: '#48484A',
  lightGray: '#C7C7CC',

  // Functional Colors
  success: '#34C759',
  error: '#FF3B30',
  warning: '#FF9500',
  info: '#007AFF',

  // Gradients (use with LinearGradient)
  gradientDark: ['#0A0A0A', '#1C1C1E'] as const,
  gradientGold: ['#D4AF37', '#F4E5B5'] as const,
  gradientAccent: ['#2C2C2E', '#48484A'] as const,
  gradientBlackToGraphite: ['#0A0A0A', '#2C2C2E'] as const,

  // Game-Specific Colors
  swipeLeft: '#FF3B30', // Delete/Archive
  swipeRight: '#34C759', // Keep/Favorite
  swipeHold: '#D4AF37', // Hold for roulette
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
  xxxl: 64,
};

export const typography = {
  // Display (luxury serif - Playfair Display)
  display: {
    fontFamily: 'PlayfairDisplay-Bold',
    fontSize: 48,
    lineHeight: 56,
    letterSpacing: -0.5,
    color: colors.white,
  },
  displayMedium: {
    fontFamily: 'PlayfairDisplay-Bold',
    fontSize: 36,
    lineHeight: 44,
    letterSpacing: -0.3,
    color: colors.white,
  },

  // Headings (Montserrat)
  h1: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 32,
    lineHeight: 40,
    letterSpacing: -0.2,
    color: colors.white,
  },
  h2: {
    fontFamily: 'Montserrat-SemiBold',
    fontSize: 24,
    lineHeight: 32,
    letterSpacing: 0,
    color: colors.white,
  },
  h3: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 20,
    lineHeight: 28,
    letterSpacing: 0.15,
    color: colors.white,
  },
  h4: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 18,
    lineHeight: 24,
    letterSpacing: 0.15,
    color: colors.white,
  },

  // Body (Inter)
  body: {
    fontFamily: 'Inter-Regular',
    fontSize: 16,
    lineHeight: 24,
    letterSpacing: 0.5,
    color: colors.softWhite,
  },
  bodyBold: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 16,
    lineHeight: 24,
    letterSpacing: 0.5,
    color: colors.softWhite,
  },
  bodySmall: {
    fontFamily: 'Inter-Regular',
    fontSize: 14,
    lineHeight: 20,
    letterSpacing: 0.25,
    color: colors.softWhite,
  },

  // Captions & Labels
  caption: {
    fontFamily: 'Inter-Regular',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.4,
    color: colors.fogText,
  },
  captionBold: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.4,
    color: colors.fogText,
  },
  label: {
    fontFamily: 'Inter-Medium',
    fontSize: 14,
    lineHeight: 20,
    letterSpacing: 0.1,
    color: colors.white,
  },

  // Button Text
  button: {
    fontFamily: 'Montserrat-SemiBold',
    fontSize: 16,
    lineHeight: 24,
    letterSpacing: 1.25,
    color: colors.white,
  },
  buttonSmall: {
    fontFamily: 'Montserrat-Medium',
    fontSize: 14,
    lineHeight: 20,
    letterSpacing: 1,
    color: colors.white,
  },

  // Numbers (for scores, timers)
  score: {
    fontFamily: 'Montserrat-Bold',
    fontSize: 48,
    lineHeight: 56,
    letterSpacing: 0,
    color: colors.champagneGold,
  },
  timer: {
    fontFamily: 'Montserrat-SemiBold',
    fontSize: 32,
    lineHeight: 40,
    letterSpacing: 0,
    color: colors.white,
  },
};

export const borderRadius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 24,
  full: 9999,
};

export const shadows = {
  none: {
    shadowColor: colors.onyxBlack,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0,
    shadowRadius: 0,
    elevation: 0,
  },
  sm: {
    shadowColor: colors.onyxBlack,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  md: {
    shadowColor: colors.onyxBlack,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  lg: {
    shadowColor: colors.onyxBlack,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 8,
  },
  gold: {
    shadowColor: colors.champagneGold,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 6,
  },
};

export const animations = {
  // Timing
  quick: 200,
  medium: 400,
  slow: 600,
  verySlow: 1000,

  // Spring configs
  spring: {
    damping: 20,
    stiffness: 90,
    mass: 1,
  },
  springBouncy: {
    damping: 15,
    stiffness: 120,
    mass: 1,
  },
  springSubtle: {
    damping: 25,
    stiffness: 80,
    mass: 1,
  },
};

export const haptics = {
  light: 'impactLight' as const,
  medium: 'impactMedium' as const,
  heavy: 'impactHeavy' as const,
  success: 'notificationSuccess' as const,
  warning: 'notificationWarning' as const,
  error: 'notificationError' as const,
  selection: 'selection' as const,
};

export const theme = {
  colors,
  spacing,
  typography,
  borderRadius,
  shadows,
  animations,
  haptics,
};

export type Theme = typeof theme;

export default theme;
