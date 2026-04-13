/**
 * Vantaris Audio Engine
 *
 * Powered by Tone.js for procedural synthesis + Howler-style playback.
 * No audio files needed -- everything is generated algorithmically.
 *
 * Sound categories:
 * 1. AMBIENT -- procedural lounge jazz (chords, bass, atmosphere)
 * 2. GAME SFX -- card deal snap, chip clink, hit tap, stand exhale
 * 3. OUTCOME -- win chime, loss tone, blackjack fanfare, bust crack
 * 4. UI -- button click, panel open/close, notification ping
 * 5. DEALER -- ElevenLabs TTS (handled via Supabase edge function)
 *
 * All sounds are procedurally generated from oscillators, filters,
 * and envelopes. Zero audio file dependencies.
 */

let toneLoaded = false
let Tone: any = null

async function loadTone() {
  if (toneLoaded) return Tone
  try {
    Tone = await import('tone')
    toneLoaded = true
    return Tone
  } catch {
    console.warn('Tone.js not available, audio disabled')
    return null
  }
}

// ============================================================
// AMBIENT CASINO MUSIC (Tone.js procedural jazz)
// ============================================================

let ambientPlaying = false
let ambientParts: any[] = []

export async function startAmbientMusic() {
  const T = await loadTone()
  if (!T || ambientPlaying) return

  await T.start()
  ambientPlaying = true

  // Jazz chord progression (Cmaj7 -> Dm7 -> Fmaj7 -> G7 -> Cm7 -> Am7)
  const chords = [
    ['C3', 'E3', 'G3', 'B3'],   // Cmaj7
    ['D3', 'F3', 'A3', 'C4'],   // Dm7
    ['F3', 'A3', 'C4', 'E4'],   // Fmaj7
    ['G3', 'B3', 'D4', 'F4'],   // G7
    ['C3', 'Eb3', 'G3', 'Bb3'], // Cm7
    ['A2', 'C3', 'E3', 'G3'],   // Am7
  ]

  // Soft pad synth
  const padSynth = new T.PolySynth(T.Synth, {
    oscillator: { type: 'triangle' },
    envelope: { attack: 0.8, decay: 1.5, sustain: 0.3, release: 2.0 },
    volume: -28,
  }).toDestination()

  // Bass
  const bassSynth = new T.Synth({
    oscillator: { type: 'triangle' },
    envelope: { attack: 0.3, decay: 0.8, sustain: 0.4, release: 1.5 },
    volume: -22,
  }).toDestination()

  // Low-pass filter for warmth
  const filter = new T.Filter({ frequency: 800, type: 'lowpass' }).toDestination()
  padSynth.connect(filter)
  bassSynth.connect(filter)

  let chordIdx = 0

  const loop = new T.Loop((time: number) => {
    const chord = chords[chordIdx % chords.length]
    padSynth.triggerAttackRelease(chord, '2n', time)
    bassSynth.triggerAttackRelease(chord[0].replace(/\d/, (m: string) => String(parseInt(m) - 1)), '2n', time)
    chordIdx++
  }, '2m') // every 2 measures

  loop.start(0)
  T.Transport.bpm.value = 72
  T.Transport.start()

  ambientParts.push(loop, padSynth, bassSynth, filter)
}

export async function stopAmbientMusic() {
  const T = await loadTone()
  if (!T || !ambientPlaying) return

  T.Transport.stop()
  ambientParts.forEach(p => { try { p.dispose() } catch {} })
  ambientParts = []
  ambientPlaying = false
}

// ============================================================
// GAME SOUND EFFECTS (procedural, no audio files)
// ============================================================

export async function playCardDeal() {
  const T = await loadTone()
  if (!T) return

  // Card snap: short noise burst + filter sweep
  const noise = new T.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.08, sustain: 0, release: 0.02 },
    volume: -18,
  }).toDestination()

  const filter = new T.Filter({ frequency: 4000, type: 'highpass' }).toDestination()
  noise.connect(filter)
  noise.triggerAttackRelease('32n')

  setTimeout(() => { noise.dispose(); filter.dispose() }, 200)
}

export async function playChipClink() {
  const T = await loadTone()
  if (!T) return

  // Metallic ping: high-freq sine with fast decay
  const synth = new T.Synth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: 0.15, sustain: 0, release: 0.1 },
    volume: -15,
  }).toDestination()

  // Randomize pitch slightly for organic feel
  const freq = 2000 + Math.random() * 800
  synth.triggerAttackRelease(freq, '64n')

  setTimeout(() => synth.dispose(), 300)
}

export async function playHit() {
  const T = await loadTone()
  if (!T) return

  // Short tap: filtered click
  const synth = new T.MembraneSynth({
    pitchDecay: 0.008,
    octaves: 2,
    envelope: { attack: 0.001, decay: 0.05, sustain: 0, release: 0.03 },
    volume: -20,
  }).toDestination()

  synth.triggerAttackRelease('C5', '64n')
  setTimeout(() => synth.dispose(), 150)
}

export async function playStand() {
  const T = await loadTone()
  if (!T) return

  // Soft exhale: filtered noise, longer decay
  const noise = new T.NoiseSynth({
    noise: { type: 'brown' },
    envelope: { attack: 0.05, decay: 0.3, sustain: 0, release: 0.2 },
    volume: -25,
  }).toDestination()

  const filter = new T.Filter({ frequency: 600, type: 'lowpass' }).toDestination()
  noise.connect(filter)
  noise.triggerAttackRelease('8n')

  setTimeout(() => { noise.dispose(); filter.dispose() }, 600)
}

// ============================================================
// OUTCOME SOUNDS
// ============================================================

export async function playWin() {
  const T = await loadTone()
  if (!T) return

  // Ascending crystal chime (432Hz base)
  const synth = new T.PolySynth(T.Synth, {
    oscillator: { type: 'sine' },
    envelope: { attack: 0.01, decay: 0.4, sustain: 0.1, release: 0.8 },
    volume: -12,
  }).toDestination()

  const notes = ['E5', 'G5', 'B5', 'E6']
  notes.forEach((note, i) => {
    setTimeout(() => synth.triggerAttackRelease(note, '8n'), i * 100)
  })

  setTimeout(() => synth.dispose(), 1500)
}

export async function playBlackjack() {
  const T = await loadTone()
  if (!T) return

  // Brass fanfare: stacked major chord with shimmer
  const synth = new T.PolySynth(T.Synth, {
    oscillator: { type: 'sawtooth' },
    envelope: { attack: 0.05, decay: 0.6, sustain: 0.3, release: 1.2 },
    volume: -10,
  }).toDestination()

  const filter = new T.Filter({ frequency: 2000, type: 'lowpass', Q: 2 }).toDestination()
  synth.connect(filter)

  // Dramatic chord
  synth.triggerAttackRelease(['C4', 'E4', 'G4', 'C5'], '2n')

  // Shimmer (delayed high octave)
  setTimeout(() => {
    const shimmer = new T.Synth({
      oscillator: { type: 'sine' },
      envelope: { attack: 0.1, decay: 0.8, sustain: 0.1, release: 1.0 },
      volume: -15,
    }).toDestination()
    shimmer.triggerAttackRelease('C6', '4n')
    setTimeout(() => shimmer.dispose(), 2000)
  }, 300)

  setTimeout(() => { synth.dispose(); filter.dispose() }, 3000)
}

export async function playLoss() {
  const T = await loadTone()
  if (!T) return

  // Descending minor tone: muted, brief
  const synth = new T.Synth({
    oscillator: { type: 'triangle' },
    envelope: { attack: 0.05, decay: 0.5, sustain: 0, release: 0.3 },
    volume: -18,
  }).toDestination()

  synth.triggerAttackRelease('E3', '8n')
  setTimeout(() => {
    synth.triggerAttackRelease('C3', '8n')
  }, 200)

  setTimeout(() => synth.dispose(), 1000)
}

export async function playBust() {
  const T = await loadTone()
  if (!T) return

  // Glass crack: noise burst + low thud
  const noise = new T.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.12, sustain: 0, release: 0.05 },
    volume: -12,
  }).toDestination()

  const thud = new T.MembraneSynth({
    pitchDecay: 0.02,
    octaves: 4,
    envelope: { attack: 0.001, decay: 0.2, sustain: 0, release: 0.1 },
    volume: -15,
  }).toDestination()

  noise.triggerAttackRelease('16n')
  thud.triggerAttackRelease('C1', '8n')

  setTimeout(() => { noise.dispose(); thud.dispose() }, 500)
}

export async function playSplit() {
  const T = await loadTone()
  if (!T) return

  // Two quick metallic pings (card split apart)
  const synth = new T.Synth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: 0.1, sustain: 0, release: 0.08 },
    volume: -14,
  }).toDestination()

  synth.triggerAttackRelease('A5', '64n')
  setTimeout(() => synth.triggerAttackRelease('E6', '64n'), 120)

  setTimeout(() => synth.dispose(), 400)
}

// ============================================================
// UI SOUNDS
// ============================================================

export async function playButtonClick() {
  const T = await loadTone()
  if (!T) return

  const synth = new T.Synth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.001, decay: 0.04, sustain: 0, release: 0.02 },
    volume: -22,
  }).toDestination()

  synth.triggerAttackRelease('G5', '64n')
  setTimeout(() => synth.dispose(), 100)
}

export async function playNotification() {
  const T = await loadTone()
  if (!T) return

  const synth = new T.Synth({
    oscillator: { type: 'sine' },
    envelope: { attack: 0.01, decay: 0.2, sustain: 0.05, release: 0.3 },
    volume: -16,
  }).toDestination()

  synth.triggerAttackRelease('E5', '16n')
  setTimeout(() => synth.triggerAttackRelease('A5', '16n'), 150)

  setTimeout(() => synth.dispose(), 600)
}

// ============================================================
// MASTER CONTROLLER
// ============================================================

let soundEnabled = true

export function setSoundEnabled(enabled: boolean) {
  soundEnabled = enabled
}

export function isSoundEnabled(): boolean {
  return soundEnabled
}

// Wrapper that checks if sound is enabled before playing
export function withSound(fn: () => Promise<void>) {
  return async () => {
    if (soundEnabled) await fn()
  }
}
