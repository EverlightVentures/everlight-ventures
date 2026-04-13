/**
 * Vantaris Jukebox Engine
 *
 * From the GDD: "The jukebox is always visible, always spinning,
 * always influencing the room."
 *
 * Core concepts:
 * - Community song queue (anyone can add, costs Quarters)
 * - Vibe States: HYPE (128+ BPM), HEAT (90-128), CHILL (60-90), AFTER_HOURS (<60)
 * - Vibe state drives lighting, crowd, dealer behavior
 * - House Mix mode when queue is empty (AI-filled ambient)
 * - DJ leaderboard (most-upvoted songs)
 *
 * Phase 1 (current): Genre-based ambient tracks via Tone.js
 * Phase 2: Licensed tracks from Epidemic Sound/Artlist
 * Phase 3: Spotify/Apple Music API integration
 */

export type VibeState = 'HYPE' | 'HEAT' | 'CHILL' | 'AFTER_HOURS'

export interface Song {
  id: string
  title: string
  artist: string
  bpm: number
  genre: string
  vibeState: VibeState
  duration: number // seconds
  votes: number
  queuedBy: string
}

export interface JukeboxState {
  currentSong: Song | null
  queue: Song[]
  vibeState: VibeState
  isPlaying: boolean
  volume: number
  houseMixActive: boolean
  quartersBalance: number
}

// Determine vibe state from BPM
export function getVibeState(bpm: number): VibeState {
  if (bpm >= 128) return 'HYPE'
  if (bpm >= 90) return 'HEAT'
  if (bpm >= 60) return 'CHILL'
  return 'AFTER_HOURS'
}

// Vibe state -> environment config
export const VIBE_CONFIGS: Record<VibeState, {
  ambientVolume: number
  crowdEnergy: number
  musicVolume: number
  lightingProfile: string
  particleEffect: string | null
  dealerReactChance: number
}> = {
  HYPE: {
    ambientVolume: 0.4,
    crowdEnergy: 1.0,
    musicVolume: 0.8,
    lightingProfile: 'neon_night', // cyan/magenta, high bloom
    particleEffect: 'strobe',
    dealerReactChance: 0.1, // 10% chance per hand
  },
  HEAT: {
    ambientVolume: 0.5,
    crowdEnergy: 0.7,
    musicVolume: 0.8,
    lightingProfile: 'red_gold', // warm high contrast
    particleEffect: null,
    dealerReactChance: 0.05,
  },
  CHILL: {
    ambientVolume: 0.7,
    crowdEnergy: 0.3,
    musicVolume: 0.7,
    lightingProfile: 'amber_lounge', // warm dim, fog
    particleEffect: 'smoke_haze',
    dealerReactChance: 0.02,
  },
  AFTER_HOURS: {
    ambientVolume: 0.9,
    crowdEnergy: 0.1,
    musicVolume: 0.6,
    lightingProfile: 'night_blue', // deep blue, spotlight on table
    particleEffect: null,
    dealerReactChance: 0.01,
  },
}

// House Mix: pre-built ambient tracks per vibe state
const HOUSE_MIX_LIBRARY: Song[] = [
  { id: 'hm1', title: 'Midnight Lounge', artist: 'Vantaris DJ', bpm: 72, genre: 'Jazz', vibeState: 'CHILL', duration: 240, votes: 0, queuedBy: 'House' },
  { id: 'hm2', title: 'Neon Nights', artist: 'Vantaris DJ', bpm: 130, genre: 'EDM', vibeState: 'HYPE', duration: 210, votes: 0, queuedBy: 'House' },
  { id: 'hm3', title: 'Golden Hour', artist: 'Vantaris DJ', bpm: 95, genre: 'R&B', vibeState: 'HEAT', duration: 220, votes: 0, queuedBy: 'House' },
  { id: 'hm4', title: 'After Dark', artist: 'Vantaris DJ', bpm: 55, genre: 'Ambient', vibeState: 'AFTER_HOURS', duration: 300, votes: 0, queuedBy: 'House' },
  { id: 'hm5', title: 'Casino Royale', artist: 'Vantaris DJ', bpm: 85, genre: 'Jazz', vibeState: 'CHILL', duration: 250, votes: 0, queuedBy: 'House' },
  { id: 'hm6', title: 'High Roller', artist: 'Vantaris DJ', bpm: 110, genre: 'Hip-Hop', vibeState: 'HEAT', duration: 200, votes: 0, queuedBy: 'House' },
]

// Initialize jukebox state
export function createJukeboxState(): JukeboxState {
  return {
    currentSong: HOUSE_MIX_LIBRARY[0],
    queue: [],
    vibeState: 'CHILL',
    isPlaying: false,
    volume: 0.7,
    houseMixActive: true,
    quartersBalance: 50, // starting quarters
  }
}

// Queue a song (costs quarters)
export function queueSong(state: JukeboxState, song: Song, cost: number): JukeboxState {
  if (state.quartersBalance < cost) return state
  return {
    ...state,
    queue: [...state.queue, song],
    quartersBalance: state.quartersBalance - cost,
    houseMixActive: false,
  }
}

// Advance to next song
export function advanceQueue(state: JukeboxState): JukeboxState {
  if (state.queue.length > 0) {
    const [next, ...rest] = state.queue
    return {
      ...state,
      currentSong: next,
      queue: rest,
      vibeState: next.vibeState,
      houseMixActive: rest.length === 0,
    }
  }
  // Queue empty -> House Mix
  const random = HOUSE_MIX_LIBRARY[Math.floor(Math.random() * HOUSE_MIX_LIBRARY.length)]
  return {
    ...state,
    currentSong: random,
    vibeState: random.vibeState,
    houseMixActive: true,
  }
}

// Vote to skip current song
export function voteSkip(state: JukeboxState): JukeboxState {
  // In real multiplayer, this would need majority vote
  // For now, instant skip
  return advanceQueue(state)
}
