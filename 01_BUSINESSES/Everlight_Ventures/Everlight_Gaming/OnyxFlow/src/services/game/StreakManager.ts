/**
 * StreakManager - Daily streak tracking, shields, and reset logic
 */

import type { UserProfile } from '@types';
import { STREAKS } from '@config/constants';

export class StreakManager {
  /**
   * Calculate new streak based on last played date
   */
  calculateStreak(user: UserProfile, newGameDate: number = Date.now()): {
    newStreak: number;
    usedShield: boolean;
    streakBroken: boolean;
  } {
    const lastPlayed = user.lastPlayedDate;

    // First game ever
    if (!lastPlayed) {
      return {
        newStreak: 1,
        usedShield: false,
        streakBroken: false,
      };
    }

    // Get dates at midnight (ignore time)
    const lastDate = new Date(lastPlayed).setHours(0, 0, 0, 0);
    const todayDate = new Date(newGameDate).setHours(0, 0, 0, 0);
    const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));

    // Same day - no change
    if (diffDays === 0) {
      return {
        newStreak: user.currentStreak,
        usedShield: false,
        streakBroken: false,
      };
    }

    // Consecutive day - increment
    if (diffDays === 1) {
      return {
        newStreak: user.currentStreak + 1,
        usedShield: false,
        streakBroken: false,
      };
    }

    // Missed day(s) - check for shield
    if (diffDays > 1 && user.streakShields > 0) {
      // Use shield to preserve streak
      return {
        newStreak: user.currentStreak,
        usedShield: true,
        streakBroken: false,
      };
    }

    // No shield - streak broken
    return {
      newStreak: 1,
      usedShield: false,
      streakBroken: true,
    };
  }

  /**
   * Check if user should be prompted to use a shield
   */
  shouldOfferShield(user: UserProfile, newGameDate: number = Date.now()): boolean {
    if (!user.lastPlayedDate || user.streakShields < 1) {
      return false;
    }

    const lastDate = new Date(user.lastPlayedDate).setHours(0, 0, 0, 0);
    const todayDate = new Date(newGameDate).setHours(0, 0, 0, 0);
    const diffDays = Math.floor((todayDate - lastDate) / (1000 * 60 * 60 * 24));

    // Offer shield if missed 2+ days and have a streak worth saving
    return diffDays > 1 && user.currentStreak >= 3;
  }

  /**
   * Get streak milestone rewards
   */
  getStreakMilestoneReward(streak: number): {
    isMilestone: boolean;
    tokens?: number;
    shields?: number;
    message?: string;
  } {
    if (!STREAKS.milestones.includes(streak as any)) {
      return { isMilestone: false };
    }

    const rewards = {
      3: { tokens: 50, shields: 1, message: '3-day streak! Keep it up!' },
      7: { tokens: 150, shields: 2, message: '1 week streak! Impressive!' },
      14: { tokens: 300, shields: 3, message: '2 weeks! You\'re on fire!' },
      30: { tokens: 1000, shields: 5, message: '30 days! Legendary streak!' },
    };

    const reward = rewards[streak as keyof typeof rewards];

    return {
      isMilestone: true,
      ...reward,
    };
  }

  /**
   * Get game count milestone rewards
   */
  getGameMilestoneReward(gamesPlayed: number): {
    isMilestone: boolean;
    tokens?: number;
    message?: string;
  } {
    if (!STREAKS.gameMilestones.includes(gamesPlayed as any)) {
      return { isMilestone: false };
    }

    const rewards = {
      10: { tokens: 100, message: 'First 10 games complete!' },
      25: { tokens: 250, message: '25 games! You\'re getting good!' },
      50: { tokens: 500, message: 'Half century! Amazing!' },
      100: { tokens: 1500, message: '100 games! Flow master!' },
    };

    const reward = rewards[gamesPlayed as keyof typeof rewards];

    return {
      isMilestone: true,
      ...reward,
    };
  }

  /**
   * Check if it's a new day (for daily rewards)
   */
  isNewDay(lastPlayedDate: number | undefined, currentDate: number = Date.now()): boolean {
    if (!lastPlayedDate) return true;

    const lastDate = new Date(lastPlayedDate).setHours(0, 0, 0, 0);
    const todayDate = new Date(currentDate).setHours(0, 0, 0, 0);

    return todayDate > lastDate;
  }

  /**
   * Get streak multiplier for scoring
   */
  getStreakMultiplier(streak: number): number {
    // Max out at 10x multiplier for 100+ day streaks
    return Math.min(streak, 100);
  }

  /**
   * Get motivational message based on streak
   */
  getStreakMessage(streak: number): string {
    if (streak === 0) return 'Start your streak today!';
    if (streak === 1) return 'Day 1! Keep going!';
    if (streak < 7) return `${streak} days! Build the habit!`;
    if (streak < 14) return `${streak} days! Great momentum!`;
    if (streak < 30) return `${streak} days! Unstoppable!`;
    if (streak < 100) return `${streak} days! Legendary!`;
    return `${streak} days! Hall of fame!`;
  }
}

export default new StreakManager();
