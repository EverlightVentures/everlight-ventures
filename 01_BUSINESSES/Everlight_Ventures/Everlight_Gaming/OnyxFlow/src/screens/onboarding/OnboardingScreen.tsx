/**
 * Onboarding Screen
 * Welcome new users and explain core features
 */

import React, { useState, useRef } from 'react';
import {
  View,
  StyleSheet,
  Dimensions,
  FlatList,
  ViewToken,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Text } from '@components/atoms/Text';
import { Button } from '@components/atoms/Button';
import { GradientBackground } from '@components/atoms/GradientBackground';
import { theme } from '@config/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface OnboardingSlide {
  id: string;
  title: string;
  description: string;
  icon: string;
  gradient: 'dark' | 'gold' | 'accent';
}

const SLIDES: OnboardingSlide[] = [
  {
    id: '1',
    title: 'Welcome to OnyxFlow',
    description: 'A luxury productivity game. Make quick decisions in 60-second sessions and build daily streaks.',
    icon: '💎',
    gradient: 'dark',
  },
  {
    id: '2',
    title: 'Swipe to Decide',
    description: 'Left to dismiss, right to keep, or hold for priority. Quick decisions, powerful results.',
    icon: '👆',
    gradient: 'gold',
  },
  {
    id: '3',
    title: 'Get Your Action',
    description: 'Spin the roulette wheel to select your focused action. Complete it in a 5-minute sprint.',
    icon: '🎯',
    gradient: 'accent',
  },
  {
    id: '4',
    title: 'Build Streaks',
    description: 'Play daily to build your streak. Unlock shields, earn tokens, and achieve milestones.',
    icon: '🔥',
    gradient: 'dark',
  },
  {
    id: '5',
    title: 'Ready to Flow?',
    description: 'Start your first 60-second session and experience focused productivity.',
    icon: '🚀',
    gradient: 'gold',
  },
];

interface OnboardingScreenProps {
  onComplete: () => void;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const flatListRef = useRef<FlatList>(null);

  const handleNext = () => {
    if (currentIndex < SLIDES.length - 1) {
      flatListRef.current?.scrollToIndex({
        index: currentIndex + 1,
        animated: true,
      });
    } else {
      onComplete();
    }
  };

  const handleSkip = () => {
    onComplete();
  };

  const onViewableItemsChanged = useRef(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (viewableItems.length > 0 && viewableItems[0].index !== null) {
        setCurrentIndex(viewableItems[0].index);
      }
    }
  ).current;

  const viewabilityConfig = useRef({
    itemVisiblePercentThreshold: 50,
  }).current;

  const renderSlide = ({ item }: { item: OnboardingSlide }) => (
    <View style={styles.slide}>
      <Text style={styles.icon}>{item.icon}</Text>
      <Text variant="h1" style={styles.title}>
        {item.title}
      </Text>
      <Text variant="body" style={styles.description}>
        {item.description}
      </Text>
    </View>
  );

  const renderPagination = () => (
    <View style={styles.pagination}>
      {SLIDES.map((_, index) => (
        <View
          key={index}
          style={[
            styles.dot,
            currentIndex === index && styles.dotActive,
          ]}
        />
      ))}
    </View>
  );

  return (
    <GradientBackground variant={SLIDES[currentIndex].gradient}>
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          {currentIndex < SLIDES.length - 1 && (
            <Button
              title="Skip"
              variant="ghost"
              onPress={handleSkip}
              style={styles.skipButton}
            />
          )}
        </View>

        <FlatList
          ref={flatListRef}
          data={SLIDES}
          renderItem={renderSlide}
          keyExtractor={item => item.id}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onViewableItemsChanged={onViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          scrollEventThrottle={16}
        />

        {renderPagination()}

        <View style={styles.footer}>
          <Button
            title={currentIndex === SLIDES.length - 1 ? 'Get Started' : 'Next'}
            variant={currentIndex === SLIDES.length - 1 ? 'gold' : 'primary'}
            onPress={handleNext}
            fullWidth
          />
        </View>
      </SafeAreaView>
    </GradientBackground>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    paddingHorizontal: theme.spacing.lg,
    paddingTop: theme.spacing.md,
  },
  skipButton: {
    paddingHorizontal: theme.spacing.lg,
  },
  slide: {
    width: SCREEN_WIDTH,
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: theme.spacing.xl,
  },
  icon: {
    fontSize: 120,
    marginBottom: theme.spacing.xl,
  },
  title: {
    color: theme.colors.white,
    textAlign: 'center',
    marginBottom: theme.spacing.md,
  },
  description: {
    color: theme.colors.fogText,
    textAlign: 'center',
    lineHeight: 24,
    maxWidth: 320,
  },
  pagination: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: theme.spacing.xl,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: theme.colors.mediumGray,
    marginHorizontal: 4,
  },
  dotActive: {
    width: 24,
    backgroundColor: theme.colors.champagneGold,
  },
  footer: {
    paddingHorizontal: theme.spacing.lg,
    paddingBottom: theme.spacing.xl,
  },
});
