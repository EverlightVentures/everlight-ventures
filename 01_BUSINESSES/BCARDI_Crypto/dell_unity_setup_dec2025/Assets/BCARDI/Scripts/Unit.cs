using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace BCARDI
{
    public sealed class Unit : MonoBehaviour
    {
        public Team Team;
        public int LaneIndex;
        public CardDefinition Card;

        public float CurrentHp;
        public float Damage;
        public float AttackSpeed;
        public float MoveSpeed;
        public float Range;

        private float _attackTimer;
        private int _rotationIndex;
        private Coroutine _abilityRoutine;
        private readonly List<StatusEffect> _effects = new List<StatusEffect>();

        public void Initialize(CardDefinition card, Team team, int laneIndex)
        {
            Card = card;
            Team = team;
            LaneIndex = laneIndex;

            CurrentHp = card.Hp;
            Damage = card.Damage;
            AttackSpeed = card.AttackSpeed;
            MoveSpeed = card.MoveSpeed;
            Range = card.Range;

            if (_abilityRoutine != null) StopCoroutine(_abilityRoutine);
            _abilityRoutine = StartCoroutine(AbilityLoop());
            ArenaManager.Instance.RegisterUnit(this);
        }

        public void TakeDamage(float amount)
        {
            if (HasEffect(StatusEffectType.Evasion, out float evade) && Random.value < evade)
            {
                return;
            }
            CurrentHp -= amount;
            if (CurrentHp <= 0f)
            {
                Destroy(gameObject);
            }
        }

        public void Heal(float amount)
        {
            CurrentHp = Mathf.Min(Card.Hp, CurrentHp + amount);
        }

        private IEnumerator AbilityLoop()
        {
            var rotations = ArenaManager.Instance.GetAbilityRotation(Card.Name);
            if (rotations == null || rotations.Steps.Count == 0) yield break;

            while (true)
            {
                var step = rotations.Steps[_rotationIndex % rotations.Steps.Count];
                _rotationIndex++;
                if (!HasEffect(StatusEffectType.Silence, out _))
                {
                    ApplyAbility(step);
                }
                yield return new WaitForSeconds(Mathf.Max(0.5f, step.Cooldown));
            }
        }

        private void ApplyAbility(AbilityStep step)
        {
            if (HasEffect(StatusEffectType.Stun, out _)) return;

            switch (step.Type)
            {
                case "shield":
                    StartCoroutine(TempShield(step));
                    break;
                case "buff":
                    StartCoroutine(TempDamageBuff(step));
                    break;
                case "spawn":
                    ArenaManager.Instance.SpawnMinion(Team, LaneIndex, transform.position, step.Count);
                    break;
                case "slow":
                    ApplyStatusToNearestEnemy(StatusEffectType.Slow, step.Duration, step.Value, step.Radius);
                    break;
                case "stun":
                    ApplyStatusToNearestEnemy(StatusEffectType.Stun, step.Duration, 0f, step.Radius);
                    break;
                case "silence":
                case "disable_tower":
                    ApplySilenceOrDisable(step);
                    break;
                case "root":
                    ApplyStatusToNearestEnemy(StatusEffectType.Root, step.Duration, 0f, step.Radius);
                    break;
                case "blind":
                    ApplyStatusToNearestEnemy(StatusEffectType.Evasion, step.Duration, 0.15f, step.Radius);
                    break;
                case "dash":
                case "teleport":
                    DashForward(step.Distance);
                    break;
                case "lane_swap":
                    SwapLane();
                    break;
                case "knockback":
                    KnockbackNearest(step.Distance, step.Radius);
                    break;
                case "heal":
                    HealNearbyAllies(step);
                    break;
                case "chain":
                case "line":
                case "aoe":
                case "pierce":
                case "turret_break":
                    ApplyBonusDamage(step);
                    break;
                default:
                    // Other ability types can be expanded later.
                    break;
            }
        }

        private IEnumerator TempShield(AbilityStep step)
        {
            float bonus = Card.Hp * Mathf.Clamp01(step.Value);
            CurrentHp += bonus;
            yield return new WaitForSeconds(step.Duration);
            CurrentHp = Mathf.Max(1f, CurrentHp - bonus);
        }

        private IEnumerator TempDamageBuff(AbilityStep step)
        {
            float bonus = Damage * Mathf.Clamp01(step.Value);
            Damage += bonus;
            yield return new WaitForSeconds(step.Duration);
            Damage -= bonus;
        }

        private void ApplyStatusToNearestEnemy(StatusEffectType type, float duration, float value, float radius)
        {
            float useRadius = radius > 0f ? radius : Range + 1.5f;
            var target = ArenaManager.Instance.FindClosestEnemyUnitInRadius(transform.position, Team, useRadius);
            if (target == null) return;
            target.AddEffect(new StatusEffect(type, duration, value));
        }

        private void ApplySilenceOrDisable(AbilityStep step)
        {
            float useRadius = step.Radius > 0f ? step.Radius : Range + 1.5f;
            var target = ArenaManager.Instance.FindClosestEnemyUnitInRadius(transform.position, Team, useRadius);
            if (target != null)
            {
                target.AddEffect(new StatusEffect(StatusEffectType.Silence, Mathf.Max(0.8f, step.Duration), 0f));
                return;
            }

            var tower = ArenaManager.Instance.FindLaneEnemyTowerForDisable(Team, LaneIndex);
            if (tower != null)
            {
                tower.DisableFor(Mathf.Max(1.0f, step.Duration));
            }
        }

        private void KnockbackNearest(float distance, float radius)
        {
            float useRadius = radius > 0f ? radius : Range + 1.5f;
            var target = ArenaManager.Instance.FindClosestEnemyUnitInRadius(transform.position, Team, useRadius);
            if (target == null) return;
            Vector3 dir = (target.transform.position - transform.position).normalized;
            target.transform.position += dir * Mathf.Max(0.5f, distance);
        }

        private void DashForward(float distance)
        {
            float dist = Mathf.Max(0.5f, distance);
            transform.position = ArenaManager.Instance.GetLaneForwardPoint(Team, LaneIndex, dist);
        }

        private void SwapLane()
        {
            int newLane = Mathf.Clamp(LaneIndex + (Random.value > 0.5f ? 1 : -1), 0, 2);
            LaneIndex = newLane;
            transform.position = ArenaManager.Instance.GetLaneForwardPoint(Team, LaneIndex, 0f);
        }

        private void HealNearbyAllies(AbilityStep step)
        {
            float radius = step.Radius > 0f ? step.Radius : 2f;
            var ally = ArenaManager.Instance.FindClosestAllyUnitInRadius(transform.position, Team, radius);
            if (ally == null) return;
            float amount = ally.Card.Hp * Mathf.Clamp(step.Value, 0.02f, 0.10f);
            ally.Heal(amount);
        }

        private void ApplyBonusDamage(AbilityStep step)
        {
            float useRadius = step.Radius > 0f ? step.Radius : Range + 1.5f;
            var target = ArenaManager.Instance.FindClosestEnemyUnitInRadius(transform.position, Team, useRadius);
            if (target != null)
            {
                target.TakeDamage(Damage * Mathf.Clamp(step.Value, 0.05f, 0.25f));
                return;
            }

            var tower = ArenaManager.Instance.FindLaneTowerTarget(Team, LaneIndex, Card.QueenTarget);
            if (tower != null)
            {
                tower.TakeDamage(Damage * Mathf.Clamp(step.Value, 0.05f, 0.25f));
            }
        }

        public void AddEffect(StatusEffect effect)
        {
            _effects.Add(effect);
        }

        private bool HasEffect(StatusEffectType type, out float value)
        {
            value = 0f;
            bool found = false;
            for (int i = 0; i < _effects.Count; i++)
            {
                if (_effects[i].Type != type) continue;
                value = Mathf.Max(value, _effects[i].Value);
                found = true;
            }
            return found;
        }

        private void UpdateEffects()
        {
            for (int i = _effects.Count - 1; i >= 0; i--)
            {
                _effects[i].Duration -= Time.deltaTime;
                if (_effects[i].Duration <= 0f)
                {
                    _effects.RemoveAt(i);
                }
            }
        }

        private void Update()
        {
            if (Card == null) return;
            UpdateEffects();

            if (HasEffect(StatusEffectType.Stun, out _)) return;

            var target = ArenaManager.Instance.FindClosestEnemyUnit(transform.position, Team, Range);
            if (target != null)
            {
                AttackTarget(target.transform.position, () => target.TakeDamage(Damage));
                return;
            }

            var tower = ArenaManager.Instance.FindLaneTowerTarget(Team, LaneIndex, Card.QueenTarget);
            if (tower != null)
            {
                float dist = Vector3.Distance(transform.position, tower.transform.position);
                if (dist <= Range)
                {
                    AttackTarget(tower.transform.position, () => tower.TakeDamage(Damage));
                }
                else
                {
                    MoveToward(tower.transform.position);
                }
            }
        }

        private void MoveToward(Vector3 target)
        {
            if (HasEffect(StatusEffectType.Root, out _)) return;
            float slowFactor = 0f;
            if (HasEffect(StatusEffectType.Slow, out float slow)) slowFactor = Mathf.Clamp01(slow);
            float speed = MoveSpeed * (1f - slowFactor);
            transform.position = Vector3.MoveTowards(transform.position, target, speed * Time.deltaTime);
        }

        private void AttackTarget(Vector3 target, System.Action onHit)
        {
            _attackTimer -= Time.deltaTime;
            if (_attackTimer > 0f) return;
            float slowFactor = 0f;
            if (HasEffect(StatusEffectType.Slow, out float slow)) slowFactor = Mathf.Clamp01(slow);
            float speed = AttackSpeed * (1f - slowFactor);
            _attackTimer = 1f / Mathf.Max(0.1f, speed);
            onHit?.Invoke();
            if (VfxSpawner.Instance != null)
            {
                VfxSpawner.Instance.SpawnHit(target);
            }
        }

        private void OnDestroy()
        {
            if (ArenaManager.Instance != null)
            {
                ArenaManager.Instance.UnregisterUnit(this);
            }
        }
    }
}
