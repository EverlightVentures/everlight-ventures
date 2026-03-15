# LOVABLE PROMPT: Arcade as Easter Egg -- Exclusive VIP Discovery

Paste this into Lovable. The Arcade (Blackjack, Alley Kingz) is being repositioned from "a tab in the nav" to an EXCLUSIVE, HIDDEN experience that players discover organically. Think speakeasy, not storefront.

Design philosophy: "You don't find the lounge. The lounge finds you."

---

## PROMPT:

Remove the Arcade from the main site navigation entirely. Instead, implement an Easter egg discovery system where the Arcade is unlocked through hidden interactions on the main site. This creates an air of exclusivity -- players who find it feel like they have found something special. VIP feel. No mixing business (Onyx, Logistics, HiveMind) with pleasure (the Arcade).

---

## STEP 1: REMOVE ARCADE FROM MAIN NAV

- Remove /arcade from the top navigation links
- Remove /arcade from the mobile bottom nav tabs
- The route /arcade still EXISTS and is functional -- it is just not linked from the nav
- Players who already know the URL can still navigate directly
- /arcade/blackjack and /arcade/alley-kingz remain accessible via direct URL

Do NOT show a 404 or "coming soon" if someone visits /arcade directly. The page still loads -- it just is not advertised.

---

## STEP 2: EASTER EGG TRIGGERS (three discovery paths)

Implement THREE ways players can discover and unlock the Arcade. The first time any trigger fires, show an elegant reveal animation and the Arcade becomes permanently accessible from their account menu.

### Trigger A: The EV Monogram Long Press

On the EV monogram logo in the top-left corner of the nav:
- Desktop: Click and hold for 3 seconds
- Mobile: Long press for 3 seconds

A subtle gold pulse radiates from the logo while holding. On success:
- The logo briefly flashes white, then returns to gold
- A card slides up from the bottom: "You found the Lounge. Welcome."
- Routes to /arcade

```typescript
function useLongPress(callback: () => void, duration = 3000) {
  const timerRef = useRef<NodeJS.Timeout>();
  const [isHolding, setIsHolding] = useState(false);

  const start = () => {
    setIsHolding(true);
    timerRef.current = setTimeout(() => {
      setIsHolding(false);
      callback();
    }, duration);
  };

  const cancel = () => {
    setIsHolding(false);
    clearTimeout(timerRef.current);
  };

  return {
    onMouseDown: start,
    onMouseUp: cancel,
    onMouseLeave: cancel,
    onTouchStart: start,
    onTouchEnd: cancel,
    isHolding,
  };
}

const longPress = useLongPress(() => {
  setArcadeUnlocked(true);
  sessionStorage.setItem('arcade_unlocked', 'true');
  setShowArcadeReveal(true);
}, 3000);

<EVMonogram {...longPress} />
```

### Trigger B: Konami Code on Any Page

Classic sequence: ArrowUp ArrowUp ArrowDown ArrowDown ArrowLeft ArrowRight ArrowLeft ArrowRight B A

```typescript
useEffect(() => {
  const KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  let index = 0;

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === KONAMI[index]) {
      index++;
      if (index === KONAMI.length) {
        index = 0;
        setArcadeUnlocked(true);
        localStorage.setItem('arcade_unlocked', 'true');
        setShowArcadeReveal(true);
        router.push('/arcade');
      }
    } else {
      index = 0;
    }
  };

  window.addEventListener('keydown', handleKey);
  return () => window.removeEventListener('keydown', handleKey);
}, []);
```

### Trigger C: The Hidden Link (Whisper in the Copy)

On the homepage footer, embed a barely-visible link in the copyright line:

```
Copyright 2026 Everlight Ventures LLC. All rights reserved.
Built in the light. [The lounge is always open.]
```

The "The lounge is always open." text is:
- Color: #1E1E1E on #0A0A0A background (nearly invisible, almost matches background)
- On hover: fades to #8A8A8A (smoke)
- Font-size: 11px, Inter, not underlined
- Links to /arcade
- No tooltip, no indicator -- if you find it, you find it

```typescript
<p
  className="text-[11px] text-[#1E1E1E] hover:text-[#8A8A8A] transition-colors duration-500 cursor-pointer mt-1"
  onClick={() => router.push('/arcade')}
>
  The lounge is always open.
</p>
```

---

## STEP 3: ARCADE REVEAL ANIMATION

When any Easter egg trigger fires for the first time, show this reveal sequence:

```typescript
function ArcadeRevealModal({ onComplete }: { onComplete: () => void }) {
  return (
    <div
      className="fixed inset-0 z-[9999] bg-[#0A0A0A] flex items-center justify-center"
      style={{ animation: 'fadeIn 0.5s ease' }}
    >
      <div className="text-center max-w-md px-8">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#D4AF37"
          strokeWidth="1.5"
          className="mx-auto mb-8 animate-pulse"
        >
          <polygon points="12,2 22,9 12,22 2,9" />
        </svg>

        <p className="text-[#8A8A8A] text-xs tracking-[0.3em] uppercase mb-3">
          You found it
        </p>
        <h2 className="text-[#D4AF37] font-['Cormorant_Garamond'] text-4xl font-semibold mb-4">
          The Lounge
        </h2>
        <p className="text-[#8A8A8A] text-sm leading-relaxed mb-10">
          Not everything worth having is advertised.<br/>
          Welcome to the exclusive side of Everlight.
        </p>
        <button
          onClick={onComplete}
          className="border border-[#D4AF37] text-[#D4AF37] px-10 py-3 text-sm tracking-widest uppercase hover:bg-[#D4AF37] hover:text-[#0A0A0A] transition-all duration-300"
        >
          Enter
        </button>
      </div>
    </div>
  );
}
```

After clicking Enter: navigate to /arcade.

---

## STEP 4: PERSISTENT ARCADE ACCESS (after first discovery)

Once a player has discovered the Arcade (via any trigger):
- Store arcade_unlocked: true in localStorage AND in their player profile (if logged in)
- Add a subtle Arcade entry point to their account dropdown menu ONLY:

```
[Avatar dropdown]
  Profile
  Rewards
  ---------
  The Lounge      <- ONLY shows after discovery (diamond icon, muted gold)
  ---------
  Logout
```

- "The Lounge" uses the diamond icon in muted gold (#D4AF37 at 70% opacity)
- It is the ONLY place Arcade appears in any navigation element post-discovery
- Users who have not discovered it yet do not see this option -- the dropdown shows no Arcade link

---

## STEP 5: /arcade PAGE ITSELF (the lounge landing)

When a player navigates to /arcade (via Easter egg, direct URL, or account menu), the page title is:

"The Lounge" -- not "Arcade," not "Games."

Layout:
```
[Full dark screen, #0A0A0A]

[Centered header]
  Small caps: "EVERLIGHT"
  Large (Cormorant Garamond): "The Lounge"
  Thin gold underline (1px, 60px wide, centered)

[Two game cards, side by side on desktop, stacked on mobile]

  Card 1: Blackjack
    Background: dark leather texture (#111)
    Gold card suits scattered subtly in corners
    Title: "Everlight Blackjack"
    Subtitle: "Premium tables. Live jukebox. Real competition."
    CTA button: "Take a Seat" -> /arcade/blackjack

  Card 2: Alley Kingz
    Background: midnight blue (#0D0D1A), neon cyan glow on card edges
    Title: "Alley Kingz"
    Subtitle: "Real-time PvP. Ten city factions. One throne."
    CTA button: "Enter the Streets" -> /arcade/alley-kingz

[Footer line, centered, soft gold text]
  "Members play for free. The house always welcomes you."
  Links to /arcade/membership
```

---

## WHAT NOT TO CHANGE

- The /arcade, /arcade/blackjack, and /arcade/alley-kingz routes still work and load correctly
- All existing game logic, auth flow, leaderboards, and shop remain intact
- The Arcade link on the homepage portfolio grid (the Alley Kingz venture card "Play the Demo") can still link to /arcade/alley-kingz directly
- The Master Pass membership page /arcade/membership can still be linked from the VIP Diamond badge in the header
- All existing Blackjack and Alley Kingz features are preserved -- this only changes navigation and discovery
