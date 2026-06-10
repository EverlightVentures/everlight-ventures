/**
 * CardGenerator Unit Tests
 */

import { CardGenerator } from '../src/services/game/CardGenerator';
import type { Card, TaskCardContent } from '../src/types';

describe('CardGenerator', () => {
  let cardGenerator: CardGenerator;

  beforeEach(() => {
    cardGenerator = new CardGenerator();
  });

  describe('generateCards', () => {
    it('should throw error for invalid deck', () => {
      expect(() => {
        cardGenerator.generateCards('invalid_deck');
      }).toThrow('Deck not found: invalid_deck');
    });

    it('should return empty array for photos deck (not implemented)', () => {
      const cards = cardGenerator.generateCards('deck_photos');

      expect(cards).toEqual([]);
    });

    it('should generate home deck cards', () => {
      const cards = cardGenerator.generateCards('deck_home', 10);

      expect(cards).toHaveLength(10);
      expect(cards[0].deckId).toBe('deck_home');
      expect(cards[0].type).toBe('task');
    });

    it('should generate work deck cards', () => {
      const cards = cardGenerator.generateCards('deck_work', 10);

      expect(cards).toHaveLength(10);
      expect(cards[0].deckId).toBe('deck_work');
      expect(cards[0].type).toBe('task');
    });

    it('should generate travel deck cards', () => {
      const cards = cardGenerator.generateCards('deck_travel', 10);

      expect(cards).toHaveLength(10);
      expect(cards[0].deckId).toBe('deck_travel');
      expect(cards[0].type).toBe('task');
    });

    it('should generate up to available templates', () => {
      // Request more cards than available templates
      const cards = cardGenerator.generateCards('deck_home', 100);

      // Should generate only as many as templates available (12 home tasks)
      expect(cards.length).toBeLessThanOrEqual(12);
    });

    it('should generate cards with unique IDs', () => {
      const cards = cardGenerator.generateCards('deck_home', 10);
      const ids = cards.map(card => card.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(cards.length);
    });
  });

  describe('Task Card Structure', () => {
    it('should generate cards with correct structure', () => {
      const cards = cardGenerator.generateCards('deck_home', 1);
      const card = cards[0];

      expect(card).toHaveProperty('id');
      expect(card).toHaveProperty('deckId');
      expect(card).toHaveProperty('type');
      expect(card).toHaveProperty('content');
      expect(card).toHaveProperty('metadata');
      expect(card).toHaveProperty('createdAt');
    });

    it('should generate task content with required fields', () => {
      const cards = cardGenerator.generateCards('deck_home', 1);
      const content = cards[0].content as TaskCardContent;

      expect(content).toHaveProperty('title');
      expect(content).toHaveProperty('description');
      expect(content).toHaveProperty('priority');
      expect(content).toHaveProperty('estimatedMinutes');
      expect(content).toHaveProperty('category');
    });

    it('should set correct category in task content', () => {
      const homeCards = cardGenerator.generateCards('deck_home', 1);
      const workCards = cardGenerator.generateCards('deck_work', 1);
      const travelCards = cardGenerator.generateCards('deck_travel', 1);

      expect((homeCards[0].content as TaskCardContent).category).toBe('home');
      expect((workCards[0].content as TaskCardContent).category).toBe('work');
      expect((travelCards[0].content as TaskCardContent).category).toBe('travel');
    });

    it('should include metadata with boost, tags, and importance', () => {
      const cards = cardGenerator.generateCards('deck_home', 1);
      const metadata = cards[0].metadata;

      expect(metadata).toHaveProperty('boost');
      expect(metadata).toHaveProperty('tags');
      expect(metadata).toHaveProperty('importance');
      expect(metadata.tags).toContain('home');
    });

    it('should set timestamp for createdAt', () => {
      const before = Date.now();
      const cards = cardGenerator.generateCards('deck_home', 1);
      const after = Date.now();

      expect(cards[0].createdAt).toBeGreaterThanOrEqual(before);
      expect(cards[0].createdAt).toBeLessThanOrEqual(after);
    });
  });

  describe('Priority and Boost Calculation', () => {
    it('should assign boost of 5 for high priority tasks', () => {
      const cards = cardGenerator.generateCards('deck_home', 12);

      // Find a high priority card
      const highPriorityCard = cards.find(
        card => (card.content as TaskCardContent).priority === 'high'
      );

      if (highPriorityCard) {
        expect(highPriorityCard.metadata.boost).toBe(5);
        expect(highPriorityCard.metadata.importance).toBe(3);
      }
    });

    it('should assign boost of 3 for medium priority tasks', () => {
      const cards = cardGenerator.generateCards('deck_home', 12);

      // Find a medium priority card
      const mediumPriorityCard = cards.find(
        card => (card.content as TaskCardContent).priority === 'medium'
      );

      if (mediumPriorityCard) {
        expect(mediumPriorityCard.metadata.boost).toBe(3);
        expect(mediumPriorityCard.metadata.importance).toBe(2);
      }
    });

    it('should assign boost of 0 for low priority tasks', () => {
      const cards = cardGenerator.generateCards('deck_home', 12);

      // Find a low priority card
      const lowPriorityCard = cards.find(
        card => (card.content as TaskCardContent).priority === 'low'
      );

      if (lowPriorityCard) {
        expect(lowPriorityCard.metadata.boost).toBe(0);
        expect(lowPriorityCard.metadata.importance).toBe(1);
      }
    });
  });

  describe('Task Templates', () => {
    it('should generate different tasks from home templates', () => {
      const cards = cardGenerator.generateCards('deck_home', 5);
      const titles = cards.map(card => (card.content as TaskCardContent).title);

      // Check that we have variety (not all the same task)
      const uniqueTitles = new Set(titles);
      expect(uniqueTitles.size).toBeGreaterThan(1);
    });

    it('should generate different tasks from work templates', () => {
      const cards = cardGenerator.generateCards('deck_work', 5);
      const titles = cards.map(card => (card.content as TaskCardContent).title);

      const uniqueTitles = new Set(titles);
      expect(uniqueTitles.size).toBeGreaterThan(1);
    });

    it('should generate different tasks from travel templates', () => {
      const cards = cardGenerator.generateCards('deck_travel', 5);
      const titles = cards.map(card => (card.content as TaskCardContent).title);

      const uniqueTitles = new Set(titles);
      expect(uniqueTitles.size).toBeGreaterThan(1);
    });

    it('should include estimated time in minutes', () => {
      const cards = cardGenerator.generateCards('deck_home', 5);

      cards.forEach(card => {
        const content = card.content as TaskCardContent;
        expect(content.estimatedMinutes).toBeDefined();
        expect(content.estimatedMinutes).toBeGreaterThan(0);
      });
    });

    it('should include task descriptions', () => {
      const cards = cardGenerator.generateCards('deck_work', 5);

      cards.forEach(card => {
        const content = card.content as TaskCardContent;
        expect(content.description).toBeDefined();
        expect(content.description).not.toBe('');
      });
    });
  });

  describe('Randomization', () => {
    it('should generate different card selections on multiple calls', () => {
      const cards1 = cardGenerator.generateCards('deck_home', 5);
      const cards2 = cardGenerator.generateCards('deck_home', 5);

      const titles1 = cards1.map(c => (c.content as TaskCardContent).title).sort();
      const titles2 = cards2.map(c => (c.content as TaskCardContent).title).sort();

      // With randomization, the sets should be different (might occasionally fail, but very unlikely)
      const areDifferent = titles1.some((title, index) => title !== titles2[index]);

      // Note: This test has a small chance of false failure due to randomization
      // If it fails consistently, there may be an issue with randomization
      expect(areDifferent || titles1.length !== titles2.length).toBe(true);
    });
  });

  describe('Edge Cases', () => {
    it('should handle count of 0', () => {
      const cards = cardGenerator.generateCards('deck_home', 0);

      expect(cards).toEqual([]);
    });

    it('should handle count of 1', () => {
      const cards = cardGenerator.generateCards('deck_home', 1);

      expect(cards).toHaveLength(1);
    });

    it('should default to 20 cards if count not specified', () => {
      const cards = cardGenerator.generateCards('deck_home');

      expect(cards.length).toBeLessThanOrEqual(20);
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});
