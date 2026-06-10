using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class MatchEndUI : MonoBehaviour
    {
        public GameObject Panel;
        public Text ResultText;
        public Text TrophyText;
        public Text GiftText;
        public Button ClaimButton;

        private void OnEnable()
        {
            if (ArenaManager.Instance != null)
            {
                ArenaManager.Instance.MatchEnded += OnMatchEnded;
            }
            if (ClaimButton != null)
            {
                ClaimButton.onClick.AddListener(ClaimRewards);
            }
            if (Panel != null) Panel.SetActive(false);
        }

        private void OnDisable()
        {
            if (ArenaManager.Instance != null)
            {
                ArenaManager.Instance.MatchEnded -= OnMatchEnded;
            }
            if (ClaimButton != null)
            {
                ClaimButton.onClick.RemoveListener(ClaimRewards);
            }
        }

        private void OnMatchEnded(bool playerWon)
        {
            if (Panel != null) Panel.SetActive(true);
            if (ResultText != null) ResultText.text = playerWon ? "Victory" : "Defeat";

            if (ProgressionManager.Instance != null)
            {
                if (TrophyText != null)
                {
                    TrophyText.text = "Trophies: " + ProgressionManager.Instance.Trophies + " (" + ProgressionManager.Instance.LastTrophyDelta + ")";
                }
                if (GiftText != null)
                {
                    if (ProgressionManager.Instance.LastGifts.Count > 0)
                    {
                        GiftText.text = "Gift: " + string.Join(", ", ProgressionManager.Instance.LastGifts);
                    }
                    else
                    {
                        GiftText.text = "Gift: None";
                    }
                }
            }
        }

        public void ClaimRewards()
        {
            if (ProgressionManager.Instance != null)
            {
                ProgressionManager.Instance.ClaimLastGifts();
            }
            if (GiftText != null) GiftText.text = "Gift: Claimed";
        }
    }
}
