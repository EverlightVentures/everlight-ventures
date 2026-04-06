using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Core;
using ArenaAdvance.Data;
using ArenaAdvance.ScriptableObjects;

namespace ArenaAdvance.AI
{
    /// <summary>
    /// Smart Matchmaking System
    /// Aims for 51-55% win rate sweet spot for engagement
    /// </summary>
    public static class Matchmaker
    {
        // Target win rate range for optimal engagement
        private const float TARGET_WIN_RATE_MIN = 0.48f;
        private const float TARGET_WIN_RATE_MAX = 0.55f;

        // Matchmaking parameters
        private const int TROPHY_RANGE_BASE = 100;
        private const int TROPHY_RANGE_EXPANSION_RATE = 50;  // Per second of waiting
        private const float MAX_CARD_LEVEL_DIFFERENCE = 2f;

        [Serializable]
        public class MatchmakingTicket
        {
            public string playerId;
            public int trophies;
            public float averageCardLevel;
            public float recentWinRate;
            public int currentWinStreak;
            public int currentLoseStreak;
            public bool hasActiveContract;
            public float waitTime;
            public DateTime createdAt;

            public MatchmakingTicket(PlayerData player)
            {
                playerId = player.playerId;
                trophies = player.trophies;
                averageCardLevel = CalculateAverageCardLevel(player);
                recentWinRate = player.stats.RecentWinRate;
                currentWinStreak = player.stats.currentWinStreak;
                currentLoseStreak = CalculateLoseStreak(player);
                hasActiveContract = player.creditProfile.activeContractIds.Count > 0;
                waitTime = 0f;
                createdAt = DateTime.UtcNow;
            }

            private static float CalculateAverageCardLevel(PlayerData player)
            {
                var deck = player.GetCurrentDeck();
                if (deck == null || deck.cardIds.Count == 0) return 1f;

                float total = 0f;
                int count = 0;

                foreach (var cardId in deck.cardIds)
                {
                    if (player.cardCollection.TryGetValue(cardId, out var card))
                    {
                        total += card.level;
                        count++;
                    }
                }

                return count > 0 ? total / count : 1f;
            }

            private static int CalculateLoseStreak(PlayerData player)
            {
                int streak = 0;
                for (int i = player.stats.recentMatches.Count - 1; i >= 0; i--)
                {
                    if (player.stats.recentMatches[i] == MatchResult.Loss)
                        streak++;
                    else
                        break;
                }
                return streak;
            }
        }

        [Serializable]
        public class MatchResult
        {
            public MatchmakingTicket player1;
            public MatchmakingTicket player2;
            public float qualityScore;
            public string matchType;  // "RANKED", "CASUAL", "BOT"
        }

        /// <summary>
        /// Find a suitable opponent for the player
        /// In a real implementation, this would query a matchmaking server
        /// </summary>
        public static MatchResult FindMatch(PlayerData player, float maxWaitTime = 30f)
        {
            var ticket = new MatchmakingTicket(player);

            // In a real game, we'd search for real players
            // For now, generate a simulated opponent
            var opponent = GenerateSimulatedOpponent(ticket);

            return new MatchResult
            {
                player1 = ticket,
                player2 = opponent,
                qualityScore = CalculateMatchQuality(ticket, opponent),
                matchType = "BOT"  // Would be "RANKED" with real players
            };
        }

        /// <summary>
        /// Generate a bot opponent calibrated to the player's skill
        /// </summary>
        private static MatchmakingTicket GenerateSimulatedOpponent(MatchmakingTicket player)
        {
            var opponent = new MatchmakingTicket(new PlayerData("bot_" + Guid.NewGuid().ToString(), "Bot"));

            // Base trophy on player's trophies with some variance
            int trophyVariance = UnityEngine.Random.Range(-150, 150);
            opponent.trophies = Mathf.Max(0, player.trophies + trophyVariance);

            // Card level matching
            float levelVariance = UnityEngine.Random.Range(-0.5f, 0.5f);
            opponent.averageCardLevel = Mathf.Max(1, player.averageCardLevel + levelVariance);

            // Adjust difficulty based on player's recent performance
            AdjustOpponentDifficulty(player, opponent);

            return opponent;
        }

        /// <summary>
        /// Implements the "morale boost" and "challenge" mechanics
        /// </summary>
        private static void AdjustOpponentDifficulty(MatchmakingTicket player, MatchmakingTicket opponent)
        {
            // If player is on a losing streak, give them an easier match
            if (player.currentLoseStreak >= 3)
            {
                // Morale boost: slightly weaker opponent
                opponent.trophies = Mathf.Max(0, opponent.trophies - 100);
                opponent.averageCardLevel = Mathf.Max(1, opponent.averageCardLevel - 0.3f);
                opponent.recentWinRate = Mathf.Max(0.3f, player.recentWinRate - 0.1f);
                Debug.Log("Matchmaking: Applying morale boost (easier opponent)");
            }
            // If player is dominating, give them a challenge
            else if (player.currentWinStreak >= 5)
            {
                opponent.trophies += 100;
                opponent.averageCardLevel = Mathf.Min(14, opponent.averageCardLevel + 0.3f);
                opponent.recentWinRate = Mathf.Min(0.7f, player.recentWinRate + 0.1f);
                Debug.Log("Matchmaking: Applying challenge (harder opponent)");
            }
            // If player has active contract, aim for sweaty but fair
            else if (player.hasActiveContract)
            {
                // Try to match closely for exciting games
                opponent.trophies = player.trophies + UnityEngine.Random.Range(-50, 50);
                opponent.averageCardLevel = player.averageCardLevel + UnityEngine.Random.Range(-0.2f, 0.2f);
                Debug.Log("Matchmaking: Contract holder - matching closely");
            }
        }

        private static float CalculateMatchQuality(MatchmakingTicket p1, MatchmakingTicket p2)
        {
            float quality = 1f;

            // Trophy difference penalty
            int trophyDiff = Mathf.Abs(p1.trophies - p2.trophies);
            quality -= trophyDiff / 500f * 0.3f;

            // Card level difference penalty
            float levelDiff = Mathf.Abs(p1.averageCardLevel - p2.averageCardLevel);
            quality -= levelDiff / MAX_CARD_LEVEL_DIFFERENCE * 0.3f;

            // Win rate difference (slight penalty)
            float winRateDiff = Mathf.Abs(p1.recentWinRate - p2.recentWinRate);
            quality -= winRateDiff * 0.2f;

            return Mathf.Clamp01(quality);
        }
    }

    /// <summary>
    /// AI opponent that plays the game
    /// Uses simple heuristics for Phase 1, could be ML-based later
    /// </summary>
    public class AIOpponent
    {
        public enum AIPersonality
        {
            Aggressive,     // Plays cards quickly, pushes hard
            Defensive,      // Waits for opponent, counter-pushes
            Balanced,       // Mix of both
            Cycle           // Plays cheap cards quickly to cycle deck
        }

        private AIPersonality personality;
        private float elixirThreshold;
        private float reactionTime;
        private float mistakeChance;

        public AIOpponent(float skillLevel = 0.5f)
        {
            // Skill level 0-1 affects AI quality
            skillLevel = Mathf.Clamp01(skillLevel);

            // Random personality
            personality = (AIPersonality)UnityEngine.Random.Range(0, 4);

            // Higher skill = lower reaction time, fewer mistakes
            reactionTime = Mathf.Lerp(2f, 0.3f, skillLevel);
            mistakeChance = Mathf.Lerp(0.3f, 0.05f, skillLevel);

            // Elixir threshold based on personality
            switch (personality)
            {
                case AIPersonality.Aggressive:
                    elixirThreshold = 4f;
                    break;
                case AIPersonality.Defensive:
                    elixirThreshold = 8f;
                    break;
                case AIPersonality.Cycle:
                    elixirThreshold = 3f;
                    break;
                default:
                    elixirThreshold = 6f;
                    break;
            }
        }

        /// <summary>
        /// Decide what card to play and where
        /// </summary>
        public AIDecision MakeDecision(Gameplay.BattleState battleState)
        {
            var decision = new AIDecision();
            var aiPlayer = battleState.opponent;

            // Check if we should play anything
            if (aiPlayer.currentElixir < elixirThreshold)
            {
                // Check for emergency defensive play
                if (!ShouldDefend(battleState))
                {
                    decision.shouldPlay = false;
                    return decision;
                }
            }

            // Introduce reaction delay for realism
            if (UnityEngine.Random.value < reactionTime * Time.deltaTime)
            {
                decision.shouldPlay = false;
                return decision;
            }

            // Occasionally make mistakes
            if (UnityEngine.Random.value < mistakeChance)
            {
                decision = MakeRandomPlay(aiPlayer);
                return decision;
            }

            // Smart decision making
            decision = MakeSmartDecision(battleState, aiPlayer);

            return decision;
        }

        private bool ShouldDefend(Gameplay.BattleState battleState)
        {
            // Check if enemy units are close to our towers
            foreach (var unit in battleState.activeUnits)
            {
                if (unit.ownerId == 0)  // Player's unit
                {
                    // Check distance to our towers
                    float distToKing = Vector3.Distance(unit.position, battleState.opponent.kingTower.position);
                    float distToLeft = Vector3.Distance(unit.position, battleState.opponent.leftPrincessTower.position);
                    float distToRight = Vector3.Distance(unit.position, battleState.opponent.rightPrincessTower.position);

                    if (distToKing < 8f || distToLeft < 6f || distToRight < 6f)
                    {
                        return true;
                    }
                }
            }
            return false;
        }

        private AIDecision MakeRandomPlay(Gameplay.BattlePlayer aiPlayer)
        {
            var decision = new AIDecision();

            // Find a playable card
            for (int i = 0; i < aiPlayer.hand.Count; i++)
            {
                if (aiPlayer.currentElixir >= aiPlayer.hand[i].card.elixirCost)
                {
                    decision.shouldPlay = true;
                    decision.handIndex = i;
                    decision.targetPosition = GetRandomPosition(true);
                    break;
                }
            }

            return decision;
        }

        private AIDecision MakeSmartDecision(Gameplay.BattleState battleState, Gameplay.BattlePlayer aiPlayer)
        {
            var decision = new AIDecision();

            // Prioritize based on personality and situation
            bool shouldDefend = ShouldDefend(battleState);

            int bestCardIndex = -1;
            float bestScore = float.MinValue;
            Vector3 bestPosition = Vector3.zero;

            for (int i = 0; i < aiPlayer.hand.Count; i++)
            {
                var handCard = aiPlayer.hand[i];
                if (aiPlayer.currentElixir < handCard.card.elixirCost)
                    continue;

                float score = EvaluateCard(handCard.card, battleState, shouldDefend);

                if (score > bestScore)
                {
                    bestScore = score;
                    bestCardIndex = i;
                    bestPosition = GetBestPosition(handCard.card, battleState, shouldDefend);
                }
            }

            if (bestCardIndex >= 0)
            {
                decision.shouldPlay = true;
                decision.handIndex = bestCardIndex;
                decision.targetPosition = bestPosition;
            }

            return decision;
        }

        private float EvaluateCard(CardDefinition card, Gameplay.BattleState battleState, bool defending)
        {
            float score = 0f;

            // Base value from elixir cost (cheap cards cycle faster)
            if (personality == AIPersonality.Cycle)
            {
                score += (10 - card.elixirCost) * 2;
            }
            else
            {
                score += card.elixirCost;  // More expensive = more impact
            }

            // Defensive value
            if (defending)
            {
                // Prefer high HP units for defense
                score += card.hitpoints / 500f;

                // Buildings are great for defense
                if (card.cardType == CardType.Building)
                    score += 3f;

                // Splash damage good against swarms
                if (card.isAreaDamage)
                    score += 2f;
            }
            else
            {
                // Offensive value
                score += card.damage / 100f;

                // Fast units for offense
                score += card.moveSpeed;

                // Tank units to absorb damage
                if (card.hitpoints > 1000)
                    score += 2f;
            }

            // Personality modifiers
            switch (personality)
            {
                case AIPersonality.Aggressive:
                    score += card.damage / 150f;
                    break;
                case AIPersonality.Defensive:
                    score += card.hitpoints / 600f;
                    break;
            }

            return score;
        }

        private Vector3 GetBestPosition(CardDefinition card, Gameplay.BattleState battleState, bool defending)
        {
            if (defending)
            {
                // Place near threatened tower
                foreach (var unit in battleState.activeUnits)
                {
                    if (unit.ownerId == 0)
                    {
                        // Place between enemy and our tower
                        Vector3 defensePos = new Vector3(
                            unit.position.x,
                            Mathf.Max(unit.position.y + 2f, 4f),
                            0
                        );
                        return defensePos;
                    }
                }
            }

            // Offensive placement
            if (card.cardType == CardType.Building)
            {
                // Place buildings in the middle
                return new Vector3(
                    UnityEngine.Random.Range(-2f, 2f),
                    UnityEngine.Random.Range(5f, 8f),
                    0
                );
            }

            // Regular troops behind the bridge
            Gameplay.Lane lane = UnityEngine.Random.value > 0.5f ? Gameplay.Lane.Left : Gameplay.Lane.Right;
            float x = lane == Gameplay.Lane.Left ? -4f : 4f;

            return new Vector3(x + UnityEngine.Random.Range(-1f, 1f), UnityEngine.Random.Range(3f, 7f), 0);
        }

        private Vector3 GetRandomPosition(bool isOpponent)
        {
            float x = UnityEngine.Random.Range(-6f, 6f);
            float y = isOpponent
                ? UnityEngine.Random.Range(3f, 10f)    // Opponent's side
                : UnityEngine.Random.Range(-10f, -3f); // Player's side

            return new Vector3(x, y, 0);
        }
    }

    public class AIDecision
    {
        public bool shouldPlay;
        public int handIndex;
        public Vector3 targetPosition;
    }
}
