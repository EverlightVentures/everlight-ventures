/**
 * GameEngine Unit Tests
 */

import { GameEngine } from '../src/services/game/GameEngine';
import type { Card } from '../src/types/game';

describe('GameEngine', () => {
  let gameEngine: GameEngine;

  beforeEach(() => {
    gameEngine = new GameEngine();
  });

  afterEach(() => {
    // Clean up any active sessions
    gameEngine.endGame();
  });

  describe('Game Session', () => {
    it('should start a new game session', () => {
      const mockCards: Card[] = [];
      const session = gameEngine.startGame('user123', 'deck-home', mockCards);

      expect(session).toBeDefined();
      expect(session.userId).toBe('user123');
      expect(session.deckId).toBe('deck-home');
      expect(session.score).toBe(0);
      expect(session.cardsProcessed).toBe(0);
      expect(session.heldCards).toEqual([]);
      expect(session.status).toBe('active');
    });

    it('should track held cards when swiping hold', () => {
      const mockCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: {
          title: 'Clean kitchen',
          description: 'Wipe counters and do dishes',
          priority: 'high',
          estimatedMinutes: 15,
        },
        metadata: { boost: 5 },
        createdAt: Date.now(),
      };

      const mockCards = [mockCard];
      gameEngine.startGame('user123', 'deck-home', mockCards);

      // Swipe hold should add to heldCards
      gameEngine.swipe('hold', mockCard);

      const session = gameEngine.getCurrentSession();
      expect(session?.heldCards).toHaveLength(1);
      expect(session?.heldCards[0]).toEqual(mockCard);
      expect(session?.holds).toBe(1);
    });

    it('should not track cards swiped left or right', () => {
      const mockCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: {
          title: 'Clean kitchen',
          priority: 'medium',
        },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-home', [mockCard]);

      gameEngine.swipe('left', mockCard);
      gameEngine.swipe('right', mockCard);

      const session = gameEngine.getCurrentSession();
      expect(session?.heldCards).toHaveLength(0);
      expect(session?.leftSwipes).toBe(1);
      expect(session?.rightSwipes).toBe(1);
    });
  });

  describe('Checklist Generation', () => {
    it('should generate checklist from held task cards', () => {
      const taskCard: Card = {
        id: 'task1',
        deckId: 'deck-work',
        type: 'task',
        content: {
          title: 'Review pull request',
          priority: 'high',
          estimatedMinutes: 30,
        },
        metadata: { boost: 5 },
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-work', [taskCard]);
      gameEngine.swipe('hold', taskCard);

      const session = gameEngine.endGame();

      expect(session?.checklist).toBeDefined();
      expect(session?.checklist.length).toBeGreaterThan(0);
      expect(session?.checklist[0].text).toContain('Review pull request');
      expect(session?.checklist[0].text).toContain('30 min');
      expect(session?.checklist[0].completed).toBe(false);
    });

    it('should generate checklist from held photo cards', () => {
      const photoCard: Card = {
        id: 'photo1',
        deckId: 'deck-photos',
        type: 'photo',
        content: {
          photoUri: 'file://photo.jpg',
          thumbnailUri: 'file://thumb.jpg',
          isScreenshot: true,
        },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-photos', [photoCard]);
      gameEngine.swipe('hold', photoCard);

      const session = gameEngine.endGame();

      expect(session?.checklist[0].text).toContain('screenshot');
    });

    it('should generate default checklist when no cards held', () => {
      const mockCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: { title: 'Task', priority: 'low' },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-home', [mockCard]);
      gameEngine.swipe('left', mockCard); // Don't hold any cards

      const session = gameEngine.endGame();

      expect(session?.checklist).toBeDefined();
      expect(session?.checklist.length).toBeGreaterThan(0);
      expect(session?.checklist[0].text).toContain('Great session');
    });
  });

  describe('Roulette Action Selection', () => {
    it('should select action from held task cards', () => {
      const highPriorityTask: Card = {
        id: 'task1',
        deckId: 'deck-work',
        type: 'task',
        content: {
          title: 'Fix critical bug',
          priority: 'high',
        },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-work', [highPriorityTask]);
      gameEngine.swipe('hold', highPriorityTask);

      const session = gameEngine.endGame();

      expect(session?.selectedAction).toBeDefined();
      expect(session?.selectedAction).toContain('Fix critical bug');
    });

    it('should select action from held photo cards', () => {
      const duplicatePhoto: Card = {
        id: 'photo1',
        deckId: 'deck-photos',
        type: 'photo',
        content: {
          photoUri: 'file://photo.jpg',
          thumbnailUri: 'file://thumb.jpg',
          isDuplicate: true,
        },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-photos', [duplicatePhoto]);
      gameEngine.swipe('hold', duplicatePhoto);

      const session = gameEngine.endGame();

      expect(session?.selectedAction).toBeDefined();
      expect(session?.selectedAction).toContain('duplicate');
    });

    it('should select default action when no cards held', () => {
      const mockCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: { title: 'Task', priority: 'low' },
        metadata: {},
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-home', [mockCard]);
      gameEngine.swipe('right', mockCard); // Don't hold any cards

      const session = gameEngine.endGame();

      expect(session?.selectedAction).toBeDefined();
      expect(typeof session?.selectedAction).toBe('string');
    });
  });

  describe('Scoring', () => {
    it('should award points for swipes', () => {
      const mockCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: { title: 'Task', priority: 'medium' },
        metadata: { boost: 0 },
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-home', [mockCard]);

      const leftResult = gameEngine.swipe('left', mockCard);
      expect(leftResult.points).toBeGreaterThan(0);

      const rightResult = gameEngine.swipe('right', mockCard);
      expect(rightResult.points).toBeGreaterThan(0);

      const holdResult = gameEngine.swipe('hold', mockCard);
      expect(holdResult.points).toBeGreaterThan(0);
    });

    it('should apply card boost to score', () => {
      const highBoostCard: Card = {
        id: 'card1',
        deckId: 'deck-home',
        type: 'task',
        content: { title: 'Important task', priority: 'high' },
        metadata: { boost: 10 },
        createdAt: Date.now(),
      };

      gameEngine.startGame('user123', 'deck-home', [highBoostCard]);
      const result = gameEngine.swipe('left', highBoostCard);

      expect(result.points).toBeGreaterThan(10); // Base + boost
    });
  });
});
