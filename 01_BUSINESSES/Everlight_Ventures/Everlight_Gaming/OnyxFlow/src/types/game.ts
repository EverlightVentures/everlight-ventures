/**
 * Game Type Definitions
 */

// Card Types
export type CardType = 'photo' | 'task' | 'decision';
export type SwipeDirection = 'left' | 'right' | 'hold';
export type SessionStatus = 'active' | 'completed' | 'abandoned';
export type DeckCategory = 'photos' | 'home' | 'work' | 'travel' | 'custom';

// Card Content Types
export interface PhotoCardContent {
  photoUri: string;
  thumbnailUri: string;
  dateTaken?: number;
  location?: string; // City level only (privacy)
  suggestedCategory?: DeckCategory;
  fileSize?: number;
  isDuplicate?: boolean;
  isScreenshot?: boolean;
}

export interface TaskCardContent {
  title: string;
  description?: string;
  priority: 'low' | 'medium' | 'high';
  estimatedMinutes?: number;
  category?: string;
}

export interface DecisionCardContent {
  question: string;
  options: string[];
}

export type CardContent = PhotoCardContent | TaskCardContent | DecisionCardContent;

// Card Metadata
export interface CardMetadata {
  boost?: number; // Scoring boost (recent, important, etc.)
  tags?: string[];
  importance?: number;
}

// Main Card Interface
export interface Card {
  id: string;
  deckId: string;
  type: CardType;
  content: CardContent;
  metadata: CardMetadata;
  createdAt: number;
}

// Checklist
export interface ChecklistItem {
  id: string;
  text: string;
  completed: boolean;
  createdAt: number;
  completedAt?: number;
}

// Game Session
export interface GameSession {
  id: string;
  userId: string;
  deckId: string;
  startTime: number;
  endTime?: number;
  score: number;
  baseScore: number;
  multiplier: number;
  cardsProcessed: number;
  leftSwipes: number;
  rightSwipes: number;
  holds: number;
  heldCards: Card[]; // Cards that were held (swiped up)
  comboCount: number;
  maxCombo: number;
  selectedAction?: string; // From roulette
  checklist: ChecklistItem[];
  status: SessionStatus;
  tokensEarned?: number;
}

// Swipe Result
export interface SwipeResult {
  direction: SwipeDirection;
  points: number;
  combo: number;
  card: Card;
}
