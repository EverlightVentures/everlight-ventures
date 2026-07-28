// CardImporter.cs -- the Phase 0 KEYSTONE.
// Reads Assets/AlleyKingz/Data/cards.json (exported straight from canon.js) and
// generates/updates one CardDef ScriptableObject per card. Run it from the menu:
//     Alley Kingz > Import Cards from cards.json
// Re-run any time canon.js changes and re-export cards.json -- assets update in place,
// so the web game stays the single source of truth for balance.
//
// Dependency: Newtonsoft JSON (Unity package "com.unity.nuget.newtonsoft-json").
// Add it via Window > Package Manager > + > Add package by name.
#if UNITY_EDITOR
using System.IO;
using UnityEditor;
using UnityEngine;
using Newtonsoft.Json.Linq;

namespace AlleyKingz
{
    public static class CardImporter
    {
        const string JsonPath = "Assets/AlleyKingz/Data/cards.json";
        const string OutDir   = "Assets/AlleyKingz/Cards";

        [MenuItem("Alley Kingz/Import Cards from cards.json")]
        public static void Import()
        {
            if (!File.Exists(JsonPath))
            {
                Debug.LogError("[AK] cards.json not found at " + JsonPath +
                    " -- drop the exported cards.json there first.");
                return;
            }
            if (!Directory.Exists(OutDir)) Directory.CreateDirectory(OutDir);

            var root  = JObject.Parse(File.ReadAllText(JsonPath));
            var cards = (JArray)root["cards"];
            int made = 0, updated = 0;

            foreach (var jt in cards)
            {
                var j = (JObject)jt;
                string num = (string)j["cardNumber"];
                if (string.IsNullOrEmpty(num)) continue;

                string assetPath = OutDir + "/Card_" + num + ".asset";
                var def = AssetDatabase.LoadAssetAtPath<CardDef>(assetPath);
                bool isNew = def == null;
                if (isNew) def = ScriptableObject.CreateInstance<CardDef>();

                // ---- identity ----
                def.cardNumber = num;
                def.cardName   = (string)j["name"];
                def.breed      = (string)j["breed"];
                def.className  = (string)j["class"];
                def.factionId  = (string)j["factionId"];
                def.rarity     = (string)j["rarity"];
                def.role       = (string)j["role"];
                def.isMythic   = (bool?)j["isMythic"] ?? false;
                def.variant    = (string)j["variant"];
                def.family     = (string)j["family"];
                def.desc       = (string)j["desc"];

                // ---- stats (snake_case in JSON -> camelCase here) ----
                def.cost         = (int?)j["cost"] ?? 0;
                def.hp           = (int?)j["hp"] ?? 0;
                def.damage       = (int?)j["damage"] ?? 0;
                def.attackSpeed  = (float?)j["attack_speed"] ?? 0f;
                def.moveSpeed    = (float?)j["move_speed"] ?? 0f;
                def.range        = (float?)j["range"] ?? 0f;
                def.domain       = (string)j["domain"];
                def.targets      = (string)j["targets"];
                def.splash       = (bool?)j["splash"] ?? false;
                def.splashRadius = (float?)j["splashRadius"] ?? 0f;
                def.queenTarget  = (bool?)j["queen_target"] ?? false;
                def.abilityType  = (string)j["abilityType"];

                // ---- ability ----
                def.ability = new CardAbility();
                if (j["ability"] is JObject ab)
                {
                    def.ability.name        = (string)ab["name"];
                    def.ability.description = (string)ab["description"];
                    def.ability.cooldown    = (float?)ab["cooldown"] ?? 0f;
                }

                // ---- rig (the 2D->3D mapping) ----
                def.rig = new CardRig();
                if (j["rig"] is JObject rg)
                {
                    def.rig.name      = (string)rg["name"];
                    def.rig.rigClass  = (string)rg["rigClass"];
                    def.rig.weaponMod = (string)rg["weaponMod"];
                    def.rig.sourceCar = (string)rg["sourceCar"];
                    def.rig.flavor    = (string)rg["flavor"];
                }

                if (isNew) { AssetDatabase.CreateAsset(def, assetPath); made++; }
                else       { EditorUtility.SetDirty(def);               updated++; }
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"[AK] Imported {made} new + {updated} updated CardDefs from cards.json. " +
                      "Balance is now canonical in Unity.");
        }
    }
}
#endif
