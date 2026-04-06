# Alley Kingz -- Card & Game Data Model v1.0
Updated: 2026-02-28 | Hive Mind Session: 89059981

---

## Card ScriptableObject Schema

```csharp
// CardDefinition.cs -- full expanded schema for v1.0+
[CreateAssetMenu(menuName = "Alley Kingz/Card Definition")]
public class CardDefinition : ScriptableObject
{
    // === IDENTITY ===
    public string cardId;          // snake_case unique key e.g. "muscle_car"
    public string displayName;     // "Muscle Car"
    public string description;     // Short gameplay description
    public string loreText;        // Flavor text (street culture vibe)

    // === TAXONOMY ===
    public CardType cardType;      // Troop | Spell | Building
    public CardClass cardClass;    // Street | Cartel | Tech | Lowrider | Muscle | Ghost | Rookie
    public CardRarity rarity;      // Common | Rare | Epic | Legendary | Icon
    public CardSynergy[] synergies; // e.g. [speed_stack, gang_rush]
    public CardTrait[] traits;     // e.g. [flying, armored, splash]

    // === COST ===
    public int elixirCost;         // 1-10

    // === UNLOCK ===
    public int unlockLevel;        // 1-100; 1 = available from start
    public bool isStarterCard;     // Always in new player deck

    // === COMBAT STATS (Troops + Buildings only) ===
    public int baseHitpoints;
    public int baseDamage;
    public float moveSpeed;        // Units/sec; 0 for buildings/spells
    public float attackRange;      // Arena units
    public float attackSpeed;      // Attacks/sec
    public float deployTime;       // Spawn delay in seconds
    public int spawnCount;         // For swarm cards (e.g. Corner Boys = 4)
    public float lifetime;         // 0 = permanent until destroyed

    // === SPELL STATS (Spells only) ===
    public int spellDamage;
    public float spellRadius;
    public float spellDuration;    // For DoT/slow effects
    public float slowPercent;      // 0-1 for slow spells

    // === TARGETING ===
    public TargetPriority targetPriority;  // Ground | Air | Both | Buildings | None
    public bool isAreaDamage;
    public float areaDamageRadius;

    // === SPECIAL ===
    public bool isFlying;
    public bool hasAbility;
    public string abilityName;
    public float abilityCooldown;
    public string abilityDescription;

    // === UPGRADE ===
    public float upgradeMultiplier;  // Default 1.10 (10% per level)

    // === VISUAL ===
    public Sprite cardArtwork;       // Full card illustration
    public Sprite cardIcon;          // Small icon for hand
    public Color primaryColor;       // Card accent color
    public GameObject unitPrefab;    // Battle prefab
    public GameObject spellEffectPrefab;
    public AudioClip deploySound;
    public AudioClip attackSound;
    public AudioClip deathSound;
}
```

---

## Enum Definitions

```csharp
public enum CardType { Troop, Spell, Building }

public enum CardClass
{
    Street,    // Everyday brawlers
    Cartel,    // High value, high cost
    Tech,      // Electronic/gadget
    Lowrider,  // Slow unstoppable tanks
    Muscle,    // Brute force
    Ghost,     // Stealth/flankers
    Rookie     // Starter/cheap/swarm
}

public enum CardRarity
{
    Common,
    Rare,
    Epic,
    Legendary,
    Icon        // New top tier -- ultra rare
}

public enum CardSynergy
{
    SpeedStack,    // Chain speed buffs
    GangRush,      // Multi-unit combo
    SplashSquad,   // AoE damage group
    TankLine,      // Tank shielding
    SpellCycle,    // Low-cost cycling
    GhostFlanks,   // Flanking exploiters
    ChoppedUp      // Chop Shop synergy
}

public enum CardTrait
{
    Flying,
    Armored,        // Reduced damage from some sources
    Splash,         // Area melee
    BuildingTarget, // Only targets buildings/towers
    Stealth,        // Invisible on deploy
    Ranged,
    Healer,
    SpellImmune,
    DeathSummon,    // Spawns units on death
    Zap             // Chain lightning
}

public enum TargetPriority
{
    Ground,
    Air,
    Both,
    Buildings,
    None           // For spells
}
```

---

## PlayerData Schema (Updated)

```csharp
[Serializable]
public class PlayerData
{
    // === IDENTITY ===
    public string playerId;
    public string displayName;
    public string authProvider;    // "google" | "apple" | "facebook" | "guest"
    public DateTime accountCreated;
    public DateTime lastSeen;

    // === PROGRESSION ===
    public int nosBottles;          // Was: trophies. Renamed to NOS Bottles.
    public int highestNosBottles;
    public AlleyArena currentArena; // Updated enum
    public AlleyLeague currentLeague;
    public int playerLevel;         // XP-based account level 1-50
    public int playerXP;

    // === STORY/PVE ===
    public int highestLevelCompleted;  // 0-100
    public bool rankedUnlocked;        // True after level 50
    public bool iconTierUnlocked;      // True after level 100
    public HashSet<string> unlockedCardIds;
    public Dictionary<int, bool> districtChallengesCompleted; // zone 1-10

    // === CURRENCIES (3-currency system) ===
    public int fuel;        // Soft currency (was: gold)
    public int gears;       // Mid currency (season-based)
    public int gems;        // Hard/IAP currency

    // === COLLECTION ===
    public Dictionary<string, PlayerCard> cardCollection;
    public List<PlayerDeck> decks;     // Up to 5 (8 with Crew Pass)
    public int selectedDeckIndex;

    // === STATS ===
    public PlayerStats stats;
    public EngagementStats engagement;

    // === MONETIZATION ===
    public bool hasCrewPass;           // Was: hasSeasonPass
    public bool isVipSubscriber;
    public DateTime? crewPassExpiry;
    public float totalSpent;
    public bool hasEverSpent;

    // === COSMETICS ===
    public string equippedArenaSkin;
    public string equippedEmote;
    public List<string> ownedSkins;
    public List<string> ownedEmotes;
}
```

---

## Level Config Schema

```csharp
[CreateAssetMenu(menuName = "Alley Kingz/Level Config")]
public class LevelConfig : ScriptableObject
{
    public int levelNumber;          // 1-100
    public string levelName;         // "The Lot - Rookie Run"
    public int zoneNumber;           // 1-10
    public string zoneName;          // "Training Lot", "Strip Run", etc.
    public bool isDistrictChallenge; // True for levels 10,20,30...100

    // Opponent config
    public string[] opponentDeckIds; // 8 card IDs for AI deck
    public float hpMultiplier;       // Scales from 1.0 at L1 to ~7.0 at L100
    public float damageMultiplier;
    public float aiReactionDelay;    // Seconds between AI decisions
    public float aiElixirIQ;         // 0-1 -- how smart the elixir spending is

    // Rewards
    public int fuelReward;
    public int xpReward;
    public ChestType chestReward;
    public string unlockCardId;      // Card unlocked on first completion (null if none)

    // District Challenge extras
    public string bossCardId;        // Special boss-only card the AI uses
    public string legendaryRewardId; // Legendary card reward for winning
}
```

---

## Shop Offer Schema (Updated)

```csharp
[Serializable]
public class ShopOffer
{
    public string offerId;
    public string offerName;
    public string description;
    public OfferType offerType;

    // Costs
    public int fuelCost;       // Was: goldCost
    public int gearsCost;      // New
    public int gemCost;
    public float realMoneyCost;

    // Rewards
    public int fuelReward;     // Was: goldReward
    public int gearsReward;    // New
    public int gemReward;
    public List<CardReward> cardRewards;
    public ChestType? chestReward;
    public bool includesCrewPass; // Was: includesSeasonPass
    public int vipDays;

    // Display
    public Sprite iconSprite;
    public string valueLabel;
    public DateTime? expiryTime;
    public bool isLimitedTime;

    // Targeting
    public PlayerSegment targetSegment;
    public bool isOneTimePurchase;
    public bool hasBeenPurchased;
}

public enum OfferType
{
    GemPack,
    FuelPack,      // Was: GoldPack
    GearsPack,     // New
    CardBundle,
    ChestBundle,
    CrewPass,      // Was: SeasonPass
    StarterPack,
    RevivalPack,   // Was: ComebackOffer -- triggers at loss streak
    WelcomeBack,
    EventSpecial,
    ChopShopSlot   // New -- extra Chop Shop merge slot
}
```

---

## HQ Van Health State

```csharp
[Serializable]
public class HQVanState
{
    public int maxHealth;
    public int currentHealth;
    public bool isDestroyed;
    public bool crownCounted;

    // Visual state
    public float HealthPercent => (float)currentHealth / maxHealth;
    public bool IsCritical => HealthPercent < 0.30f;   // Red glow at 30%
    public bool IsEndangered => HealthPercent < 0.15f; // Screen pulse at 15%

    // When this hits 0 -> GameManager.TriggerGameOver(owner)
    // This is NOT just a crown -- it ends the battle immediately
}
```

---

## Audio Event Enum

```csharp
public enum AudioEvent
{
    // Card Deploy
    DeployTroop,
    DeploySpell,
    DeployBuilding,

    // Combat
    UnitAttack,
    UnitTakeDamage,
    UnitDeath,

    // Towers
    TowerDamaged,
    TowerDestroyed,
    HQVanDestroyed,    // Special -- louder, triggers game over screen

    // Elixir
    ElixirFill,
    ElixirFull,

    // Game State
    BattleStart,
    BattleVictory,
    BattleDefeat,
    DoubleElixirStart,
    OvertimeStart,

    // UI
    MenuClick,
    CardSelect,
    DeckEdit,
    PurchaseSuccess,
    ChestOpen,

    // NOS Ladder
    NOSBottleGain,
    NOSBottleLoss,
    ArenaPromotion,
    ArenaDemotion
}
```

---

## Difficulty Scaling Reference Table

| Level | HP Mult | DMG Mult | AI Delay (s) | AI IQ |
|-------|---------|---------|-------------|-------|
| 1 | 1.00 | 1.00 | 2.50 | 0.30 |
| 10 | 1.65 | 1.45 | 2.30 | 0.37 |
| 25 | 2.59 | 2.20 | 2.00 | 0.46 |
| 50 | 4.18 | 3.45 | 1.50 | 0.63 |
| 75 | 5.88 | 4.70 | 1.00 | 0.79 |
| 90 | 6.96 | 5.45 | 0.70 | 0.89 |
| 100 | 7.75 | 5.95 | 0.50 | 0.95 |
