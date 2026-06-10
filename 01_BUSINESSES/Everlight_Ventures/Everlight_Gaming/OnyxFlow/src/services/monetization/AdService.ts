/**
 * AdService - Manages Google AdMob ads
 * Shows ads to free users, respects subscription status
 */

import { Platform } from 'react-native';
import {
  InterstitialAd,
  RewardedAd,
  BannerAd,
  BannerAdSize,
  TestIds,
  AdEventType,
  RewardedAdEventType,
} from 'react-native-google-mobile-ads';
import { AD_UNIT_IDS, AD_CONFIG } from '@config/ads';

class AdServiceClass {
  private interstitialAd: InterstitialAd | null = null;
  private rewardedAd: RewardedAd | null = null;
  private lastInterstitialTime: number = 0;
  private gamesSinceLastAd: number = 0;
  private isInitialized: boolean = false;

  /**
   * Initialize AdMob
   */
  async initialize() {
    if (this.isInitialized) return;

    try {
      // Initialize interstitial ad
      this.interstitialAd = InterstitialAd.createForAdRequest(
        AD_UNIT_IDS.android.interstitial
      );

      // Load the first interstitial
      this.loadInterstitial();

      // Initialize rewarded ad
      this.rewardedAd = RewardedAd.createForAdRequest(AD_UNIT_IDS.android.rewarded);
      this.loadRewarded();

      this.isInitialized = true;
      console.log('AdService initialized');
    } catch (error) {
      console.error('Failed to initialize AdService:', error);
    }
  }

  /**
   * Load interstitial ad
   */
  private loadInterstitial() {
    if (!this.interstitialAd) return;

    this.interstitialAd.addAdEventListener(AdEventType.LOADED, () => {
      console.log('Interstitial ad loaded');
    });

    this.interstitialAd.addAdEventListener(AdEventType.CLOSED, () => {
      console.log('Interstitial ad closed');
      // Load next ad
      this.loadInterstitial();
    });

    this.interstitialAd.load();
  }

  /**
   * Load rewarded ad
   */
  private loadRewarded() {
    if (!this.rewardedAd) return;

    this.rewardedAd.addAdEventListener(RewardedAdEventType.LOADED, () => {
      console.log('Rewarded ad loaded');
    });

    this.rewardedAd.addAdEventListener(RewardedAdEventType.EARNED_REWARD, reward => {
      console.log('User earned reward:', reward);
    });

    this.rewardedAd.load();
  }

  /**
   * Check if user should see ads (not subscribed)
   */
  shouldShowAds(isPlusSubscriber: boolean): boolean {
    return !isPlusSubscriber;
  }

  /**
   * Check if enough time has passed since last interstitial
   */
  private canShowInterstitial(): boolean {
    const now = Date.now();
    const timeSinceLastAd = now - this.lastInterstitialTime;
    return timeSinceLastAd >= AD_CONFIG.interstitialMinInterval;
  }

  /**
   * Show interstitial ad after game (if conditions met)
   */
  async showInterstitialAfterGame(isPlusSubscriber: boolean): Promise<void> {
    // Don't show ads to subscribers
    if (!this.shouldShowAds(isPlusSubscriber)) {
      return;
    }

    this.gamesSinceLastAd++;

    // Check frequency and time interval
    if (
      this.gamesSinceLastAd >= AD_CONFIG.interstitialFrequency &&
      this.canShowInterstitial()
    ) {
      await this.showInterstitial();
      this.gamesSinceLastAd = 0;
      this.lastInterstitialTime = Date.now();
    }
  }

  /**
   * Show interstitial ad
   */
  async showInterstitial(): Promise<void> {
    if (!this.interstitialAd) {
      console.warn('Interstitial ad not initialized');
      return;
    }

    try {
      const loaded = this.interstitialAd.loaded;
      if (loaded) {
        await this.interstitialAd.show();
      } else {
        console.log('Interstitial ad not ready yet');
      }
    } catch (error) {
      console.error('Failed to show interstitial ad:', error);
    }
  }

  /**
   * Show rewarded ad (for earning tokens/shields)
   */
  async showRewardedAd(
    onReward: (reward: { tokens?: number; shield?: number }) => void
  ): Promise<void> {
    if (!this.rewardedAd) {
      console.warn('Rewarded ad not initialized');
      return;
    }

    try {
      const loaded = this.rewardedAd.loaded;
      if (!loaded) {
        console.log('Rewarded ad not ready yet');
        return;
      }

      // Add reward listener
      this.rewardedAd.addAdEventListener(RewardedAdEventType.EARNED_REWARD, () => {
        onReward(AD_CONFIG.rewardedAdBenefits);
      });

      await this.rewardedAd.show();

      // Load next ad
      this.loadRewarded();
    } catch (error) {
      console.error('Failed to show rewarded ad:', error);
    }
  }

  /**
   * Get banner ad component
   */
  getBannerComponent() {
    return BannerAd;
  }

  /**
   * Get banner ad size
   */
  getBannerSize() {
    return BannerAdSize.ANCHORED_ADAPTIVE_BANNER;
  }

  /**
   * Get banner unit ID
   */
  getBannerUnitId() {
    return AD_UNIT_IDS.android.banner;
  }
}

export const AdService = new AdServiceClass();
export default AdService;
