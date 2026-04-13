/**
 * Vantaris GSAP Cinematic Animations
 *
 * Frame-perfect sequenced animations for game events.
 * Framer Motion handles UI state transitions.
 * GSAP handles the CINEMATIC MOMENTS:
 *
 * 1. Card deal sequence (staggered, spring, with sound cues)
 * 2. Chip toss to pot (arc trajectory)
 * 3. Win reveal (banner + particles + camera + sound orchestrated)
 * 4. Blackjack celebration (full-screen takeover)
 * 5. Dealer card flip (3D rotation with content swap at midpoint)
 * 6. Bust shatter (cards scatter with physics)
 * 7. Split separation (cards slide apart)
 */

import gsap from 'gsap'

// ============================================================
// CARD DEAL TIMELINE
// ============================================================

/**
 * Animate dealing 4 cards in casino order.
 * P1 (300ms) -> D1 (300ms) -> P2 (300ms) -> D2-facedown (300ms)
 *
 * Each card: scale 0 -> 1, rotateY 90 -> 0, translateX from off-screen
 * with overshoot spring easing.
 */
export function animateDeal(
  cardElements: HTMLElement[],
  onCardDealt?: (index: number) => void,
): gsap.core.Timeline {
  const tl = gsap.timeline()

  cardElements.forEach((el, i) => {
    // Initial state
    gsap.set(el, {
      opacity: 0,
      scale: 0,
      rotateY: 90,
      x: 200,
    })

    tl.to(el, {
      opacity: 1,
      scale: 1,
      rotateY: 0,
      x: 0,
      duration: 0.4,
      ease: 'back.out(1.7)',
      onStart: () => onCardDealt?.(i),
    }, i * 0.3) // 300ms stagger
  })

  return tl
}

// ============================================================
// DEALER CARD FLIP (3D rotation with content swap)
// ============================================================

/**
 * Flip a face-down card to reveal its face.
 * Uses a two-phase rotation: 0 -> 90 (hide), swap content, 90 -> 0 (reveal)
 *
 * @param element The card DOM element
 * @param onMidpoint Called at 90deg to swap the visual content
 */
export function animateCardFlip(
  element: HTMLElement,
  onMidpoint: () => void,
): gsap.core.Timeline {
  const tl = gsap.timeline()

  // Phase 1: rotate to 90 (card becomes invisible edge-on)
  tl.to(element, {
    rotateY: 90,
    duration: 0.15,
    ease: 'power2.in',
  })

  // Midpoint: swap content
  tl.call(onMidpoint)

  // Phase 2: rotate from 90 to 0 (reveal face)
  tl.to(element, {
    rotateY: 0,
    duration: 0.2,
    ease: 'back.out(1.4)',
  })

  return tl
}

// ============================================================
// WIN CELEBRATION (orchestrated sequence)
// ============================================================

/**
 * Full win celebration sequence:
 * 1. Banner scales in with spring (0ms)
 * 2. Amount counter ticks up (200ms)
 * 3. Screen edge glow (400ms)
 * 4. XP bar fills (600ms)
 * 5. Chip count updates (800ms)
 *
 * For BLACKJACK: add gold flash + camera zoom + extended particles
 */
export function animateWinCelebration(
  bannerEl: HTMLElement | null,
  amountEl: HTMLElement | null,
  isBlackjack: boolean = false,
): gsap.core.Timeline {
  const tl = gsap.timeline()

  if (bannerEl) {
    gsap.set(bannerEl, { scale: 0.3, opacity: 0 })
    tl.to(bannerEl, {
      scale: 1,
      opacity: 1,
      duration: 0.4,
      ease: 'back.out(2.5)',
    })
  }

  if (amountEl) {
    tl.from(amountEl, {
      y: 20,
      opacity: 0,
      duration: 0.3,
      ease: 'power2.out',
    }, '+=0.2')
  }

  if (isBlackjack && bannerEl) {
    // Extra pulse for blackjack
    tl.to(bannerEl, {
      scale: 1.15,
      duration: 0.15,
      ease: 'power2.out',
      yoyo: true,
      repeat: 1,
    }, '+=0.1')
  }

  return tl
}

// ============================================================
// BUST SHATTER (cards scatter)
// ============================================================

/**
 * On bust: cards scatter outward with rotation and fade.
 * Each card gets a random velocity vector.
 */
export function animateBustShatter(cardElements: HTMLElement[]): gsap.core.Timeline {
  const tl = gsap.timeline()

  cardElements.forEach((el) => {
    const randomX = (Math.random() - 0.5) * 300
    const randomY = (Math.random() - 0.5) * 200 + 100 // mostly downward
    const randomRotate = (Math.random() - 0.5) * 180

    tl.to(el, {
      x: `+=${randomX}`,
      y: `+=${randomY}`,
      rotation: randomRotate,
      opacity: 0,
      scale: 0.5,
      duration: 0.6,
      ease: 'power2.out',
    }, 0) // all cards scatter simultaneously
  })

  return tl
}

// ============================================================
// SPLIT SEPARATION
// ============================================================

/**
 * When player splits: the two cards slide apart horizontally
 * and new cards deal into each hand position.
 */
export function animateSplit(
  card1: HTMLElement,
  card2: HTMLElement,
  separationPx: number = 120,
): gsap.core.Timeline {
  const tl = gsap.timeline()

  tl.to(card1, {
    x: `-=${separationPx / 2}`,
    duration: 0.4,
    ease: 'back.out(1.4)',
  }, 0)

  tl.to(card2, {
    x: `+=${separationPx / 2}`,
    duration: 0.4,
    ease: 'back.out(1.4)',
  }, 0)

  return tl
}

// ============================================================
// CHIP TOSS (arc trajectory to pot)
// ============================================================

/**
 * Animate a chip flying from the player's chip stack
 * to the center betting area in an arc.
 */
export function animateChipToss(
  chipEl: HTMLElement,
  startPos: { x: number; y: number },
  endPos: { x: number; y: number },
): gsap.core.Timeline {
  const tl = gsap.timeline()

  gsap.set(chipEl, {
    x: startPos.x,
    y: startPos.y,
    scale: 1,
    opacity: 1,
  })

  // Arc motion using motionPath-like approach
  const midX = (startPos.x + endPos.x) / 2
  const midY = Math.min(startPos.y, endPos.y) - 80 // arc height

  tl.to(chipEl, {
    x: midX,
    y: midY,
    scale: 0.8,
    duration: 0.2,
    ease: 'power2.out',
  })

  tl.to(chipEl, {
    x: endPos.x,
    y: endPos.y,
    scale: 0.6,
    duration: 0.2,
    ease: 'power2.in',
  })

  return tl
}

// ============================================================
// SCREEN SHAKE (on bust/loss)
// ============================================================

export function screenShake(
  element: HTMLElement,
  intensity: number = 4,
  duration: number = 0.4,
) {
  gsap.to(element, {
    x: `random(-${intensity}, ${intensity})`,
    y: `random(-${intensity / 2}, ${intensity / 2})`,
    duration: 0.05,
    repeat: Math.floor(duration / 0.05),
    yoyo: true,
    ease: 'none',
    onComplete: () => {
      gsap.to(element, { x: 0, y: 0, duration: 0.1 })
    },
  })
}

// ============================================================
// COUNTER ANIMATION (smooth number tick-up)
// ============================================================

/**
 * Animate a number counting up from start to end.
 * Used for chip balance, XP, win amount displays.
 */
export function animateCounter(
  element: HTMLElement,
  startVal: number,
  endVal: number,
  duration: number = 1.0,
  prefix: string = '',
  suffix: string = '',
) {
  const obj = { val: startVal }

  gsap.to(obj, {
    val: endVal,
    duration,
    ease: 'power2.out',
    onUpdate: () => {
      element.textContent = `${prefix}${Math.floor(obj.val).toLocaleString()}${suffix}`
    },
  })
}

// ============================================================
// LIGHTNING FLASH
// ============================================================

/**
 * Flash the screen with a golden lightning effect
 * when a lightning multiplier is active.
 */
export function lightningFlash(container: HTMLElement) {
  const flash = document.createElement('div')
  flash.style.cssText = `
    position: fixed; inset: 0; z-index: 100;
    background: radial-gradient(circle, rgba(241,196,15,0.15), transparent 70%);
    pointer-events: none;
  `
  container.appendChild(flash)

  gsap.fromTo(flash,
    { opacity: 0 },
    {
      opacity: 1,
      duration: 0.1,
      yoyo: true,
      repeat: 3,
      ease: 'power4.inOut',
      onComplete: () => flash.remove(),
    },
  )
}

// ============================================================
// GAMBIT ENERGY CHARGE
// ============================================================

/**
 * Card vibrates, glows pink, then launches with trail.
 * The signature Gambit kinetic energy effect.
 */
export function animateGambitCharge(
  cardEl: HTMLElement,
  onRelease: () => void,
): gsap.core.Timeline {
  const tl = gsap.timeline()

  // Phase 1: Vibrate (400ms, 8Hz = ~3px amplitude)
  tl.to(cardEl, {
    x: '+=3',
    duration: 0.0625, // 1/16th second = 16Hz (close enough to 8Hz with yoyo)
    repeat: 12,
    yoyo: true,
    ease: 'none',
  })

  // Phase 2: Glow
  tl.to(cardEl, {
    boxShadow: '0 0 30px rgba(255,45,119,0.6), 0 0 60px rgba(255,45,119,0.3)',
    duration: 0.3,
    ease: 'power2.out',
  }, '-=0.3') // overlap with vibrate

  // Phase 3: Release
  tl.call(onRelease)

  // Phase 4: Reset glow
  tl.to(cardEl, {
    boxShadow: '0 4px 20px rgba(0,0,0,0.6)',
    duration: 0.4,
    ease: 'power2.out',
  })

  return tl
}
