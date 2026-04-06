
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ArenaAdvance.Gameplay;
using ArenaAdvance.ScriptableObjects;
using ArenaAdvance.Data;

namespace ArenaAdvance.Managers
{
    public class BattleManager : MonoBehaviour
    {
        public static BattleManager Instance { get; private set; }

        [Header("References")]
        [SerializeField] private Transform arenaRoot;
        [SerializeField] private Transform unitsParent;

        [Header("Arena Config")]
        [SerializeField] private float arenaWidth = 18f;
        [SerializeField] private float arenaHeight = 30f;
        [SerializeField] private float bridgeY = 0f;
        [SerializeField] private float leftBridgeX = -4f;
        [SerializeField] private float rightBridgeX = 4f;
        [SerializeField] private float playerSpawnMinY = -14f;
        [SerializeField] private float playerSpawnMaxY = -2f;
        [SerializeField] private float opponentSpawnMinY = 2f;
        [SerializeField] private float opponentSpawnMaxY = 14f;

        private BattleState battleState;
        private bool isPaused;

        // Events
        public event System.Action<BattlePhase> OnPhaseChanged;
        public event System.Action<int, int> OnCrownsChanged;
        public event System.Action<Tower, int> OnTowerDamaged;
        public event System.Action<Tower> OnTowerDestroyed;
        public event System.Action<BattleUnit> OnUnitSpawned;
        public event System.Action<BattleUnit> OnUnitDied;
        public event System.Action<int, float> OnElixirChanged;

        public BattleState State => battleState;
        public bool IsPaused => isPaused;

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

        public void InitializeBattle(BattleState state)
        {
            battleState = state;
            isPaused = false;
            Debug.Log("Battle initialized");
        }

        public void SetPaused(bool paused)
        {
            isPaused = paused;
        }

        private void Update()
        {
            if (battleState == null || isPaused) return;
            if (battleState.phase == BattlePhase.Ended) return;

            float deltaTime = Time.deltaTime;

            // Update timers
            BattlePhase previousPhase = battleState.phase;
            battleState.UpdateTimers(deltaTime);

            if (battleState.phase != previousPhase)
            {
                OnPhaseChanged?.Invoke(battleState.phase);

                if (battleState.phase == BattlePhase.Ended)
                {
                    EndBattle();
                }
            }

            if (battleState.phase == BattlePhase.Countdown) return;

            // Update game systems
            UpdateElixir(deltaTime);
            UpdateUnits(deltaTime);
            UpdateTowerCombat(deltaTime);
        }

        private void UpdateElixir(float deltaTime)
        {
            bool isDouble = battleState.IsDoubleElixir;

            float prevPlayer = battleState.player.currentElixir;
            float prevOpponent = battleState.opponent.currentElixir;

            battleState.player.UpdateElixir(deltaTime, isDouble);
            battleState.opponent.UpdateElixir(deltaTime, isDouble);

            if (Mathf.FloorToInt(prevPlayer) != Mathf.FloorToInt(battleState.player.currentElixir))
            {
                OnElixirChanged?.Invoke(0, battleState.player.currentElixir);
            }
        }

        #region Card Playing

        public bool CanPlayCard(int playerId, int handIndex)
        {
            BattlePlayer player = playerId == 0 ? battleState.player : battleState.opponent;
            return player.CanPlayCard(handIndex);
        }

        public bool TryPlayCard(int playerId, int handIndex, Vector3 worldPosition)
        {
            BattlePlayer player = playerId == 0 ? battleState.player : battleState.opponent;

            // Validate position
            if (!IsValidSpawnPosition(playerId, worldPosition))
            {
                Debug.Log("Invalid spawn position");
                return false;
            }

            // Check elixir
            if (!player.CanPlayCard(handIndex))
            {
                Debug.Log("Not enough elixir");
                return false;
            }

            // Get card and play it
            CardDefinition card = player.PlayCard(handIndex);
            if (card == null) return false;

            // Spawn unit(s)
            Lane lane = worldPosition.x < 0 ? Lane.Left : Lane.Right;
            SpawnUnit(card, playerId, player.cardLevels.GetValueOrDefault(card.cardId, 1), worldPosition, lane);

            OnElixirChanged?.Invoke(playerId, player.currentElixir);

            return true;
        }

        private bool IsValidSpawnPosition(int playerId, Vector3 position)
        {
            // Check arena bounds
            if (Mathf.Abs(position.x) > arenaWidth / 2) return false;

            // Check spawn zone
            if (playerId == 0)
            {
                // Player can spawn on their side
                return position.y >= playerSpawnMinY && position.y <= playerSpawnMaxY;
            }
            else
            {
                // Opponent spawns on their side
                return position.y >= opponentSpawnMinY && position.y <= opponentSpawnMaxY;
            }
        }

        #endregion

        #region Unit Management

        private void SpawnUnit(CardDefinition card, int ownerId, int level, Vector3 position, Lane lane)
        {
            // For cards that spawn multiple units
            int spawnCount = Mathf.Max(1, card.spawnCount);

            for (int i = 0; i < spawnCount; i++)
            {
                Vector3 spawnPos = position;
                if (spawnCount > 1)
                {
                    // Spread multiple units
                    float offset = (i - (spawnCount - 1) / 2f) * 0.5f;
                    spawnPos += new Vector3(offset, 0, 0);
                }

                BattleUnit unit = new BattleUnit(card, ownerId, level, spawnPos, lane);
                battleState.activeUnits.Add(unit);

                // Instantiate visual
                if (card.unitPrefab != null)
                {
                    GameObject unitObj = Instantiate(card.unitPrefab, spawnPos, Quaternion.identity, unitsParent);
                    unit.gameObject = unitObj;

                    var behaviour = unitObj.GetComponent<UnitBehaviour>();
                    if (behaviour != null)
                    {
                        behaviour.Initialize(unit);
                    }
                }

                OnUnitSpawned?.Invoke(unit);
            }
        }

        private void UpdateUnits(float deltaTime)
        {
            List<BattleUnit> unitsToRemove = new List<BattleUnit>();

            foreach (var unit in battleState.activeUnits)
            {
                if (!unit.isAlive)
                {
                    unitsToRemove.Add(unit);
                    continue;
                }

                // Update attack cooldown
                if (unit.attackCooldown > 0)
                {
                    unit.attackCooldown -= deltaTime;
                }

                // Find target
                UpdateUnitTarget(unit);

                // Move or attack
                if (unit.targetUnit != null || unit.targetTower != null)
                {
                    float distToTarget = GetDistanceToTarget(unit);

                    if (distToTarget <= unit.cardDef.range)
                    {
                        // In range - attack
                        TryAttack(unit);
                    }
                    else
                    {
                        // Move towards target
                        MoveUnit(unit, deltaTime);
                    }
                }
                else
                {
                    // No target - move towards enemy side
                    MoveTowardsEnemySide(unit, deltaTime);
                }
            }

            // Remove dead units
            foreach (var unit in unitsToRemove)
            {
                OnUnitDied?.Invoke(unit);
                if (unit.gameObject != null)
                {
                    Destroy(unit.gameObject);
                }
                battleState.activeUnits.Remove(unit);
            }
        }

        private void UpdateUnitTarget(BattleUnit unit)
        {
            BattlePlayer enemyPlayer = unit.ownerId == 0 ? battleState.opponent : battleState.player;

            // Reset targets
            unit.targetUnit = null;
            unit.targetTower = null;

            float closestDist = float.MaxValue;

            // Check enemy units
            foreach (var otherUnit in battleState.activeUnits)
            {
                if (otherUnit.ownerId == unit.ownerId) continue;
                if (!otherUnit.isAlive) continue;

                // Check targeting rules
                if (!CanTarget(unit, otherUnit)) continue;

                float dist = Vector3.Distance(unit.position, otherUnit.position);
                if (dist < closestDist)
                {
                    closestDist = dist;
                    unit.targetUnit = otherUnit;
                }
            }

            // If no unit target, check towers
            if (unit.targetUnit == null)
            {
                // Target nearest non-destroyed tower
                Tower[] towers = new Tower[]
                {
                    enemyPlayer.leftPrincessTower,
                    enemyPlayer.rightPrincessTower,
                    enemyPlayer.kingTower
                };

                foreach (var tower in towers)
                {
                    if (tower.isDestroyed) continue;

                    // King tower only targetable if princess towers down or directly attacked
                    if (tower.type == TowerType.King)
                    {
                        if (!enemyPlayer.leftPrincessTower.isDestroyed &&
                            !enemyPlayer.rightPrincessTower.isDestroyed)
                        {
                            // Only target king if in same lane as destroyed princess
                            continue;
                        }
                    }

                    float dist = Vector3.Distance(unit.position, tower.position);
                    if (dist < closestDist)
                    {
                        closestDist = dist;
                        unit.targetTower = tower;
                        unit.targetUnit = null;
                    }
                }
            }
        }

        private bool CanTarget(BattleUnit attacker, BattleUnit target)
        {
            // Air targeting
            if (target.cardDef.isFlying && !attacker.cardDef.canTargetAir)
            {
                return false;
            }

            // Building targeting
            if (attacker.cardDef.targetType == TargetType.Buildings)
            {
                return false;  // Can only target buildings
            }

            return true;
        }

        private float GetDistanceToTarget(BattleUnit unit)
        {
            if (unit.targetUnit != null)
            {
                return Vector3.Distance(unit.position, unit.targetUnit.position);
            }
            if (unit.targetTower != null)
            {
                return Vector3.Distance(unit.position, unit.targetTower.position);
            }
            return float.MaxValue;
        }

        private void MoveUnit(BattleUnit unit, float deltaTime)
        {
            Vector3 targetPos;

            if (unit.targetUnit != null)
            {
                targetPos = unit.targetUnit.position;
            }
            else if (unit.targetTower != null)
            {
                targetPos = unit.targetTower.position;
            }
            else
            {
                return;
            }

            Vector3 direction = (targetPos - unit.position).normalized;
            float moveAmount = unit.cardDef.moveSpeed * deltaTime;

            unit.position += direction * moveAmount;

            if (unit.gameObject != null)
            {
                unit.gameObject.transform.position = unit.position;
            }
        }

        private void MoveTowardsEnemySide(BattleUnit unit, float deltaTime)
        {
            // Move towards enemy king tower
            float targetY = unit.ownerId == 0 ? 12f : -12f;
            Vector3 targetPos = new Vector3(unit.position.x, targetY, unit.position.z);

            Vector3 direction = (targetPos - unit.position).normalized;
            float moveAmount = unit.cardDef.moveSpeed * deltaTime;

            unit.position += direction * moveAmount;

            if (unit.gameObject != null)
            {
                unit.gameObject.transform.position = unit.position;
            }
        }

        private void TryAttack(BattleUnit unit)
        {
            if (unit.attackCooldown > 0) return;

            int damage = unit.damage;

            if (unit.targetUnit != null)
            {
                // Area damage
                if (unit.cardDef.isAreaDamage)
                {
                    foreach (var otherUnit in battleState.activeUnits)
                    {
                        if (otherUnit.ownerId == unit.ownerId) continue;

                        float dist = Vector3.Distance(unit.targetUnit.position, otherUnit.position);
                        if (dist <= unit.cardDef.areaDamageRadius)
                        {
                            otherUnit.TakeDamage(damage);
                        }
                    }
                }
                else
                {
                    unit.targetUnit.TakeDamage(damage);
                }
            }
            else if (unit.targetTower != null)
            {
                DamageTower(unit.targetTower, damage, unit.ownerId);
            }

            // Reset cooldown
            unit.attackCooldown = 1f / unit.cardDef.attackSpeed;
        }

        #endregion

        #region Tower Combat

        private void UpdateTowerCombat(float deltaTime)
        {
            // Player towers attack opponent units
            UpdateTowerAttack(battleState.player.leftPrincessTower, 0, deltaTime);
            UpdateTowerAttack(battleState.player.rightPrincessTower, 0, deltaTime);
            if (battleState.player.kingTower.isActivated)
            {
                UpdateTowerAttack(battleState.player.kingTower, 0, deltaTime);
            }

            // Opponent towers attack player units
            UpdateTowerAttack(battleState.opponent.leftPrincessTower, 1, deltaTime);
            UpdateTowerAttack(battleState.opponent.rightPrincessTower, 1, deltaTime);
            if (battleState.opponent.kingTower.isActivated)
            {
                UpdateTowerAttack(battleState.opponent.kingTower, 1, deltaTime);
            }
        }

        private void UpdateTowerAttack(Tower tower, int ownerPlayerId, float deltaTime)
        {
            if (tower.isDestroyed) return;

            // Find closest enemy unit in range
            BattleUnit target = null;
            float closestDist = tower.range;

            foreach (var unit in battleState.activeUnits)
            {
                if (unit.ownerId == ownerPlayerId) continue;

                float dist = Vector3.Distance(tower.position, unit.position);
                if (dist < closestDist)
                {
                    closestDist = dist;
                    target = unit;
                }
            }

            // Attack if target found
            // (Simplified - would need cooldown tracking per tower)
            if (target != null)
            {
                target.TakeDamage(Mathf.RoundToInt(tower.damage * deltaTime * tower.attackSpeed));
            }
        }

        private void DamageTower(Tower tower, int damage, int attackerPlayerId)
        {
            if (tower.isDestroyed) return;

            tower.TakeDamage(damage);
            OnTowerDamaged?.Invoke(tower, damage);

            // Activate king tower when princess is hit
            if (tower.type == TowerType.Princess)
            {
                BattlePlayer towerOwner = attackerPlayerId == 0 ? battleState.opponent : battleState.player;
                towerOwner.kingTower.Activate();
            }

            if (tower.isDestroyed)
            {
                OnTowerDestroyed?.Invoke(tower);
                battleState.OnTowerDestroyed(attackerPlayerId, tower.type);

                int playerCrowns = battleState.playerCrowns;
                int opponentCrowns = battleState.opponentCrowns;
                OnCrownsChanged?.Invoke(playerCrowns, opponentCrowns);
            }
        }

        #endregion

        private void EndBattle()
        {
            Debug.Log($"Battle ended! Winner: {battleState.winnerId}, " +
            $"Crowns: {battleState.playerCrowns}-{battleState.opponentCrowns}");

            // Cleanup units
            foreach (var unit in battleState.activeUnits)
            {
                if (unit.gameObject != null)
                {
                    Destroy(unit.gameObject);
                }
            }
            battleState.activeUnits.Clear();

            // Notify GameManager
            GameManager.Instance?.EndBattle();
        }

        public void Surrender()
        {
            if (battleState == null) return;

            // Force opponent win
            battleState.opponent.crownsEarned = 3;
            battleState.opponentCrowns = 3;

            // End the battle
            EndBattle();
        }
    }
}
