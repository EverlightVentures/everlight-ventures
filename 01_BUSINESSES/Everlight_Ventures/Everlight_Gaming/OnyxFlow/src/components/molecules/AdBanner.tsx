/**
 * AdBanner - Google AdMob banner component
 * Only shows for free users (non-subscribers)
 */

import React from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { BannerAd, BannerAdSize } from 'react-native-google-mobile-ads';
import { useUserStore } from '@store';
import { AD_UNIT_IDS } from '@config/ads';
import { theme } from '@config/theme';

interface AdBannerProps {
  position?: 'top' | 'bottom';
}

export const AdBanner: React.FC<AdBannerProps> = ({ position = 'bottom' }) => {
  const { profile } = useUserStore();

  // Don't show ads to Plus subscribers
  if (profile?.isPlusSubscriber) {
    return null;
  }

  return (
    <View style={[styles.container, position === 'top' ? styles.top : styles.bottom]}>
      <BannerAd
        unitId={AD_UNIT_IDS.android.banner}
        size={BannerAdSize.ANCHORED_ADAPTIVE_BANNER}
        requestOptions={{
          requestNonPersonalizedAdsOnly: false,
        }}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
    backgroundColor: theme.colors.graphite,
    borderTopWidth: 1,
    borderTopColor: theme.colors.mediumGray,
  },
  top: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 999,
  },
  bottom: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    zIndex: 999,
  },
});

export default AdBanner;
