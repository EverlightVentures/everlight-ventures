/**
 * StreakManager Unit Tests
 */

import { StreakManager } from '../src/services/game/StreakManager';
import type { UserProfile } from '../src/types';

describe('StreakManager', () => {
  let streakManager: StreakManager;
  let mockUser: UserProfile;

  beforeEach(() => {
    streakManager = new StreakManager();
    mockUser = {
      id: 'user123',
      displayName: 'Test User',
      email: 'test@example.com',
      tokens: 100,
      currentStreak: 5,
      longestStreak: 10,
      streakShields: 2,
      totalGamesPlayed: 20,
      totalScore: 5000,
      highestScore: 500,
      lastPlayedDate: Date.now() - 24 * 60 * 60 * 1000, // Yesterday
      isPlusSubscriber: false,
      ownedDecks: [],
      ownedCosmetics: [],
      createdAt: Date.now() - 30 * 24 * 60 * 60 * 1000,
    };
  });

  describe('calculateStreak', () => {
    it('should start at streak 1 for first game ever', () => {
      const newUser = { ...mockUser, lastPlayedDate: undefined, currentStreak: 0 };

      const result = streakManager.calculateStreak(newUser);

      expect(result.newStreak).toBe(1);
      expect(result.usedShield).toBe(false);
      expect(result.streakBroken).toBe(false);
    });

    it('should maintain streak when playing on same day', () => {
      const sameDay = mockUser.lastPlayedDate!;

      const result = streakManager.calculateStreak(mockUser, sameDay);

      expect(result.newStreak).toBe(5); // Same as current streak
      expect(result.usedShield).toBe(false);
      expect(result.streakBroken).toBe(false);
    });

    it('should increment streak for consecutive day', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(10, 0, 0, 0);

      const today = new Date();
      today.setHours(15, 0, 0, 0);

      const user = { ...mockUser, lastPlayedDate: yesterday.getTime(), currentStreak: 5 };

      const result = streakManager.calculateStreak(user, today.getTime());

      expect(result.newStreak).toBe(6);
      expect(result.usedShield).toBe(false);
      expect(result.streakBroken).toBe(false);
    });

    it('should use shield when missing days and shields available', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const user = { ...mockUser, lastPlayedDate: threeDaysAgo.getTime(), currentStreak: 7, streakShields: 2 };

      const result = streakManager.calculateStreak(user);

      expect(result.newStreak).toBe(7); // Preserved
      expect(result.usedShield).toBe(true);
      expect(result.streakBroken).toBe(false);
    });

    it('should break streak when missing days and no shields', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const user = { ...mockUser, lastPlayedDate: threeDaysAgo.getTime(), currentStreak: 7, streakShields: 0 };

      const result = streakManager.calculateStreak(user);

      expect(result.newStreak).toBe(1); // Reset
      expect(result.usedShield).toBe(false);
      expect(result.streakBroken).toBe(true);
    });
  });

  describe('shouldOfferShield', () => {
    it('should not offer shield if no last played date', () => {
      const newUser = { ...mockUser, lastPlayedDate: undefined };

      const shouldOffer = streakManager.shouldOfferShield(newUser);

      expect(shouldOffer).toBe(false);
    });

    it('should not offer shield if no shields available', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const user = { ...mockUser, lastPlayedDate: threeDaysAgo.getTime(), streakShields: 0, currentStreak: 5 };

      const shouldOffer = streakManager.shouldOfferShield(user);

      expect(shouldOffer).toBe(false);
    });

    it('should not offer shield if streak is less than 3', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const user = { ...mockUser, lastPlayedDate: threeDaysAgo.getTime(), streakShields: 2, currentStreak: 2 };

      const shouldOffer = streakManager.shouldOfferShield(user);

      expect(shouldOffer).toBe(false);
    });

    it('should offer shield when missed 2+ days with streak >= 3', () => {
      const threeDaysAgo = new Date();
      threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);

      const user = { ...mockUser, lastPlayedDate: threeDaysAgo.getTime(), streakShields: 2, currentStreak: 5 };

      const shouldOffer = streakManager.shouldOfferShield(user);

      expect(shouldOffer).toBe(true);
    });

    it('should not offer shield if only missed 1 day', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);

      const user = { ...mockUser, lastPlayedDate: yesterday.getTime(), streakShields: 2, currentStreak: 5 };

      const shouldOffer = streakManager.shouldOfferShield(user);

      expect(shouldOffer).toBe(false);
    });
  });

  describe('getStreakMilestoneReward', () => {
    it('should return reward for 3-day milestone', () => {
      const result = streakManager.getStreakMilestoneReward(3);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(50);
      expect(result.shields).toBe(1);
      expect(result.message).toContain('3-day');
    });

    it('should return reward for 7-day milestone', () => {
      const result = streakManager.getStreakMilestoneReward(7);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(150);
      expect(result.shields).toBe(2);
      expect(result.message).toContain('week');
    });

    it('should return reward for 14-day milestone', () => {
      const result = streakManager.getStreakMilestoneReward(14);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(300);
      expect(result.shields).toBe(3);
      expect(result.message).toContain('2 weeks');
    });

    it('should return reward for 30-day milestone', () => {
      const result = streakManager.getStreakMilestoneReward(30);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(1000);
      expect(result.shields).toBe(5);
      expect(result.message).toContain('30 days');
    });

    it('should return no reward for non-milestone streak', () => {
      const result = streakManager.getStreakMilestoneReward(5);

      expect(result.isMilestone).toBe(false);
      expect(result.tokens).toBeUndefined();
      expect(result.shields).toBeUndefined();
      expect(result.message).toBeUndefined();
    });
  });

  describe('getGameMilestoneReward', () => {
    it('should return reward for 10 games', () => {
      const result = streakManager.getGameMilestoneReward(10);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(100);
      expect(result.message).toContain('10 games');
    });

    it('should return reward for 25 games', () => {
      const result = streakManager.getGameMilestoneReward(25);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(250);
      expect(result.message).toContain('25 games');
    });

    it('should return reward for 50 games', () => {
      const result = streakManager.getGameMilestoneReward(50);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(500);
      expect(result.message).toContain('Half century');
    });

    it('should return reward for 100 games', () => {
      const result = streakManager.getGameMilestoneReward(100);

      expect(result.isMilestone).toBe(true);
      expect(result.tokens).toBe(1500);
      expect(result.message).toContain('100 games');
    });

    it('should return no reward for non-milestone game count', () => {
      const result = streakManager.getGameMilestoneReward(15);

      expect(result.isMilestone).toBe(false);
      expect(result.tokens).toBeUndefined();
      expect(result.message).toBeUndefined();
    });
  });

  describe('isNewDay', () => {
    it('should return true if no last played date', () => {
      const isNew = streakManager.isNewDay(undefined);

      expect(isNew).toBe(true);
    });

    it('should return false if played on same day', () => {
      const today = new Date();
      today.setHours(10, 0, 0, 0);

      const laterToday = new Date();
      laterToday.setHours(18, 0, 0, 0);

      const isNew = streakManager.isNewDay(today.getTime(), laterToday.getTime());

      expect(isNew).toBe(false);
    });

    it('should return true if playing on new day', () => {
      const yesterday = new Date();
      yesterday.setDate(yesterday.getDate() - 1);
      yesterday.setHours(10, 0, 0, 0);

      const today = new Date();
      today.setHours(10, 0, 0, 0);

      const isNew = streakManager.isNewDay(yesterday.getTime(), today.getTime());

      expect(isNew).toBe(true);
    });
  });

  describe('getStreakMultiplier', () => {
    it('should return streak value as multiplier', () => {
      expect(streakManager.getStreakMultiplier(5)).toBe(5);
      expect(streakManager.getStreakMultiplier(10)).toBe(10);
      expect(streakManager.getStreakMultiplier(50)).toBe(50);
    });

    it('should cap multiplier at 100', () => {
      expect(streakManager.getStreakMultiplier(100)).toBe(100);
      expect(streakManager.getStreakMultiplier(150)).toBe(100);
      expect(streakManager.getStreakMultiplier(500)).toBe(100);
    });
  });

  describe('getStreakMessage', () => {
    it('should return appropriate message for zero streak', () => {
      const message = streakManager.getStreakMessage(0);
      expect(message).toContain('Start your streak');
    });

    it('should return appropriate message for day 1', () => {
      const message = streakManager.getStreakMessage(1);
      expect(message).toContain('Day 1');
    });

    it('should return appropriate message for early streak (2-6 days)', () => {
      const message = streakManager.getStreakMessage(5);
      expect(message).toContain('5 days');
      expect(message).toContain('Build the habit');
    });

    it('should return appropriate message for medium streak (7-13 days)', () => {
      const message = streakManager.getStreakMessage(10);
      expect(message).toContain('10 days');
      expect(message).toContain('Great momentum');
    });

    it('should return appropriate message for long streak (14-29 days)', () => {
      const message = streakManager.getStreakMessage(20);
      expect(message).toContain('20 days');
      expect(message).toContain('Unstoppable');
    });

    it('should return appropriate message for very long streak (30-99 days)', () => {
      const message = streakManager.getStreakMessage(50);
      expect(message).toContain('50 days');
      expect(message).toContain('Legendary');
    });

    it('should return appropriate message for hall of fame streak (100+ days)', () => {
      const message = streakManager.getStreakMessage(150);
      expect(message).toContain('150 days');
      expect(message).toContain('Hall of fame');
    });
  });
});
