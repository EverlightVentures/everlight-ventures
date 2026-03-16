// ============================================================
// SaveSystem.cs  --  JSON save to PlayerPrefs + optional cloud
// Browser-safe: PlayerPrefs persists in IndexedDB on WebGL
// ============================================================
using UnityEngine;

namespace BlackjackVegas
{
    public class SaveSystem : MonoBehaviour
    {
        public static SaveSystem Instance { get; private set; }

        private const string SAVE_KEY = "bj_player_v1";
        private bool isDirty = false;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        void OnApplicationPause(bool paused) { if (paused && isDirty) Save(); }
        void OnApplicationQuit() { if (isDirty) Save(); }

        public void MarkDirty() => isDirty = true;

        public void Save()
        {
            if (PlayerProfile.Instance == null) return;
            var data = PlayerProfile.Instance.ToSaveData();
            string json = JsonUtility.ToJson(data);
            PlayerPrefs.SetString(SAVE_KEY, json);
            PlayerPrefs.Save();
            isDirty = false;
            Debug.Log("[Save] Player data saved");
        }

        public void Load()
        {
            if (!PlayerPrefs.HasKey(SAVE_KEY)) return;
            string json = PlayerPrefs.GetString(SAVE_KEY);
            try
            {
                var data = JsonUtility.FromJson<PlayerSaveData>(json);
                PlayerProfile.Instance?.FromSaveData(data);
                Debug.Log("[Save] Player data loaded");
            }
            catch (System.Exception ex)
            {
                Debug.LogError($"[Save] Load failed: {ex.Message}. Starting fresh.");
            }
        }

        public void WipeData()
        {
            PlayerPrefs.DeleteKey(SAVE_KEY);
            PlayerPrefs.Save();
            Debug.Log("[Save] Save data wiped");
        }
    }
}
