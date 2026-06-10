/**
 * App Constants
 */

export const APP_CONFIG = {
  name: 'OnyxFlow',
  version: '1.0.0',
  tagline: 'Swipe into focus — luxury in a minute',
};

export const GAME_CONFIG = {
  sessionDuration: 60, // seconds
  minCardsPerSession: 10,
  maxCardsPerSession: 30,
  checklistItemCount: 3,
  sprintTimerDuration: 5 * 60, // 5 minutes in seconds
};

export const SCORING = {
  swipeLeft: 10,
  swipeRight: 10,
  hold: 20,
  speedBonusThreshold: 45, // seconds remaining
  speedBonusPoints: 5,
  completionRateThreshold: 0.9, // 90%
  completionBonus: 50,
  streakMultiplierPerDay: 0.1, // 10% per streak day
  plusSubscriberMultiplier: 1.5, // 50% bonus
};

export const TOKENS = {
  dailyRunReward: 50,
  perfectRunBonus: 25,
  checklistCompletedBonus: 25,
  extraSessionCost: 80,
  rerollCost: 40,
  streakShieldCost: 200,
  deckRentalCost: 250,
  cosmeticMinCost: 300,
  cosmeticMaxCost: 600,
};

export const STREAKS = {
  shieldDaysProtection: 1,
  milestones: [3, 7, 14, 30] as const,
  gameMilestones: [10, 25, 50, 100] as const,
};

export const STORAGE_KEYS = {
  user: 'user_profile',
  session: 'current_session',
  settings: 'app_settings',
  streaks: 'user_streaks',
  achievements: 'user_achievements',
  decks: 'owned_decks',
  purchases: 'purchase_history',
  tokens: 'user_tokens',
};

export const PERMISSIONS = {
  android: {
    readExternalStorage: 'android.permission.READ_EXTERNAL_STORAGE',
    readMediaImages: 'android.permission.READ_MEDIA_IMAGES',
  },
};

export const DECK_IDS = {
  photos: 'deck_photos',
  home: 'deck_home',
  work: 'deck_work',
  travel: 'deck_travel',
} as const;

export const SUBSCRIPTION_TIER_CHANGE_MONTH = 4; // Month when price changes from $4.99 to $19.99
