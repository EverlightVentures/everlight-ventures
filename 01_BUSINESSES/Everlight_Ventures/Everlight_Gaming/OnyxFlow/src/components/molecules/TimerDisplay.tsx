/**
 * TimerDisplay - 60-second countdown timer
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Text } from '@components/atoms';
import { theme } from '@config/theme';

interface TimerDisplayProps {
  timeRemaining: number;
  size?: 'small' | 'large';
}

export const TimerDisplay: React.FC<TimerDisplayProps> = ({
  timeRemaining,
  size = 'large',
}) => {
  const isLowTime = timeRemaining <= 10;
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const displayTime = `${minutes}:${seconds.toString().padStart(2, '0')}`;

  return (
    <View style={styles.container}>
      <Text
        variant={size === 'large' ? 'timer' : 'h3'}
        color={isLowTime ? theme.colors.error : theme.colors.white}
        align="center"
      >
        {displayTime}
      </Text>
      {size === 'large' && (
        <Text variant="caption" color={theme.colors.fogText} align="center">
          Time Remaining
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
});

export default TimerDisplay;
