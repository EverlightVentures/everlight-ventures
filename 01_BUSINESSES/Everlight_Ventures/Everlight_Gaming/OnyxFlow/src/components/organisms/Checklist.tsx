/**
 * Checklist - Interactive checklist with tap-to-complete
 */

import React, { useState } from 'react';
import { View, StyleSheet, TouchableOpacity } from 'react-native';
import Animated, { FadeIn, FadeOut, ZoomIn } from 'react-native-reanimated';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { Icon, Text, Card } from '@components/atoms';
import type { ChecklistItem } from '@types';
import { theme } from '@config/theme';

interface ChecklistProps {
  items: ChecklistItem[];
  onItemToggle?: (itemId: string, completed: boolean) => void;
  onAllComplete?: () => void;
}

export const Checklist: React.FC<ChecklistProps> = ({
  items: initialItems,
  onItemToggle,
  onAllComplete,
}) => {
  const [items, setItems] = useState(initialItems);

  const handleToggle = (itemId: string) => {
    const updatedItems = items.map(item => {
      if (item.id === itemId) {
        const newCompleted = !item.completed;

        // Haptic feedback
        ReactNativeHapticFeedback.trigger(
          newCompleted ? 'notificationSuccess' : 'impactLight',
          {
            enableVibrateFallback: true,
            ignoreAndroidSystemSettings: false,
          }
        );

        if (onItemToggle) {
          onItemToggle(itemId, newCompleted);
        }

        return {
          ...item,
          completed: newCompleted,
          completedAt: newCompleted ? Date.now() : undefined,
        };
      }
      return item;
    });

    setItems(updatedItems);

    // Check if all complete
    const allComplete = updatedItems.every(item => item.completed);
    if (allComplete && onAllComplete) {
      setTimeout(() => {
        onAllComplete();
      }, 300);
    }
  };

  const completedCount = items.filter(item => item.completed).length;
  const totalCount = items.length;
  const progress = (completedCount / totalCount) * 100;

  return (
    <View style={styles.container}>
      {/* Progress Header */}
      <View style={styles.progressHeader}>
        <Text variant="h4" color={theme.colors.white}>
          {completedCount} of {totalCount} Complete
        </Text>
        <View style={styles.progressBarContainer}>
          <View style={[styles.progressBar, { width: `${progress}%` }]} />
        </View>
      </View>

      {/* Checklist Items */}
      <View style={styles.itemsContainer}>
        {items.map((item, index) => (
          <Animated.View
            key={item.id}
            entering={FadeIn.delay(index * 100)}
            exiting={FadeOut}
          >
            <TouchableOpacity
              onPress={() => handleToggle(item.id)}
              activeOpacity={0.7}
            >
              <Card
                variant={item.completed ? 'gradient' : 'elevated'}
                padding="md"
                style={styles.itemCard}
              >
                <View style={styles.itemContent}>
                  {/* Checkbox */}
                  <View
                    style={[
                      styles.checkbox,
                      item.completed && styles.checkboxCompleted,
                    ]}
                  >
                    {item.completed && (
                      <Animated.View entering={ZoomIn}>
                        <Icon
                          name="check"
                          size={20}
                          color={theme.colors.onyxBlack}
                        />
                      </Animated.View>
                    )}
                  </View>

                  {/* Text */}
                  <Text
                    variant="body"
                    style={[
                      styles.itemText,
                      item.completed && styles.itemTextCompleted,
                    ]}
                  >
                    {item.text}
                  </Text>
                </View>
              </Card>
            </TouchableOpacity>
          </Animated.View>
        ))}
      </View>

      {/* Completion Message */}
      {completedCount === totalCount && (
        <Animated.View entering={FadeIn} style={styles.completionMessage}>
          <Icon name="award" size={32} color={theme.colors.champagneGold} />
          <Text
            variant="h3"
            color={theme.colors.champagneGold}
            style={{ marginTop: theme.spacing.sm }}
          >
            All Done! 🎉
          </Text>
        </Animated.View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  progressHeader: {
    marginBottom: theme.spacing.lg,
  },
  progressBarContainer: {
    height: 8,
    backgroundColor: theme.colors.darkGray,
    borderRadius: theme.borderRadius.full,
    marginTop: theme.spacing.sm,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: theme.colors.champagneGold,
    borderRadius: theme.borderRadius.full,
  },
  itemsContainer: {
    flex: 1,
  },
  itemCard: {
    marginBottom: theme.spacing.md,
  },
  itemContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkbox: {
    width: 32,
    height: 32,
    borderRadius: theme.borderRadius.md,
    borderWidth: 2,
    borderColor: theme.colors.fogText,
    marginRight: theme.spacing.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkboxCompleted: {
    backgroundColor: theme.colors.champagneGold,
    borderColor: theme.colors.champagneGold,
  },
  itemText: {
    flex: 1,
  },
  itemTextCompleted: {
    textDecorationLine: 'line-through',
    color: theme.colors.fogText,
  },
  completionMessage: {
    alignItems: 'center',
    marginTop: theme.spacing.lg,
  },
});

export default Checklist;
