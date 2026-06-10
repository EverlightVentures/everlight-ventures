/**
 * User Type Definitions
 */

export interface UserProfile {
  id: string;
  displayName?: string;
  email?: string;
  googleId?: string;
  createdAt: number;
  currentStreak: number;
  longestStreak: number;
  totalGamesPlayed: number;
  totalScore: number;
  highestScore: number;
  tokens: number;
  streakShields: number;
  isPlusSubscriber: boolean;
  subscriptionStartDate?: number;
  subscriptionTier?: 1 | 2; // Tier 1: $4.99, Tier 2: $19.99
  lastPlayedDate?: number;
  dailyRewardHistory?: DailyRewardHistory;
  ownedDecks: string[];
  ownedCosmetics: string[];
}

export interface UserStatistics {
  totalPlayTime: number; // seconds
  averageScore: number;
  perfectRuns: number;
  totalSwipes: number;
  favoriteSwipeDirection: 'left' | 'right' | 'hold';
  mostPlayedDeck: string;
  checklistCompletionRate: number;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'games' | 'streaks' | 'score' | 'special';
  unlockedAt?: number;
  progress: number;
  target: number;
  reward?: {
    tokens?: number;
    cosmetic?: string;
    shield?: number;
  };
}

export interface DailyReward {
  day: number;
  tokens: number;
  shields?: number;
  bonus?: {
    type: 'cosmetic' | 'deck' | 'multiplier';
    value: string | number;
  };
  isClaimed: boolean;
  isAvailable: boolean;
}

export interface DailyRewardHistory {
  lastClaimDate?: number;
  consecutiveDays: number;
  totalRewardsClaimed: number;
  currentCycle: number; // Which 7-day cycle (resets every 7 days)
  lifetimeTokensEarned: number;
}
