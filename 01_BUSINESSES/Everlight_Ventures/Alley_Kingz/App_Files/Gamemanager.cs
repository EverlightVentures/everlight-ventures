using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Core;
using ArenaAdvance.Data;
using ArenaAdvance.Contracts;
using ArenaAdvance.Gameplay;
using ArenaAdvance.AI;

namespace ArenaAdvance.Managers
{
    public class GameManager : MonoBehaviour
    {
        public static GameManager Instance { get; private set; }

        [Header("Game State")]
        [SerializeField] private GameState currentState = GameState.MainMenu;
        [SerializeField] private PlayerData playerData;
        [SerializeField] private BattleState currentBattle;

        [Header("Season Info")]
        [SerializeField] private int currentSeason = 1;
        [SerializeField] private DateTime seasonStartDate;
        [SerializeField] private DateTime seasonEndDate;
        [SerializeField] private int seasonDurationDays = 28;

        [Header("Active Contracts")]
        [SerializeField] private List<AdvanceContract> activeContracts = new List<AdvanceContract>();
        [SerializeField] private List<AdvanceContract> availableContracts = new List<AdvanceContract>();

        // Events
        public event Action<GameState> OnGameStateChanged;
        public event Action<BattleState> OnBattleStarted;
        public event Action<BattleState> OnBattleEnded;
        public event Action<AdvanceContract> OnContractAccepted;
        public event Action<AdvanceContract, bool> OnContractCompleted; // bool = success
        public event Action<PlayerData> OnPlayerDataChanged;

        public GameState CurrentState => currentState;
        public PlayerData Player => playerData;
        public BattleState CurrentBattle => currentBattle;
        public int DaysRemainingInSeason => Mathf.Max(0, (seasonEndDate - DateTime.UtcNow).Days);

        private void Awake()
        {
            if (Instance == null)
            {
                Instance = this;
                DontDestroyOnLoad(gameObject);
                Initialize();
            }
            else
            {
                Destroy(gameObject);
            }
        }

        private void Initialize()
        {
            // Load or create player data
            LoadPlayerData();

            // Initialize season
            InitializeSeason();

            // Generate available contracts
            RefreshAvailableContracts();

            Debug.Log($"GameManager initialized. Player: {playerData.displayName}, " +
            $"NOS Bottles: {playerData.nosBottles}, Credit Tier: {playerData.creditProfile.trustTier}");
        }

        private void LoadPlayerData()
        {
            // Try to load from PlayerPrefs/file
            string savedData = PlayerPrefs.GetString("PlayerData", "");

            if (!string.IsNullOrEmpty(savedData))
            {
                try
                {
                    playerData = JsonUtility.FromJson<PlayerData>(savedData);
                    Debug.Log("Player data loaded successfully");
                }
                catch
                {
                    CreateNewPlayer();
                }
            }
            else
            {
                CreateNewPlayer();
            }
        }

        private void CreateNewPlayer()
        {
            string playerId = Guid.NewGuid().ToString();
            playerData = new PlayerData(playerId, "Player" + UnityEngine.Random.Range(1000, 9999));

            // Give starter cards
            GiveStarterCards();

            SavePlayerData();
            Debug.Log("New player created: " + playerData.displayName);
        }

        private void GiveStarterCards()
        {
            // These would be actual card IDs from your ScriptableObjects
            string[] starterCardIds = new string[]
            {
                "knight", "archers", "fireball", "arrows",
                "giant", "musketeer", "mini_pekka", "bomber"
            };

            foreach (var cardId in starterCardIds)
            {
                playerData.AddCard(cardId, 1);
            }

            // Set up first deck
            if (playerData.decks.Count > 0)
            {
                playerData.decks[0].cardIds = new List<string>(starterCardIds);
            }
        }

        public void SavePlayerData()
        {
            if (playerData == null) return;

            playerData.lastSeen = DateTime.UtcNow;
            string json = JsonUtility.ToJson(playerData);
            PlayerPrefs.SetString("PlayerData", json);
            PlayerPrefs.Save();
        }

        private void InitializeSeason()
        {
            // Check if we need a new season
            string lastSeasonData = PlayerPrefs.GetString("SeasonData", "");

            if (string.IsNullOrEmpty(lastSeasonData) || DateTime.UtcNow > seasonEndDate)
            {
                StartNewSeason();
            }
            else
            {
                // Parse saved season data
                var parts = lastSeasonData.Split('|');
                if (parts.Length >= 3)
                {
                    currentSeason = int.Parse(parts[0]);
                    seasonStartDate = DateTime.Parse(parts[1]);
                    seasonEndDate = DateTime.Parse(parts[2]);
                }
            }
        }

        private void StartNewSeason()
        {
            currentSeason++;
            seasonStartDate = DateTime.UtcNow;
            seasonEndDate = seasonStartDate.AddDays(seasonDurationDays);

            // Reset seasonal stats
            playerData.engagement.ResetForNewSeason();

            // Evaluate any active contracts
            foreach (var contract in activeContracts)
            {
                EvaluateContract(contract);
            }
            activeContracts.Clear();

            // Save season info
            string seasonData = $"{currentSeason}|{seasonStartDate}|{seasonEndDate}";
            PlayerPrefs.SetString("SeasonData", seasonData);

            Debug.Log($"Season {currentSeason} started. Ends: {seasonEndDate}");
        }

        #region Game State Management

        public void ChangeState(GameState newState)
        {
            if (currentState == newState) return;

            var oldState = currentState;
            currentState = newState;

            Debug.Log($"Game state changed: {oldState} -> {newState}");
            OnGameStateChanged?.Invoke(newState);
        }

        #endregion

        #region Battle Management

        public void StartBattle(List<ScriptableObjects.CardDefinition> playerDeck)
        {
            currentBattle = new BattleState();

            // Initialize battle with tower stats based on player level
            int towerHealth = 2000 + (playerData.experienceLevel * 100);
            int towerDamage = 50 + (playerData.experienceLevel * 5);

            currentBattle.Initialize(playerData.displayName, "Opponent", towerHealth, towerDamage);

            // Set up player's deck with levels
            var levels = new Dictionary<string, int>();
            foreach (var card in playerDeck)
            {
                if (playerData.cardCollection.TryGetValue(card.cardId, out var playerCard))
                {
                    levels[card.cardId] = playerCard.level;
                }
                else
                {
                    levels[card.cardId] = 1;
                }
            }
            currentBattle.player.SetupDeck(playerDeck, levels);

            // TODO: Set up opponent's deck (matchmaking system would provide this)

            ChangeState(GameState.Battle);
            OnBattleStarted?.Invoke(currentBattle);
        }

        public void EndBattle()
        {
            if (currentBattle == null) return;

            var result = currentBattle.GetResultForPlayer();
            int crownsEarned = currentBattle.playerCrowns;

            // Update player stats
            playerData.stats.RecordMatch(result);
            playerData.stats.totalCrownsEarned += crownsEarned;

            if (crownsEarned == 3)
                playerData.stats.threeCrownWins++;

            // Update NOS Bottles (trophy ladder)
            int trophyChange = CalculateTrophyChange(result);
            playerData.nosBottles = Mathf.Max(0, playerData.nosBottles + trophyChange);
            playerData.UpdateArenaAndLeague();

            // Update engagement
            playerData.engagement.matchesThisSeason++;
            playerData.engagement.RecordLogin();

            // Update active contracts
            UpdateContractProgress(result, crownsEarned);

            // Save
            SavePlayerData();

            OnBattleEnded?.Invoke(currentBattle);
            OnPlayerDataChanged?.Invoke(playerData);

            ChangeState(GameState.PostMatch);
        }

        private int CalculateTrophyChange(MatchResult result)
        {
            // Base trophy change, can be made more sophisticated
            switch (result)
            {
                case MatchResult.Win:
                    return UnityEngine.Random.Range(25, 35);
                case MatchResult.Loss:
                    // Lose less at lower trophy counts
                    int loss = UnityEngine.Random.Range(20, 30);
                    if (playerData.nosBottles < 1000) loss = loss / 2;
                    return -loss;
                default:
                    return 0;
            }
        }

        #endregion

        #region Contract Management

        public void RefreshAvailableContracts()
        {
            availableContracts.Clear();

            var tier = playerData.creditProfile.trustTier;

            // Generate contracts based on player's tier
            availableContracts.Add(ContractTemplates.CreateGoldPassContract(tier));
            availableContracts.Add(ContractTemplates.CreateUpgradeBundleContract(tier));

            if (tier >= CreditTier.Silver)
            {
                availableContracts.Add(ContractTemplates.CreateHybridContract(tier));
            }
        }

        public List<ContractAdvice> GetContractAdvice()
        {
            return ContractAdvisor.GetContractOptions(
                playerData,
                availableContracts,
                DaysRemainingInSeason);
        }

        public bool AcceptContract(string contractId)
        {
            var contract = availableContracts.Find(c => c.contractId == contractId);
            if (contract == null)
            {
                Debug.LogWarning($"Contract not found: {contractId}");
                return false;
            }

            // Check eligibility
            if (playerData.creditProfile.IsOnCooldown())
            {
                Debug.LogWarning("Player is on contract cooldown");
                return false;
            }

            if (playerData.creditProfile.activeContractIds.Count >=
                playerData.creditProfile.GetMaxActiveContracts())
            {
                Debug.LogWarning("Player at max active contracts");
                return false;
            }

            if (contract.minimumTier > playerData.creditProfile.trustTier)
            {
                Debug.LogWarning("Player tier too low for this contract");
                return false;
            }

            // Activate contract
            contract.Activate(playerData.playerId);

            // Grant immediate rewards
            GrantRewards(contract.immediateRewards);

            // Track
            activeContracts.Add(contract);
            availableContracts.Remove(contract);
            playerData.creditProfile.activeContractIds.Add(contract.contractId);
            playerData.creditProfile.totalContractsTaken++;

            SavePlayerData();

            OnContractAccepted?.Invoke(contract);
            Debug.Log($"Contract accepted: {contract.contractName}");

            return true;
        }

        private void UpdateContractProgress(MatchResult result, int crowns)
        {
            foreach (var contract in activeContracts)
            {
                if (contract.status != ContractStatus.Active) continue;

                // Update progress based on match result
                if (result == MatchResult.Win)
                {
                    contract.progress.currentWins++;
                    if (crowns == 3)
                        contract.progress.currentThreeCrownWins++;
                }

                contract.progress.currentCrowns += crowns;
                contract.progress.currentMatches++;
                contract.progress.currentLeague = playerData.currentLeague;
                contract.progress.currentPlayDays = playerData.engagement.uniquePlayDaysThisSeason;
                contract.progress.currentQuestsCompleted = playerData.engagement.questsCompletedThisSeason;

                // Check for completion
                if (contract.progress.CheckSuccess(contract.conditions))
                {
                    CompleteContract(contract, true);
                }
            }
        }

        public void EvaluateContract(AdvanceContract contract)
        {
            var result = contract.Evaluate();

            if (result.isSuccess)
            {
                CompleteContract(contract, true);
            }
            else if (result.isExpired)
            {
                // Contract failed - needs settlement
                contract.status = ContractStatus.Failed;
                Debug.Log($"Contract failed: {contract.contractName} ({result.completionPercent:P0} complete)");
            }
        }

        private void CompleteContract(AdvanceContract contract, bool success)
        {
            if (success)
            {
                contract.status = ContractStatus.Succeeded;

                // Grant success rewards
                GrantRewards(contract.successRewards);

                // Update credit profile
                playerData.creditProfile.OnContractSuccess();

                Debug.Log($"Contract completed successfully: {contract.contractName}");
            }

            // Remove from active
            activeContracts.Remove(contract);
            playerData.creditProfile.activeContractIds.Remove(contract.contractId);

            SavePlayerData();
            OnContractCompleted?.Invoke(contract, success);
        }

        public bool SettleFailedContract(string contractId, SettlementOption option)
        {
            var contract = activeContracts.Find(c => c.contractId == contractId);
            if (contract == null || contract.status != ContractStatus.Failed)
                return false;

            switch (option)
            {
                case SettlementOption.PayGems:
                    if (playerData.gems < contract.failurePenalty.gemsToSettle)
                    {
                        Debug.LogWarning("Not enough gems to settle");
                        return false;
                    }
                    playerData.gems -= contract.failurePenalty.gemsToSettle;
                    playerData.creditProfile.OnContractFailed(true, 5);
                    contract.status = ContractStatus.Settled;
                    Debug.Log($"Contract settled with gems: {contract.contractName}");
                    break;

                case SettlementOption.ForfeitRewards:
                    // Revoke some rewards (simplified - you'd track what was given)
                    playerData.creditProfile.OnContractFailed(false, 10);
                    contract.status = ContractStatus.Settled;
                    Debug.Log($"Contract forfeited: {contract.contractName}");
                    break;

                case SettlementOption.RedemptionQuest:
                    // Start redemption quest (would need quest system)
                    // For now, treat like forfeit with smaller penalty
                    playerData.creditProfile.OnContractFailed(true, 3);
                    contract.status = ContractStatus.Settled;
                    Debug.Log($"Contract redemption quest started: {contract.contractName}");
                    break;
            }

            // Cleanup
            activeContracts.Remove(contract);
            playerData.creditProfile.activeContractIds.Remove(contract.contractId);
            SavePlayerData();

            return true;
        }

        #endregion

        #region Economy

        private void GrantRewards(ContractRewards rewards)
        {
            playerData.gold += rewards.goldReward;
            playerData.gems += rewards.gemsReward;

            foreach (var cardReward in rewards.cardRewards)
            {
                playerData.AddCard(cardReward.cardId, cardReward.count);
            }

            if (rewards.includesSeasonPass)
            {
                playerData.hasSeasonPass = true;
            }

            if (rewards.includesVipDays)
            {
                if (playerData.vipExpiryDate == null || playerData.vipExpiryDate < DateTime.UtcNow)
                {
                    playerData.vipExpiryDate = DateTime.UtcNow.AddDays(rewards.vipDaysAmount);
                }
                else
                {
                    playerData.vipExpiryDate = playerData.vipExpiryDate.Value.AddDays(rewards.vipDaysAmount);
                }
                playerData.isVipSubscriber = true;
            }

            OnPlayerDataChanged?.Invoke(playerData);
        }

        public bool SpendGold(int amount)
        {
            if (playerData.gold < amount) return false;
            playerData.gold -= amount;
            SavePlayerData();
            OnPlayerDataChanged?.Invoke(playerData);
            return true;
        }

        public bool SpendGems(int amount)
        {
            if (playerData.gems < amount) return false;
            playerData.gems -= amount;
            SavePlayerData();
            OnPlayerDataChanged?.Invoke(playerData);
            return true;
        }

        public void AddCurrency(int gold = 0, int gems = 0)
        {
            playerData.gold += gold;
            playerData.gems += gems;
            SavePlayerData();
            OnPlayerDataChanged?.Invoke(playerData);
        }

        #endregion

        private void OnApplicationPause(bool pause)
        {
            if (pause)
            {
                SavePlayerData();
            }
        }

        private void OnApplicationQuit()
        {
            SavePlayerData();
        }
    }
}
