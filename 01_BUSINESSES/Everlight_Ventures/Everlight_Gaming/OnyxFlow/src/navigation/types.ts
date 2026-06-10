/**
 * Navigation Types
 */

import type { NavigatorScreenParams } from '@react-navigation/native';

// Root Stack (before auth)
export type RootStackParamList = {
  Splash: undefined;
  Onboarding: NavigatorScreenParams<OnboardingStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
};

// Onboarding Stack
export type OnboardingStackParamList = {
  Welcome: undefined;
  Permissions: undefined;
  Tutorial: undefined;
};

// Main Bottom Tabs
export type MainTabParamList = {
  HomeTab: NavigatorScreenParams<HomeStackParamList>;
  DecksTab: NavigatorScreenParams<DecksStackParamList>;
  ShopTab: NavigatorScreenParams<ShopStackParamList>;
  ProfileTab: NavigatorScreenParams<ProfileStackParamList>;
};

// Home Stack
export type HomeStackParamList = {
  Home: undefined;
  Game: { deckId: string };
  Roulette: { sessionId: string };
  Checklist: { sessionId: string };
  Results: { sessionId: string };
};

// Decks Stack
export type DecksStackParamList = {
  DeckList: undefined;
  DeckDetail: { deckId: string };
};

// Shop Stack
export type ShopStackParamList = {
  Shop: undefined;
  Subscription: undefined;
};

// Profile Stack
export type ProfileStackParamList = {
  Profile: undefined;
  Stats: undefined;
  Achievements: undefined;
  Settings: undefined;
};
