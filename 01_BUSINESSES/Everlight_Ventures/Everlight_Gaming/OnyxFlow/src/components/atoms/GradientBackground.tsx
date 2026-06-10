import React from 'react';
import { ViewProps } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '@config/theme';

interface GradientBackgroundProps extends ViewProps {
  variant?: 'dark' | 'gold' | 'accent';
  children: React.ReactNode;
}

export const GradientBackground: React.FC<GradientBackgroundProps> = ({
  variant = 'dark',
  children,
  style,
  ...props
}) => {
  const gradientColors =
    variant === 'gold'
      ? theme.colors.gradientGold
      : variant === 'accent'
        ? theme.colors.gradientAccent
        : theme.colors.gradientDark;

  return (
    <LinearGradient
      colors={gradientColors}
      start={{ x: 0, y: 0 }}
      end={{ x: 0, y: 1 }}
      style={[{ flex: 1 }, style]}
      {...props}
    >
      {children}
    </LinearGradient>
  );
};

export default GradientBackground;
