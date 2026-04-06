
using System;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Data;
using ArenaAdvance.ScriptableObjects;

namespace ArenaAdvance.Gameplay
{
    public enum BattlePhase
    {
        Countdown,
        Regular,
        DoubleElixir,
        SuddenDeath,
        Overtime,
        Ended
    }

    public enum Lane
    {
        Left,
        Right,
        Center  // For king tower area
    }

    public enum TowerType
    {
        Princess,
        King
    }

    [Serializable]
    public class Tower
    {
        public TowerType type;
        public Lane lane;
        public int maxHealth;
        public int currentHealth;
        public int damage;
        public float attackSpeed;
        public float range;
        public bool isDestroyed;
        public bool isActivated;  // King tower starts inactive

        public Vector3 position;
        public GameObject gameObject;

        public Tower(TowerType towerType, Lane towerLane, int health, int dmg)
        {
            type = towerType;
            lane = towerLane;
            maxHealth = health;
            currentHealth = health;
            damage = dmg;
            attackSpeed = 0.8f;
            range = towerType == TowerType.King ? 7f : 6f;
            isDestroyed = false;
            isActivated = towerType == TowerType.Princess; // Princess towers start active
        }

        public float HealthPercent => (float)currentHealth / maxHealth;

        public void TakeDamage(int amount)
        {
            currentHealth = Mathf.Max(0, currentHealth - amount);
            if (currentHealth <= 0)
            {
                isDestroyed = true;
            }
        }

        public void Activate()
        {
            isActivated = true;
        }
    }

    [Serializable]
    public class BattleUnit
    {
        public string unitId;
        public CardDefinition cardDef;
        public int ownerId;  // 0 = player, 1 = opponent
        public int level;

        public int currentHealth;
        public int maxHealth;
        public int damage;

        public Vector3 position;
        public Vector3 targetPosition;
        public Lane currentLane;

        public float attackCooldown;
        public BattleUnit targetUnit;
        public Tower targetTower;

        public bool isAlive => currentHealth > 0;
        public GameObject gameObject;

        public BattleUnit(CardDefinition card, int owner, int cardLevel, Vector3 spawnPos, Lane lane)
        {
            unitId = Guid.NewGuid().ToString();
            cardDef = card;
            ownerId = owner;
            level = cardLevel;
            position = spawnPos;
            currentLane = lane;

            maxHealth = card.GetHitpointsAtLevel(level);
            currentHealth = maxHealth;
            damage = card.GetDamageAtLevel(level);
        }

        public void TakeDamage(int amount)
        {
            currentHealth = Mathf.Max(0, currentHealth - amount);
        }
    }

    [Serializable]
    public class HandCard
    {
        public CardDefinition card;
        public int level;
        public bool isPlayable;

        public HandCard(CardDefinition cardDef, int cardLevel)
        {
            card = cardDef;
            level = cardLevel;
            isPlayable = true;
        }
    }

    [Serializable]
    public class BattlePlayer
    {
        public int playerId;  // 0 or 1
        public string displayName;

        // Elixir
        public float currentElixir;
        public float maxElixir = 10f;
        public float elixirRegenRate = 1f;  // Per second (doubles in overtime)

        // Deck & Hand
        public List<CardDefinition> deck = new List<CardDefinition>();
        public Dictionary<string, int> cardLevels = new Dictionary<string, int>();
        public List<HandCard> hand = new List<HandCard>();
        public Queue<CardDefinition> drawPile = new Queue<CardDefinition>();
        public CardDefinition nextCard;

        // Towers
        public Tower kingTower;
        public Tower leftPrincessTower;
        public Tower rightPrincessTower;

        // Stats
        public int crownsEarned;
        public int towersDestroyed;
        public int elixirSpent;
        public int unitsDeployed;

        public BattlePlayer(int id, string name)
        {
            playerId = id;
            displayName = name;
            currentElixir = 5f;  // Start with 5 elixir
        }

        public void InitializeTowers(int towerHealth, int towerDamage, bool isTopSide)
        {
            float yOffset = isTopSide ? 10f : -10f;

            kingTower = new Tower(TowerType.King, Lane.Center, towerHealth, towerDamage);
            kingTower.position = new Vector3(0, yOffset * 1.5f, 0);

            leftPrincessTower = new Tower(TowerType.Princess, Lane.Left, (int)(towerHealth * 0.6f), (int)(towerDamage * 0.8f));
            leftPrincessTower.position = new Vector3(-4f, yOffset, 0);

            rightPrincessTower = new Tower(TowerType.Princess, Lane.Right, (int)(towerHealth * 0.6f), (int)(towerDamage * 0.8f));
            rightPrincessTower.position = new Vector3(4f, yOffset, 0);
        }

        public void SetupDeck(List<CardDefinition> playerDeck, Dictionary<string, int> levels)
        {
            deck = new List<CardDefinition>(playerDeck);
            cardLevels = new Dictionary<string, int>(levels);

            // Shuffle deck
            ShuffleDeck();

            // Draw initial hand (4 cards)
            for (int i = 0; i < 4 && drawPile.Count > 0; i++)
            {
                var card = drawPile.Dequeue();
                int level = cardLevels.ContainsKey(card.cardId) ? cardLevels[card.cardId] : 1;
                hand.Add(new HandCard(card, level));
            }

            // Set next card
            if (drawPile.Count > 0)
            {
                nextCard = drawPile.Dequeue();
            }
        }

        private void ShuffleDeck()
        {
            var shuffled = new List<CardDefinition>(deck);
            for (int i = shuffled.Count - 1; i > 0; i--)
            {
                int j = UnityEngine.Random.Range(0, i + 1);
                var temp = shuffled[i];
                shuffled[i] = shuffled[j];
                shuffled[j] = temp;
            }

            drawPile = new Queue<CardDefinition>();
            foreach (var card in shuffled)
            {
                drawPile.Enqueue(card);
            }
        }

        public bool CanPlayCard(int handIndex)
        {
            if (handIndex < 0 || handIndex >= hand.Count) return false;
            return currentElixir >= hand[handIndex].card.elixirCost;
        }

        public CardDefinition PlayCard(int handIndex)
        {
            if (!CanPlayCard(handIndex)) return null;

            var playedCard = hand[handIndex];
            currentElixir -= playedCard.card.elixirCost;
            elixirSpent += playedCard.card.elixirCost;
            unitsDeployed++;

            // Remove from hand
            hand.RemoveAt(handIndex);

            // Add next card to hand
            if (nextCard != null)
            {
                int level = cardLevels.ContainsKey(nextCard.cardId) ? cardLevels[nextCard.cardId] : 1;
                hand.Add(new HandCard(nextCard, level));
                nextCard = null;
            }

            // Draw new next card
            if (drawPile.Count > 0)
            {
                nextCard = drawPile.Dequeue();
            }
            else
            {
                // Reshuffle played cards back (cycle through deck)
                ShuffleDeck();
                if (drawPile.Count > 0)
                {
                    nextCard = drawPile.Dequeue();
                }
            }

            return playedCard.card;
        }

        public void UpdateElixir(float deltaTime, bool isDoubleElixir)
        {
            float rate = isDoubleElixir ? elixirRegenRate * 2f : elixirRegenRate;
            currentElixir = Mathf.Min(maxElixir, currentElixir + rate * deltaTime);
        }

        public int GetCrownsEarned()
        {
            // Crowns are earned by destroying opponent towers, tracked externally
            return crownsEarned;
        }

        public bool HasLost()
        {
            return kingTower.isDestroyed;
        }

        public int GetRemainingTowerCount()
        {
            int count = 0;
            if (!kingTower.isDestroyed) count++;
            if (!leftPrincessTower.isDestroyed) count++;
            if (!rightPrincessTower.isDestroyed) count++;
            return count;
        }

        public int GetTotalTowerHealth()
        {
            int health = 0;
            if (!kingTower.isDestroyed) health += kingTower.currentHealth;
            if (!leftPrincessTower.isDestroyed) health += leftPrincessTower.currentHealth;
            if (!rightPrincessTower.isDestroyed) health += rightPrincessTower.currentHealth;
            return health;
        }
    }

    [Serializable]
    public class BattleState
    {
        [Header("Match Info")]
        public string matchId;
        public BattlePhase phase;
        public float matchTimer;
        public float phaseTimer;

        // Time constants
        public const float REGULAR_TIME = 120f;      // 2 minutes
        public const float DOUBLE_ELIXIR_TIME = 60f; // 1 minute
        public const float OVERTIME_TIME = 60f;      // 1 minute sudden death
        public const float COUNTDOWN_TIME = 3f;

        [Header("Players")]
        public BattlePlayer player;
        public BattlePlayer opponent;

        [Header("Units")]
        public List<BattleUnit> activeUnits = new List<BattleUnit>();

        [Header("Result")]
        public int winnerId = -1;  // -1 = ongoing, 0 = player, 1 = opponent, 2 = draw
        public int playerCrowns;
        public int opponentCrowns;

        public bool IsDoubleElixir => phase == BattlePhase.DoubleElixir || phase == BattlePhase.Overtime;

        public BattleState()
        {
            matchId = Guid.NewGuid().ToString();
            phase = BattlePhase.Countdown;
            matchTimer = 0f;
            phaseTimer = COUNTDOWN_TIME;
        }

        public void Initialize(string playerName, string opponentName, int towerHealth, int towerDamage)
        {
            player = new BattlePlayer(0, playerName);
            opponent = new BattlePlayer(1, opponentName);

            player.InitializeTowers(towerHealth, towerDamage, false);  // Bottom
            opponent.InitializeTowers(towerHealth, towerDamage, true); // Top
        }

        public void UpdateTimers(float deltaTime)
        {
            if (phase == BattlePhase.Ended) return;

            phaseTimer -= deltaTime;

            switch (phase)
            {
                case BattlePhase.Countdown:
                    if (phaseTimer <= 0)
                    {
                        phase = BattlePhase.Regular;
                        phaseTimer = REGULAR_TIME;
                    }
                    break;

                case BattlePhase.Regular:
                    matchTimer += deltaTime;
                    if (phaseTimer <= 0)
                    {
                        phase = BattlePhase.DoubleElixir;
                        phaseTimer = DOUBLE_ELIXIR_TIME;
                    }
                    break;

                case BattlePhase.DoubleElixir:
                    matchTimer += deltaTime;
                    if (phaseTimer <= 0)
                    {
                        // Check if tie
                        if (playerCrowns == opponentCrowns)
                        {
                            phase = BattlePhase.Overtime;
                            phaseTimer = OVERTIME_TIME;
                        }
                        else
                        {
                            EndMatch();
                        }
                    }
                    break;

                case BattlePhase.Overtime:
                    matchTimer += deltaTime;
                    // Overtime ends on first crown or time
                    if (phaseTimer <= 0)
                    {
                        EndMatch();
                    }
                    break;
            }
        }

        public void OnTowerDestroyed(int destroyerPlayerId, TowerType towerType)
        {
            if (destroyerPlayerId == 0)
            {
                playerCrowns++;
                player.crownsEarned++;

                // Activate opponent's king if princess destroyed
                if (towerType == TowerType.Princess)
                {
                    opponent.kingTower.Activate();
                }

                // 3-crown win
                if (opponent.HasLost())
                {
                    playerCrowns = 3;
                    EndMatch();
                }
            }
            else
            {
                opponentCrowns++;
                opponent.crownsEarned++;

                if (towerType == TowerType.Princess)
                {
                    player.kingTower.Activate();
                }

                if (player.HasLost())
                {
                    opponentCrowns = 3;
                    EndMatch();
                }
            }

            // Check for overtime win
            if (phase == BattlePhase.Overtime)
            {
                EndMatch();
            }
        }

        private void EndMatch()
        {
            phase = BattlePhase.Ended;

            if (player.HasLost())
            {
                winnerId = 1;
            }
            else if (opponent.HasLost())
            {
                winnerId = 0;
            }
            else if (playerCrowns > opponentCrowns)
            {
                winnerId = 0;
            }
            else if (opponentCrowns > playerCrowns)
            {
                winnerId = 1;
            }
            else
            {
                // Tiebreaker: tower health percentage
                float playerHealthPct = (float)player.GetTotalTowerHealth() /
                (player.kingTower.maxHealth + player.leftPrincessTower.maxHealth + player.rightPrincessTower.maxHealth);
                float opponentHealthPct = (float)opponent.GetTotalTowerHealth() /
                (opponent.kingTower.maxHealth + opponent.leftPrincessTower.maxHealth + opponent.rightPrincessTower.maxHealth);

                if (playerHealthPct > opponentHealthPct)
                    winnerId = 0;
                else if (opponentHealthPct > playerHealthPct)
                    winnerId = 1;
                else
                    winnerId = 2; // True draw
            }
        }

        public MatchResult GetResultForPlayer()
        {
            if (winnerId == 0) return MatchResult.Win;
            if (winnerId == 1) return MatchResult.Loss;
            return MatchResult.Draw;
        }

        public string GetTimeDisplay()
        {
            int minutes = (int)(phaseTimer / 60);
            int seconds = (int)(phaseTimer % 60);
            return $"{minutes}:{seconds:D2}";
        }
    }
}
