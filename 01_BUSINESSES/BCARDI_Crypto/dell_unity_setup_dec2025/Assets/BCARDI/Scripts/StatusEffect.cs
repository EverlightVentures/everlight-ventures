using System;

namespace BCARDI
{
    public enum StatusEffectType
    {
        Slow,
        Stun,
        Silence,
        Root,
        Blind,
        Evasion,
        DamageBoost,
        AttackSpeedBoost,
        MoveSpeedBoost
    }

    [Serializable]
    public sealed class StatusEffect
    {
        public StatusEffectType Type;
        public float Duration;
        public float Value;

        public StatusEffect(StatusEffectType type, float duration, float value)
        {
            Type = type;
            Duration = duration;
            Value = value;
        }
    }
}
