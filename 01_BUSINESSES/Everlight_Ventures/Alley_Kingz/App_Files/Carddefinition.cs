using UnityEngine;
using ArenaAdvance.Data;

namespace ArenaAdvance.ScriptableObjects
{
    [CreateAssetMenu(fileName = "NewCard", menuName = "Arena Advance/Card Definition")]
    public class CardDefinition : ScriptableObject
    {
        [Header("Basic Info")]
        public string cardId;
        public string cardName;
        [TextArea(2, 4)]
        public string description;
        public Sprite cardArt;
        public Sprite cardIcon;

        [Header("Card Properties")]
        public CardRarity rarity;
        public CardType cardType;
        public int elixirCost;
        public Arena unlockArena;

        [Header("Combat Stats (Base Level 1)")]
        public int hitpoints;
        public int damage;
        public float attackSpeed;      // Attacks per second
        public float moveSpeed;        // Units per second
        public float range;            // Attack range
        public float deployTime;       // Spawn delay

        [Header("Targeting")]
        public TargetType targetType;
        public bool isAreaDamage;
        public float areaDamageRadius;

        [Header("Special Properties")]
        public bool isFlying;
        public bool canTargetAir;
        public int spawnCount;         // For cards that spawn multiple units
        public float lifetime;         // For buildings/spells (0 = permanent until destroyed)

        [Header("Prefabs")]
        public GameObject unitPrefab;
        public GameObject spellEffectPrefab;

        [Header("Upgrade Scaling")]
        [Tooltip("Multiplier per level for HP and Damage")]
        public float upgradeMultiplier = 1.1f;  // 10% per level

        // Calculate stats at a specific level
        public int GetHitpointsAtLevel(int level)
        {
            return Mathf.RoundToInt(hitpoints * Mathf.Pow(upgradeMultiplier, level - 1));
        }

        public int GetDamageAtLevel(int level)
        {
            return Mathf.RoundToInt(damage * Mathf.Pow(upgradeMultiplier, level - 1));
        }

        public float GetDPSAtLevel(int level)
        {
            return GetDamageAtLevel(level) * attackSpeed;
        }
    }
}

