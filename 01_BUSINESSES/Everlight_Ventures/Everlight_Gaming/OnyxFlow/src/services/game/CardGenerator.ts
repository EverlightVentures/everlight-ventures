/**
 * CardGenerator - Generate cards for different decks
 */

import { v4 as uuidv4 } from 'uuid';
import type { Card, TaskCardContent } from '@types';
import { DECKS, getDeckById } from '@config/decks';

export class CardGenerator {
  /**
   * Generate cards for a specific deck
   */
  generateCards(deckId: string, count: number = 20): Card[] {
    const deck = getDeckById(deckId);
    if (!deck) {
      throw new Error(`Deck not found: ${deckId}`);
    }

    const cards: Card[] = [];

    switch (deck.category) {
      case 'photos':
        // Photos will be generated from actual photo library
        // For now, return empty array (will be implemented in Phase 3)
        return [];

      case 'home':
      case 'work':
      case 'travel':
        // Generate task cards
        return this.generateTaskCards(deckId, deck.category, count);

      default:
        return [];
    }
  }

  /**
   * Generate task cards for Home/Work/Travel decks
   */
  private generateTaskCards(deckId: string, category: string, count: number): Card[] {
    const tasks = this.getTaskTemplates(category);
    const cards: Card[] = [];

    // Shuffle and pick random tasks
    const shuffled = [...tasks].sort(() => Math.random() - 0.5);
    const selected = shuffled.slice(0, Math.min(count, shuffled.length));

    for (const task of selected) {
      const content: TaskCardContent = {
        title: task.title,
        description: task.description,
        priority: task.priority,
        estimatedMinutes: task.estimatedMinutes,
        category,
      };

      cards.push({
        id: uuidv4(),
        deckId,
        type: 'task',
        content,
        metadata: {
          boost: this.calculateBoost(task.priority),
          tags: [category],
          importance: task.priority === 'high' ? 3 : task.priority === 'medium' ? 2 : 1,
        },
        createdAt: Date.now(),
      });
    }

    return cards;
  }

  /**
   * Get task templates by category
   */
  private getTaskTemplates(category: string) {
    const templates = {
      home: [
        { title: 'Wipe down kitchen counters', description: 'Quick 2-minute clean', priority: 'low' as const, estimatedMinutes: 2 },
        { title: 'Organize 1 drawer', description: 'Pick any drawer and declutter', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Take out trash', description: 'All bins in the house', priority: 'medium' as const, estimatedMinutes: 5 },
        { title: 'Water plants', description: 'Check soil moisture first', priority: 'low' as const, estimatedMinutes: 5 },
        { title: 'Make your bed', description: 'Start your day right', priority: 'low' as const, estimatedMinutes: 2 },
        { title: 'Clean bathroom sink', description: 'Quick wipe and rinse', priority: 'medium' as const, estimatedMinutes: 3 },
        { title: 'Sort 10 items to donate', description: 'Declutter closet or drawers', priority: 'high' as const, estimatedMinutes: 15 },
        { title: 'Vacuum one room', description: 'Quick pass through', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Wipe down appliances', description: 'Microwave, fridge exterior', priority: 'low' as const, estimatedMinutes: 5 },
        { title: 'Clean mirrors', description: 'All mirrors in the house', priority: 'low' as const, estimatedMinutes: 5 },
        { title: 'Organize pantry shelf', description: 'One shelf only', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Declutter coffee table', description: 'Remove unnecessary items', priority: 'low' as const, estimatedMinutes: 3 },
      ],
      work: [
        { title: 'Clear 20 unread emails', description: 'Delete, archive, or respond', priority: 'high' as const, estimatedMinutes: 15 },
        { title: 'Schedule 1 meeting', description: 'Send calendar invite', priority: 'medium' as const, estimatedMinutes: 5 },
        { title: 'Update project status', description: 'Brief progress note', priority: 'high' as const, estimatedMinutes: 10 },
        { title: 'Review 1 document', description: 'Provide feedback or approve', priority: 'medium' as const, estimatedMinutes: 15 },
        { title: 'Send 3 follow-up emails', description: 'Check pending responses', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Organize desktop files', description: 'Create folders, move files', priority: 'low' as const, estimatedMinutes: 10 },
        { title: 'Update task list', description: 'Add new items, mark complete', priority: 'high' as const, estimatedMinutes: 5 },
        { title: 'Research 1 topic', description: '15-minute deep dive', priority: 'medium' as const, estimatedMinutes: 15 },
        { title: 'Draft 1 message', description: 'Email, Slack, or document', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Review calendar for tomorrow', description: 'Prep for meetings', priority: 'high' as const, estimatedMinutes: 5 },
        { title: 'Archive old emails', description: 'Older than 6 months', priority: 'low' as const, estimatedMinutes: 10 },
        { title: 'Update team on progress', description: 'Quick status message', priority: 'medium' as const, estimatedMinutes: 5 },
      ],
      travel: [
        { title: 'Research 1 destination', description: 'Look up attractions', priority: 'high' as const, estimatedMinutes: 20 },
        { title: 'Book accommodation', description: 'Reserve hotel or rental', priority: 'high' as const, estimatedMinutes: 15 },
        { title: 'Create packing list', description: 'Essentials for trip', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Check travel requirements', description: 'Visa, passport, COVID', priority: 'high' as const, estimatedMinutes: 10 },
        { title: 'Book transportation', description: 'Flights, trains, or car', priority: 'high' as const, estimatedMinutes: 20 },
        { title: 'Make restaurant reservation', description: '1-2 must-try places', priority: 'low' as const, estimatedMinutes: 10 },
        { title: 'Download offline maps', description: 'Google Maps offline', priority: 'medium' as const, estimatedMinutes: 5 },
        { title: 'Check weather forecast', description: 'Pack accordingly', priority: 'medium' as const, estimatedMinutes: 5 },
        { title: 'Notify bank of travel', description: 'Avoid card blocks', priority: 'high' as const, estimatedMinutes: 5 },
        { title: 'Share itinerary with family', description: 'Emergency contact info', priority: 'medium' as const, estimatedMinutes: 10 },
        { title: 'Pack toiletries', description: 'Travel-size essentials', priority: 'low' as const, estimatedMinutes: 10 },
        { title: 'Charge all devices', description: 'Phone, tablet, camera', priority: 'medium' as const, estimatedMinutes: 2 },
      ],
    };

    return templates[category as keyof typeof templates] || [];
  }

  /**
   * Calculate boost based on priority
   */
  private calculateBoost(priority: 'low' | 'medium' | 'high'): number {
    switch (priority) {
      case 'high': return 5;
      case 'medium': return 3;
      case 'low': return 0;
      default: return 0;
    }
  }
}

export default new CardGenerator();
