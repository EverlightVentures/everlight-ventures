/**
 * GameBoard - Main game area with card stack and UI
 */

import React from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import { SwipeCard, TimerDisplay, ScoreDisplay } from '@components/molecules';
import { Icon } from '@components/atoms';
import type { Card, SwipeDirection } from '@types';
import { theme } from '@config/theme';

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

interface GameBoardProps {
  cards: Card[];
  currentCardIndex: number;
  score: number;
  combo: number;
  timeRemaining: number;
  onSwipe: (direction: SwipeDirection) => void;
}

export const GameBoard: React.FC<GameBoardProps> = ({
  cards,
  currentCardIndex,
  score,
  combo,
  timeRemaining,
  onSwipe,
}) => {
  const currentCard = cards[currentCardIndex];
  const nextCard = cards[currentCardIndex + 1];

  return (
    <View style={styles.container}>
      {/* Header - Timer & Score */}
      <View style={styles.header}>
        <TimerDisplay timeRemaining={timeRemaining} size="large" />
        <ScoreDisplay score={score} combo={combo} />
      </View>

      {/* Card Stack Area */}
      <View style={styles.cardStack}>
        {nextCard && (
          <SwipeCard
            key={nextCard.id}
            card={nextCard}
            onSwipe={onSwipe}
            isTopCard={false}
          />
        )}
        {currentCard && (
          <SwipeCard
            key={currentCard.id}
            card={currentCard}
            onSwipe={onSwipe}
            isTopCard={true}
          />
        )}
      </View>

      {/* Footer - Action Hints */}
      <View style={styles.footer}>
        <View style={styles.hint}>
          <Icon name="arrow-left" size={24} color={theme.colors.swipeLeft} />
          <View style={{ marginLeft: theme.spacing.sm }}>
            <View style={{ color: theme.colors.swipeLeft }}>Delete</View>
          </View>
        </View>

        <View style={styles.hint}>
          <Icon name="circle" size={24} color={theme.colors.champagneGold} />
          <View style={{ marginLeft: theme.spacing.sm }}>
            <View style={{ color: theme.colors.champagneGold }}>Hold</View>
          </View>
        </View>

        <View style={styles.hint}>
          <Icon name="arrow-right" size={24} color={theme.colors.swipeRight} />
          <View style={{ marginLeft: theme.spacing.sm }}>
            <View style={{ color: theme.colors.swipeRight }}>Keep</View>
          </View>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.lg,
    paddingBottom: theme.spacing.md,
  },
  cardStack: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    position: 'relative',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.xl,
    paddingTop: theme.spacing.md,
  },
  hint: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});

export default GameBoard;
