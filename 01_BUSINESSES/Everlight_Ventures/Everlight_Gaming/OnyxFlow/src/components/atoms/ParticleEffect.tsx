/**
 * ParticleEffect - Celebratory particle animation using Reanimated
 * Used for achievements, milestones, and special events
 */

import React, { useEffect, useMemo } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  Easing,
  interpolate,
} from 'react-native-reanimated';
import { theme } from '@config/theme';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface Particle {
  id: number;
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  size: number;
  color: string;
  delay: number;
  rotation: number;
}

interface ParticleEffectProps {
  type?: 'confetti' | 'sparkles';
  origin?: { x: number; y: number };
  particleCount?: number;
  duration?: number;
  onComplete?: () => void;
}

export const ParticleEffect: React.FC<ParticleEffectProps> = ({
  type = 'confetti',
  origin = { x: SCREEN_WIDTH / 2, y: SCREEN_HEIGHT / 3 },
  particleCount = 30,
  duration = 2000,
  onComplete,
}) => {
  const progress = useSharedValue(0);

  useEffect(() => {
    progress.value = withTiming(
      1,
      {
        duration,
        easing: Easing.out(Easing.quad),
      },
      finished => {
        if (finished && onComplete) {
          onComplete();
        }
      }
    );
  }, [progress, duration, onComplete]);

  // Generate particles
  const particles: Particle[] = useMemo(() => {
    return Array.from({ length: particleCount }, (_, i) => {
      const angle = (Math.PI * 2 * i) / particleCount + (Math.random() - 0.5) * 0.5;
      const distance = 150 + Math.random() * 150;
      const endX = origin.x + Math.cos(angle) * distance;
      const endY = origin.y + Math.sin(angle) * distance + 100; // Gravity effect

      return {
        id: i,
        startX: origin.x,
        startY: origin.y,
        endX,
        endY,
        size: type === 'confetti' ? 8 + Math.random() * 8 : 4 + Math.random() * 6,
        color: getParticleColor(type),
        delay: Math.random() * 200,
        rotation: Math.random() * 720, // 0-720 degrees
      };
    });
  }, [particleCount, type, origin]);

  return (
    <View style={styles.container} pointerEvents="none">
      {particles.map(particle => (
        <ParticleItem key={particle.id} particle={particle} progress={progress} type={type} />
      ))}
    </View>
  );
};

interface ParticleItemProps {
  particle: Particle;
  progress: Animated.SharedValue<number>;
  type: 'confetti' | 'sparkles';
}

const ParticleItem: React.FC<ParticleItemProps> = ({ particle, progress, type }) => {
  const animatedStyle = useAnimatedStyle(() => {
    const x = interpolate(progress.value, [0, 1], [particle.startX, particle.endX]);
    const y = interpolate(progress.value, [0, 1], [particle.startY, particle.endY]);
    const opacity = interpolate(progress.value, [0, 0.7, 1], [1, 0.8, 0]);
    const scale = interpolate(progress.value, [0, 0.2, 1], [0, 1.2, 0.6]);
    const rotate = interpolate(progress.value, [0, 1], [0, particle.rotation]);

    return {
      position: 'absolute',
      left: x,
      top: y,
      width: particle.size,
      height: particle.size,
      backgroundColor: particle.color,
      borderRadius: type === 'sparkles' ? particle.size / 2 : particle.size / 4,
      opacity,
      transform: [{ scale }, { rotate: `${rotate}deg` }],
    };
  });

  return <Animated.View style={animatedStyle} />;
};

const getParticleColor = (type: string): string => {
  if (type === 'confetti') {
    const colors = [
      theme.colors.champagneGold,
      theme.colors.silverGray,
      theme.colors.white,
      theme.colors.success,
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }

  // Sparkles are always gold
  return theme.colors.champagneGold;
};

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 9998,
  },
});

export default ParticleEffect;
