
using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Core;
using ArenaAdvance.Data;

namespace ArenaAdvance.AI
{
    public enum DifficultyBucket
    {
        Easy,       // >80% success probability
        Fair,       // 50-80% success probability
        Hard,       // 30-50% success probability
        Extreme     // <30% success probability
    }

    [Serializable]
    public class ContractAdvice
    {
        public string contractId;
        public float successProbability;        // 0.0 - 1.0
        public DifficultyBucket difficultyBucket;
        public string recommendedVariant;       // "LITE", "STANDARD", "PRO"
        public List<string> notes = new List<string>();
        public ChurnRisk churnRiskIfFail;
        public bool shouldOffer;                // False if too risky for this player
    }

    public enum ChurnRisk
    {
        Low,
        Medium,
        High
    }

    /// <summary>
    /// AI Contract Advisor - Phase 1: Heuristic-based
    /// Estimates probability of contract success and provides recommendations
    /// </summary>
    public static class ContractAdvisor
    {
        // Configuration constants
        private const float MATCHES_PER_DAY_DEFAULT = 5f;
        private const float WIN_RATE_DEFAULT = 0.5f;
        private const float CROWNS_PER_WIN_AVG = 1.5f;

        /// <summary>
        /// Main entry point: Get advice for a specific contract
        /// </summary>
        public static ContractAdvice GetAdvice(
            PlayerData player,
            Contracts.AdvanceContract contract,
            int daysRemainingInSeason)
        {
            var advice = new ContractAdvice
            {
                contractId = contract.contractId,
                notes = new List<string>()
            };

            // Calculate expected performance
            float avgMatchesPerDay = player.engagement.averageMatchesPerDay > 0
            ? player.engagement.averageMatchesPerDay
            : MATCHES_PER_DAY_DEFAULT;

            float recentWinRate = player.stats.RecentWinRate > 0
            ? player.stats.RecentWinRate
            : WIN_RATE_DEFAULT;

            int effectiveDays = Mathf.Min(daysRemainingInSeason, contract.durationDays);
            float expectedMatches = avgMatchesPerDay * effectiveDays;
            float expectedWins = expectedMatches * recentWinRate;
            float expectedCrowns = expectedWins * CROWNS_PER_WIN_AVG;

            // Calculate individual condition probabilities
            List<float> conditionProbs = new List<float>();

            // Win probability
            if (contract.conditions.requiredWins > 0)
            {
                float winProb = CalculateGoalProbability(
                    expectedWins,
                    contract.conditions.requiredWins,
                    recentWinRate);
                conditionProbs.Add(winProb);

                advice.notes.Add($"You typically play {avgMatchesPerDay:F1} matches/day. " +
                $"This challenge needs ~{contract.conditions.requiredWins / (float)effectiveDays:F1} wins/day.");
            }

            // Crown probability
            if (contract.conditions.requiredCrowns > 0)
            {
                float crownProb = CalculateGoalProbability(
                    expectedCrowns,
                    contract.conditions.requiredCrowns,
                    recentWinRate);
                conditionProbs.Add(crownProb);
            }

            // League/rank probability (more complex)
            if (contract.conditions.requiredLeague != League.None)
            {
                float leagueProb = CalculateLeagueProbability(
                    player.currentLeague,
                    contract.conditions.requiredLeague,
                    player.trophies,
                    recentWinRate,
                    expectedMatches);
                conditionProbs.Add(leagueProb);

                if (player.currentLeague < contract.conditions.requiredLeague)
                {
                    advice.notes.Add($"You're currently in {player.currentLeague}. " +
                    $"Target: {contract.conditions.requiredLeague}.");
                }
            }

            // Play days probability
            if (contract.conditions.requiredPlayDays > 0)
            {
                float daysProb = CalculatePlayDaysProbability(
                    player.engagement.uniquePlayDaysThisSeason,
                    player.engagement.loginDatesThisSeason.Count,
                    contract.conditions.requiredPlayDays,
                    effectiveDays);
                conditionProbs.Add(daysProb);

                advice.notes.Add($"You've played {player.engagement.uniquePlayDaysThisSeason} days this season.");
            }

            // Match count probability
            if (contract.conditions.requiredMatches > 0)
            {
                float matchProb = CalculateGoalProbability(
                    expectedMatches,
                    contract.conditions.requiredMatches,
                    0.9f); // High base rate - just playing, not winning
                conditionProbs.Add(matchProb);
            }

            // Combine probabilities
            if (conditionProbs.Count > 0)
            {
                if (contract.conditions.useOrLogic)
                {
                    // OR logic: probability of at least one succeeding
                    float failAll = 1f;
                    foreach (var p in conditionProbs)
                        failAll *= (1f - p);
                    advice.successProbability = 1f - failAll;
                }
                else
                {
                    // AND logic: all must succeed
                    float successAll = 1f;
                    foreach (var p in conditionProbs)
                        successAll *= p;
                    advice.successProbability = successAll;
                }
            }
            else
            {
                advice.successProbability = 0.5f; // Default
            }

            // Determine difficulty bucket
            advice.difficultyBucket = GetDifficultyBucket(advice.successProbability);

            // Recommend variant
            advice.recommendedVariant = RecommendVariant(advice.successProbability);

            // Assess churn risk
            advice.churnRiskIfFail = AssessChurnRisk(player, advice.successProbability);

            // Determine if we should offer this contract
            advice.shouldOffer = ShouldOfferContract(player, advice);

            // Add historical context
            if (player.creditProfile.successfulContracts > 0 || player.creditProfile.failedContracts > 0)
            {
                int total = player.creditProfile.successfulContracts + player.creditProfile.failedContracts;
                float historicalRate = (float)player.creditProfile.successfulContracts / total;
                advice.notes.Add($"You've completed {player.creditProfile.successfulContracts}/{total} contracts ({historicalRate:P0}).");
            }

            return advice;
        }

        /// <summary>
        /// Calculate probability of reaching a numeric goal
        /// </summary>
        private static float CalculateGoalProbability(float expected, int required, float varianceFactor)
        {
            if (required <= 0) return 1f;

            float ratio = expected / required;

            // Use a sigmoid-like function for probability
            // ratio = 1.0 means 50% chance
            // ratio = 1.2 means ~75% chance
            // ratio = 0.8 means ~25% chance

            if (ratio >= 1.5f) return 0.95f;
            if (ratio >= 1.2f) return 0.75f + (ratio - 1.2f) * 0.67f;
            if (ratio >= 1.0f) return 0.50f + (ratio - 1.0f) * 1.25f;
            if (ratio >= 0.8f) return 0.25f + (ratio - 0.8f) * 1.25f;
            if (ratio >= 0.5f) return 0.10f + (ratio - 0.5f) * 0.5f;
            return Mathf.Max(0.05f, ratio * 0.2f);
        }

        /// <summary>
        /// Calculate probability of reaching a target league
        /// </summary>
        private static float CalculateLeagueProbability(
            League current,
            League target,
            int currentTrophies,
            float winRate,
            float expectedMatches)
        {
            if (current >= target) return 0.95f; // Already there

            int leagueGap = (int)target - (int)current;

            // Rough trophy thresholds
            int trophiesNeeded = leagueGap * 500; // ~500 trophies per league

            // Expected trophy change: each match is roughly +/- 30 trophies
            // Net = (winRate * 30) - ((1-winRate) * 30) = (2*winRate - 1) * 30
            float netTrophiesPerMatch = (2f * winRate - 1f) * 30f;
            float expectedTrophyChange = netTrophiesPerMatch * expectedMatches;

            // If negative net rate, climbing is very hard
            if (netTrophiesPerMatch <= 0)
                return 0.1f * (1f / (leagueGap + 1));

            float ratio = expectedTrophyChange / trophiesNeeded;
            return CalculateGoalProbability(ratio * trophiesNeeded, trophiesNeeded, winRate);
        }

        /// <summary>
        /// Calculate probability of playing enough days
        /// </summary>
        private static float CalculatePlayDaysProbability(
            int currentDaysPlayed,
            int totalDaysTracked,
            int requiredDays,
            int daysRemaining)
        {
            if (requiredDays <= 0) return 1f;

            // Calculate player's play rate
            float playRate = totalDaysTracked > 7
            ? (float)currentDaysPlayed / totalDaysTracked
            : 0.7f; // Default assumption

            float expectedPlayDays = daysRemaining * playRate;
            return CalculateGoalProbability(expectedPlayDays, requiredDays, playRate);
        }

        private static DifficultyBucket GetDifficultyBucket(float probability)
        {
            if (probability >= 0.8f) return DifficultyBucket.Easy;
            if (probability >= 0.5f) return DifficultyBucket.Fair;
            if (probability >= 0.3f) return DifficultyBucket.Hard;
            return DifficultyBucket.Extreme;
        }

        private static string RecommendVariant(float probability)
        {
            if (probability >= 0.7f) return "PRO";      // They can handle harder
            if (probability >= 0.4f) return "STANDARD"; // Good fit
            return "LITE";                              // Should try easier
        }

        private static ChurnRisk AssessChurnRisk(PlayerData player, float successProb)
        {
            // High churn risk indicators:
            // - Low win rate recently
            // - Failed recent contracts
            // - Low engagement
            // - New player

            int riskScore = 0;

            if (player.stats.RecentWinRate < 0.4f) riskScore += 2;
            if (player.creditProfile.failedContracts > player.creditProfile.successfulContracts) riskScore += 2;
            if (player.engagement.averageMatchesPerDay < 3f) riskScore += 1;
            if (player.stats.totalMatches < 50) riskScore += 1;  // New player
            if (successProb < 0.3f) riskScore += 2;

            if (riskScore >= 5) return ChurnRisk.High;
            if (riskScore >= 3) return ChurnRisk.Medium;
            return ChurnRisk.Low;
        }

        private static bool ShouldOfferContract(PlayerData player, ContractAdvice advice)
        {
            // Don't offer extremely difficult contracts to at-risk players
            if (advice.churnRiskIfFail == ChurnRisk.High &&
                advice.difficultyBucket == DifficultyBucket.Extreme)
                return false;

            // Don't offer if player is on cooldown
            if (player.creditProfile.IsOnCooldown())
                return false;

            // Don't offer if at max active contracts
            if (player.creditProfile.activeContractIds.Count >=
                player.creditProfile.GetMaxActiveContracts())
                return false;

            return true;
        }

        /// <summary>
        /// Get multiple contract options with difficulty variants
        /// </summary>
        public static List<ContractAdvice> GetContractOptions(
            PlayerData player,
            List<Contracts.AdvanceContract> availableContracts,
            int daysRemainingInSeason)
        {
            var options = new List<ContractAdvice>();

            foreach (var contract in availableContracts)
            {
                var advice = GetAdvice(player, contract, daysRemainingInSeason);
                if (advice.shouldOffer)
                {
                    options.Add(advice);
                }
            }

            // Sort by how "fair" they are (closest to 60% success rate is ideal)
            options.Sort((a, b) =>
            {
                float aFairness = Mathf.Abs(a.successProbability - 0.6f);
                float bFairness = Mathf.Abs(b.successProbability - 0.6f);
                return aFairness.CompareTo(bFairness);
            });

            return options;
        }

        /// <summary>
        /// Generate a progress update message for active contracts
        /// </summary>
        public static string GetProgressMessage(
            PlayerData player,
            Contracts.AdvanceContract contract)
        {
            float completion = contract.progress.GetCompletionPercentage(contract.conditions);
            int daysRemaining = contract.GetDaysRemaining();

            // Calculate pace
            float expectedCompletionByNow = 1f - contract.GetTimeRemainingPercent();
            bool onPace = completion >= expectedCompletionByNow;

            if (completion >= 1f)
            {
                return "🎉 Challenge complete! Your rewards are now permanent.";
            }
            else if (onPace)
            {
                return $"✅ You're on track! {completion:P0} complete with {daysRemaining} days left.";
            }
            else
            {
                float deficit = expectedCompletionByNow - completion;
                if (deficit > 0.3f)
                {
                    return $"⚠️ You're behind pace. {completion:P0} complete, {daysRemaining} days left. " +
                    "Consider increasing your daily play!";
                }
                else
                {
                    return $"📊 Slightly behind: {completion:P0} complete with {daysRemaining} days remaining.";
                }
            }
        }
    }
}
