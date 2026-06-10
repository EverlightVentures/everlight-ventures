/**
 * StreakCounter - Displays current streak with flame icon
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Icon, Text } from '@components/atoms';
import { theme } from '@config/theme';

interface StreakCounterProps {
  streak: number;
  hasShield?: boolean;
}

export const StreakCounter: React.FC<StreakCounterProps> = ({ streak, hasShield = false }) => {
  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Icon
          name={streak > 0 ? 'zap' : 'zap-off'}
          size={32}
          color={streak > 0 ? theme.colors.champagneGold : theme.colors.fogText}
        />
        {hasShield && (
          <View style={styles.shieldBadge}>
            <Icon name="shield" size={16} color={theme.colors.success} />
          </View>
        )}
      </View>
      <Text variant="h2" color={theme.colors.champagneGold} align="center">
        {streak}
      </Text>
      <Text variant="caption" color={theme.colors.fogText} align="center">
        Day Streak
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  iconContainer: {
    position: 'relative',
    marginBottom: theme.spacing.sm,
  },
  shieldBadge: {
    position: 'absolute',
    top: -4,
    right: -4,
    backgroundColor: theme.colors.graphite,
    borderRadius: theme.borderRadius.full,
    padding: 2,
  },
});

export default StreakCounter;
