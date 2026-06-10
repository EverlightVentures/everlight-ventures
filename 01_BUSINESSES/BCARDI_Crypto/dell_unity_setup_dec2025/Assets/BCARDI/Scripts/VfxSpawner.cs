using UnityEngine;

namespace BCARDI
{
    public sealed class VfxSpawner : MonoBehaviour
    {
        public static VfxSpawner Instance { get; private set; }

        public GameObject HitFlashPrefab;
        public GameObject TrailPrefab;

        private void Awake()
        {
            Instance = this;
        }

        public void SpawnHit(Vector3 position)
        {
            if (HitFlashPrefab == null) return;
            Instantiate(HitFlashPrefab, position, Quaternion.identity);
        }

        public void SpawnTrail(Vector3 position)
        {
            if (TrailPrefab == null) return;
            Instantiate(TrailPrefab, position, Quaternion.identity);
        }
    }
}
