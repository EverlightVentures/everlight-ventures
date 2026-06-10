/**
 * OnyxFlow - Main App Entry Point
 * Luxury productivity game
 */

import React, { useEffect } from 'react';
import { StatusBar } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import mobileAds from 'react-native-google-mobile-ads';
import AppNavigator from './src/navigation/AppNavigator';
import { AdService } from './src/services/monetization/AdService';
import { ErrorBoundary } from './src/components/molecules/ErrorBoundary';
import { theme } from './src/config/theme';

function App(): React.JSX.Element {
  useEffect(() => {
    // Initialize Google Mobile Ads
    mobileAds()
      .initialize()
      .then(adapterStatuses => {
        console.log('AdMob initialized:', adapterStatuses);
        // Initialize AdService
        AdService.initialize();
      })
      .catch(error => {
        console.error('Failed to initialize AdMob:', error);
      });
  }, []);

  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaProvider>
          <StatusBar barStyle="light-content" backgroundColor={theme.colors.onyxBlack} />
          <AppNavigator />
        </SafeAreaProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
}

export default App;
