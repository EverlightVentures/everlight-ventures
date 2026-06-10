/**
 * Deck Definitions
 */

export interface Deck {
  id: string;
  name: string;
  description: string;
  icon: string; // Feather icon name or custom icon
  color: string; // Hex color
  isPremium: boolean;
  packId?: string; // Associated IAP pack
  category: 'photos' | 'home' | 'work' | 'travel' | 'custom';
  actions: string[]; // Possible roulette actions for this deck
}

export const DECKS: Deck[] = [
  {
    id: 'deck_photos',
    name: 'Photos',
    description: 'Organize your photo library — delete, keep, or create albums',
    icon: 'camera',
    color: '#007AFF',
    isPremium: false,
    category: 'photos',
    actions: [
      'Delete 10 screenshots',
      'Create 1 new album',
      'Share 3 favorite photos',
      'Archive old photos (6+ months)',
      'Delete duplicate photos',
      'Organize photos by location',
      'Delete blurry photos',
      'Create a photo collage',
    ],
  },
  {
    id: 'deck_home',
    name: 'Home',
    description: 'Quick household tasks — clean, organize, and maintain',
    icon: 'home',
    color: '#34C759',
    isPremium: true,
    packId: 'momentum_pack',
    category: 'home',
    actions: [
      'Wipe down kitchen counters',
      'Organize 1 drawer',
      'Take out trash',
      'Water plants',
      'Make your bed',
      'Clean bathroom sink',
      'Sort 10 items to donate',
      'Vacuum one room',
      'Wipe down appliances',
      'Clean mirrors',
      'Organize pantry shelf',
      'Declutter coffee table',
    ],
  },
  {
    id: 'deck_work',
    name: 'Work',
    description: 'Productivity tasks — emails, meetings, and project work',
    icon: 'briefcase',
    color: '#D4AF37',
    isPremium: true,
    packId: 'flow_pack',
    category: 'work',
    actions: [
      'Clear 20 unread emails',
      'Schedule 1 meeting',
      'Update project status',
      'Review 1 document',
      'Send 3 follow-up emails',
      'Organize desktop files',
      'Update task list',
      'Research 1 topic',
      'Draft 1 message',
      'Review calendar for tomorrow',
      'Archive old emails',
      'Update team on progress',
    ],
  },
  {
    id: 'deck_travel',
    name: 'Travel',
    description: 'Trip planning — booking, packing, and itinerary',
    icon: 'map-pin',
    color: '#FF9500',
    isPremium: true,
    packId: 'deep_focus_pack',
    category: 'travel',
    actions: [
      'Research 1 destination',
      'Book accommodation',
      'Create packing list',
      'Check travel requirements',
      'Book transportation',
      'Make restaurant reservation',
      'Download offline maps',
      'Check weather forecast',
      'Notify bank of travel',
      'Share itinerary with family',
      'Pack toiletries',
      'Charge all devices',
    ],
  },
];

export const getDefaultDeck = (): Deck => {
  return DECKS[0]; // Photos deck
};

export const getDeckById = (id: string): Deck | undefined => {
  return DECKS.find(deck => deck.id === id);
};

export const getFreeDeck = (): Deck[] => {
  return DECKS.filter(deck => !deck.isPremium);
};

export const getPremiumDecks = (): Deck[] => {
  return DECKS.filter(deck => deck.isPremium);
};

export const getDecksByCategory = (
  category: 'photos' | 'home' | 'work' | 'travel' | 'custom',
): Deck[] => {
  return DECKS.filter(deck => deck.category === category);
};
