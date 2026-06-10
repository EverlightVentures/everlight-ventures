/**
 * User Store - User profile and progress management
 */

import { create } from 'zustand';
import type { UserProfile, Achievement } from '@types';
import { v4 as uuidv4 } from 'uuid';
import { ACHIEVEMENTS } from '@config/achievements';
import StreakManager from '@services/game/StreakManager';

interface UserState {
  // State
  profile: UserProfile | null;
  achievements: Achievement[];
  isLoading: boolean;

  // Actions
  initializeUser: () => void;
  updateStreak: (newStreak: number, usedShield?: boolean) => void;
  addTokens: (amount: number, reason?: string) => void;
  spendTokens: (amount: number) => boolean;
  addStreakShields: (amount: number) => void;
  useStreakShield: () => boolean;
  incrementGamesPlayed: () => void;
  updateHighScore: (score: number) => void;
  updateTotalScore: (score: number) => void;
  unlockAchievement: (achievementId: string) => Achievement | null;
  updateAchievementProgress: (achievementId: string, progress: number) => void;
  checkAndUnlockAchievements: () => Achievement[];
}

export const useUserStore = create<UserState>((set, get) => ({
  // Initial state
  profile: null,
  achievements: ACHIEVEMENTS.map(a => ({ ...a })),
  isLoading: false,

  // Initialize a new user (or load from storage later)
  initializeUser: () => {
    const profile: UserProfile = {
      id: uuidv4(),
      createdAt: Date.now(),
      currentStreak: 0,
      longestStreak: 0,
      totalGamesPlayed: 0,
      totalScore: 0,
      highestScore: 0,
      tokens: 0,
      streakShields: 0,
      isPlusSubscriber: false,
      ownedDecks: ['deck_photos', 'deck_home'], // Photos + Home deck free for testing
      ownedCosmetics: [],
    };

    set({ profile, achievements: ACHIEVEMENTS.map(a => ({ ...a })) });
  },

  // Update streak
  updateStreak: (newStreak: number, usedShield: boolean = false) => {
    set(state => {
      if (!state.profile) return state;

      const updatedProfile = {
        ...state.profile,
        currentStreak: newStreak,
        longestStreak: Math.max(state.profile.longestStreak, newStreak),
        lastPlayedDate: Date.now(),
      };

      // Deduct shield if used
      if (usedShield && state.profile.streakShields > 0) {
        updatedProfile.streakShields = state.profile.streakShields - 1;
      }

      return { profile: updatedProfile };
    });

    // Check for streak achievements
    get().updateAchievementProgress('streak_3', newStreak);
    get().updateAchievementProgress('streak_7', newStreak);
    get().updateAchievementProgress('streak_14', newStreak);
    get().updateAchievementProgress('streak_30', newStreak);
    get().updateAchievementProgress('streak_100', newStreak);
  },

  // Add tokens
  addTokens: (amount: number, reason?: string) => {
    set(state => {
      if (!state.profile) return state;

      console.log(`Added ${amount} tokens: ${reason || 'No reason'}`);

      return {
        profile: {
          ...state.profile,
          tokens: state.profile.tokens + amount,
        },
      };
    });
  },

  // Add streak shields
  addStreakShields: (amount: number) => {
    set(state => {
      if (!state.profile) return state;

      return {
        profile: {
          ...state.profile,
          streakShields: state.profile.streakShields + amount,
        },
      };
    });
  },

  // Spend tokens
  spendTokens: (amount: number) => {
    const { profile } = get();
    if (!profile || profile.tokens < amount) {
      return false;
    }

    set(state => ({
      profile: state.profile
        ? {
            ...state.profile,
            tokens: state.profile.tokens - amount,
          }
        : null,
    }));

    return true;
  },

  // Use streak shield
  useStreakShield: () => {
    const { profile } = get();
    if (!profile || profile.streakShields < 1) {
      return false;
    }

    set(state => ({
      profile: state.profile
        ? {
            ...state.profile,
            streakShields: state.profile.streakShields - 1,
          }
        : null,
    }));

    return true;
  },

  // Increment games played
  incrementGamesPlayed: () => {
    set(state => {
      if (!state.profile) return state;

      const newTotal = state.profile.totalGamesPlayed + 1;

      return {
        profile: {
          ...state.profile,
          totalGamesPlayed: newTotal,
        },
      };
    });

    // Check for game count achievements
    const { profile } = get();
    if (profile) {
      get().updateAchievementProgress('first_game', profile.totalGamesPlayed);
      get().updateAchievementProgress('games_10', profile.totalGamesPlayed);
      get().updateAchievementProgress('games_25', profile.totalGamesPlayed);
      get().updateAchievementProgress('games_50', profile.totalGamesPlayed);
      get().updateAchievementProgress('games_100', profile.totalGamesPlayed);
    }
  },

  // Update high score
  updateHighScore: (score: number) => {
    set(state => {
      if (!state.profile) return state;

      return {
        profile: {
          ...state.profile,
          highestScore: Math.max(state.profile.highestScore, score),
        },
      };
    });
  },

  // Update total score
  updateTotalScore: (score: number) => {
    set(state => {
      if (!state.profile) return state;

      return {
        profile: {
          ...state.profile,
          totalScore: state.profile.totalScore + score,
        },
      };
    });

    // Check for score achievements
    const { profile } = get();
    if (profile) {
      get().updateAchievementProgress('score_1k', profile.highestScore);
      get().updateAchievementProgress('score_5k', profile.highestScore);
      get().updateAchievementProgress('score_10k', profile.highestScore);
    }
  },

  // Unlock achievement
  unlockAchievement: (achievementId: string) => {
    const { achievements } = get();
    const achievement = achievements.find(a => a.id === achievementId);

    if (!achievement || achievement.unlockedAt) {
      return null; // Already unlocked or doesn't exist
    }

    // Mark as unlocked
    const updatedAchievements = achievements.map(a =>
      a.id === achievementId ? { ...a, unlockedAt: Date.now() } : a,
    );

    set({ achievements: updatedAchievements });

    // Grant rewards
    if (achievement.reward) {
      if (achievement.reward.tokens) {
        get().addTokens(achievement.reward.tokens, `Achievement: ${achievement.title}`);
      }
      if (achievement.reward.shield) {
        get().addStreakShields(achievement.reward.shield);
      }
    }

    return achievement;
  },

  // Update achievement progress
  updateAchievementProgress: (achievementId: string, progress: number) => {
    const { achievements } = get();
    const achievement = achievements.find(a => a.id === achievementId);

    if (!achievement || achievement.unlockedAt) {
      return; // Already unlocked or doesn't exist
    }

    // Update progress
    const updatedAchievements = achievements.map(a =>
      a.id === achievementId ? { ...a, progress } : a,
    );

    set({ achievements: updatedAchievements });

    // Check if should unlock
    if (progress >= achievement.target) {
      get().unlockAchievement(achievementId);
    }
  },

  // Check and unlock all qualifying achievements
  checkAndUnlockAchievements: () => {
    const { profile, achievements } = get();

    if (!profile) return [];

    const newlyUnlocked: Achievement[] = [];

    achievements.forEach(achievement => {
      if (achievement.unlockedAt) return; // Already unlocked

      let shouldUnlock = false;

      // Check based on category
      switch (achievement.category) {
        case 'games':
          shouldUnlock = profile.totalGamesPlayed >= achievement.target;
          break;
        case 'streaks':
          shouldUnlock = profile.currentStreak >= achievement.target;
          break;
        case 'score':
          shouldUnlock = profile.highestScore >= achievement.target;
          break;
        default:
          break;
      }

      if (shouldUnlock) {
        const unlocked = get().unlockAchievement(achievement.id);
        if (unlocked) {
          newlyUnlocked.push(unlocked);
        }
      }
    });

    return newlyUnlocked;
  },

  // Daily Reward methods
  claimDailyReward: () => {
    const { profile } = get();
    if (!profile) return null;

    const { DailyRewardService } = require('@services/game/DailyRewardService');
    const result = DailyRewardService.claimReward(profile);

    if (result.success && result.reward) {
      // Update profile with new history
      set(state => ({
        profile: state.profile
          ? {
              ...state.profile,
              dailyRewardHistory: result.updatedHistory,
            }
          : null,
      }));

      // Grant rewards
      get().addTokens(result.reward.tokens, 'Daily reward');
      if (result.reward.shields) {
        get().addStreakShields(result.reward.shields);
      }

      return result.reward;
    }

    return null;
  },

  getDailyRewards: () => {
    const { profile } = get();
    const { DailyRewardService } = require('@services/game/DailyRewardService');
    return DailyRewardService.generateRewardCycle(
      profile?.dailyRewardHistory,
      profile?.isPlusSubscriber
    );
  },

  isDailyRewardAvailable: () => {
    const { profile } = get();
    const { DailyRewardService } = require('@services/game/DailyRewardService');
    return DailyRewardService.isRewardAvailable(profile?.dailyRewardHistory);
  },

  getTimeUntilNextReward: () => {
    const { profile } = get();
    const { DailyRewardService } = require('@services/game/DailyRewardService');
    return DailyRewardService.getTimeUntilNextReward(profile?.dailyRewardHistory);
  },
}));

export default useUserStore;
