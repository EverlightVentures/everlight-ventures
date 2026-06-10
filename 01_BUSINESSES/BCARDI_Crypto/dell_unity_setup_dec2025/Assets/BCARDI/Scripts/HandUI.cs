using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class HandUI : MonoBehaviour
    {
        public PlayerController Player;
        public Text SelectedText;

        private void Update()
        {
            if (Player == null || SelectedText == null) return;
            string label = Player.GetSelectedCardLabel();
            SelectedText.text = label;
        }
    }
}
