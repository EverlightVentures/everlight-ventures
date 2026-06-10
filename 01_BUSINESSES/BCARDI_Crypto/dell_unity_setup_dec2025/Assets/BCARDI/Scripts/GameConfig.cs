using System.Collections.Generic;
using UnityEngine;

namespace BCARDI
{
    public sealed class GameConfig : MonoBehaviour
    {
        public static GameConfig Instance { get; private set; }

        public Dictionary<string, CardDefinition> CardsByName { get; private set; }
        public Dictionary<string, CardAbilityRotation> AbilityRotations { get; private set; }
        public List<DeckDefinition> Decks { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            CardsByName = LoadCards();
            AbilityRotations = LoadAbilityRotations();
            Decks = LoadDecks();
        }

        private Dictionary<string, CardDefinition> LoadCards()
        {
            var text = Resources.Load<TextAsset>("cards");
            if (text == null)
            {
                Debug.LogError("Missing Resources/cards.json");
                return new Dictionary<string, CardDefinition>();
            }

            var root = JsonMini.Deserialize(text.text) as List<object>;
            var result = new Dictionary<string, CardDefinition>();
            if (root == null) return result;

            foreach (var item in root)
            {
                var dict = item as Dictionary<string, object>;
                if (dict == null) continue;
                var def = new CardDefinition
                {
                    Class = GetString(dict, "class"),
                    Name = GetString(dict, "name"),
                    Breed = GetString(dict, "breed"),
                    Cost = GetInt(dict, "cost"),
                    Role = GetString(dict, "role"),
                    Rarity = GetString(dict, "rarity"),
                    Hp = GetFloat(dict, "hp"),
                    Damage = GetFloat(dict, "damage"),
                    AttackSpeed = GetFloat(dict, "attack_speed"),
                    MoveSpeed = GetFloat(dict, "move_speed"),
                    Range = GetFloat(dict, "range"),
                    QueenTarget = GetBool(dict, "queen_target")
                };
                var tags = dict["tags"] as List<object>;
                if (tags != null)
                {
                    foreach (var t in tags)
                    {
                        def.Tags.Add(t.ToString());
                    }
                }
                if (!string.IsNullOrEmpty(def.Name))
                {
                    result[def.Name] = def;
                }
            }

            return result;
        }

        private Dictionary<string, CardAbilityRotation> LoadAbilityRotations()
        {
            var text = Resources.Load<TextAsset>("ability_params");
            if (text == null)
            {
                Debug.LogWarning("Missing Resources/ability_params.json (abilities will be empty)");
                return new Dictionary<string, CardAbilityRotation>();
            }

            var root = JsonMini.Deserialize(text.text) as Dictionary<string, object>;
            var result = new Dictionary<string, CardAbilityRotation>();
            if (root == null) return result;

            if (!root.TryGetValue("cards", out var cardsObj)) return result;
            var cards = cardsObj as Dictionary<string, object>;
            if (cards == null) return result;

            foreach (var kvp in cards)
            {
                var cardName = kvp.Key;
                var cardDict = kvp.Value as Dictionary<string, object>;
                if (cardDict == null || !cardDict.TryGetValue("rotation", out var rotObj)) continue;
                var rotList = rotObj as List<object>;
                if (rotList == null) continue;

                var rotation = new CardAbilityRotation { CardName = cardName };
                foreach (var stepObj in rotList)
                {
                    var stepDict = stepObj as Dictionary<string, object>;
                    if (stepDict == null) continue;
                    var step = new AbilityStep
                    {
                        Name = GetString(stepDict, "name"),
                        Type = GetString(stepDict, "type"),
                        Duration = GetFloat(stepDict, "duration"),
                        Cooldown = GetFloat(stepDict, "cooldown"),
                        Radius = GetFloat(stepDict, "radius"),
                        Distance = GetFloat(stepDict, "distance"),
                        Count = GetInt(stepDict, "count"),
                        Targets = GetInt(stepDict, "targets")
                    };

                    // Normalize various value keys into Value.
                    if (stepDict.TryGetValue("value_pct_hp", out var vhp)) step.Value = ToFloat(vhp);
                    if (stepDict.TryGetValue("value_pct_dmg", out var vdm)) step.Value = ToFloat(vdm);
                    if (stepDict.TryGetValue("value_pct_dr", out var vdr)) step.Value = ToFloat(vdr);
                    if (stepDict.TryGetValue("value_pct_slow", out var vsl)) step.Value = ToFloat(vsl);
                    if (stepDict.TryGetValue("value_pct_ms", out var vms)) step.Value = ToFloat(vms);
                    if (stepDict.TryGetValue("value_pct_as", out var vas)) step.Value = ToFloat(vas);
                    if (stepDict.TryGetValue("value_pct_crit", out var vcr)) step.Value = ToFloat(vcr);
                    if (stepDict.TryGetValue("value_pct_evade", out var vev)) step.Value = ToFloat(vev);
                    if (stepDict.TryGetValue("value_pct_ls", out var vls)) step.Value = ToFloat(vls);

                    rotation.Steps.Add(step);
                }
                result[cardName] = rotation;
            }

            return result;
        }

        private List<DeckDefinition> LoadDecks()
        {
            var text = Resources.Load<TextAsset>("decks");
            if (text == null)
            {
                Debug.LogWarning("Missing Resources/decks.json");
                return new List<DeckDefinition>();
            }

            var root = JsonMini.Deserialize(text.text) as Dictionary<string, object>;
            var result = new List<DeckDefinition>();
            if (root == null || !root.TryGetValue("decks", out var decksObj)) return result;
            var list = decksObj as List<object>;
            if (list == null) return result;

            foreach (var deckObj in list)
            {
                var deckDict = deckObj as Dictionary<string, object>;
                if (deckDict == null) continue;
                var deck = new DeckDefinition
                {
                    Name = GetString(deckDict, "name"),
                    Class = GetString(deckDict, "class")
                };
                var cards = deckDict["cards"] as List<object>;
                if (cards != null)
                {
                    foreach (var c in cards) deck.Cards.Add(c.ToString());
                }
                result.Add(deck);
            }

            return result;
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

        private static float GetFloat(Dictionary<string, object> dict, string key)
        {
            if (!dict.TryGetValue(key, out var v)) return 0f;
            return ToFloat(v);
        }

        private static float ToFloat(object v)
        {
            if (v is float f) return f;
            if (v is double d) return (float)d;
            if (v is int i) return i;
            if (v is long l) return l;
            float.TryParse(v.ToString(), out float r);
            return r;
        }

        private static bool GetBool(Dictionary<string, object> dict, string key)
        {
            if (!dict.TryGetValue(key, out var v)) return false;
            if (v is bool b) return b;
            bool.TryParse(v.ToString(), out bool r);
            return r;
        }
    }
}
