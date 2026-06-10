/**
 * ScoreCalculator - Advanced scoring with all multipliers
 */

import type { GameSession, UserProfile } from '@types';
import { SCORING, GAME_CONFIG } from '@config/constants';

export class ScoreCalculator {
  /**
   * Calculate final score with all multipliers
   */
  calculateFinalScore(session: GameSession, user: UserProfile): {
    finalScore: number;
    breakdown: ScoreBreakdown;
  } {
    let score = session.baseScore;

    // 1. Streak multiplier
    const streakMultiplier = 1 + user.currentStreak * SCORING.streakMultiplierPerDay;
    const streakBonus = Math.round(session.baseScore * (streakMultiplier - 1));

    // 2. Speed bonus (already added during swipes, but track it)
    const speedBonus = 0; // Calculated during gameplay

    // 3. Completion bonus
    const completionRate = session.cardsProcessed / GAME_CONFIG.maxCardsPerSession;
    const completionBonus =
      completionRate >= SCORING.completionRateThreshold ? SCORING.completionBonus : 0;

    // 4. Combo bonus (already in base score)
    const comboBonus = 0; // Already factored in

    // 5. Plus subscriber bonus
    const plusMultiplier = user.isPlusSubscriber ? SCORING.plusSubscriberMultiplier : 1;
    const plusBonus = user.isPlusSubscriber
      ? Math.round(session.baseScore * (plusMultiplier - 1))
      : 0;

    // 6. Perfect run bonus (no holds, all keeps or deletes)
    const isPerfectRun = session.holds === 0 && session.cardsProcessed >= 15;
    const perfectBonus = isPerfectRun ? 100 : 0;

    // Calculate final score
    const totalBeforeMultipliers = session.baseScore + completionBonus + perfectBonus;
    const finalScore = Math.round(totalBeforeMultipliers * streakMultiplier * plusMultiplier);

    const breakdown: ScoreBreakdown = {
      baseScore: session.baseScore,
      streakBonus,
      speedBonus,
      completionBonus,
      comboBonus,
      plusBonus,
      perfectBonus,
      streakMultiplier,
      plusMultiplier,
      finalScore,
    };

    return { finalScore, breakdown };
  }

  /**
   * Calculate tokens earned from session
   */
  calculateTokensEarned(session: GameSession, user: UserProfile, isNewDay: boolean): number {
    let tokens = 0;

    // Daily run reward (50 tokens)
    if (isNewDay) {
      tokens += 50;
    }

    // Perfect run bonus (25 tokens)
    const isPerfectRun = session.holds === 0 && session.cardsProcessed >= 15;
    if (isPerfectRun) {
      tokens += 25;
    }

    // High score bonus (if beat personal best)
    if (session.score > user.highestScore) {
      tokens += 50;
    }

    // Combo achievement bonuses
    if (session.maxCombo >= 10) {
      tokens += 25;
    }

    return tokens;
  }

  /**
   * Check if score qualifies for achievements
   */
  checkScoreAchievements(score: number): string[] {
    const unlocked: string[] = [];

    if (score >= 1000) unlocked.push('score_1k');
    if (score >= 5000) unlocked.push('score_5k');
    if (score >= 10000) unlocked.push('score_10k');
    if (score >= 50000) unlocked.push('score_50k');

    return unlocked;
  }

  /**
   * Get score rank/grade
   */
  getScoreRank(score: number): {
    rank: 'F' | 'D' | 'C' | 'B' | 'A' | 'S' | 'SS';
    message: string;
    color: string;
  } {
    if (score >= 10000)
      return { rank: 'SS', message: 'Flow Master!', color: '#D4AF37' };
    if (score >= 5000) return { rank: 'S', message: 'Exceptional!', color: '#FFD700' };
    if (score >= 2000) return { rank: 'A', message: 'Excellent!', color: '#34C759' };
    if (score >= 1000) return { rank: 'B', message: 'Great!', color: '#007AFF' };
    if (score >= 500) return { rank: 'C', message: 'Good!', color: '#8E8E93' };
    if (score >= 200) return { rank: 'D', message: 'Keep trying!', color: '#FF9500' };
    return { rank: 'F', message: 'Practice more!', color: '#FF3B30' };
  }
}

interface ScoreBreakdown {
  baseScore: number;
  streakBonus: number;
  speedBonus: number;
  completionBonus: number;
  comboBonus: number;
  plusBonus: number;
  perfectBonus: number;
  streakMultiplier: number;
  plusMultiplier: number;
  finalScore: number;
}

export default new ScoreCalculator();
