using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Core;
using ArenaAdvance.Data;

namespace ArenaAdvance.Economy
{
    [Serializable]
    public class ShopOffer
    {
        public string offerId;
        public string offerName;
        public string description;
        public OfferType offerType;
        public int goldCost;
        public int gemCost;
        public float realMoneyCost;  // 0 = not a real money purchase

        // Rewards
        public int goldReward;
        public int gemReward;
        public List<CardReward> cardRewards = new List<CardReward>();
        public ChestType? chestReward;
        public bool includesSeasonPass;
        public int vipDays;

        // Display
        public Sprite iconSprite;
        public string valueLabel;  // e.g., "5X VALUE!"
        public DateTime? expiryTime;

        // Targeting
        public string targetSegment;  // Which player segment this is for
        public bool isOneTimePurchase;
        public bool hasBeenPurchased;

        [Serializable]
        public class CardReward
        {
            public string cardId;
            public int count;
            public CardRarity rarity;  // For random cards
            public bool isRandom;
        }

        public bool IsExpired => expiryTime.HasValue && DateTime.UtcNow > expiryTime.Value;
        public bool IsAvailable => !IsExpired && (!isOneTimePurchase || !hasBeenPurchased);
    }

    public enum OfferType
    {
        GemPack,
        GoldPack,
        CardBundle,
        ChestBundle,
        SeasonPass,
        VipSubscription,
        StarterPack,
        ComebackOffer,
        SecondChancePack,
        EventSpecial
    }

    public enum PlayerSegment
    {
        NewPlayer,          // < 50 matches
        F2PGrinder,         // Many matches, no spend
        LightSpender,       // Has spent < $20
        MidSpender,         // $20-$100
        Whale,              // > $100
        AtRiskChurn,        // Decreasing engagement
        Subscriber,         // Active VIP
        ContractHolder,     // Has active advance contract
        ReturningPlayer     // Was gone > 7 days
    }

    /// <summary>
    /// Manages shop offers, purchases, and economy balance
    /// </summary>
    public class EconomyManager : MonoBehaviour
    {
        public static EconomyManager Instance { get; private set; }

        [Header("Shop Configuration")]
        [SerializeField] private List<ShopOffer> dailyOffers = new List<ShopOffer>();
        [SerializeField] private List<ShopOffer> featuredOffers = new List<ShopOffer>();
        [SerializeField] private List<ShopOffer> gemStoreOffers = new List<ShopOffer>();

        [Header("Economy Settings")]
        [SerializeField] private int cardUpgradeBaseCost = 50;
        [SerializeField] private float upgradeScaleFactor = 2f;
        [SerializeField] private int chestUnlockGemsPerHour = 10;

        // Events
        public event Action<ShopOffer> OnOfferPurchased;
        public event Action OnShopRefreshed;

        private PlayerSegment currentSegment;
        private DateTime lastShopRefresh;

        private void Awake()
        {
            if (Instance == null)
            {
                Instance = this;
            }
            else
            {
                Destroy(gameObject);
            }
        }

        private void Start()
        {
            RefreshShopIfNeeded();
        }

        #region Player Segmentation

        /// <summary>
        /// Determine which player segment this user belongs to
        /// Used for offer targeting (non-predatory - segments determine WHAT to show, not price)
        /// </summary>
        public PlayerSegment DeterminePlayerSegment(PlayerData player)
        {
            // Check engagement patterns first
            if (IsAtRiskOfChurn(player))
                return PlayerSegment.AtRiskChurn;

            if (IsReturningPlayer(player))
                return PlayerSegment.ReturningPlayer;

            if (player.creditProfile.activeContractIds.Count > 0)
                return PlayerSegment.ContractHolder;

            if (player.isVipSubscriber)
                return PlayerSegment.Subscriber;

            // Check spending history
            if (player.totalSpent > 100)
                return PlayerSegment.Whale;

            if (player.totalSpent > 20)
                return PlayerSegment.MidSpender;

            if (player.hasEverSpent)
                return PlayerSegment.LightSpender;

            // Check engagement
            if (player.stats.totalMatches < 50)
                return PlayerSegment.NewPlayer;

            return PlayerSegment.F2PGrinder;
        }

        private bool IsAtRiskOfChurn(PlayerData player)
        {
            // Check for declining engagement
            if (player.stats.recentMatches.Count < 5)
                return false;

            // Long losing streak
            int loseStreak = 0;
            for (int i = player.stats.recentMatches.Count - 1; i >= 0; i--)
            {
                if (player.stats.recentMatches[i] == MatchResult.Loss)
                    loseStreak++;
                else
                    break;
            }

            if (loseStreak >= 5) return true;

            // Decreased login frequency (would need more historical data)
            if (player.engagement.averageMatchesPerDay < 2 &&
                player.stats.totalMatches > 100)
                return true;

            return false;
        }

        private bool IsReturningPlayer(PlayerData player)
        {
            if (player.stats.totalMatches < 20) return false;

            var daysSinceLastLogin = (DateTime.UtcNow - player.engagement.lastLoginTime).TotalDays;
            return daysSinceLastLogin > 7;
        }

        #endregion

        #region Shop Management

        public void RefreshShopIfNeeded()
        {
            var now = DateTime.UtcNow;

            // Refresh daily at midnight UTC
            if (lastShopRefresh.Date != now.Date)
            {
                RefreshDailyShop();
                lastShopRefresh = now;
            }
        }

        private void RefreshDailyShop()
        {
            var player = Managers.GameManager.Instance?.Player;
            if (player == null) return;

            currentSegment = DeterminePlayerSegment(player);
            dailyOffers.Clear();

            // Generate offers based on segment
            dailyOffers.AddRange(GenerateOffersForSegment(currentSegment, player));

            OnShopRefreshed?.Invoke();
            Debug.Log($"Shop refreshed for segment: {currentSegment}");
        }

        private List<ShopOffer> GenerateOffersForSegment(PlayerSegment segment, PlayerData player)
        {
            var offers = new List<ShopOffer>();

            // Always include some basic offers
            offers.Add(CreateGoldPackOffer(1000, 50));
            offers.Add(CreateGemPackOffer(100, 0.99f));

            // Segment-specific offers
            switch (segment)
            {
                case PlayerSegment.NewPlayer:
                    offers.Add(CreateStarterPackOffer());
                    break;

                case PlayerSegment.AtRiskChurn:
                    offers.Add(CreateComebackOffer(player));
                    break;

                case PlayerSegment.ContractHolder:
                    // Offer gems in case they need to settle
                    offers.Add(CreateGemPackOffer(500, 4.99f, "Contract Support Pack"));
                    break;

                case PlayerSegment.ReturningPlayer:
                    offers.Add(CreateWelcomeBackOffer());
                    break;

                case PlayerSegment.F2PGrinder:
                    // Show good value offers to potentially convert
                    offers.Add(CreateValuePackOffer());
                    break;

                case PlayerSegment.Whale:
                    // Premium exclusive offers
                    offers.Add(CreatePremiumBundleOffer());
                    break;
            }

            // Add season pass if not owned
            if (!player.hasSeasonPass)
            {
                offers.Add(CreateSeasonPassOffer());
            }

            return offers;
        }

        #endregion

        #region Offer Creation

        private ShopOffer CreateGoldPackOffer(int gold, int gems)
        {
            return new ShopOffer
            {
                offerId = $"gold_{gold}_{Guid.NewGuid().ToString().Substring(0, 8)}",
                offerName = $"{gold} Gold",
                description = "Boost your upgrades!",
                offerType = OfferType.GoldPack,
                gemCost = gems,
                goldReward = gold
            };
        }

        private ShopOffer CreateGemPackOffer(int gems, float price, string name = null)
        {
            return new ShopOffer
            {
                offerId = $"gems_{gems}_{Guid.NewGuid().ToString().Substring(0, 8)}",
                offerName = name ?? $"{gems} Gems",
                description = "Premium currency for the shop",
                offerType = OfferType.GemPack,
                realMoneyCost = price,
                gemReward = gems
            };
        }

        private ShopOffer CreateStarterPackOffer()
        {
            return new ShopOffer
            {
                offerId = "starter_pack",
                offerName = "Starter Pack",
                description = "Everything you need to begin your journey!",
                offerType = OfferType.StarterPack,
                realMoneyCost = 4.99f,
                gemReward = 500,
                goldReward = 5000,
                chestReward = ChestType.Giant,
                isOneTimePurchase = true,
                valueLabel = "10X VALUE!"
            };
        }

        private ShopOffer CreateComebackOffer(PlayerData player)
        {
            // IMPORTANT: gemReward removed to close arbitrage loop (50-gem refund let players
            // cycle this offer infinitely for 3x the standard gold-per-gem rate).
            // isOneTimePurchase prevents repeat purchases within the 3-day window.
            return new ShopOffer
            {
                offerId = "comeback_offer",
                offerName = "Second Chance Pack",
                description = "Get back in the game!",
                offerType = OfferType.ComebackOffer,
                gemCost = 100,
                goldReward = 1000,  // Aligned with standard rate: 100 gems = 2x 1000-gold pack
                chestReward = ChestType.Gold,
                isOneTimePurchase = true,
                expiryTime = DateTime.UtcNow.AddDays(3),
                valueLabel = "LIMITED TIME!"
            };
        }

        private ShopOffer CreateWelcomeBackOffer()
        {
            return new ShopOffer
            {
                offerId = "welcome_back",
                offerName = "Welcome Back Bundle",
                description = "We missed you! Here's a special offer.",
                offerType = OfferType.ComebackOffer,
                realMoneyCost = 2.99f,
                gemReward = 300,
                goldReward = 10000,
                chestReward = ChestType.Magical,
                isOneTimePurchase = true,
                valueLabel = "SPECIAL!"
            };
        }

        private ShopOffer CreateValuePackOffer()
        {
            return new ShopOffer
            {
                offerId = "value_pack",
                offerName = "Value Bundle",
                description = "Best value for new spenders!",
                offerType = OfferType.CardBundle,
                realMoneyCost = 4.99f,
                gemReward = 500,
                goldReward = 10000,
                isOneTimePurchase = true,
                valueLabel = "BEST VALUE!"
            };
        }

        private ShopOffer CreatePremiumBundleOffer()
        {
            return new ShopOffer
            {
                offerId = $"premium_{DateTime.UtcNow.DayOfYear}",
                offerName = "Champion's Chest",
                description = "The ultimate bundle for champions",
                offerType = OfferType.ChestBundle,
                realMoneyCost = 19.99f,
                gemReward = 2500,
                goldReward = 100000,
                chestReward = ChestType.Legendary,
                expiryTime = DateTime.UtcNow.AddDays(1)
            };
        }

        private ShopOffer CreateSeasonPassOffer()
        {
            return new ShopOffer
            {
                offerId = "season_pass",
                offerName = "Season Pass",
                description = "Unlock the premium reward track!",
                offerType = OfferType.SeasonPass,
                realMoneyCost = 7.99f,
                includesSeasonPass = true,
                gemReward = 200,
                valueLabel = "RECOMMENDED"
            };
        }

        #endregion

        #region Purchases

        public bool TryPurchase(string offerId)
        {
            var offer = FindOffer(offerId);
            if (offer == null || !offer.IsAvailable)
            {
                Debug.LogWarning($"Offer not available: {offerId}");
                return false;
            }

            var player = Managers.GameManager.Instance?.Player;
            if (player == null) return false;

            // Check currency
            if (offer.gemCost > 0)
            {
                if (player.gems < offer.gemCost)
                {
                    Debug.Log("Not enough gems");
                    return false;
                }
                player.gems -= offer.gemCost;
            }

            if (offer.goldCost > 0)
            {
                if (player.gold < offer.goldCost)
                {
                    Debug.Log("Not enough gold");
                    return false;
                }
                player.gold -= offer.goldCost;
            }

            // Real money would go through platform IAP
            if (offer.realMoneyCost > 0)
            {
                // ProcessRealMoneyPurchase(offer);
                player.hasEverSpent = true;
                player.totalSpent += offer.realMoneyCost;
            }

            // Grant rewards
            GrantOfferRewards(offer, player);

            // Mark as purchased
            offer.hasBeenPurchased = true;

            Managers.GameManager.Instance?.SavePlayerData();
            OnOfferPurchased?.Invoke(offer);

            Debug.Log($"Purchased: {offer.offerName}");
            return true;
        }

        private void GrantOfferRewards(ShopOffer offer, PlayerData player)
        {
            player.gold += offer.goldReward;
            player.gems += offer.gemReward;

            if (offer.includesSeasonPass)
                player.hasSeasonPass = true;

            if (offer.vipDays > 0)
            {
                if (player.vipExpiryDate == null || player.vipExpiryDate < DateTime.UtcNow)
                    player.vipExpiryDate = DateTime.UtcNow.AddDays(offer.vipDays);
                else
                    player.vipExpiryDate = player.vipExpiryDate.Value.AddDays(offer.vipDays);

                player.isVipSubscriber = true;
            }

            foreach (var cardReward in offer.cardRewards)
            {
                if (cardReward.isRandom)
                {
                    // Would generate random card of specified rarity
                    // player.AddCard(GetRandomCardOfRarity(cardReward.rarity), cardReward.count);
                }
                else
                {
                    player.AddCard(cardReward.cardId, cardReward.count);
                }
            }

            // Chest rewards would be handled by chest system
        }

        private ShopOffer FindOffer(string offerId)
        {
            foreach (var offer in dailyOffers)
                if (offer.offerId == offerId) return offer;

            foreach (var offer in featuredOffers)
                if (offer.offerId == offerId) return offer;

            foreach (var offer in gemStoreOffers)
                if (offer.offerId == offerId) return offer;

            return null;
        }

        #endregion

        #region Card Economy

        public int GetCardUpgradeCost(int currentLevel)
        {
            // Gold cost scales exponentially
            return Mathf.RoundToInt(cardUpgradeBaseCost * Mathf.Pow(upgradeScaleFactor, currentLevel - 1));
        }

        public int GetCardsNeededForUpgrade(CardRarity rarity, int currentLevel)
        {
            // Base cards needed by rarity
            int baseCards;
            switch (rarity)
            {
                case CardRarity.Common: baseCards = 2; break;
                case CardRarity.Rare: baseCards = 2; break;
                case CardRarity.Epic: baseCards = 2; break;
                case CardRarity.Legendary: baseCards = 1; break;
                default: baseCards = 2; break;
            }

            // Scale by level
            return baseCards * currentLevel;
        }

        public int GetChestUnlockCost(float hoursRemaining)
        {
            return Mathf.CeilToInt(hoursRemaining * chestUnlockGemsPerHour);
        }

        #endregion

        public List<ShopOffer> GetDailyOffers() => dailyOffers;
        public List<ShopOffer> GetFeaturedOffers() => featuredOffers;
        public List<ShopOffer> GetGemStoreOffers() => gemStoreOffers;
    }
}
