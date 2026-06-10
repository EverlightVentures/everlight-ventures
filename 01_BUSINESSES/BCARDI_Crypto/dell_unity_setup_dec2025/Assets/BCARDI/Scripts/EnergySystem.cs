using UnityEngine;

namespace BCARDI
{
    public sealed class EnergySystem : MonoBehaviour
    {
        public int MaxBones = 12;
        public float RegenInterval = 1.3f;

        public int CurrentBones { get; private set; }
        private float _timer;

        private void Start()
        {
            CurrentBones = MaxBones;
        }

        private void Update()
        {
            if (CurrentBones >= MaxBones) return;
            _timer += Time.deltaTime;
            if (_timer >= RegenInterval)
            {
                _timer = 0f;
                CurrentBones = Mathf.Min(MaxBones, CurrentBones + 1);
            }
        }

        public bool CanSpend(int amount)
        {
            return CurrentBones >= amount;
        }

        public bool Spend(int amount)
        {
            if (!CanSpend(amount)) return false;
            CurrentBones -= amount;
            return true;
        }
    }
}
