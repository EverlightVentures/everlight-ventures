/**
 * TokenDisplay - Shows user's token balance with animation
 */

import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withSequence,
} from 'react-native-reanimated';
import { Icon, Text } from '@components/atoms';
import { theme } from '@config/theme';

interface TokenDisplayProps {
  tokens: number;
  size?: 'small' | 'medium' | 'large';
  showLabel?: boolean;
}

export const TokenDisplay: React.FC<TokenDisplayProps> = ({
  tokens,
  size = 'medium',
  showLabel = true,
}) => {
  const scale = useSharedValue(1);

  useEffect(() => {
    // Animate when tokens change
    scale.value = withSequence(
      withSpring(1.2, { damping: 10 }),
      withSpring(1, { damping: 10 })
    );
  }, [tokens]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const iconSize = size === 'small' ? 16 : size === 'large' ? 32 : 24;
  const textVariant = size === 'small' ? 'caption' : size === 'large' ? 'h3' : 'body';

  return (
    <View style={styles.container}>
      <Animated.View style={[styles.content, animatedStyle]}>
        <Icon name="dollar-sign" size={iconSize} color={theme.colors.champagneGold} />
        <Text
          variant={textVariant}
          color={theme.colors.champagneGold}
          style={{ marginLeft: theme.spacing.xs }}
        >
          {tokens.toLocaleString()}
        </Text>
      </Animated.View>
      {showLabel && (
        <Text variant="caption" color={theme.colors.fogText} style={{ marginTop: 2 }}>
          Tokens
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});

export default TokenDisplay;
