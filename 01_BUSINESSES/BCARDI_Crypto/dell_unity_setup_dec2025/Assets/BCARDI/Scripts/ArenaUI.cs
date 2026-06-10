using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class ArenaUI : MonoBehaviour
    {
        public Text TrophiesText;
        public Text ArenaText;

        private void Update()
        {
            if (ProgressionManager.Instance == null) return;
            if (TrophiesText != null)
            {
                TrophiesText.text = "Dog Skulls: " + ProgressionManager.Instance.Trophies;
            }
            if (ArenaText != null)
            {
                ArenaText.text = "Arena: " + ProgressionManager.Instance.CurrentArena;
            }
        }
    }
}
