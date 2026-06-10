/**
 * RouletteScreen - Decision roulette animation and action reveal
 */

import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { GradientBackground, Button, Text } from '@components/atoms';
import { DecisionRoulette } from '@components/organisms';
import { getDeckById } from '@config/decks';
import { useGameStore } from '@store';
import type { HomeStackParamList } from '@navigation/types';
import { theme } from '@config/theme';

type RouletteScreenNavigationProp = NativeStackNavigationProp<HomeStackParamList, 'Roulette'>;
type RouletteScreenRouteProp = RouteProp<HomeStackParamList, 'Roulette'>;

export const RouletteScreen = () => {
  const navigation = useNavigation<RouletteScreenNavigationProp>();
  const route = useRoute<RouletteScreenRouteProp>();
  const { sessionId } = route.params;

  const { session } = useGameStore();
  const [spinComplete, setSpinComplete] = useState(false);

  if (!session || session.id !== sessionId) {
    return (
      <GradientBackground variant="dark">
        <View style={styles.container}>
          <Text variant="h2">Session not found</Text>
        </View>
      </GradientBackground>
    );
  }

  const deck = getDeckById(session.deckId);
  const actions = deck?.actions || [];

  const handleSpinComplete = (action: string) => {
    setTimeout(() => {
      setSpinComplete(true);
    }, 1000);
  };

  const handleContinue = () => {
    navigation.navigate('Checklist', { sessionId: session.id });
  };

  return (
    <GradientBackground variant="dark">
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text variant="displayMedium" align="center">
            Decision Time
          </Text>
          <Text variant="body" color={theme.colors.fogText} align="center">
            The wheel will choose your next action
          </Text>
        </View>

        {/* Roulette */}
        <View style={styles.rouletteContainer}>
          <DecisionRoulette
            actions={actions}
            selectedAction={session.selectedAction}
            onSpinComplete={handleSpinComplete}
            autoSpin={true}
          />
        </View>

        {/* Continue Button */}
        {spinComplete && (
          <View style={styles.footer}>
            <Button
              title="Continue to Checklist"
              variant="primary"
              size="large"
              fullWidth
              onPress={handleContinue}
            />
          </View>
        )}
      </View>
    </GradientBackground>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: theme.spacing.lg,
  },
  header: {
    marginTop: theme.spacing.xxxl,
    marginBottom: theme.spacing.xl,
  },
  rouletteContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  footer: {
    marginBottom: theme.spacing.lg,
  },
});

export default RouletteScreen;
