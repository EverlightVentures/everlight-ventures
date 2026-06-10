using System.Collections.Generic;

namespace BCARDI
{
    public sealed class CardDefinition
    {
        public string Class;
        public string Name;
        public string Breed;
        public int Cost;
        public string Role;
        public string Rarity;
        public List<string> Tags = new List<string>();
        public float Hp;
        public float Damage;
        public float AttackSpeed;
        public float MoveSpeed;
        public float Range;
        public bool QueenTarget;
    }

    public sealed class AbilityStep
    {
        public string Name;
        public string Type;
        public float Duration;
        public float Value;
        public float Cooldown;
        public float Radius;
        public float Distance;
        public int Count;
        public int Targets;
    }

    public sealed class CardAbilityRotation
    {
        public string CardName;
        public List<AbilityStep> Steps = new List<AbilityStep>();
    }

    public sealed class DeckDefinition
    {
        public string Name;
        public string Class;
        public List<string> Cards = new List<string>();
    }
}
