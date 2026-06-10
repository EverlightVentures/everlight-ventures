/**
 * Database Service - Realm database operations
 */

import Realm from 'realm';
import {
  UserProfileSchema,
  DailyRewardHistorySchema,
  GameSessionSchema,
  AchievementSchema,
  SettingsSchema,
} from './schemas';
import type {
  UserProfile,
  DailyRewardHistory,
  GameSession,
  Achievement,
} from '@types';

export class DatabaseService {
  private static instance: DatabaseService;
  private realm: Realm | null = null;
  private initPromise: Promise<void> | null = null;

  private constructor() {}

  static getInstance(): DatabaseService {
    if (!DatabaseService.instance) {
      DatabaseService.instance = new DatabaseService();
    }
    return DatabaseService.instance;
  }

  /**
   * Initialize Realm database
   */
  async initialize(): Promise<void> {
    if (this.realm) {
      return;
    }

    if (this.initPromise) {
      return this.initPromise;
    }

    this.initPromise = (async () => {
      try {
        this.realm = await Realm.open({
          schema: [
            UserProfileSchema,
            DailyRewardHistorySchema,
            GameSessionSchema,
            AchievementSchema,
            SettingsSchema,
          ],
          schemaVersion: 1,
          onMigration: (_oldRealm: Realm, _newRealm: Realm) => {
            // Handle migrations here if schema changes
          },
        });
      } catch (error) {
        console.error('Failed to initialize Realm database:', error);
        throw error;
      }
    })();

    return this.initPromise;
  }

  /**
   * Get Realm instance (throws if not initialized)
   */
  private getRealm(): Realm {
    if (!this.realm) {
      throw new Error('Database not initialized. Call initialize() first.');
    }
    return this.realm;
  }

  /**
   * Close database connection
   */
  close(): void {
    if (this.realm && !this.realm.isClosed) {
      this.realm.close();
      this.realm = null;
      this.initPromise = null;
    }
  }

  // ==================== User Profile ====================

  /**
   * Create or update user profile
   */
  async saveUserProfile(profile: UserProfile): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    realm.write(() => {
      realm.create(
        'UserProfile',
        {
          id: profile.id,
          displayName: profile.displayName,
          email: profile.email,
          googleId: profile.googleId,
          createdAt: profile.createdAt,
          updatedAt: Date.now(),
          currentStreak: profile.currentStreak,
          longestStreak: profile.longestStreak,
          totalGamesPlayed: profile.totalGamesPlayed,
          totalScore: profile.totalScore,
          highestScore: profile.highestScore,
          tokens: profile.tokens,
          streakShields: profile.streakShields,
          isPlusSubscriber: profile.isPlusSubscriber,
          subscriptionStartDate: profile.subscriptionStartDate,
          subscriptionTier: profile.subscriptionTier,
          lastPlayedDate: profile.lastPlayedDate,
          ownedDecks: JSON.stringify(profile.ownedDecks),
          ownedCosmetics: JSON.stringify(profile.ownedCosmetics),
        },
        Realm.UpdateMode.Modified
      );
    });
  }

  /**
   * Get user profile by ID
   */
  async getUserProfile(userId: string): Promise<UserProfile | null> {
    await this.initialize();
    const realm = this.getRealm();

    const profile = realm.objectForPrimaryKey<UserProfileSchema>('UserProfile', userId);
    if (!profile) {
      return null;
    }

    return {
      id: profile.id,
      displayName: profile.displayName,
      email: profile.email,
      googleId: profile.googleId,
      createdAt: profile.createdAt,
      currentStreak: profile.currentStreak,
      longestStreak: profile.longestStreak,
      totalGamesPlayed: profile.totalGamesPlayed,
      totalScore: profile.totalScore,
      highestScore: profile.highestScore,
      tokens: profile.tokens,
      streakShields: profile.streakShields,
      isPlusSubscriber: profile.isPlusSubscriber,
      subscriptionStartDate: profile.subscriptionStartDate,
      subscriptionTier: profile.subscriptionTier as 1 | 2 | undefined,
      lastPlayedDate: profile.lastPlayedDate,
      ownedDecks: JSON.parse(profile.ownedDecks),
      ownedCosmetics: JSON.parse(profile.ownedCosmetics),
    };
  }

  /**
   * Delete user profile
   */
  async deleteUserProfile(userId: string): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    realm.write(() => {
      const profile = realm.objectForPrimaryKey('UserProfile', userId);
      if (profile) {
        realm.delete(profile);
      }
    });
  }

  // ==================== Daily Reward History ====================

  /**
   * Save daily reward history
   */
  async saveDailyRewardHistory(userId: string, history: DailyRewardHistory): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    realm.write(() => {
      realm.create(
        'DailyRewardHistory',
        {
          userId,
          lastClaimDate: history.lastClaimDate,
          consecutiveDays: history.consecutiveDays,
          totalRewardsClaimed: history.totalRewardsClaimed,
          currentCycle: history.currentCycle,
          lifetimeTokensEarned: history.lifetimeTokensEarned,
        },
        Realm.UpdateMode.Modified
      );
    });
  }

  /**
   * Get daily reward history
   */
  async getDailyRewardHistory(userId: string): Promise<DailyRewardHistory | null> {
    await this.initialize();
    const realm = this.getRealm();

    const history = realm.objectForPrimaryKey<DailyRewardHistorySchema>(
      'DailyRewardHistory',
      userId
    );
    if (!history) {
      return null;
    }

    return {
      lastClaimDate: history.lastClaimDate,
      consecutiveDays: history.consecutiveDays,
      totalRewardsClaimed: history.totalRewardsClaimed,
      currentCycle: history.currentCycle,
      lifetimeTokensEarned: history.lifetimeTokensEarned,
    };
  }

  // ==================== Game Sessions ====================

  /**
   * Save game session
   */
  async saveGameSession(session: GameSession): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    realm.write(() => {
      realm.create(
        'GameSession',
        {
          id: session.id,
          userId: session.userId,
          deckId: session.deckId,
          startTime: session.startTime,
          endTime: session.endTime,
          score: session.score,
          baseScore: session.baseScore,
          multiplier: session.multiplier,
          cardsProcessed: session.cardsProcessed,
          leftSwipes: session.leftSwipes,
          rightSwipes: session.rightSwipes,
          holds: session.holds,
          comboCount: session.comboCount,
          maxCombo: session.maxCombo,
          status: session.status,
          selectedAction: session.selectedAction,
          tokensEarned: session.tokensEarned,
          checklist: JSON.stringify(session.checklist),
        },
        Realm.UpdateMode.Modified
      );
    });
  }

  /**
   * Get game session by ID
   */
  async getGameSession(sessionId: string): Promise<GameSession | null> {
    await this.initialize();
    const realm = this.getRealm();

    const session = realm.objectForPrimaryKey<GameSessionSchema>('GameSession', sessionId);
    if (!session) {
      return null;
    }

    return {
      id: session.id,
      userId: session.userId,
      deckId: session.deckId,
      startTime: session.startTime,
      endTime: session.endTime,
      score: session.score,
      baseScore: session.baseScore,
      multiplier: session.multiplier,
      cardsProcessed: session.cardsProcessed,
      leftSwipes: session.leftSwipes,
      rightSwipes: session.rightSwipes,
      holds: session.holds,
      comboCount: session.comboCount,
      maxCombo: session.maxCombo,
      status: session.status as 'active' | 'completed' | 'abandoned',
      selectedAction: session.selectedAction,
      tokensEarned: session.tokensEarned,
      checklist: JSON.parse(session.checklist),
      heldCards: [], // Held cards not persisted in DB
    };
  }

  /**
   * Get all game sessions for a user
   */
  async getUserGameSessions(userId: string, limit: number = 50): Promise<GameSession[]> {
    await this.initialize();
    const realm = this.getRealm();

    const sessions = realm
      .objects<GameSessionSchema>('GameSession')
      .filtered('userId == $0', userId)
      .sorted('startTime', true)
      .slice(0, limit);

    return sessions.map(session => ({
      id: session.id,
      userId: session.userId,
      deckId: session.deckId,
      startTime: session.startTime,
      endTime: session.endTime,
      score: session.score,
      baseScore: session.baseScore,
      multiplier: session.multiplier,
      cardsProcessed: session.cardsProcessed,
      leftSwipes: session.leftSwipes,
      rightSwipes: session.rightSwipes,
      holds: session.holds,
      comboCount: session.comboCount,
      maxCombo: session.maxCombo,
      status: session.status as 'active' | 'completed' | 'abandoned',
      selectedAction: session.selectedAction,
      tokensEarned: session.tokensEarned,
      checklist: JSON.parse(session.checklist),
      heldCards: [],
    }));
  }

  /**
   * Delete old game sessions
   */
  async deleteOldGameSessions(userId: string, olderThan: number): Promise<number> {
    await this.initialize();
    const realm = this.getRealm();

    let deletedCount = 0;

    realm.write(() => {
      const oldSessions = realm
        .objects('GameSession')
        .filtered('userId == $0 AND startTime < $1', userId, olderThan);

      deletedCount = oldSessions.length;
      realm.delete(oldSessions);
    });

    return deletedCount;
  }

  // ==================== Achievements ====================

  /**
   * Save achievement progress
   */
  async saveAchievement(userId: string, achievement: Achievement): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    const id = `${userId}_${achievement.id}`;

    realm.write(() => {
      realm.create(
        'Achievement',
        {
          id,
          userId,
          achievementId: achievement.id,
          progress: achievement.progress,
          unlockedAt: achievement.unlockedAt,
        },
        Realm.UpdateMode.Modified
      );
    });
  }

  /**
   * Get all achievements for a user
   */
  async getUserAchievements(userId: string): Promise<Achievement[]> {
    await this.initialize();
    const realm = this.getRealm();

    const achievements = realm
      .objects<AchievementSchema>('Achievement')
      .filtered('userId == $0', userId);

    // Note: This returns the progress data only
    // You'll need to merge with achievement definitions from config
    return achievements.map(ach => ({
      id: ach.achievementId,
      title: '', // Will be filled from config
      description: '',
      icon: '',
      category: 'games' as const,
      progress: ach.progress,
      target: 0, // Will be filled from config
      unlockedAt: ach.unlockedAt,
    }));
  }

  /**
   * Delete all user data (for account deletion)
   */
  async deleteAllUserData(userId: string): Promise<void> {
    await this.initialize();
    const realm = this.getRealm();

    realm.write(() => {
      // Delete profile
      const profile = realm.objectForPrimaryKey('UserProfile', userId);
      if (profile) realm.delete(profile);

      // Delete daily reward history
      const history = realm.objectForPrimaryKey('DailyRewardHistory', userId);
      if (history) realm.delete(history);

      // Delete game sessions
      const sessions = realm.objects('GameSession').filtered('userId == $0', userId);
      realm.delete(sessions);

      // Delete achievements
      const achievements = realm.objects('Achievement').filtered('userId == $0', userId);
      realm.delete(achievements);

      // Delete settings
      const settings = realm.objectForPrimaryKey('Settings', userId);
      if (settings) realm.delete(settings);
    });
  }
}

export default DatabaseService.getInstance();
