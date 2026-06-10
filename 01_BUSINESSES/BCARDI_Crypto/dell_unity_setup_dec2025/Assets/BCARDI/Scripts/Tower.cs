using UnityEngine;

namespace BCARDI
{
    public sealed class Tower : MonoBehaviour
    {
        public Team Team;
        public bool IsQueen;
        public float MaxHp = 1000f;
        public float CurrentHp = 1000f;
        public float DamagePerShot = 30f;
        public float AttackRange = 6f;
        public float AttackCooldown = 1.2f;

        private float _cooldown;
        private bool _invulnerable;
        private float _disabledTimer;

        public void SetInvulnerable(bool value)
        {
            _invulnerable = value;
        }

        public void SetHealth(float maxHp)
        {
            MaxHp = maxHp;
            CurrentHp = maxHp;
        }

        public void TakeDamage(float amount)
        {
            if (_invulnerable) return;
            CurrentHp = Mathf.Max(0f, CurrentHp - amount);
        }

        public void DisableFor(float seconds)
        {
            _disabledTimer = Mathf.Max(_disabledTimer, seconds);
        }

        private void Update()
        {
            if (CurrentHp <= 0f) return;
            if (_disabledTimer > 0f)
            {
                _disabledTimer -= Time.deltaTime;
                return;
            }
            _cooldown -= Time.deltaTime;
            if (_cooldown > 0f) return;

            var target = ArenaManager.Instance.FindClosestEnemyUnit(transform.position, Team, AttackRange);
            if (target == null) return;

            _cooldown = AttackCooldown;
            target.TakeDamage(DamagePerShot);
        }
    }
}
