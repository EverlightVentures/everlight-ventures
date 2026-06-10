/**
 * In-App Purchase Products Configuration
 */

export interface IAPProduct {
  id: string;
  type: 'pack' | 'subscription';
  name: string;
  price: number;
  description: string;
  rewards: {
    tokens?: number;
    decks?: string[];
    streakShields?: number;
    cosmetics?: string[];
    premiumRoulette?: boolean;
  };
}

export const IAP_PRODUCTS: IAPProduct[] = [
  {
    id: 'quick_boost',
    type: 'pack',
    name: 'Quick Boost',
    price: 2.49,
    description: 'Get started with a token boost and basic perks',
    rewards: {
      tokens: 200,
      streakShields: 1,
    },
  },
  {
    id: 'momentum_pack',
    type: 'pack',
    name: 'Momentum',
    price: 5.99,
    description: 'Keep your streak alive with shields and extra tokens',
    rewards: {
      tokens: 500,
      streakShields: 3,
      decks: ['deck_home'],
    },
  },
  {
    id: 'flow_pack',
    type: 'pack',
    name: 'Flow',
    price: 12.49,
    description: 'Unlock premium decks and cosmetic themes',
    rewards: {
      tokens: 1200,
      streakShields: 5,
      decks: ['deck_home', 'deck_work'],
      cosmetics: ['theme_dark_gold', 'theme_minimal'],
    },
  },
  {
    id: 'deep_focus_pack',
    type: 'pack',
    name: 'Deep Focus',
    price: 24.99,
    description: 'All decks plus premium roulette themes',
    rewards: {
      tokens: 2500,
      streakShields: 10,
      decks: ['deck_home', 'deck_work', 'deck_travel'],
      cosmetics: ['theme_dark_gold', 'theme_minimal', 'theme_luxury'],
      premiumRoulette: true,
    },
  },
  {
    id: 'mastery_pack',
    type: 'pack',
    name: 'Mastery',
    price: 44.99,
    description: 'Master-tier pack with exclusive content',
    rewards: {
      tokens: 5000,
      streakShields: 20,
      decks: ['deck_home', 'deck_work', 'deck_travel'],
      cosmetics: ['theme_dark_gold', 'theme_minimal', 'theme_luxury', 'theme_onyx_elite'],
      premiumRoulette: true,
    },
  },
  {
    id: 'ultra_pack',
    type: 'pack',
    name: 'Ultra',
    price: 79.99,
    description: 'Ultra-premium bundle for serious users',
    rewards: {
      tokens: 10000,
      streakShields: 40,
      decks: ['deck_home', 'deck_work', 'deck_travel'],
      cosmetics: [
        'theme_dark_gold',
        'theme_minimal',
        'theme_luxury',
        'theme_onyx_elite',
        'theme_platinum',
      ],
      premiumRoulette: true,
    },
  },
  {
    id: 'legend_pack',
    type: 'pack',
    name: 'Legend',
    price: 129.99,
    description: 'Ultimate pack with everything unlocked',
    rewards: {
      tokens: 20000,
      streakShields: 99,
      decks: ['deck_home', 'deck_work', 'deck_travel'],
      cosmetics: [
        'theme_dark_gold',
        'theme_minimal',
        'theme_luxury',
        'theme_onyx_elite',
        'theme_platinum',
        'theme_diamond',
      ],
      premiumRoulette: true,
    },
  },
];

export interface SubscriptionProduct {
  id: string;
  name: string;
  tierOne: {
    price: number;
    duration: number; // months
  };
  tierTwo: {
    price: number;
    fromMonth: number;
  };
  trialDays: number;
  benefits: string[];
}

export const SUBSCRIPTION: SubscriptionProduct = {
  id: 'onyxflow_plus',
  name: 'OnyxFlow+',
  tierOne: {
    price: 4.99,
    duration: 3, // first 3 months
  },
  tierTwo: {
    price: 19.99,
    fromMonth: 4, // from month 4 onwards
  },
  trialDays: 3,
  benefits: [
    'Ad-free experience',
    'Unlimited sessions',
    'SmartFlow AI',
    '1 free reroll per session',
    '1 Streak Shield per week',
    'Monthly Focus Pack (deck + theme)',
    'Early access to event decks',
  ],
};

// Google Play product IDs (these need to match what's configured in Play Console)
export const PLAY_STORE_PRODUCT_IDS = {
  quickBoost: 'com.onyxflow.pack.quick_boost',
  momentum: 'com.onyxflow.pack.momentum',
  flow: 'com.onyxflow.pack.flow',
  deepFocus: 'com.onyxflow.pack.deep_focus',
  mastery: 'com.onyxflow.pack.mastery',
  ultra: 'com.onyxflow.pack.ultra',
  legend: 'com.onyxflow.pack.legend',
  subscription: 'com.onyxflow.subscription.plus',
};

export const getProductById = (id: string): IAPProduct | undefined => {
  return IAP_PRODUCTS.find(product => product.id === id);
};

export const getProductsByType = (type: 'pack' | 'subscription'): IAPProduct[] => {
  return IAP_PRODUCTS.filter(product => product.type === type);
};
