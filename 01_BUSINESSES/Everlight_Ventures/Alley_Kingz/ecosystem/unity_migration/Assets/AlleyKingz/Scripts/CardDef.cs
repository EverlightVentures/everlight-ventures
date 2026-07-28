// CardDef.cs -- Alley Kingz card, as a Unity ScriptableObject.
// This mirrors canon.js / cards.json FIELD FOR FIELD. The web game and the Unity
// build read the SAME balance data (cards.json), so stats never fork between them.
// The `rig` block is pre-authored: rigClass picks 1 of 4 shared animation families,
// so 106 cards need ~4 rigs + 1 shared clip set, not 106 bespoke rigs.
//
// Generated assets live at Assets/AlleyKingz/Cards/Card_<NNNN>.asset via CardImporter.
using UnityEngine;

namespace AlleyKingz
{
    [System.Serializable]
    public class CardAbility
    {
        public string name;
        [TextArea] public string description;
        public float cooldown;
    }

    [System.Serializable]
    public class CardRig
    {
        public string name;        // "The Crown Rig"
        public string rigClass;    // bruiser | sprinter | tech_ops | turret_util  (the 4 families)
        public string weaponMod;   // e.g. "ram_plow"
        public string sourceCar;   // silhouette/proportion reference for the modeler
        [TextArea] public string flavor;
    }

    [CreateAssetMenu(fileName = "Card", menuName = "Alley Kingz/Card", order = 0)]
    public class CardDef : ScriptableObject
    {
        [Header("Identity")]
        public string cardNumber;   // "0001"
        public string cardName;     // "$BCARDD"  (UnityEngine.Object.name is reserved -> cardName)
        public string breed;
        public string className;    // "Boneguard Crew"  (class is a C# keyword -> className)
        public string factionId;
        public string rarity;
        public string role;
        public bool isMythic;
        public string variant;
        public string family;
        [TextArea] public string desc;

        [Header("Stats -- verbatim from canon.js; balance never forks")]
        public int cost;
        public int hp;
        public int damage;
        public float attackSpeed;   // attack_speed
        public float moveSpeed;     // move_speed
        public float range;
        public string domain;       // ground | air
        public string targets;      // ground | air | both
        public bool splash;
        public float splashRadius;
        public bool queenTarget;    // queen_target -- may strike the enemy Queen/tower

        [Header("Ability")]
        public string abilityType;
        public CardAbility ability;

        [Header("Rig -- which of 4 Unity rig families + weapon mod")]
        public CardRig rig;

        /// The shared animator family this card drives (drives the Mixamo retarget set).
        public string RigFamily => (rig != null && !string.IsNullOrEmpty(rig.rigClass)) ? rig.rigClass : "bruiser";
    }
}
