
using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Data;

namespace ArenaAdvance.Core
{
    [Serializable]
    public class PlayerCard
    {
        public string cardId;
        public int level;
        public int cardCount;
        public int cardsNeededForUpgrade;

        public PlayerCard(string id)
        {
            cardId = id;
            level = 1;
            cardCount = 1;
            cardsNeededForUpgrade = 2;
        }

        public bool CanUpgrade()
        {
            return cardCount >= cardsNeededForUpgrade;
        }

        public int GetUpgradeCost()
        {
            // Gold cost scales with level
            return level * 100 * (level + 1);
        }
    }

    [Serializable]
    public class PlayerDeck
    {
        public string deckName;
        public List<string> cardIds = new List<string>(8);

        public PlayerDeck(string name)
        {
            deckName = name;
        }

        public bool IsValid()
        {
            return cardIds.Count == 8;
        }
    }

    [Serializable]
    public class PlayerStats
    {
        public int totalMatches;
        public int totalWins;
        public int totalLosses;
        public int totalDraws;
        public int currentWinStreak;
        public int bestWinStreak;
        public int totalCrownsEarned;
        public int totalTowerDestroyed;
        public int threeCrownWins;

        public float WinRate => totalMatches > 0 ? (float)totalWins / totalMatches : 0f;

        // Recent performance tracking (last 20 matches)
        public List<MatchResult> recentMatches = new List<MatchResult>();

        public float RecentWinRate
        {
            get
            {
                if (recentMatches.Count == 0) return 0f;
                int wins = 0;
                foreach (var match in recentMatches)
                {
                    if (match == MatchResult.Win) wins++;
                }
                return (float)wins / recentMatches.Count;
            }
        }

        public void RecordMatch(MatchResult result)
        {
            totalMatches++;

            switch (result)
            {
                case MatchResult.Win:
                    totalWins++;
                    currentWinStreak++;
                    if (currentWinStreak > bestWinStreak)
                        bestWinStreak = currentWinStreak;
                break;
                case MatchResult.Loss:
                    totalLosses++;
                    currentWinStreak = 0;
                    break;
                case MatchResult.Draw:
                    totalDraws++;
                    break;
            }

            recentMatches.Add(result);
            if (recentMatches.Count > 20)
                recentMatches.RemoveAt(0);
        }
    }

    [Serializable]
    public class PlayerCreditProfile
    {
        public int creditScore;                 // 0-100
        public CreditTier trustTier;
        public int totalContractsTaken;
        public int successfulContracts;
        public int failedContracts;
        public int settledContracts;
        public DateTime? cooldownEndTime;
        public List<string> activeContractIds = new List<string>();

        public PlayerCreditProfile()
        {
            creditScore = 50;  // Start at middle
            trustTier = CreditTier.Silver;
        }

        public void UpdateTier()
        {
            if (creditScore <= 20)
                trustTier = CreditTier.Bronze;
            else if (creditScore <= 50)
                trustTier = CreditTier.Silver;
            else if (creditScore <= 80)
                trustTier = CreditTier.Gold;
            else
                trustTier = CreditTier.Platinum;
        }

        public int GetMaxActiveContracts()
        {
            switch (trustTier)
            {
                case CreditTier.Bronze: return 1;
                case CreditTier.Silver: return 2;
                case CreditTier.Gold: return 3;
                case CreditTier.Platinum: return 4;
                default: return 1;
            }
        }

        public float GetMaxPrincipalValue()
        {
            switch (trustTier)
            {
                case CreditTier.Bronze: return 3f;      // $3 value
                case CreditTier.Silver: return 10f;     // $10 value
                case CreditTier.Gold: return 25f;       // $25 value
                case CreditTier.Platinum: return 50f;   // $50+ value
                default: return 3f;
            }
        }

        public bool IsOnCooldown()
        {
            if (!cooldownEndTime.HasValue) return false;
            return DateTime.UtcNow < cooldownEndTime.Value;
        }

        public void OnContractSuccess(int difficultyBonus = 5)
        {
            successfulContracts++;
            creditScore = Mathf.Min(100, creditScore + 5 + difficultyBonus);
            UpdateTier();
        }

        public void OnContractFailed(bool settled, int penaltySeverity = 10)
        {
            failedContracts++;
            if (settled)
            {
                settledContracts++;
                creditScore = Mathf.Max(0, creditScore - penaltySeverity / 2);
            }
            else
            {
                creditScore = Mathf.Max(0, creditScore - penaltySeverity);
                // Apply cooldown
                cooldownEndTime = DateTime.UtcNow.AddDays(3);
            }
            UpdateTier();
        }
    }

    [Serializable]
    public class EngagementStats
    {
        public int uniquePlayDaysThisSeason;
        public int matchesThisSeason;
        public int questsCompletedThisSeason;
        public float averageMatchesPerDay;
        public float averageSessionMinutes;
        public DateTime lastLoginTime;
        public List<DateTime> loginDatesThisSeason = new List<DateTime>();

        public void RecordLogin()
        {
            DateTime today = DateTime.UtcNow.Date;
            lastLoginTime = DateTime.UtcNow;

            if (!loginDatesThisSeason.Contains(today))
            {
                loginDatesThisSeason.Add(today);
                uniquePlayDaysThisSeason++;
            }

            // Recalculate average
            if (loginDatesThisSeason.Count > 0)
            {
                averageMatchesPerDay = (float)matchesThisSeason / loginDatesThisSeason.Count;
            }
        }

        public void ResetForNewSeason()
        {
            uniquePlayDaysThisSeason = 0;
            matchesThisSeason = 0;
            questsCompletedThisSeason = 0;
            loginDatesThisSeason.Clear();
        }
    }

    [Serializable]
    public class PlayerData
    {
        [Header("Identity")]
        public string playerId;
        public string displayName;
        public DateTime accountCreated;
        public DateTime lastSeen;

        [Header("Progression")]
        public int trophies;
        public int highestTrophies;
        public Arena currentArena;
        public League currentLeague;
        public int experienceLevel;
        public int experiencePoints;

        [Header("Currencies")]
        public int gold;
        public int gems;
        public int starPoints;  // For star levels

        [Header("Collection")]
        public Dictionary<string, PlayerCard> cardCollection = new Dictionary<string, PlayerCard>();
        public List<PlayerDeck> decks = new List<PlayerDeck>();
        public int selectedDeckIndex;

        [Header("Performance")]
        public PlayerStats stats = new PlayerStats();
        public EngagementStats engagement = new EngagementStats();

        [Header("Credit System")]
        public PlayerCreditProfile creditProfile = new PlayerCreditProfile();

        [Header("Monetization")]
        public bool hasEverSpent;
        public bool isVipSubscriber;
        public bool hasSeasonPass;
        public float totalSpent;
        public DateTime? vipExpiryDate;

        public PlayerData(string id, string name)
        {
            playerId = id;
            displayName = name;
            accountCreated = DateTime.UtcNow;
            lastSeen = DateTime.UtcNow;
            trophies = 0;
            highestTrophies = 0;
            currentArena = Arena.TrainingCamp;
            currentLeague = League.None;
            experienceLevel = 1;
            gold = 1000;  // Starting gold
            gems = 100;   // Starting gems

            // Create 5 empty deck slots
            for (int i = 0; i < 5; i++)
            {
                decks.Add(new PlayerDeck($"Deck {i + 1}"));
            }
        }

        public void AddCard(string cardId, int count = 1)
        {
            if (cardCollection.ContainsKey(cardId))
            {
                cardCollection[cardId].cardCount += count;
            }
            else
            {
                cardCollection[cardId] = new PlayerCard(cardId);
                if (count > 1)
                    cardCollection[cardId].cardCount = count;
            }
        }

        public PlayerDeck GetCurrentDeck()
        {
            if (selectedDeckIndex >= 0 && selectedDeckIndex < decks.Count)
                return decks[selectedDeckIndex];
            return null;
        }

        public void UpdateArenaAndLeague()
        {
            // Update arena based on trophies
            if (trophies < 400) currentArena = Arena.TrainingCamp;
            else if (trophies < 800) currentArena = Arena.GoblinStadium;
            else if (trophies < 1200) currentArena = Arena.BonePit;
            else if (trophies < 1600) currentArena = Arena.BarbarianBowl;
            else if (trophies < 2000) currentArena = Arena.SpellValley;
            else if (trophies < 2600) currentArena = Arena.BuildersWorkshop;
            else if (trophies < 3200) currentArena = Arena.RoyalArena;
            else if (trophies < 3800) currentArena = Arena.FrozenPeak;
            else if (trophies < 4400) currentArena = Arena.JungleArena;
            else if (trophies < 5000) currentArena = Arena.HogMountain;
            else currentArena = Arena.ElectroValley;

            // Update league for high trophy players
            if (trophies < 5000) currentLeague = League.None;
            else if (trophies < 5500) currentLeague = League.Bronze;
            else if (trophies < 6000) currentLeague = League.Silver;
            else if (trophies < 6500) currentLeague = League.Gold;
            else if (trophies < 7000) currentLeague = League.Platinum;
            else if (trophies < 7500) currentLeague = League.Diamond;
            else if (trophies < 8000) currentLeague = League.Champion;
            else currentLeague = League.GrandChampion;

            // Track highest
            if (trophies > highestTrophies)
                highestTrophies = trophies;
        }
    }
}
