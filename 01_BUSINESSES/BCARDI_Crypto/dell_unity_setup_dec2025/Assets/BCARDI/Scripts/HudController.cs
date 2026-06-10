using UnityEngine;

namespace BCARDI
{
    public sealed class HudController : MonoBehaviour
    {
        public PlayerController Player;
        public int SelectedIndex;

        public void SelectCard(int index)
        {
            SelectedIndex = Mathf.Clamp(index, 0, 7);
            if (Player != null) Player.SetSelectedIndex(SelectedIndex);
        }

        public void PlayLeft()
        {
            Player?.PlayLane(0);
        }

        public void PlayCenter()
        {
            Player?.PlayLane(1);
        }

        public void PlayRight()
        {
            Player?.PlayLane(2);
        }
    }
}
