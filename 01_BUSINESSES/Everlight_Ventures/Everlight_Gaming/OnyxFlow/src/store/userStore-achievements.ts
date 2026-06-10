/**
 * Achievement tracking methods for userStore
 * (Separated for clarity)
 */

import type { Achievement } from '@types';

export const achievementMethods = {
  // Unlock an achievement
  unlockAchievement: (
    set: any,
    get: any,
    achievementId: string,
  ): Achievement | null => {
    const state = get();
    const achievement = state.achievements.find((a: Achievement) => a.id === achievementId);

    if (!achievement || achievement.unlockedAt) {
      return null; // Already unlocked or doesn't exist
    }

    // Mark as unlocked
    const updatedAchievements = state.achievements.map((a: Achievement) =>
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
      // Cosmetics would be added to ownedCosmetics
    }

    return achievement;
  },

  // Update achievement progress
  updateAchievementProgress: (
    set: any,
    get: any,
    achievementId: string,
    progress: number,
  ): void => {
    const state = get();
    const achievement = state.achievements.find((a: Achievement) => a.id === achievementId);

    if (!achievement || achievement.unlockedAt) {
      return; // Already unlocked or doesn't exist
    }

    // Update progress
    const updatedAchievements = state.achievements.map((a: Achievement) =>
      a.id === achievementId ? { ...a, progress } : a,
    );

    set({ achievements: updatedAchievements });

    // Check if should unlock
    if (progress >= achievement.target) {
      get().unlockAchievement(achievementId);
    }
  },

  // Check all achievements and unlock any that qualify
  checkAndUnlockAchievements: (set: any, get: any): Achievement[] => {
    const state = get();
    const { profile, achievements } = state;

    if (!profile) return [];

    const newlyUnlocked: Achievement[] = [];

    achievements.forEach((achievement: Achievement) => {
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
};
