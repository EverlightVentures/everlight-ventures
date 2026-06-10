using UnityEngine;

namespace BCARDI
{
    public sealed class PlayerController : MonoBehaviour
    {
        public EnergySystem Energy;
        public int DeckIndex = 0;
        private string[] _cards = new string[0];
        private int _selected = 0;

        private void Start()
        {
            ReloadDeck();
        }

        private void Update()
        {
            for (int i = 0; i < 8; i++)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1 + i))
                {
                    _selected = i;
                }
            }

            if (_cards.Length == 0 || _selected >= _cards.Length) return;
            if (Input.GetKeyDown(KeyCode.Q)) TryPlay(0);
            if (Input.GetKeyDown(KeyCode.W)) TryPlay(1);
            if (Input.GetKeyDown(KeyCode.E)) TryPlay(2);
        }

        public void SetSelectedIndex(int index)
        {
            _selected = Mathf.Clamp(index, 0, _cards.Length - 1);
        }

        public void SetDeckIndex(int index)
        {
            DeckIndex = index;
            ReloadDeck();
        }

        public void PlayLane(int lane)
        {
            TryPlay(lane);
        }

        public string GetSelectedCardLabel()
        {
            if (_cards.Length == 0 || _selected >= _cards.Length) return "No card";
            string cardName = _cards[_selected];
            if (GameConfig.Instance == null || !GameConfig.Instance.CardsByName.TryGetValue(cardName, out var card))
            {
                return cardName;
            }
            return cardName + " (" + card.Cost + ")";
        }

        private void TryPlay(int lane)
        {
            if (_cards.Length == 0 || _selected >= _cards.Length) return;
            string cardName = _cards[_selected];
            if (!GameConfig.Instance.CardsByName.TryGetValue(cardName, out var card)) return;
            if (Energy == null || !Energy.Spend(card.Cost)) return;

            ArenaManager.Instance.SpawnUnit(cardName, Team.Player, lane);
        }

        private void ReloadDeck()
        {
            if (GameConfig.Instance != null && GameConfig.Instance.Decks.Count > DeckIndex)
            {
                _cards = GameConfig.Instance.Decks[DeckIndex].Cards.ToArray();
                _selected = Mathf.Clamp(_selected, 0, _cards.Length - 1);
            }
        }
    }
}
