/**
 * ScoreDisplay - Live score counter with combo multiplier
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { Text } from '@components/atoms';
import { theme } from '@config/theme';

interface ScoreDisplayProps {
  score: number;
  combo?: number;
  showCombo?: boolean;
}

export const ScoreDisplay: React.FC<ScoreDisplayProps> = ({
  score,
  combo = 0,
  showCombo = true,
}) => {
  return (
    <View style={styles.container}>
      <Text variant="score" align="center">
        {score.toLocaleString()}
      </Text>
      <Text variant="caption" color={theme.colors.fogText} align="center">
        Score
      </Text>

      {showCombo && combo > 2 && (
        <Animated.View entering={FadeIn} exiting={FadeOut} style={styles.comboContainer}>
          <Text variant="h4" color={theme.colors.champagneGold}>
            {combo}x COMBO
          </Text>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  comboContainer: {
    marginTop: theme.spacing.sm,
  },
});

export default ScoreDisplay;
