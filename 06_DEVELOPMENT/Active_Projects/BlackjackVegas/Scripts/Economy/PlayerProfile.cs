// ============================================================
// PlayerProfile.cs  --  Persistent player data singleton
// Chips (soft), Gems (hard), Clout XP, Rank, Cosmetics
// ============================================================
using System.Collections.Generic;
using UnityEngine;

namespace BlackjackVegas
{
    public class PlayerProfile : MonoBehaviour
    {
        public static PlayerProfile Instance { get; private set; }

        // ---- Economy ----
        public int  Chips       { get; private set; } = 10000;   // free soft currency
        public int  Gems        { get; private set; } = 0;       // purchased hard currency
        public int  CloutXP     { get; private set; } = 0;
        public int  CloutLevel  { get; private set; } = 1;
        public int  CloutRank   { get; private set; } = 0;       // leaderboard position

        // ---- Cosmetics unlocked ----
        public HashSet<string> UnlockedCardBacks { get; private set; } = new HashSet<string> { "standard" };
        public string EquippedCardBack { get; private set; } = "standard";
        public string EquippedTableFelt { get; private set; } = "green";

        // ---- Session stats ----
        public int HandsPlayed    { get; private set; }
        public int HandsWon       { get; private set; }
        public int BlackjacksHit  { get; private set; }
        public int TotalWagered   { get; private set; }

        // ---- Subscription ----
        public SubscriptionTier ActiveSubscription { get; private set; } = SubscriptionTier.Free;
        public System.DateTime  SubExpiresUtc      { get; private set; }

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        // --------------------------------------------------------
        // Chips (soft currency -- earned in game)
        // --------------------------------------------------------

        public void AddChips(int amount)
        {
            Chips += amount;
            SaveSystem.Instance?.MarkDirty();
        }

        public bool DeductChips(int amount)
        {
            if (Chips < amount) return false;
            Chips -= amount;
            TotalWagered += amount;
            SaveSystem.Instance?.MarkDirty();
            return true;
        }

        // Daily free chip grant -- call on login
        public void GrantDailyChips()
        {
            int grant = ActiveSubscription switch
            {
                SubscriptionTier.VIPPit    => 50000,
                SubscriptionTier.GoldTable => 25000,
                _                          => 10000
            };
            AddChips(grant);
            Debug.Log($"[Profile] Daily chip grant: +{grant:N0}");
        }

        // --------------------------------------------------------
        // Gems (hard currency -- purchased with real money)
        // --------------------------------------------------------

        public void AddGems(int amount)
        {
            Gems += amount;
            SaveSystem.Instance?.MarkDirty();
        }

        public bool SpendGems(int cost, string itemId)
        {
            if (Gems < cost)
            {
                Debug.LogWarning($"[Gems] Not enough gems for {itemId}. Have {Gems}, need {cost}");
                return false;
            }
            Gems -= cost;
            Debug.Log($"[Gems] Spent {cost} gems on {itemId}. Balance: {Gems}");
            SaveSystem.Instance?.MarkDirty();
            return true;
        }

        // --------------------------------------------------------
        // Clout (XP / rank / leaderboard)
        // --------------------------------------------------------

        public void AddCloutXP(int xp)
        {
            CloutXP += xp;
            int newLevel = CloutXPToLevel(CloutXP);
            if (newLevel > CloutLevel)
            {
                CloutLevel = newLevel;
                Debug.Log($"[Clout] LEVEL UP → {CloutLevel}");
                // Fire level-up event for UI fanfare
                OnCloutLevelUp?.Invoke(CloutLevel);
            }
            SaveSystem.Instance?.MarkDirty();
        }

        private int CloutXPToLevel(int xp)
        {
            // Simple curve: level = floor(sqrt(xp / 100)) + 1
            return Mathf.FloorToInt(Mathf.Sqrt(xp / 100f)) + 1;
        }

        public System.Action<int> OnCloutLevelUp;

        // --------------------------------------------------------
        // Cosmetics
        // --------------------------------------------------------

        public bool UnlockCardBack(string id)
        {
            UnlockedCardBacks.Add(id);
            SaveSystem.Instance?.MarkDirty();
            return true;
        }

        public bool EquipCardBack(string id)
        {
            if (!UnlockedCardBacks.Contains(id)) return false;
            EquippedCardBack = id;
            SaveSystem.Instance?.MarkDirty();
            return true;
        }

        // --------------------------------------------------------
        // Stats tracking (called by GameManager / PitBoss)
        // --------------------------------------------------------

        public void RecordHand(RoundResult result)
        {
            HandsPlayed++;
            if (result == RoundResult.WIN || result == RoundResult.BLACKJACK) HandsWon++;
            if (result == RoundResult.BLACKJACK) BlackjacksHit++;
        }

        // --------------------------------------------------------
        // Serialization (used by SaveSystem)
        // --------------------------------------------------------

        public PlayerSaveData ToSaveData() => new PlayerSaveData
        {
            chips         = Chips,
            gems          = Gems,
            cloutXP       = CloutXP,
            cloutLevel    = CloutLevel,
            handsPlayed   = HandsPlayed,
            handsWon      = HandsWon,
            blackjacksHit = BlackjacksHit,
            totalWagered  = TotalWagered,
            cardBack      = EquippedCardBack,
            subTier       = (int)ActiveSubscription,
            subExpires    = SubExpiresUtc.ToString("o")
        };

        public void FromSaveData(PlayerSaveData d)
        {
            Chips              = d.chips;
            Gems               = d.gems;
            CloutXP            = d.cloutXP;
            CloutLevel         = d.cloutLevel;
            HandsPlayed        = d.handsPlayed;
            HandsWon           = d.handsWon;
            BlackjacksHit      = d.blackjacksHit;
            TotalWagered       = d.totalWagered;
            EquippedCardBack   = d.cardBack;
            ActiveSubscription = (SubscriptionTier)d.subTier;
            if (System.DateTime.TryParse(d.subExpires, out var exp))
                SubExpiresUtc  = exp;
        }
    }

    [System.Serializable]
    public class PlayerSaveData
    {
        public int    chips, gems, cloutXP, cloutLevel;
        public int    handsPlayed, handsWon, blackjacksHit, totalWagered;
        public string cardBack;
        public int    subTier;
        public string subExpires;
    }
}
