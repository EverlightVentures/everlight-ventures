/**
 * GameEngine - Core 60-second game logic
 */

import { v4 as uuidv4 } from 'uuid';
import type {
  GameSession,
  Card,
  SwipeDirection,
  SwipeResult,
  ChecklistItem,
  TaskCardContent,
  PhotoCardContent,
  DecisionCardContent,
} from '@types';
import { GAME_CONFIG, SCORING } from '@config/constants';

export class GameEngine {
  private session: GameSession | null = null;
  private timer: NodeJS.Timeout | null = null;
  private timeRemaining: number = GAME_CONFIG.sessionDuration;
  private comboTimer: NodeJS.Timeout | null = null;
  private currentCombo: number = 0;

  // Callbacks
  private onTick?: (time: number) => void;
  private onComplete?: (session: GameSession) => void;
  private onSwipe?: (result: SwipeResult) => void;

  /**
   * Start a new game session
   */
  startGame(userId: string, deckId: string, cards: Card[]): GameSession {
    // Clear any existing session
    this.endGame();

    // Initialize new session
    this.session = {
      id: uuidv4(),
      userId,
      deckId,
      startTime: Date.now(),
      score: 0,
      baseScore: 0,
      multiplier: 1,
      cardsProcessed: 0,
      leftSwipes: 0,
      rightSwipes: 0,
      holds: 0,
      heldCards: [],
      comboCount: 0,
      maxCombo: 0,
      checklist: [],
      status: 'active',
    };

    this.timeRemaining = GAME_CONFIG.sessionDuration;
    this.currentCombo = 0;

    // Start countdown timer
    this.startTimer();

    return this.session;
  }

  /**
   * Start the 60-second countdown
   */
  private startTimer() {
    this.timer = setInterval(() => {
      this.timeRemaining -= 1;

      // Notify listener
      if (this.onTick) {
        this.onTick(this.timeRemaining);
      }

      // Check if time is up
      if (this.timeRemaining <= 0) {
        this.endGame();
      }
    }, 1000);
  }

  /**
   * Process a swipe action
   */
  swipe(direction: SwipeDirection, card: Card, streakMultiplier: number = 1): SwipeResult {
    if (!this.session || this.session.status !== 'active') {
      throw new Error('No active game session');
    }

    // Calculate base points
    let points = 0;
    if (direction === 'left') {
      points = SCORING.swipeLeft;
      this.session.leftSwipes += 1;
    } else if (direction === 'right') {
      points = SCORING.swipeRight;
      this.session.rightSwipes += 1;
    } else if (direction === 'hold') {
      points = SCORING.hold;
      this.session.holds += 1;
      // Track held cards for checklist and roulette
      this.session.heldCards.push(card);
    }

    // Apply card metadata boost
    const boost = card.metadata.boost || 0;
    points += boost;

    // Apply combo multiplier
    this.currentCombo += 1;
    const comboMultiplier = this.getComboMultiplier(this.currentCombo);
    points = Math.round(points * comboMultiplier);

    // Reset combo after 3 seconds of inactivity
    this.resetComboTimer();

    // Speed bonus (if playing fast)
    if (this.timeRemaining > SCORING.speedBonusThreshold) {
      points += SCORING.speedBonusPoints;
    }

    // Update session
    this.session.cardsProcessed += 1;
    this.session.baseScore += points;
    this.session.comboCount = this.currentCombo;
    this.session.maxCombo = Math.max(this.session.maxCombo, this.currentCombo);

    // Calculate final score with streak multiplier
    this.session.multiplier = 1 + (streakMultiplier * SCORING.streakMultiplierPerDay);
    this.session.score = Math.round(this.session.baseScore * this.session.multiplier);

    const result: SwipeResult = {
      direction,
      points,
      combo: this.currentCombo,
      card,
    };

    // Notify listener
    if (this.onSwipe) {
      this.onSwipe(result);
    }

    return result;
  }

  /**
   * Get combo multiplier
   */
  private getComboMultiplier(combo: number): number {
    if (combo < 3) return 1.0;
    if (combo < 6) return 1.2;
    if (combo < 10) return 1.5;
    return 2.0; // Max 2x multiplier
  }

  /**
   * Reset combo after inactivity
   */
  private resetComboTimer() {
    if (this.comboTimer) {
      clearTimeout(this.comboTimer);
    }

    this.comboTimer = setTimeout(() => {
      this.currentCombo = 0;
    }, 3000); // 3 seconds
  }

  /**
   * Pause the game
   */
  pauseGame() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  /**
   * Resume the game
   */
  resumeGame() {
    if (!this.timer && this.session?.status === 'active') {
      this.startTimer();
    }
  }

  /**
   * End the game session
   */
  endGame(): GameSession | null {
    if (!this.session) return null;

    // Stop timers
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    if (this.comboTimer) {
      clearTimeout(this.comboTimer);
      this.comboTimer = null;
    }

    // Finalize session
    this.session.endTime = Date.now();
    this.session.status = 'completed';

    // Apply completion bonus
    const completionRate = this.session.cardsProcessed / GAME_CONFIG.maxCardsPerSession;
    if (completionRate >= SCORING.completionRateThreshold) {
      this.session.baseScore += SCORING.completionBonus;
      this.session.score = Math.round(this.session.baseScore * this.session.multiplier);
    }

    // Generate checklist from held cards (placeholder - will be enhanced later)
    this.session.checklist = this.generateChecklist();

    // Select roulette action (placeholder - will be enhanced later)
    this.session.selectedAction = this.selectRouletteAction();

    const completedSession = { ...this.session };

    // Notify listener
    if (this.onComplete) {
      this.onComplete(completedSession);
    }

    // Reset
    this.session = null;
    this.timeRemaining = GAME_CONFIG.sessionDuration;
    this.currentCombo = 0;

    return completedSession;
  }

  /**
   * Generate checklist items from held cards
   */
  private generateChecklist(): ChecklistItem[] {
    if (!this.session) return [];

    const checklist: ChecklistItem[] = [];
    const now = Date.now();

    // Generate checklist items from held cards
    for (const card of this.session.heldCards) {
      let text = '';

      switch (card.type) {
        case 'task':
          const taskContent = card.content as TaskCardContent;
          text = taskContent.title;
          if (taskContent.estimatedMinutes) {
            text += ` (${taskContent.estimatedMinutes} min)`;
          }
          break;

        case 'photo':
          const photoContent = card.content as PhotoCardContent;
          if (photoContent.isScreenshot) {
            text = 'Organize or delete screenshot';
          } else if (photoContent.isDuplicate) {
            text = 'Review and delete duplicate photo';
          } else if (photoContent.location) {
            text = `Organize photo from ${photoContent.location}`;
          } else {
            text = 'Organize photo';
          }
          break;

        case 'decision':
          const decisionContent = card.content as DecisionCardContent;
          text = `Decide: ${decisionContent.question}`;
          break;
      }

      if (text) {
        checklist.push({
          id: uuidv4(),
          text,
          completed: false,
          createdAt: now,
        });
      }
    }

    // If no held cards, add default motivational items
    if (checklist.length === 0) {
      checklist.push({
        id: uuidv4(),
        text: 'Great session! Take a quick break',
        completed: false,
        createdAt: now,
      });
    }

    return checklist;
  }

  /**
   * Select roulette action from held cards
   */
  private selectRouletteAction(): string {
    if (!this.session || this.session.heldCards.length === 0) {
      // Default actions if no cards were held
      const defaultActions = [
        'Take a 5-minute break',
        'Organize your workspace',
        'Clear notifications',
        'Review your calendar',
        'Hydrate and stretch',
      ];
      return defaultActions[Math.floor(Math.random() * defaultActions.length)];
    }

    // Select a random held card
    const randomCard = this.session.heldCards[
      Math.floor(Math.random() * this.session.heldCards.length)
    ];

    let action = '';

    switch (randomCard.type) {
      case 'task':
        const taskContent = randomCard.content as TaskCardContent;
        // Create action based on priority
        if (taskContent.priority === 'high') {
          action = `Complete high-priority task: ${taskContent.title}`;
        } else {
          action = `Start task: ${taskContent.title}`;
        }
        break;

      case 'photo':
        const photoContent = randomCard.content as PhotoCardContent;
        if (photoContent.isScreenshot) {
          action = 'Delete 10 screenshots from your photo library';
        } else if (photoContent.isDuplicate) {
          action = 'Remove duplicate photos';
        } else if (photoContent.suggestedCategory) {
          action = `Organize photos into ${photoContent.suggestedCategory} album`;
        } else {
          action = 'Organize 5 photos';
        }
        break;

      case 'decision':
        const decisionContent = randomCard.content as DecisionCardContent;
        action = `Make a decision: ${decisionContent.question}`;
        break;
    }

    return action || 'Take action on a held item';
  }

  /**
   * Get current session
   */
  getCurrentSession(): GameSession | null {
    return this.session;
  }

  /**
   * Get time remaining
   */
  getTimeRemaining(): number {
    return this.timeRemaining;
  }

  /**
   * Set callbacks
   */
  setOnTick(callback: (time: number) => void) {
    this.onTick = callback;
  }

  setOnComplete(callback: (session: GameSession) => void) {
    this.onComplete = callback;
  }

  setOnSwipe(callback: (result: SwipeResult) => void) {
    this.onSwipe = callback;
  }
}

export default new GameEngine();
