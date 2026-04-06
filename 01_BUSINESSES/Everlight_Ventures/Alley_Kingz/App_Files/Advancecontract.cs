
using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Data;

namespace ArenaAdvance.Contracts
{
    [Serializable]
    public class ContractConditions
    {
        [Header("Skill-Based (Performance)")]
        public League requiredLeague = League.None;
        public int requiredWins;
        public int requiredCrowns;
        public int requiredThreeCrownWins;

        [Header("Engagement-Based (Grind)")]
        public int requiredPlayDays;
        public int requiredMatches;
        public int requiredQuestsCompleted;

        [Header("Hybrid Options")]
        public bool useOrLogic;  // If true, completing ANY condition succeeds

        public bool IsSkillBased => requiredLeague != League.None || requiredWins > 0 || requiredCrowns > 0;
        public bool IsEngagementBased => requiredPlayDays > 0 || requiredMatches > 0 || requiredQuestsCompleted > 0;
        public bool IsHybrid => IsSkillBased && IsEngagementBased;
    }

    [Serializable]
    public class ContractProgress
    {
        public League currentLeague;
        public int currentWins;
        public int currentCrowns;
        public int currentThreeCrownWins;
        public int currentPlayDays;
        public int currentMatches;
        public int currentQuestsCompleted;

        public float GetCompletionPercentage(ContractConditions conditions)
        {
            List<float> progressValues = new List<float>();

            if (conditions.requiredWins > 0)
                progressValues.Add((float)currentWins / conditions.requiredWins);

            if (conditions.requiredCrowns > 0)
                progressValues.Add((float)currentCrowns / conditions.requiredCrowns);

            if (conditions.requiredPlayDays > 0)
                progressValues.Add((float)currentPlayDays / conditions.requiredPlayDays);

            if (conditions.requiredMatches > 0)
                progressValues.Add((float)currentMatches / conditions.requiredMatches);

            if (conditions.requiredQuestsCompleted > 0)
                progressValues.Add((float)currentQuestsCompleted / conditions.requiredQuestsCompleted);

            // League progress is binary for now
            if (conditions.requiredLeague != League.None)
            {
                progressValues.Add(currentLeague >= conditions.requiredLeague ? 1f : 0f);
            }

            if (progressValues.Count == 0) return 0f;

            if (conditions.useOrLogic)
            {
                // Return max progress if using OR logic
                float max = 0f;
                foreach (var p in progressValues) max = Mathf.Max(max, p);
                return Mathf.Clamp01(max);
            }
            else
            {
                // Return average if all conditions must be met
                float sum = 0f;
                foreach (var p in progressValues) sum += p;
                return Mathf.Clamp01(sum / progressValues.Count);
            }
        }

        public bool CheckSuccess(ContractConditions conditions)
        {
            bool skillMet = true;
            bool engagementMet = true;

            // Check skill conditions
            if (conditions.requiredLeague != League.None)
                skillMet &= currentLeague >= conditions.requiredLeague;
            if (conditions.requiredWins > 0)
                skillMet &= currentWins >= conditions.requiredWins;
            if (conditions.requiredCrowns > 0)
                skillMet &= currentCrowns >= conditions.requiredCrowns;
            if (conditions.requiredThreeCrownWins > 0)
                skillMet &= currentThreeCrownWins >= conditions.requiredThreeCrownWins;

            // Check engagement conditions
            if (conditions.requiredPlayDays > 0)
                engagementMet &= currentPlayDays >= conditions.requiredPlayDays;
            if (conditions.requiredMatches > 0)
                engagementMet &= currentMatches >= conditions.requiredMatches;
            if (conditions.requiredQuestsCompleted > 0)
                engagementMet &= currentQuestsCompleted >= conditions.requiredQuestsCompleted;

            if (conditions.useOrLogic)
                return skillMet || engagementMet;
            else
                return skillMet && engagementMet;
        }
    }

    [Serializable]
    public class ContractRewards
    {
        public int goldReward;
        public int gemsReward;
        public List<CardReward> cardRewards = new List<CardReward>();
        public List<string> cosmeticIds = new List<string>();
        public bool includesSeasonPass;
        public bool includesVipDays;
        public int vipDaysAmount;

        [Serializable]
        public class CardReward
        {
            public string cardId;
            public int count;
        }

        public float GetEstimatedValue()
        {
            float value = 0f;
            value += goldReward * 0.001f;      // $1 per 1000 gold
            value += gemsReward * 0.01f;       // $1 per 100 gems
            if (includesSeasonPass) value += 7.99f;
            if (includesVipDays) value += vipDaysAmount * 0.16f;  // ~$5/month
            // Cards add value based on rarity (simplified)
            value += cardRewards.Count * 0.5f;
            return value;
        }
    }

    [Serializable]
    public class FailurePenalty
    {
        public int gemsToSettle;            // Gem cost to keep rewards
        public float rewardRetentionPercent; // What % of rewards they keep if forfeit
        public int cooldownDays;            // Days before next contract
        public string redemptionQuestId;    // Alternative: complete a quest instead

        public List<SettlementOption> availableOptions = new List<SettlementOption>
        {
            SettlementOption.PayGems,
            SettlementOption.ForfeitRewards
        };
    }

    [Serializable]
    public class AdvanceContract
    {
        [Header("Identity")]
        public string contractId;
        public string contractName;
        [TextArea(2, 3)]
        public string description;
        public ContractType contractType;

        [Header("Timing")]
        public DateTime startTime;
        public DateTime endTime;
        public int durationDays;

        [Header("Conditions")]
        public ContractConditions conditions;

        [Header("Rewards & Penalties")]
        public ContractRewards successRewards;
        public ContractRewards immediateRewards;  // Given upfront
        public FailurePenalty failurePenalty;

        [Header("Economy")]
        public float principalValue;        // Internal $ value
        public CreditTier minimumTier;      // Required tier to accept

        [Header("State")]
        public ContractStatus status;
        public ContractProgress progress;
        public string playerId;

        public AdvanceContract()
        {
            contractId = Guid.NewGuid().ToString();
            status = ContractStatus.Available;
            progress = new ContractProgress();
            conditions = new ContractConditions();
            successRewards = new ContractRewards();
            immediateRewards = new ContractRewards();
            failurePenalty = new FailurePenalty();
        }

        public void Activate(string playerIdToAssign)
        {
            playerId = playerIdToAssign;
            startTime = DateTime.UtcNow;
            endTime = startTime.AddDays(durationDays);
            status = ContractStatus.Active;
        }

        public float GetTimeRemainingPercent()
        {
            if (status != ContractStatus.Active) return 0f;

            TimeSpan total = endTime - startTime;
            TimeSpan remaining = endTime - DateTime.UtcNow;

            if (remaining.TotalSeconds <= 0) return 0f;
            return (float)(remaining.TotalSeconds / total.TotalSeconds);
        }

        public int GetDaysRemaining()
        {
            if (status != ContractStatus.Active) return 0;
            TimeSpan remaining = endTime - DateTime.UtcNow;
            return Mathf.Max(0, (int)remaining.TotalDays);
        }

        public bool IsExpired()
        {
            return DateTime.UtcNow >= endTime;
        }

        public void UpdateProgress(ContractProgress newProgress)
        {
            progress = newProgress;

            // Check for early completion
            if (progress.CheckSuccess(conditions))
            {
                status = ContractStatus.Succeeded;
            }
        }

        public ContractEvaluationResult Evaluate()
        {
            var result = new ContractEvaluationResult();
            result.contractId = contractId;
            result.completionPercent = progress.GetCompletionPercentage(conditions);
            result.isSuccess = progress.CheckSuccess(conditions);
            result.isExpired = IsExpired();

            if (result.isSuccess)
            {
                status = ContractStatus.Succeeded;
            }
            else if (result.isExpired)
            {
                status = ContractStatus.Failed;
            }

            return result;
        }
    }

    [Serializable]
    public class ContractEvaluationResult
    {
        public string contractId;
        public float completionPercent;
        public bool isSuccess;
        public bool isExpired;
        public List<string> missedConditions = new List<string>();
    }

    // Contract Templates for easy creation
    public static class ContractTemplates
    {
        public static AdvanceContract CreateGoldPassContract(CreditTier playerTier)
        {
            var contract = new AdvanceContract
            {
                contractName = "Advance Gold Pass",
                description = "Get Gold Pass rewards now. Complete the challenge to keep them!",
                contractType = ContractType.Pass,
                durationDays = 28,
                minimumTier = CreditTier.Bronze
            };

            // Scale based on player tier
            switch (playerTier)
            {
                case CreditTier.Bronze:
                    contract.conditions.requiredLeague = League.Silver;
                    contract.conditions.requiredWins = 30;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 5f;
                    contract.failurePenalty.gemsToSettle = 150;
                    break;

                case CreditTier.Silver:
                    contract.conditions.requiredLeague = League.Gold;
                    contract.conditions.requiredWins = 50;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 8f;
                    contract.failurePenalty.gemsToSettle = 250;
                    break;

                case CreditTier.Gold:
                    contract.conditions.requiredLeague = League.Gold;
                    contract.conditions.requiredWins = 80;
                    contract.conditions.requiredPlayDays = 10;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 10f;
                    contract.failurePenalty.gemsToSettle = 300;
                    break;

                case CreditTier.Platinum:
                    contract.conditions.requiredLeague = League.Platinum;
                    contract.conditions.requiredWins = 100;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 15f;
                    contract.failurePenalty.gemsToSettle = 200;  // Lower for trusted players
                    break;
            }

            // Immediate rewards (what they get upfront)
            contract.immediateRewards.includesSeasonPass = true;
            contract.immediateRewards.goldReward = 2000;

            // Success rewards (bonus for completing)
            contract.successRewards.gemsReward = 100;
            contract.successRewards.goldReward = 5000;

            // Failure options
            contract.failurePenalty.rewardRetentionPercent = 0.5f;
            contract.failurePenalty.cooldownDays = 3;
            contract.failurePenalty.availableOptions = new List<SettlementOption>
            {
                SettlementOption.PayGems,
                SettlementOption.ForfeitRewards,
                SettlementOption.RedemptionQuest
            };

            return contract;
        }

        public static AdvanceContract CreateUpgradeBundleContract(CreditTier playerTier)
        {
            var contract = new AdvanceContract
            {
                contractName = "Advance Upgrade Bundle",
                description = "Get card upgrades now. Play actively to keep them!",
                contractType = ContractType.Upgrade,
                durationDays = 14,
                minimumTier = CreditTier.Bronze
            };

            // Engagement-focused conditions
            switch (playerTier)
            {
                case CreditTier.Bronze:
                    contract.conditions.requiredPlayDays = 7;
                    contract.conditions.requiredMatches = 50;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 3f;
                    contract.failurePenalty.gemsToSettle = 100;
                    break;

                case CreditTier.Silver:
                    contract.conditions.requiredPlayDays = 10;
                    contract.conditions.requiredMatches = 80;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 6f;
                    contract.failurePenalty.gemsToSettle = 180;
                    break;

                case CreditTier.Gold:
                    contract.conditions.requiredPlayDays = 10;
                    contract.conditions.requiredMatches = 100;
                    contract.conditions.requiredQuestsCompleted = 10;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 10f;
                    contract.failurePenalty.gemsToSettle = 250;
                    break;

                case CreditTier.Platinum:
                    contract.conditions.requiredPlayDays = 12;
                    contract.conditions.requiredMatches = 120;
                    contract.conditions.useOrLogic = true;
                    contract.principalValue = 15f;
                    contract.failurePenalty.gemsToSettle = 200;
                    break;
            }

            // Immediate rewards
            contract.immediateRewards.goldReward = 10000;

            // Success rewards
            contract.successRewards.goldReward = 5000;
            contract.successRewards.gemsReward = 50;

            contract.failurePenalty.rewardRetentionPercent = 0.3f;
            contract.failurePenalty.cooldownDays = 2;

            return contract;
        }

        public static AdvanceContract CreateHybridContract(CreditTier playerTier)
        {
            var contract = new AdvanceContract
            {
                contractName = "Champion's Challenge",
                description = "The ultimate challenge. Prove your skill OR dedication!",
                contractType = ContractType.Pass,
                durationDays = 28,
                minimumTier = CreditTier.Silver
            };

            // Both skill AND engagement options
            contract.conditions.requiredLeague = League.Gold;
            contract.conditions.requiredWins = 60;
            contract.conditions.requiredPlayDays = 14;
            contract.conditions.requiredMatches = 100;
            contract.conditions.useOrLogic = true;  // Complete ANY path

            contract.principalValue = 12f;

            contract.immediateRewards.includesSeasonPass = true;
            contract.immediateRewards.goldReward = 5000;
            contract.immediateRewards.gemsReward = 50;

            contract.successRewards.goldReward = 10000;
            contract.successRewards.gemsReward = 200;

            contract.failurePenalty.gemsToSettle = 350;
            contract.failurePenalty.rewardRetentionPercent = 0.4f;
            contract.failurePenalty.cooldownDays = 5;

            return contract;
        }
    }
}
