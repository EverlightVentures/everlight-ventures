using System;
using System.Collections.Generic;
using UnityEngine;

namespace BCARDI
{
    public sealed class ArenaManager : MonoBehaviour
    {
        public static ArenaManager Instance { get; private set; }
        public event Action<bool> MatchEnded;

        [Header("Spawns")]
        public Transform[] PlayerLaneSpawns = new Transform[3];
        public Transform[] EnemyLaneSpawns = new Transform[3];

        [Header("Towers")]
        public Tower[] PlayerPrincessTowers = new Tower[3];
        public Tower[] EnemyPrincessTowers = new Tower[3];
        public Tower PlayerQueenTower;
        public Tower EnemyQueenTower;

        [Header("Units")]
        public Unit UnitPrefab;
        public Unit MinionPrefab;

        [Header("Match")]
        public float MatchTimeSeconds = 180f;
        public float OvertimeSeconds = 120f;
        public float QueenBaseHp = 3000f;
        public float QueenScalePerLevel = 0.10f;
        public int TowerLevel = 1;

        private readonly List<Unit> _units = new List<Unit>();
        private float _timeRemaining;
        private bool _overtime;
        private bool _matchEnded;

        private void Awake()
        {
            Instance = this;
        }

        private void Start()
        {
            SetupTowers();
            _timeRemaining = MatchTimeSeconds;
        }

        public void RegisterUnit(Unit unit)
        {
            if (!_units.Contains(unit)) _units.Add(unit);
        }

        public void UnregisterUnit(Unit unit)
        {
            _units.Remove(unit);
        }

        public Unit FindClosestEnemyUnit(Vector3 from, Team team, float range)
        {
            float best = float.MaxValue;
            Unit chosen = null;
            for (int i = 0; i < _units.Count; i++)
            {
                var u = _units[i];
                if (u == null || u.Team == team) continue;
                float dist = Vector3.Distance(from, u.transform.position);
                if (dist <= range && dist < best)
                {
                    best = dist;
                    chosen = u;
                }
            }
            return chosen;
        }

        public Unit FindClosestEnemyUnitInRadius(Vector3 from, Team team, float radius)
        {
            return FindClosestEnemyUnit(from, team, radius);
        }

        public Unit FindClosestAllyUnitInRadius(Vector3 from, Team team, float radius)
        {
            float best = float.MaxValue;
            Unit chosen = null;
            for (int i = 0; i < _units.Count; i++)
            {
                var u = _units[i];
                if (u == null || u.Team != team) continue;
                float dist = Vector3.Distance(from, u.transform.position);
                if (dist <= radius && dist < best)
                {
                    best = dist;
                    chosen = u;
                }
            }
            return chosen;
        }

        public Tower FindLaneTowerTarget(Team team, int laneIndex, bool canTargetQueen)
        {
            Tower[] enemyPrincess = team == Team.Player ? EnemyPrincessTowers : PlayerPrincessTowers;
            Tower enemyQueen = team == Team.Player ? EnemyQueenTower : PlayerQueenTower;

            if (enemyPrincess[laneIndex] != null && enemyPrincess[laneIndex].CurrentHp > 0f)
            {
                return enemyPrincess[laneIndex];
            }

            if (canTargetQueen && enemyQueen != null && enemyQueen.CurrentHp > 0f)
            {
                return enemyQueen;
            }

            return null;
        }

        public Tower FindLaneEnemyTowerForDisable(Team team, int laneIndex)
        {
            Tower[] enemyPrincess = team == Team.Player ? EnemyPrincessTowers : PlayerPrincessTowers;
            Tower enemyQueen = team == Team.Player ? EnemyQueenTower : PlayerQueenTower;

            if (enemyPrincess[laneIndex] != null && enemyPrincess[laneIndex].CurrentHp > 0f)
            {
                return enemyPrincess[laneIndex];
            }
            return enemyQueen;
        }

        public CardAbilityRotation GetAbilityRotation(string cardName)
        {
            if (GameConfig.Instance == null) return null;
            GameConfig.Instance.AbilityRotations.TryGetValue(cardName, out var rotation);
            return rotation;
        }

        public void SpawnUnit(string cardName, Team team, int laneIndex)
        {
            if (GameConfig.Instance == null || UnitPrefab == null) return;
            if (!GameConfig.Instance.CardsByName.TryGetValue(cardName, out var card)) return;
            var spawn = team == Team.Player ? PlayerLaneSpawns[laneIndex] : EnemyLaneSpawns[laneIndex];
            var unit = Instantiate(UnitPrefab, spawn.position, Quaternion.identity);
            unit.Initialize(card, team, laneIndex);
        }

        public void SpawnMinion(Team team, int laneIndex, Vector3 origin, int count)
        {
            if (MinionPrefab == null) return;
            for (int i = 0; i < count; i++)
            {
                var offset = new Vector3(0.4f * i, 0f, 0f);
                var minion = Instantiate(MinionPrefab, origin + offset, Quaternion.identity);
                var card = new CardDefinition
                {
                    Name = "Minion",
                    Hp = 200f,
                    Damage = 30f,
                    AttackSpeed = 1.0f,
                    MoveSpeed = 1.2f,
                    Range = 1f,
                    QueenTarget = false
                };
                minion.Initialize(card, team, laneIndex);
            }
        }

        public Vector3 GetLaneForwardPoint(Team team, int laneIndex, float distance)
        {
            var spawn = team == Team.Player ? PlayerLaneSpawns[laneIndex] : EnemyLaneSpawns[laneIndex];
            Vector3 forward = team == Team.Player ? Vector3.forward : Vector3.back;
            return spawn.position + forward * distance;
        }

        private void SetupTowers()
        {
            float qhp = QueenBaseHp * (1f + TowerLevel * QueenScalePerLevel);
            float php = qhp / 3f;

            if (PlayerQueenTower != null) PlayerQueenTower.SetHealth(qhp);
            if (EnemyQueenTower != null) EnemyQueenTower.SetHealth(qhp);

            for (int i = 0; i < 3; i++)
            {
                if (PlayerPrincessTowers[i] != null) PlayerPrincessTowers[i].SetHealth(php);
                if (EnemyPrincessTowers[i] != null) EnemyPrincessTowers[i].SetHealth(php);
            }

            UpdateQueenVulnerability();
        }

        private void UpdateQueenVulnerability()
        {
            bool playerPrincessAlive = false;
            bool enemyPrincessAlive = false;

            for (int i = 0; i < 3; i++)
            {
                if (PlayerPrincessTowers[i] != null && PlayerPrincessTowers[i].CurrentHp > 0f) playerPrincessAlive = true;
                if (EnemyPrincessTowers[i] != null && EnemyPrincessTowers[i].CurrentHp > 0f) enemyPrincessAlive = true;
            }

            if (PlayerQueenTower != null) PlayerQueenTower.SetInvulnerable(playerPrincessAlive);
            if (EnemyQueenTower != null) EnemyQueenTower.SetInvulnerable(enemyPrincessAlive);
        }

        private void Update()
        {
            if (_matchEnded) return;

            _timeRemaining -= Time.deltaTime;
            UpdateQueenVulnerability();

            if (_timeRemaining <= 0f)
            {
                if (!_overtime)
                {
                    _overtime = true;
                    _timeRemaining = OvertimeSeconds;
                }
                else
                {
                    EndMatchByHealth();
                }
            }

            if (PlayerQueenTower != null && PlayerQueenTower.CurrentHp <= 0f) EndMatch(false);
            if (EnemyQueenTower != null && EnemyQueenTower.CurrentHp <= 0f) EndMatch(true);
        }

        private void EndMatchByHealth()
        {
            int playerTowers = CountTowers(PlayerPrincessTowers) + (PlayerQueenTower != null && PlayerQueenTower.CurrentHp > 0f ? 1 : 0);
            int enemyTowers = CountTowers(EnemyPrincessTowers) + (EnemyQueenTower != null && EnemyQueenTower.CurrentHp > 0f ? 1 : 0);

            if (playerTowers != enemyTowers)
            {
                EndMatch(playerTowers > enemyTowers);
                return;
            }

            float playerHp = SumTowerHp(PlayerPrincessTowers) + (PlayerQueenTower != null ? PlayerQueenTower.CurrentHp : 0f);
            float enemyHp = SumTowerHp(EnemyPrincessTowers) + (EnemyQueenTower != null ? EnemyQueenTower.CurrentHp : 0f);
            EndMatch(playerHp >= enemyHp);
        }

        private int CountTowers(Tower[] towers)
        {
            int count = 0;
            for (int i = 0; i < towers.Length; i++)
            {
                if (towers[i] != null && towers[i].CurrentHp > 0f) count++;
            }
            return count;
        }

        private float SumTowerHp(Tower[] towers)
        {
            float sum = 0f;
            for (int i = 0; i < towers.Length; i++)
            {
                if (towers[i] != null) sum += Mathf.Max(0f, towers[i].CurrentHp);
            }
            return sum;
        }

        private void EndMatch(bool playerWon)
        {
            _matchEnded = true;
            Debug.Log(playerWon ? "Player wins" : "Enemy wins");
            if (ProgressionManager.Instance != null)
            {
                ProgressionManager.Instance.ApplyMatchResult(playerWon);
            }
            MatchEnded?.Invoke(playerWon);
        }
    }
}
