/**
 * DailyRewardService Unit Tests
 */

import { DailyRewardService } from '../src/services/game/DailyRewardService';
import type { UserProfile, DailyRewardHistory } from '../src/types';

describe('DailyRewardService', () => {
  let mockProfile: UserProfile;
  let mockHistory: DailyRewardHistory;

  beforeEach(() => {
    mockProfile = {
      id: 'user123',
      createdAt: Date.now() - 30 * 24 * 60 * 60 * 1000,
      currentStreak: 5,
      longestStreak: 10,
      totalGamesPlayed: 20,
      totalScore: 5000,
      highestScore: 500,
      tokens: 100,
      streakShields: 2,
      isPlusSubscriber: false,
      ownedDecks: [],
      ownedCosmetics: [],
    };

    mockHistory = {
      lastClaimDate: undefined,
      consecutiveDays: 0,
      totalRewardsClaimed: 0,
      currentCycle: 0,
      lifetimeTokensEarned: 0,
    };
  });

  describe('generateRewardCycle', () => {
    it('should generate 7 days of rewards', () => {
      const rewards = DailyRewardService.generateRewardCycle();

      expect(rewards).toHaveLength(7);
      expect(rewards[0].day).toBe(1);
      expect(rewards[6].day).toBe(7);
    });

    it('should apply 1.5x multiplier for plus subscribers', () => {
      const freeRewards = DailyRewardService.generateRewardCycle(undefined, false);
      const plusRewards = DailyRewardService.generateRewardCycle(undefined, true);

      expect(plusRewards[0].tokens).toBe(Math.floor(freeRewards[0].tokens * 1.5));
      expect(plusRewards[6].tokens).toBe(Math.floor(freeRewards[6].tokens * 1.5));
    });

    it('should include shields on day 3 and day 6', () => {
      const rewards = DailyRewardService.generateRewardCycle();

      expect(rewards[2].shields).toBe(1); // Day 3
      expect(rewards[5].shields).toBe(1); // Day 6
    });

    it('should include bonus multiplier on day 7', () => {
      const rewards = DailyRewardService.generateRewardCycle();

      expect(rewards[6].shields).toBe(2);
      expect(rewards[6].bonus).toBeDefined();
      expect(rewards[6].bonus?.type).toBe('multiplier');
      expect(rewards[6].bonus?.value).toBe(1.25);
    });

    it('should mark first day as available for new users', () => {
      const rewards = DailyRewardService.generateRewardCycle();

      expect(rewards[0].isAvailable).toBe(true);
      expect(rewards[0].isClaimed).toBe(false);
      expect(rewards[1].isAvailable).toBe(false);
    });

    it('should mark correct day based on consecutive days', () => {
      const history: DailyRewardHistory = {
        consecutiveDays: 2,
        totalRewardsClaimed: 2,
        currentCycle: 1,
        lifetimeTokensEarned: 125,
      };

      const rewards = DailyRewardService.generateRewardCycle(history);

      expect(rewards[0].isClaimed).toBe(true); // Day 1
      expect(rewards[1].isClaimed).toBe(true); // Day 2
      expect(rewards[2].isAvailable).toBe(true); // Day 3
      expect(rewards[2].isClaimed).toBe(false);
    });

    it('should cycle back to day 1 after day 7', () => {
      const history: DailyRewardHistory = {
        consecutiveDays: 7,
        totalRewardsClaimed: 7,
        currentCycle: 1,
        lifetimeTokensEarned: 1000,
      };

      const rewards = DailyRewardService.generateRewardCycle(history);

      expect(rewards[0].isAvailable).toBe(true); // Back to day 1
      expect(rewards[0].isClaimed).toBe(false);
    });
  });

  describe('isRewardAvailable', () => {
    it('should return true for first time claiming', () => {
      const available = DailyRewardService.isRewardAvailable(undefined);

      expect(available).toBe(true);
    });

    it('should return true for new day', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const history: DailyRewardHistory = {
        lastClaimDate: yesterday.getTime(),
        consecutiveDays: 3,
        totalRewardsClaimed: 3,
        currentCycle: 1,
        lifetimeTokensEarned: 225,
      };

      const available = DailyRewardService.isRewardAvailable(history);

      expect(available).toBe(true);
    });

    it('should return false if already claimed today', () => {
      const today = new Date();
      today.setHours(10, 0, 0, 0);

      const history: DailyRewardHistory = {
        lastClaimDate: today.getTime(),
        consecutiveDays: 3,
        totalRewardsClaimed: 3,
        currentCycle: 1,
        lifetimeTokensEarned: 225,
      };

      const available = DailyRewardService.isRewardAvailable(history);

      expect(available).toBe(false);
    });
  });

  describe('getCurrentDay', () => {
    it('should return 1 for new users', () => {
      const day = DailyRewardService.getCurrentDay(undefined);

      expect(day).toBe(1);
    });

    it('should return correct day within cycle', () => {
      const history: DailyRewardHistory = {
        consecutiveDays: 3,
        totalRewardsClaimed: 3,
        currentCycle: 1,
        lifetimeTokensEarned: 225,
      };

      const day = DailyRewardService.getCurrentDay(history);

      expect(day).toBe(4); // consecutiveDays 3 means next is day 4
    });

    it('should cycle back to 1 after 7 days', () => {
      const history: DailyRewardHistory = {
        consecutiveDays: 7,
        totalRewardsClaimed: 7,
        currentCycle: 1,
        lifetimeTokensEarned: 1000,
      };

      const day = DailyRewardService.getCurrentDay(history);

      expect(day).toBe(1);
    });

    it('should handle multiple cycles correctly', () => {
      const history: DailyRewardHistory = {
        consecutiveDays: 17, // 2 full cycles + 3 days
        totalRewardsClaimed: 17,
        currentCycle: 3,
        lifetimeTokensEarned: 2000,
      };

      const day = DailyRewardService.getCurrentDay(history);

      expect(day).toBe(4); // 17 % 7 = 3, so next is day 4
    });
  });

  describe('claimReward', () => {
    it('should successfully claim first reward', () => {
      const result = DailyRewardService.claimReward(mockProfile);

      expect(result.success).toBe(true);
      expect(result.reward).toBeDefined();
      expect(result.reward?.day).toBe(1);
      expect(result.reward?.tokens).toBe(50);
      expect(result.updatedHistory.consecutiveDays).toBe(1);
      expect(result.updatedHistory.totalRewardsClaimed).toBe(1);
    });

    it('should apply plus subscriber multiplier', () => {
      const plusProfile = { ...mockProfile, isPlusSubscriber: true };
      const result = DailyRewardService.claimReward(plusProfile);

      expect(result.success).toBe(true);
      expect(result.reward?.tokens).toBe(75); // 50 * 1.5
    });

    it('should fail if already claimed today', () => {
      const profileWithToday = {
        ...mockProfile,
        dailyRewardHistory: {
          lastClaimDate: Date.now(),
          consecutiveDays: 3,
          totalRewardsClaimed: 3,
          currentCycle: 1,
          lifetimeTokensEarned: 225,
        },
      };

      const result = DailyRewardService.claimReward(profileWithToday);

      expect(result.success).toBe(false);
      expect(result.error).toContain('already claimed');
    });

    it('should maintain consecutive days within 48 hour grace period', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(10, 0, 0, 0);

      const profileWithHistory = {
        ...mockProfile,
        dailyRewardHistory: {
          lastClaimDate: yesterday.getTime(),
          consecutiveDays: 3,
          totalRewardsClaimed: 3,
          currentCycle: 1,
          lifetimeTokensEarned: 225,
        },
      };

      const result = DailyRewardService.claimReward(profileWithHistory);

      expect(result.success).toBe(true);
      expect(result.updatedHistory.consecutiveDays).toBe(4); // Incremented
    });

    it('should reset consecutive days after 48 hour grace period', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const profileWithHistory = {
        ...mockProfile,
        dailyRewardHistory: {
          lastClaimDate: threeDaysAgo.getTime(),
          consecutiveDays: 3,
          totalRewardsClaimed: 3,
          currentCycle: 1,
          lifetimeTokensEarned: 225,
        },
      };

      const result = DailyRewardService.claimReward(profileWithHistory);

      expect(result.success).toBe(true);
      expect(result.updatedHistory.consecutiveDays).toBe(1); // Reset
    });

    it('should accumulate lifetime tokens earned', () => {
      const profileWithHistory = {
        ...mockProfile,
        dailyRewardHistory: {
          consecutiveDays: 2,
          totalRewardsClaimed: 2,
          currentCycle: 1,
          lifetimeTokensEarned: 125,
        },
      };

      const result = DailyRewardService.claimReward(profileWithHistory);

      expect(result.success).toBe(true);
      expect(result.updatedHistory.lifetimeTokensEarned).toBe(225); // 125 + 100 (day 3)
    });

    it('should increment current cycle after completing 7 days', () => {
      const profileWithHistory = {
        ...mockProfile,
        dailyRewardHistory: {
          lastClaimDate: Date.now() - 24 * 60 * 60 * 1000,
          consecutiveDays: 6,
          totalRewardsClaimed: 6,
          currentCycle: 1,
          lifetimeTokensEarned: 900,
        },
      };

      const result = DailyRewardService.claimReward(profileWithHistory);

      expect(result.success).toBe(true);
      expect(result.updatedHistory.consecutiveDays).toBe(7);
      expect(result.updatedHistory.currentCycle).toBe(2); // (6 + 1) / 7 = 1, floor(1) + 1 = 2
    });
  });

  describe('getTimeUntilNextReward', () => {
    it('should return 0 for new users', () => {
      const timeUntil = DailyRewardService.getTimeUntilNextReward(undefined);

      expect(timeUntil).toBe(0);
    });

    it('should return time until midnight', () => {
      const now = new Date();
      now.setHours(14, 0, 0, 0); // 2 PM today

      const history: DailyRewardHistory = {
        lastClaimDate: now.getTime(),
        consecutiveDays: 3,
        totalRewardsClaimed: 3,
        currentCycle: 1,
        lifetimeTokensEarned: 225,
      };

      const timeUntil = DailyRewardService.getTimeUntilNextReward(history);

      // Should be around 10 hours (until midnight)
      expect(timeUntil).toBeGreaterThan(0);
      expect(timeUntil).toBeLessThanOrEqual(24 * 60 * 60 * 1000);
    });

    it('should return 0 if next reward is available', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const history: DailyRewardHistory = {
        lastClaimDate: yesterday.getTime(),
        consecutiveDays: 3,
        totalRewardsClaimed: 3,
        currentCycle: 1,
        lifetimeTokensEarned: 225,
      };

      const timeUntil = DailyRewardService.getTimeUntilNextReward(history);

      expect(timeUntil).toBe(0);
    });
  });

  describe('formatTimeRemaining', () => {
    it('should format hours and minutes', () => {
      const twoHours = 2 * 60 * 60 * 1000;
      const formatted = DailyRewardService.formatTimeRemaining(twoHours);

      expect(formatted).toBe('2h 0m');
    });

    it('should format hours and minutes with partial hour', () => {
      const timeMs = 3 * 60 * 60 * 1000 + 45 * 60 * 1000; // 3h 45m
      const formatted = DailyRewardService.formatTimeRemaining(timeMs);

      expect(formatted).toBe('3h 45m');
    });

    it('should format minutes only when less than 1 hour', () => {
      const fortyMinutes = 40 * 60 * 1000;
      const formatted = DailyRewardService.formatTimeRemaining(fortyMinutes);

      expect(formatted).toBe('40m');
    });

    it('should handle zero time', () => {
      const formatted = DailyRewardService.formatTimeRemaining(0);

      expect(formatted).toBe('0m');
    });
  });
});
