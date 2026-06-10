using System.Collections.Generic;
using UnityEngine;

namespace BCARDI
{
    public sealed class ProgressionManager : MonoBehaviour
    {
        public static ProgressionManager Instance { get; private set; }

        public int Trophies { get; private set; }
        public string CurrentArena { get; private set; }
        public int CurrentGiftTier { get; private set; }
        public int LastTrophyDelta { get; private set; }
        public List<string> LastGifts { get; private set; } = new List<string>();

        private List<ArenaDefinition> _arenas = new List<ArenaDefinition>();
        private Dictionary<int, List<string>> _rewards = new Dictionary<int, List<string>>();

        private const string TrophyKey = "BCARDI_TROPHIES";
        private const string GiftTierKey = "BCARDI_GIFT_TIER";

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            LoadData();
            Trophies = PlayerPrefs.GetInt(TrophyKey, 0);
            CurrentGiftTier = PlayerPrefs.GetInt(GiftTierKey, 0);
            UpdateArena();
        }

        public void ApplyMatchResult(bool playerWon)
        {
            LastTrophyDelta = playerWon ? 30 : -20;
            Trophies = Mathf.Max(0, Trophies + LastTrophyDelta);
            PlayerPrefs.SetInt(TrophyKey, Trophies);
            UpdateArena();
            CheckGiftTier();
        }

        private void CheckGiftTier()
        {
            int newTier = 0;
            foreach (var arena in _arenas)
            {
                if (Trophies >= arena.MinTrophies) newTier = arena.GiftTier;
            }

            LastGifts.Clear();
            if (newTier > CurrentGiftTier)
            {
                CurrentGiftTier = newTier;
                PlayerPrefs.SetInt(GiftTierKey, CurrentGiftTier);
                if (_rewards.TryGetValue(CurrentGiftTier, out var gifts))
                {
                    LastGifts = new List<string>(gifts);
                    Debug.Log("Gift unlocked (tier " + CurrentGiftTier + "): " + string.Join(", ", gifts));
                }
            }
        }

        private void UpdateArena()
        {
            foreach (var arena in _arenas)
            {
                if (Trophies >= arena.MinTrophies && Trophies <= arena.MaxTrophies)
                {
                    CurrentArena = arena.Name;
                    return;
                }
            }
            CurrentArena = _arenas.Count > 0 ? _arenas[_arenas.Count - 1].Name : "";
        }

        public ArenaDefinition GetCurrentArena()
        {
            foreach (var arena in _arenas)
            {
                if (Trophies >= arena.MinTrophies && Trophies <= arena.MaxTrophies) return arena;
            }
            return _arenas.Count > 0 ? _arenas[_arenas.Count - 1] : null;
        }

        public ArenaDefinition GetNextArena()
        {
            for (int i = 0; i < _arenas.Count; i++)
            {
                if (Trophies < _arenas[i].MinTrophies) return _arenas[i];
            }
            return null;
        }

        public List<string> GetGiftsForTier(int tier)
        {
            return _rewards.TryGetValue(tier, out var gifts) ? gifts : new List<string>();
        }

        public void ClaimLastGifts()
        {
            LastGifts.Clear();
        }

        private void LoadData()
        {
            var arenasText = Resources.Load<TextAsset>("arenas");
            if (arenasText != null)
            {
                var root = JsonMini.Deserialize(arenasText.text) as Dictionary<string, object>;
                if (root != null && root.TryGetValue("arenas", out var listObj))
                {
                    var list = listObj as List<object>;
                    if (list != null)
                    {
                        foreach (var item in list)
                        {
                            var dict = item as Dictionary<string, object>;
                            if (dict == null) continue;
                            var arena = new ArenaDefinition
                            {
                                Name = GetString(dict, "name"),
                                MinTrophies = GetInt(dict, "min_trophies"),
                                MaxTrophies = GetInt(dict, "max_trophies"),
                                GiftTier = GetInt(dict, "gift_tier")
                            };
                            _arenas.Add(arena);
                        }
                    }
                }
            }

            var rewardsText = Resources.Load<TextAsset>("rewards");
            if (rewardsText != null)
            {
                var root = JsonMini.Deserialize(rewardsText.text) as Dictionary<string, object>;
                if (root != null && root.TryGetValue("tiers", out var listObj))
                {
                    var list = listObj as List<object>;
                    if (list != null)
                    {
                        foreach (var item in list)
                        {
                            var dict = item as Dictionary<string, object>;
                            if (dict == null) continue;
                            int tier = GetInt(dict, "tier");
                            var gifts = new List<string>();
                            if (dict.TryGetValue("gifts", out var giftsObj))
                            {
                                var giftList = giftsObj as List<object>;
                                if (giftList != null)
                                {
                                    foreach (var g in giftList) gifts.Add(g.ToString());
                                }
                            }
                            _rewards[tier] = gifts;
                        }
                    }
                }
            }
        }

        private static string GetString(Dictionary<string, object> dict, string key)
        {
            return dict.TryGetValue(key, out var v) ? v.ToString() : "";
        }

        private static int GetInt(Dictionary<string, object> dict, string key)
        {
            if (!dict.TryGetValue(key, out var v)) return 0;
            if (v is int i) return i;
            if (v is long l) return (int)l;
            if (v is double d) return (int)d;
            int.TryParse(v.ToString(), out int r);
            return r;
        }
    }

    public sealed class ArenaDefinition
    {
        public string Name;
        public int MinTrophies;
        public int MaxTrophies;
        public int GiftTier;
    }
}
