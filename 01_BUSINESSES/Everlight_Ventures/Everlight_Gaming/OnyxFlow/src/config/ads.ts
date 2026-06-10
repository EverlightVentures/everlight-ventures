/**
 * AdMob Configuration
 * Ad unit IDs for Google AdMob monetization
 */

// Test IDs provided by Google for development
// Replace with your actual Ad Unit IDs from AdMob console before production release
export const AD_UNIT_IDS = {
  android: {
    banner: __DEV__
      ? 'ca-app-pub-3940256099942544/6300978111' // Test banner
      : 'ca-app-pub-XXXXXXXXXXXXXXXX/YYYYYYYYYY', // Replace with your production banner ID
    interstitial: __DEV__
      ? 'ca-app-pub-3940256099942544/1033173712' // Test interstitial
      : 'ca-app-pub-XXXXXXXXXXXXXXXX/ZZZZZZZZZZ', // Replace with your production interstitial ID
    rewarded: __DEV__
      ? 'ca-app-pub-3940256099942544/5224354917' // Test rewarded
      : 'ca-app-pub-XXXXXXXXXXXXXXXX/AAAAAAAAAA', // Replace with your production rewarded ID
  },
};

// Ad display configuration
export const AD_CONFIG = {
  // Show interstitial ad after every N game sessions
  interstitialFrequency: 3,

  // Minimum time between interstitial ads (milliseconds)
  interstitialMinInterval: 3 * 60 * 1000, // 3 minutes

  // Show banner on these screens (for free users)
  bannerScreens: ['Home', 'Profile', 'Stats'],

  // Rewarded ad benefits
  rewardedAdBenefits: {
    tokens: 100,
    streakShield: 1,
  },
};

export default AD_UNIT_IDS;
