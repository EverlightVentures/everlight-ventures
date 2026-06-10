/**
 * Realm Database Schemas
 */

import Realm from 'realm';

/**
 * User Profile Schema
 */
export class UserProfileSchema extends Realm.Object {
  id!: string;
  displayName?: string;
  email?: string;
  googleId?: string;
  createdAt!: number;
  updatedAt!: number;
  currentStreak!: number;
  longestStreak!: number;
  totalGamesPlayed!: number;
  totalScore!: number;
  highestScore!: number;
  tokens!: number;
  streakShields!: number;
  isPlusSubscriber!: boolean;
  subscriptionStartDate?: number;
  subscriptionTier?: number;
  lastPlayedDate?: number;
  ownedDecks!: string;
  ownedCosmetics!: string;

  static schema: Realm.ObjectSchema = {
    name: 'UserProfile',
    primaryKey: 'id',
    properties: {
      id: 'string',
      displayName: 'string?',
      email: 'string?',
      googleId: 'string?',
      createdAt: 'int',
      updatedAt: 'int',
      currentStreak: { type: 'int', default: 0 },
      longestStreak: { type: 'int', default: 0 },
      totalGamesPlayed: { type: 'int', default: 0 },
      totalScore: { type: 'int', default: 0 },
      highestScore: { type: 'int', default: 0 },
      tokens: { type: 'int', default: 100 },
      streakShields: { type: 'int', default: 0 },
      isPlusSubscriber: { type: 'bool', default: false },
      subscriptionStartDate: 'int?',
      subscriptionTier: 'int?',
      lastPlayedDate: 'int?',
      ownedDecks: { type: 'string', default: '[]' }, // JSON array
      ownedCosmetics: { type: 'string', default: '[]' }, // JSON array
    },
  };
}

/**
 * Daily Reward History Schema
 */
export class DailyRewardHistorySchema extends Realm.Object {
  userId!: string;
  lastClaimDate?: number;
  consecutiveDays!: number;
  totalRewardsClaimed!: number;
  currentCycle!: number;
  lifetimeTokensEarned!: number;

  static schema: Realm.ObjectSchema = {
    name: 'DailyRewardHistory',
    primaryKey: 'userId',
    properties: {
      userId: 'string',
      lastClaimDate: 'int?',
      consecutiveDays: { type: 'int', default: 0 },
      totalRewardsClaimed: { type: 'int', default: 0 },
      currentCycle: { type: 'int', default: 0 },
      lifetimeTokensEarned: { type: 'int', default: 0 },
    },
  };
}

/**
 * Game Session Schema
 */
export class GameSessionSchema extends Realm.Object {
  id!: string;
  userId!: string;
  deckId!: string;
  startTime!: number;
  endTime?: number;
  score!: number;
  baseScore!: number;
  multiplier!: number;
  cardsProcessed!: number;
  leftSwipes!: number;
  rightSwipes!: number;
  holds!: number;
  comboCount!: number;
  maxCombo!: number;
  status!: string;
  selectedAction?: string;
  tokensEarned?: number;
  checklist!: string; // JSON array

  static schema: Realm.ObjectSchema = {
    name: 'GameSession',
    primaryKey: 'id',
    properties: {
      id: 'string',
      userId: 'string',
      deckId: 'string',
      startTime: 'int',
      endTime: 'int?',
      score: { type: 'int', default: 0 },
      baseScore: { type: 'int', default: 0 },
      multiplier: { type: 'double', default: 1.0 },
      cardsProcessed: { type: 'int', default: 0 },
      leftSwipes: { type: 'int', default: 0 },
      rightSwipes: { type: 'int', default: 0 },
      holds: { type: 'int', default: 0 },
      comboCount: { type: 'int', default: 0 },
      maxCombo: { type: 'int', default: 0 },
      status: 'string',
      selectedAction: 'string?',
      tokensEarned: 'int?',
      checklist: { type: 'string', default: '[]' }, // JSON array
    },
  };
}

/**
 * Achievement Schema
 */
export class AchievementSchema extends Realm.Object {
  id!: string;
  userId!: string;
  achievementId!: string;
  progress!: number;
  unlockedAt?: number;

  static schema: Realm.ObjectSchema = {
    name: 'Achievement',
    primaryKey: 'id',
    properties: {
      id: 'string',
      userId: 'string',
      achievementId: 'string',
      progress: { type: 'int', default: 0 },
      unlockedAt: 'int?',
    },
  };
}

/**
 * Settings Schema
 */
export class SettingsSchema extends Realm.Object {
  userId!: string;
  notificationsEnabled!: boolean;
  soundEnabled!: boolean;
  hapticEnabled!: boolean;
  theme!: string;
  language!: string;

  static schema: Realm.ObjectSchema = {
    name: 'Settings',
    primaryKey: 'userId',
    properties: {
      userId: 'string',
      notificationsEnabled: { type: 'bool', default: true },
      soundEnabled: { type: 'bool', default: true },
      hapticEnabled: { type: 'bool', default: true },
      theme: { type: 'string', default: 'dark' },
      language: { type: 'string', default: 'en' },
    },
  };
}
