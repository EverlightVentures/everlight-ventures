/**
 * Achievements Definitions
 */

import type { Achievement } from '@types';

export const ACHIEVEMENTS: Achievement[] = [
  // Games Played Achievements
  {
    id: 'first_game',
    title: 'First Flow',
    description: 'Complete your first game',
    icon: 'play-circle',
    category: 'games',
    progress: 0,
    target: 1,
    reward: { tokens: 50 },
  },
  {
    id: 'games_10',
    title: 'Getting Started',
    description: 'Complete 10 games',
    icon: 'trending-up',
    category: 'games',
    progress: 0,
    target: 10,
    reward: { tokens: 100 },
  },
  {
    id: 'games_25',
    title: 'Flow Enthusiast',
    description: 'Complete 25 games',
    icon: 'activity',
    category: 'games',
    progress: 0,
    target: 25,
    reward: { tokens: 250 },
  },
  {
    id: 'games_50',
    title: 'Half Century',
    description: 'Complete 50 games',
    icon: 'award',
    category: 'games',
    progress: 0,
    target: 50,
    reward: { tokens: 500, shield: 1 },
  },
  {
    id: 'games_100',
    title: 'Flow Master',
    description: 'Complete 100 games',
    icon: 'star',
    category: 'games',
    progress: 0,
    target: 100,
    reward: { tokens: 1500, cosmetic: 'theme_master_gold' },
  },

  // Streak Achievements
  {
    id: 'streak_3',
    title: 'Building Momentum',
    description: 'Reach a 3-day streak',
    icon: 'zap',
    category: 'streaks',
    progress: 0,
    target: 3,
    reward: { tokens: 50, shield: 1 },
  },
  {
    id: 'streak_7',
    title: 'Week Warrior',
    description: 'Reach a 7-day streak',
    icon: 'zap',
    category: 'streaks',
    progress: 0,
    target: 7,
    reward: { tokens: 150, shield: 2 },
  },
  {
    id: 'streak_14',
    title: 'Two Weeks Strong',
    description: 'Reach a 14-day streak',
    icon: 'zap',
    category: 'streaks',
    progress: 0,
    target: 14,
    reward: { tokens: 300, shield: 3 },
  },
  {
    id: 'streak_30',
    title: 'Monthly Flow',
    description: 'Reach a 30-day streak',
    icon: 'zap',
    category: 'streaks',
    progress: 0,
    target: 30,
    reward: { tokens: 1000, shield: 5, cosmetic: 'theme_streak_legend' },
  },
  {
    id: 'streak_100',
    title: 'Centurion',
    description: 'Reach a 100-day streak',
    icon: 'zap',
    category: 'streaks',
    progress: 0,
    target: 100,
    reward: { tokens: 5000, shield: 10, cosmetic: 'theme_diamond_flow' },
  },

  // Score Achievements
  {
    id: 'score_1k',
    title: 'Breaking 1K',
    description: 'Score 1,000+ points in a single game',
    icon: 'target',
    category: 'score',
    progress: 0,
    target: 1000,
    reward: { tokens: 100 },
  },
  {
    id: 'score_5k',
    title: 'High Roller',
    description: 'Score 5,000+ points in a single game',
    icon: 'target',
    category: 'score',
    progress: 0,
    target: 5000,
    reward: { tokens: 500 },
  },
  {
    id: 'score_10k',
    title: 'Perfect Flow',
    description: 'Score 10,000+ points in a single game',
    icon: 'target',
    category: 'score',
    progress: 0,
    target: 10000,
    reward: { tokens: 1000, cosmetic: 'theme_perfect_gold' },
  },

  // Special Achievements
  {
    id: 'perfect_run',
    title: 'Perfectionist',
    description: 'Complete a game with no holds',
    icon: 'check-circle',
    category: 'special',
    progress: 0,
    target: 1,
    reward: { tokens: 200 },
  },
  {
    id: 'combo_10',
    title: 'Combo King',
    description: 'Achieve a 10x combo',
    icon: 'circle',
    category: 'special',
    progress: 0,
    target: 10,
    reward: { tokens: 150 },
  },
  {
    id: 'speed_demon',
    title: 'Speed Demon',
    description: 'Process 25+ cards in one game',
    icon: 'fast-forward',
    category: 'special',
    progress: 0,
    target: 25,
    reward: { tokens: 250 },
  },
  {
    id: 'checklist_master',
    title: 'Checklist Champion',
    description: 'Complete 10 checklists',
    icon: 'list',
    category: 'special',
    progress: 0,
    target: 10,
    reward: { tokens: 300 },
  },
  {
    id: 'early_bird',
    title: 'Early Bird',
    description: 'Play a game before 8 AM',
    icon: 'sunrise',
    category: 'special',
    progress: 0,
    target: 1,
    reward: { tokens: 100 },
  },
  {
    id: 'night_owl',
    title: 'Night Owl',
    description: 'Play a game after 10 PM',
    icon: 'moon',
    category: 'special',
    progress: 0,
    target: 1,
    reward: { tokens: 100 },
  },
];

export const getAchievementById = (id: string): Achievement | undefined => {
  return ACHIEVEMENTS.find(achievement => achievement.id === id);
};

export const getAchievementsByCategory = (
  category: 'games' | 'streaks' | 'score' | 'special',
): Achievement[] => {
  return ACHIEVEMENTS.filter(achievement => achievement.category === category);
};

export const checkAchievementUnlock = (
  achievementId: string,
  currentProgress: number,
): boolean => {
  const achievement = getAchievementById(achievementId);
  if (!achievement) return false;

  return currentProgress >= achievement.target;
};
