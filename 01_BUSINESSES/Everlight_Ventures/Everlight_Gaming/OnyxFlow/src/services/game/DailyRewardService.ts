/**
 * DailyRewardService - Manages daily login rewards
 * 7-day cycle that resets, with increasing rewards
 */

import type { DailyReward, DailyRewardHistory, UserProfile } from '@types';

export class DailyRewardService {
  /**
   * Generate 7-day reward cycle
   */
  static generateRewardCycle(
    history?: DailyRewardHistory,
    isPlusSubscriber: boolean = false
  ): DailyReward[] {
    const multiplier = isPlusSubscriber ? 1.5 : 1;
    const currentDay = history?.consecutiveDays ? (history.consecutiveDays % 7) + 1 : 1;

    const baseRewards: Omit<DailyReward, 'isClaimed' | 'isAvailable'>[] = [
      { day: 1, tokens: Math.floor(50 * multiplier) },
      { day: 2, tokens: Math.floor(75 * multiplier) },
      { day: 3, tokens: Math.floor(100 * multiplier), shields: 1 },
      { day: 4, tokens: Math.floor(150 * multiplier) },
      { day: 5, tokens: Math.floor(200 * multiplier) },
      { day: 6, tokens: Math.floor(250 * multiplier), shields: 1 },
      {
        day: 7,
        tokens: Math.floor(500 * multiplier),
        shields: 2,
        bonus: { type: 'multiplier', value: 1.25 },
      },
    ];

    return baseRewards.map(reward => ({
      ...reward,
      isClaimed: reward.day < currentDay,
      isAvailable: reward.day === currentDay,
    }));
  }

  /**
   * Check if reward is available today
   */
  static isRewardAvailable(history?: DailyRewardHistory): boolean {
    if (!history?.lastClaimDate) {
      return true; // First time claiming
    }

    const now = Date.now();
    const lastClaim = new Date(history.lastClaimDate);
    const today = new Date(now);

    // Check if it's a new day
    return (
      lastClaim.getDate() !== today.getDate() ||
      lastClaim.getMonth() !== today.getMonth() ||
      lastClaim.getFullYear() !== today.getFullYear()
    );
  }

  /**
   * Get current day in reward cycle (1-7)
   */
  static getCurrentDay(history?: DailyRewardHistory): number {
    if (!history) return 1;
    return (history.consecutiveDays % 7) + 1;
  }

  /**
   * Claim today's reward
   */
  static claimReward(
    profile: UserProfile
  ): {
    success: boolean;
    reward?: DailyReward;
    updatedHistory: DailyRewardHistory;
    error?: string;
  } {
    const history = profile.dailyRewardHistory;

    if (!this.isRewardAvailable(history)) {
      return {
        success: false,
        error: 'Reward already claimed today',
        updatedHistory: history || this.getDefaultHistory(),
      };
    }

    const currentDay = this.getCurrentDay(history);
    const rewards = this.generateRewardCycle(history, profile.isPlusSubscriber);
    const todayReward = rewards.find(r => r.day === currentDay);

    if (!todayReward) {
      return {
        success: false,
        error: 'No reward available',
        updatedHistory: history || this.getDefaultHistory(),
      };
    }

    // Check if consecutive (within 24 hours of last claim)
    const isConsecutive = history?.lastClaimDate
      ? Date.now() - history.lastClaimDate < 48 * 60 * 60 * 1000 // 48h grace period
      : true;

    const updatedHistory: DailyRewardHistory = {
      lastClaimDate: Date.now(),
      consecutiveDays: isConsecutive ? (history?.consecutiveDays || 0) + 1 : 1,
      totalRewardsClaimed: (history?.totalRewardsClaimed || 0) + 1,
      currentCycle: Math.floor(((history?.consecutiveDays || 0) + 1) / 7) + 1,
      lifetimeTokensEarned: (history?.lifetimeTokensEarned || 0) + todayReward.tokens,
    };

    return {
      success: true,
      reward: { ...todayReward, isClaimed: true },
      updatedHistory,
    };
  }

  /**
   * Get time until next reward is available
   */
  static getTimeUntilNextReward(history?: DailyRewardHistory): number {
    if (!history?.lastClaimDate) return 0;

    const lastClaim = new Date(history.lastClaimDate);
    const tomorrow = new Date(lastClaim);
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);

    return Math.max(0, tomorrow.getTime() - Date.now());
  }

  /**
   * Format time remaining
   */
  static formatTimeRemaining(milliseconds: number): string {
    const hours = Math.floor(milliseconds / (1000 * 60 * 60));
    const minutes = Math.floor((milliseconds % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }

  /**
   * Get default history for new users
   */
  private static getDefaultHistory(): DailyRewardHistory {
    return {
      consecutiveDays: 0,
      totalRewardsClaimed: 0,
      currentCycle: 0,
      lifetimeTokensEarned: 0,
    };
  }
}
