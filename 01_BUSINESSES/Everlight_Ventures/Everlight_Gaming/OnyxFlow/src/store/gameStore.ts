/**
 * Game Store - Zustand state management for game sessions
 */

import { create } from 'zustand';
import type { GameSession, Card, SwipeDirection, SwipeResult } from '@types';
import GameEngine from '@services/game/GameEngine';
import CardGenerator from '@services/game/CardGenerator';

interface GameState {
  // State
  session: GameSession | null;
  cards: Card[];
  currentCardIndex: number;
  timeRemaining: number;
  isPaused: boolean;
  lastSwipeResult: SwipeResult | null;

  // Actions
  startGame: (userId: string, deckId: string) => void;
  swipe: (direction: SwipeDirection, streakMultiplier?: number) => void;
  pauseGame: () => void;
  resumeGame: () => void;
  endGame: () => GameSession | null;
  resetGame: () => void;

  // Internal
  updateTime: (time: number) => void;
  handleSwipeResult: (result: SwipeResult) => void;
  handleSessionComplete: (session: GameSession) => void;
}

export const useGameStore = create<GameState>((set, get) => {
  // Set up GameEngine callbacks
  GameEngine.setOnTick((time: number) => {
    get().updateTime(time);
  });

  GameEngine.setOnSwipe((result: SwipeResult) => {
    get().handleSwipeResult(result);
  });

  GameEngine.setOnComplete((session: GameSession) => {
    get().handleSessionComplete(session);
  });

  return {
    // Initial state
    session: null,
    cards: [],
    currentCardIndex: 0,
    timeRemaining: 60,
    isPaused: false,
    lastSwipeResult: null,

    // Start a new game
    startGame: (userId: string, deckId: string) => {
      // Generate cards for the deck
      const cards = CardGenerator.generateCards(deckId, 20);

      // If no cards (photos deck), create placeholder tasks
      const finalCards = cards.length > 0 ? cards : CardGenerator.generateCards('deck_home', 20);

      // Start the game engine
      const session = GameEngine.startGame(userId, deckId, finalCards);

      set({
        session,
        cards: finalCards,
        currentCardIndex: 0,
        timeRemaining: 60,
        isPaused: false,
        lastSwipeResult: null,
      });
    },

    // Handle swipe
    swipe: (direction: SwipeDirection, streakMultiplier: number = 1) => {
      const { cards, currentCardIndex, session } = get();

      if (!session || currentCardIndex >= cards.length) return;

      const currentCard = cards[currentCardIndex];

      try {
        // Process swipe through game engine
        const result = GameEngine.swipe(direction, currentCard, streakMultiplier);

        // Move to next card
        set(state => ({
          currentCardIndex: state.currentCardIndex + 1,
          lastSwipeResult: result,
          session: GameEngine.getCurrentSession(),
        }));

        // Auto-end if all cards processed
        if (currentCardIndex + 1 >= cards.length) {
          setTimeout(() => {
            get().endGame();
          }, 500);
        }
      } catch (error) {
        console.error('Swipe error:', error);
      }
    },

    // Pause game
    pauseGame: () => {
      GameEngine.pauseGame();
      set({ isPaused: true });
    },

    // Resume game
    resumeGame: () => {
      GameEngine.resumeGame();
      set({ isPaused: false });
    },

    // End game
    endGame: () => {
      const session = GameEngine.endGame();
      if (session) {
        set({ session, isPaused: false });
      }
      return session;
    },

    // Reset game
    resetGame: () => {
      GameEngine.endGame();
      set({
        session: null,
        cards: [],
        currentCardIndex: 0,
        timeRemaining: 60,
        isPaused: false,
        lastSwipeResult: null,
      });
    },

    // Internal: Update timer
    updateTime: (time: number) => {
      set({ timeRemaining: time });
    },

    // Internal: Handle swipe result
    handleSwipeResult: (result: SwipeResult) => {
      set({ lastSwipeResult: result });
    },

    // Internal: Handle session complete
    handleSessionComplete: (session: GameSession) => {
      set({ session });
    },
  };
});

export default useGameStore;
