# LOVABLE PROMPT: Navigation Restructure -- VIP-First Menu Hierarchy

Paste this into Lovable. This fixes three problems:
1. Diamond icon appearing inconsistently in the nav list
2. Menu order does not reflect the VIP/business hierarchy
3. Arcade mixed into main nav instead of being an exclusive discovery

---

## PROMPT:

Restructure the global site navigation for everlightventures.io. The current menu has an inconsistency: a Diamond icon is appearing as a nav item mixed in with the main links, which breaks the visual hierarchy and feels misplaced. The goal is a clean, VIP-first navigation that separates "business utility" from "lifestyle/play."

---

## NAVIGATION REDESIGN

### Current Problem
The Diamond (likely the Master Pass / VIP badge) is showing up inline in the nav list between other links. This creates visual noise and dilutes the premium signal it should carry. The Arcade is also surfaced in the main nav, which cheapens the exclusive "speakeasy" feel the brand should project.

### New Navigation Structure

Desktop top nav bar:
```
[EV Monogram] -- Ventures  Publishing  Onyx  Loadout  Logistics  HiveMind -- [diamond VIP badge] [Login/Avatar]
```

Mobile bottom nav (5 tabs max):
```
[Home]  [Publishing]  [Onyx]  [Loadout]  [Account]
```

### Rules:
- The Diamond is NOT a nav link. It is a utility badge in the top-right corner of the header, next to the login/avatar area.
- If the player is a Master Pass member: Diamond glows gold (#D4AF37), subtle pulse animation, tooltip says "Master Pass Active"
- If the player is not a member: Diamond is muted smoke (#8A8A8A), tooltip says "Become a Member" -- links to /arcade/membership
- The Arcade (/arcade) is REMOVED from the main navigation entirely. See LOVABLE_ARCADE_EASTER_EGG_PROMPT for how players discover it.
- HIM Loadout is listed as "Loadout" to keep it compact

---

## NEW MENU ORDER (left to right, desktop)

Primary nav links:
1. Home (/) -- the venture hub
2. Publishing (/publishing) -- books, authors, series
3. Onyx (/onyx) -- POS product
4. Loadout (/him-loadout) -- affiliate gear
5. Logistics (/logistics) -- quote/services
6. HiveMind (/hivemind) -- AI platform waitlist

Utility area (top-right, NOT in nav list):
- Diamond badge (VIP status indicator -- see below)
- Login / User avatar (if logged in, show avatar with dropdown: Profile, Rewards, Logout)

What is REMOVED from the nav:
- Arcade / Blackjack -- moved to Easter egg discovery (see separate prompt)
- Dashboard (/dashboard) -- only accessible via direct URL or from user account dropdown
- Any "Coming Soon" placeholder links

---

## MOBILE NAV (bottom bar)

Mobile gets a 5-tab bottom navigation:
```
Home | Publishing | Onyx | Loadout | Account
```

- Icons are line-weight (not filled), gold (#D4AF37) when active, smoke (#8A8A8A) when inactive
- Labels are 10px Inter, uppercase, tracked
- The Diamond VIP badge appears inside the Account tab -- a small diamond in gold if member, smoke if not
- Arcade is NOT one of the 5 tabs

---

## DIAMOND BADGE COMPONENT

Replace any inline Diamond nav item with this dedicated badge component in the header utility area:

```typescript
// VIP Diamond Badge -- goes in header utility zone (top right), NOT in nav list
function VipDiamondBadge({ isMember }: { isMember: boolean }) {
  return (
    <div
      className="relative group cursor-pointer"
      onClick={() => router.push('/arcade/membership')}
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke={isMember ? '#D4AF37' : '#8A8A8A'}
        strokeWidth="1.5"
        className={isMember ? 'animate-pulse-slow' : ''}
      >
        <polygon points="12,2 22,9 12,22 2,9" />
      </svg>

      <div className="absolute right-0 top-7 bg-[#1A1A1A] border border-[#2A2A2A] rounded px-3 py-2 text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50">
        {isMember ? (
          <span className="text-[#D4AF37]">Master Pass Active</span>
        ) : (
          <span className="text-[#8A8A8A]">Become a Member</span>
        )}
      </div>
    </div>
  );
}
```

Add animate-pulse-slow to tailwind config:
```javascript
// tailwind.config.js
animation: {
  'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
}
```

---

## DROPDOWN MENU (when user is logged in)

Clicking the user avatar in the top right shows a dropdown:

```
[Avatar]  Display Name
          ---------
          Profile
          Rewards
          Join Master Pass    <- only if not a member (gold text)
          ---------
          Logout
```

- Dropdown has background #1A1A1A, border #2A2A2A, shadow 0 4px 24px rgba(0,0,0,0.6)
- The "Join Master Pass" link ONLY appears if player.is_member === false
- If player IS a member, that slot shows "Active Member" in gold (non-clickable status text)

---

## WHAT NOT TO CHANGE

- Keep all existing page content, routes, and functionality
- Keep the EV monogram logo and Cormorant Garamond wordmark in the top left
- Keep all global color tokens (#0A0A0A, #D4AF37, #8A8A8A, etc.)
- Keep the mobile-first responsive behavior
- Only the nav structure and Diamond placement change
