/**
 * GameScreen - Active 60-second game session
 */

import React, { useEffect } from 'react';
import { View, StyleSheet, BackHandler } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { GradientBackground } from '@components/atoms';
import { GameBoard } from '@components/organisms';
import { useGameStore, useUserStore } from '@store';
import { StreakManager, ScoreCalculator } from '@services/game';
import { AdService } from '@services/monetization/AdService';
import type { HomeStackParamList } from '@navigation/types';
import { TOKENS } from '@config/constants';

type GameScreenNavigationProp = NativeStackNavigationProp<HomeStackParamList, 'Game'>;
type GameScreenRouteProp = RouteProp<HomeStackParamList, 'Game'>;

export const GameScreen = () => {
  const navigation = useNavigation<GameScreenNavigationProp>();
  const route = useRoute<GameScreenRouteProp>();
  const { deckId } = route.params;

  const {
    session,
    cards,
    currentCardIndex,
    timeRemaining,
    startGame,
    swipe,
    endGame,
    resetGame,
  } = useGameStore();

  const {
    profile,
    initializeUser,
    incrementGamesPlayed,
    updateHighScore,
    updateTotalScore,
    updateStreak,
    addTokens,
    checkAndUnlockAchievements,
  } = useUserStore();

  // Initialize user if needed
  useEffect(() => {
    if (!profile) {
      initializeUser();
    }
  }, [profile, initializeUser]);

  // Start game on mount
  useEffect(() => {
    if (profile) {
      startGame(profile.id, deckId);
    }

    return () => {
      resetGame();
    };
  }, [profile, deckId, startGame, resetGame]);

  // Handle game completion
  useEffect(() => {
    if (session && session.status === 'completed' && profile) {
      // Update streak
      const streakResult = StreakManager.calculateStreak(profile);
      updateStreak(streakResult.newStreak, streakResult.usedShield);

      // Calculate final score with all multipliers
      const { finalScore, breakdown } = ScoreCalculator.calculateFinalScore(session, profile);

      // Update session with final score
      session.score = finalScore;

      // Update user stats
      incrementGamesPlayed();
      updateHighScore(finalScore);
      updateTotalScore(finalScore);

      // Calculate and award tokens
      const isNewDay = StreakManager.isNewDay(profile.lastPlayedDate);
      const tokensEarned = ScoreCalculator.calculateTokensEarned(session, profile, isNewDay);

      if (tokensEarned > 0) {
        addTokens(tokensEarned, 'Game completion rewards');
      }

      // Check for milestone rewards
      const streakMilestone = StreakManager.getStreakMilestoneReward(streakResult.newStreak);
      if (streakMilestone.isMilestone && streakMilestone.tokens) {
        addTokens(streakMilestone.tokens, `${streakResult.newStreak}-day streak milestone`);
      }

      const gameMilestone = StreakManager.getGameMilestoneReward(profile.totalGamesPlayed + 1);
      if (gameMilestone.isMilestone && gameMilestone.tokens) {
        addTokens(gameMilestone.tokens, `${profile.totalGamesPlayed + 1} games milestone`);
      }

      // Check for new achievements
      setTimeout(() => {
        checkAndUnlockAchievements();
      }, 500);

      // Show interstitial ad (for free users) before results
      AdService.showInterstitialAfterGame(profile.isPlusSubscriber)
        .then(() => {
          // Navigate to results after ad (or immediately if no ad)
          navigation.replace('Results', { sessionId: session.id });
        })
        .catch(error => {
          console.error('Ad error:', error);
          // Navigate anyway if ad fails
          navigation.replace('Results', { sessionId: session.id });
        });
    }
  }, [
    session,
    profile,
    navigation,
    incrementGamesPlayed,
    updateHighScore,
    updateTotalScore,
    updateStreak,
    addTokens,
    checkAndUnlockAchievements,
  ]);

  // Handle back button
  useEffect(() => {
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => {
      // Prevent going back during active game
      return true;
    });

    return () => backHandler.remove();
  }, []);

  const handleSwipe = (direction: 'left' | 'right' | 'hold') => {
    const streakMultiplier = profile?.currentStreak || 0;
    swipe(direction, streakMultiplier);
  };

  if (!session || !profile) {
    return (
      <GradientBackground variant="dark">
        <View style={styles.loading}>
          {/* Loading state */}
        </View>
      </GradientBackground>
    );
  }

  return (
    <GradientBackground variant="dark">
      <GameBoard
        cards={cards}
        currentCardIndex={currentCardIndex}
        score={session.score}
        combo={session.comboCount}
        timeRemaining={timeRemaining}
        onSwipe={handleSwipe}
      />
    </GradientBackground>
  );
};

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default GameScreen;
