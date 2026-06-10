/**
 * Viral Features Configuration
 * Modern, shareable, social features
 */

export const VIRAL_FEATURES = {
  // Share Templates
  shareTemplates: {
    streak: {
      title: 'I\'m on a {days}-day streak! 🔥',
      description: 'Can you beat my focus streak in OnyxFlow?',
      hashtags: ['#OnyxFlow', '#ProductivityGame', '#FlowState'],
      image: 'streak-card', // Generated dynamically
    },
    achievement: {
      title: 'Just unlocked {achievement}! 💎',
      description: 'Join me in the productivity game that makes work fun',
      hashtags: ['#Achievement', '#Productivity', '#GameOn'],
    },
    score: {
      title: 'Scored {score} points in 60 seconds! ⚡',
      description: 'Think you can do better? Challenge accepted?',
      hashtags: ['#OnyxFlow', '#ChallengeAccepted', '#Focus'],
    },
  },

  // Daily Challenges (viral engagement)
  dailyChallenges: {
    monday: {
      name: 'Momentum Monday',
      goal: 'Complete 3 games',
      reward: { tokens: 100, badge: 'monday_warrior' },
      shareText: 'Crushed #MomentumMonday! 💪',
    },
    tuesday: {
      name: 'Turbo Tuesday',
      goal: 'Swipe 100 cards',
      reward: { tokens: 150 },
      shareText: 'Swiped into productivity on #TurboTuesday! 🚀',
    },
    wednesday: {
      name: 'Win Wednesday',
      goal: 'Score 500+ points',
      reward: { tokens: 200, shield: 1 },
      shareText: '#WinWednesday vibes! 🏆',
    },
    thursday: {
      name: 'Throwdown Thursday',
      goal: 'Beat your high score',
      reward: { tokens: 250 },
      shareText: 'New high score on #ThrowdownThursday! 🔥',
    },
    friday: {
      name: 'Flow Friday',
      goal: 'Perfect combo streak',
      reward: { tokens: 300, cosmetic: 'friday_glow' },
      shareText: 'Ending the week in flow! #FlowFriday ✨',
    },
    saturday: {
      name: 'Super Saturday',
      goal: 'Complete all decks',
      reward: { tokens: 400 },
      shareText: 'Conquered all decks! #SuperSaturday 💎',
    },
    sunday: {
      name: 'Streak Sunday',
      goal: 'Maintain your streak',
      reward: { tokens: 200, shield: 2 },
      shareText: 'Week completed! #StreakSunday 🔥',
    },
  },

  // Leaderboards
  leaderboards: {
    global: {
      name: 'Global Flow Champions',
      refreshInterval: 'hourly',
      prizes: {
        1: { tokens: 5000, badge: 'world_champion', cosmetic: 'crown' },
        2: { tokens: 3000, badge: 'runner_up' },
        3: { tokens: 2000, badge: 'third_place' },
        10: { tokens: 500 }, // Top 10
        100: { tokens: 100 }, // Top 100
      },
    },
    weekly: {
      name: 'Weekly Warriors',
      resetDay: 'monday',
      prizes: {
        1: { tokens: 2000, badge: 'weekly_winner' },
        10: { tokens: 300 },
      },
    },
    friends: {
      name: 'Friend Circle',
      maxSize: 50,
      updateFrequency: 'realtime',
    },
  },

  // Viral Mechanics
  referralProgram: {
    inviterReward: { tokens: 500, shields: 2 },
    inviteeReward: { tokens: 250, shields: 1 },
    milestoneRewards: {
      5: { tokens: 1000, badge: 'influencer_bronze' },
      10: { tokens: 3000, badge: 'influencer_silver', cosmetic: 'golden_cards' },
      25: { tokens: 10000, badge: 'influencer_gold', deck: 'premium_unlock' },
      50: { tokens: 25000, badge: 'influencer_platinum', customDeck: true },
    },
    shareCode: true, // Generate unique codes like "FLOW-ALEX-2025"
  },

  // TikTok/Instagram Integration
  socialIntegration: {
    tiktok: {
      enabled: true,
      templates: [
        {
          name: 'Swipe Montage',
          duration: 15,
          music: 'trending_beat_1',
          effects: ['speed_ramp', 'swipe_glow'],
        },
        {
          name: 'Before/After',
          duration: 30,
          showStats: true,
          effects: ['split_screen', 'stat_overlay'],
        },
      ],
    },
    instagram: {
      enabled: true,
      storyTemplates: [
        'minimal_stats',
        'gradient_achievement',
        'neon_streak',
      ],
    },
  },

  // Seasonal Events (FOMO driver)
  seasonalEvents: {
    spring: {
      name: 'Spring Cleaning Sprint',
      duration: '30 days',
      specialCards: 'cherry_blossom_theme',
      rewards: 'exclusive_spring_deck',
    },
    summer: {
      name: 'Summer Flow Festival',
      duration: '60 days',
      specialDecks: ['vacation', 'beach_cleanup'],
      rewards: 'summer_cosmetics',
    },
    fall: {
      name: 'Productivity Harvest',
      duration: '45 days',
      bonusTokens: 2.0, // Double tokens
      rewards: 'fall_leaves_effect',
    },
    winter: {
      name: 'New Year Resolution Rush',
      duration: '30 days',
      specialChallenges: 'goal_setting_deck',
      rewards: 'new_year_badge',
    },
  },

  // Battle Pass (Viral retention)
  battlePass: {
    free: {
      tiers: 50,
      rewards: ['tokens', 'shields', 'basic_cosmetics'],
    },
    premium: {
      price: 9.99,
      tiers: 50,
      rewards: [
        'exclusive_decks',
        'animated_cards',
        'special_effects',
        'early_access_features',
        'custom_themes',
      ],
      bonusXP: 1.5,
    },
    duration: '60 days',
    xpSources: {
      gameCompleted: 100,
      dailyChallenge: 500,
      weeklyChallenge: 2000,
      achievement: 1000,
      friendReferral: 5000,
    },
  },

  // Live Events (Real-time viral moments)
  liveEvents: {
    hourlyChallenge: {
      name: 'Power Hour',
      frequency: 'every_hour',
      duration: 60, // minutes
      globalParticipation: true,
      liveLeaderboard: true,
      prize: { tokens: 1000, badge: 'power_hour_winner' },
    },
    weekendBlitz: {
      name: 'Weekend Warrior Blitz',
      days: ['saturday', 'sunday'],
      bonusTokens: 3.0,
      specialDecks: true,
    },
  },

  // User-Generated Content
  ugc: {
    customDecks: {
      enabled: true,
      categories: ['work', 'fitness', 'learning', 'creativity'],
      monetization: {
        creatorCut: 0.7, // 70% to creator
        minPrice: 1.99,
        maxPrice: 9.99,
      },
      curation: 'community_voted',
    },
    templates: {
      enabled: true,
      shareBonus: 50, // tokens per share
      viralBonus: 1000, // if gets 1000+ uses
    },
  },

  // Notifications (Re-engagement)
  pushNotifications: {
    streakReminder: {
      time: '20:00', // 8 PM
      message: '🔥 Don\'t break your {days}-day streak!',
      action: 'open_game',
    },
    friendActivity: {
      enabled: true,
      message: '{friend} just beat your high score! 💪',
      action: 'challenge',
    },
    dailyChallenge: {
      time: '09:00',
      message: '⚡ Today\'s challenge: {challenge_name}',
      action: 'view_challenge',
    },
    liveEvent: {
      advance: 15, // minutes before
      message: '🏆 Power Hour starts in 15 minutes!',
      action: 'join_event',
    },
  },

  // Achievements (Social proof)
  socialAchievements: {
    influencer: {
      name: 'Influencer',
      requirement: 'Get 10 friends to join',
      shareWorthiness: 'high',
      badge: 'golden_megaphone',
    },
    trendsetter: {
      name: 'Trendsetter',
      requirement: 'Create a deck with 1000+ uses',
      shareWorthiness: 'high',
      badge: 'viral_crown',
    },
    legend: {
      name: 'Flow Legend',
      requirement: '100-day streak',
      shareWorthiness: 'maximum',
      badge: 'legendary_aura',
      specialEffect: 'permanent_glow',
    },
  },
};

// Viral Coefficients (K-factor tracking)
export const VIRAL_METRICS = {
  targetKFactor: 1.5, // Each user should bring 1.5 new users
  shareConversionRate: 0.15, // 15% of shares convert to installs
  referralConversionRate: 0.40, // 40% of referrals install
  retentionTargets: {
    day1: 0.40, // 40% return next day
    day7: 0.20, // 20% return after a week
    day30: 0.10, // 10% become monthly active
  },
};
