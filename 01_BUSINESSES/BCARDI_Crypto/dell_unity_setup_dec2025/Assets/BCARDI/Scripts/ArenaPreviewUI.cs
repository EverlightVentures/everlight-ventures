using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class ArenaPreviewUI : MonoBehaviour
    {
        public Text ArenaNameText;
        public Text TrophyRangeText;
        public Text NextGiftText;

        private void Update()
        {
            if (ProgressionManager.Instance == null) return;
            var current = ProgressionManager.Instance.GetCurrentArena();
            if (current != null)
            {
                if (ArenaNameText != null) ArenaNameText.text = current.Name;
                if (TrophyRangeText != null)
                {
                    TrophyRangeText.text = current.MinTrophies + " - " + current.MaxTrophies;
                }
                if (NextGiftText != null)
                {
                    var gifts = ProgressionManager.Instance.GetGiftsForTier(current.GiftTier);
                    NextGiftText.text = gifts.Count > 0 ? "Gift: " + string.Join(", ", gifts) : "Gift: None";
                }
            }
        }
    }
}
