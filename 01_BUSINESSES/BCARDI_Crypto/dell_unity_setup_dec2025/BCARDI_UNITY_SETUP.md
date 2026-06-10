# BCARDI Unity Prototype Setup (2022.3 LTS)

## 1) Install Unity
- Install Unity Hub
- Install Unity 2022.3 LTS (best long-term support)

## 2) Create/Open Project
- Open Unity Hub
- Add project at `/home/mgn/Projects/BCARDICOIN`
- Unity will create ProjectSettings automatically

## 3) Scene Setup
Create a new scene `BCARDI_Arena` and add these GameObjects:

### Core
- `GameConfig` (add `GameConfig` component)
- `ProgressionManager` (add `ProgressionManager` component)
- `ArenaManager` (add `ArenaManager` component)
- `VfxSpawner` (add `VfxSpawner` component)
- `PlayerEnergy` (add `EnergySystem`)
- `EnemyEnergy` (add `EnergySystem`)
- `PlayerController` (add `PlayerController`, assign `PlayerEnergy`)
- `BotController` (add `BotController`, assign `EnemyEnergy`)

### Spawns
- Create empty transforms: `P_Lane_0`, `P_Lane_1`, `P_Lane_2`
- Create empty transforms: `E_Lane_0`, `E_Lane_1`, `E_Lane_2`
- Assign these to `ArenaManager.PlayerLaneSpawns` and `ArenaManager.EnemyLaneSpawns`

### Towers (Player)
- `P_Tower_L`, `P_Tower_C`, `P_Tower_R` (add `Tower` component)
- `P_Queen` (add `Tower` component, set `IsQueen = true`)

### Towers (Enemy)
- `E_Tower_L`, `E_Tower_C`, `E_Tower_R` (add `Tower` component)
- `E_Queen` (add `Tower` component, set `IsQueen = true`)

Assign these to `ArenaManager.PlayerPrincessTowers`, `ArenaManager.EnemyPrincessTowers`,
`ArenaManager.PlayerQueenTower`, and `ArenaManager.EnemyQueenTower`.

## 4) Unit Prefabs
Create a basic `UnitPrefab`:
- Create a Cube (or sprite) named `UnitPrefab`
- Add `Unit` component
- Save as Prefab in `Assets/BCARDI/`

Duplicate to create `MinionPrefab` (smaller scale)
- Assign both in `ArenaManager`

## 5) VFX Prefabs (Neon placeholders)
Create two prefabs:
- `HitFlashPrefab`:
  - Create empty GameObject with a SpriteRenderer
  - Assign a simple white circle sprite
  - Add `HitFlash` component
- `TrailPrefab` (optional):
  - Create empty GameObject with a LineRenderer or SpriteRenderer

Assign both to `VfxSpawner`.

## 6) JSON Resources
These are already copied to `Assets/BCARDI/Resources/`:
- `cards.json`
- `ability_params.json`
- `decks.json`
- `arenas.json`
- `rewards.json`

Unity auto-loads them via `Resources.Load`.

## 7) UI (Dog Bones + Card + Arena)
- Create `Canvas`
- Add `Text` named `BonesText` (legacy Text)
- Add `Text` named `SelectedCardText`
- Add `Text` named `TrophiesText`
- Add `Text` named `ArenaText`

- Create `DogBonesUI` GameObject, add `DogBonesUI` component
  - Assign `PlayerEnergy` to `Energy`
  - Assign `BonesText` to `BonesText`

- Create `HandUI` GameObject, add `HandUI` component
  - Assign `PlayerController` to `Player`
  - Assign `SelectedCardText` to `SelectedText`

- Create `ArenaUI` GameObject, add `ArenaUI` component
  - Assign `TrophiesText` and `ArenaText`

## 8) Deck Builder UI (simple)
- Create a panel `DeckBuilderPanel`
- Add `Text` named `CurrentDeckText`
- Add a `VerticalLayoutGroup` with a `DeckListRoot` object
- Create a `Button` prefab `DeckButtonPrefab` with a child Text
- Add `DeckBuilderUI` component to `DeckBuilderPanel`
  - Assign `PlayerController`, `CurrentDeckText`, `DeckListRoot`, `DeckButtonPrefab`

## 9) Arena Preview UI
- Create a panel `ArenaPreviewPanel`
- Add `Text` named `ArenaNameText`
- Add `Text` named `ArenaRangeText`
- Add `Text` named `NextGiftText`
- Add `ArenaPreviewUI` component
  - Assign `ArenaNameText`, `ArenaRangeText`, `NextGiftText`

## 10) Match End UI
- Create a panel `MatchEndPanel` (disabled by default)
- Add `Text` named `ResultText`
- Add `Text` named `TrophyResultText`
- Add `Text` named `GiftResultText`
- Add a `Button` named `ClaimButton`
- Add `MatchEndUI` component to a GameObject
  - Assign `Panel`, `ResultText`, `TrophyText`, `GiftText`, `ClaimButton`

## 11) HUD Buttons (optional, for mobile)
- Create 8 UI Buttons for cards (1-8)
  - Add `HudController` to a GameObject
  - Wire each button to `HudController.SelectCard(index)`
- Create 3 UI Buttons for lanes
  - Wire to `HudController.PlayLeft/Center/Right`

## 12) Controls
- Select card with `1-8`
- Play card to lane with:
  - `Q` = Left lane
  - `W` = Center lane
  - `E` = Right lane

## 13) Play
- Press Play
- Bot will deploy cards every ~2 seconds
- Princess towers protect Queen; Queen vulnerable only after lane towers fall unless card has Queen-target
- Trophies (Dog Skulls) update after each match
- Arena name updates based on trophies

## Notes
- Ability rotation is live and includes status effects: slow, stun, silence, root, dash, teleport, knockback.
- Extend `Unit.ApplyAbility()` for more specialized behavior as needed.
