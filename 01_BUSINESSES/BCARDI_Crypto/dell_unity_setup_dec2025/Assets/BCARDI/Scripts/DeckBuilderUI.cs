using UnityEngine;
using UnityEngine.UI;

namespace BCARDI
{
    public sealed class DeckBuilderUI : MonoBehaviour
    {
        public PlayerController Player;
        public Text CurrentDeckText;
        public Transform DeckListRoot;
        public Button DeckButtonPrefab;

        private void Start()
        {
            BuildDeckList();
        }

        private void BuildDeckList()
        {
            if (DeckListRoot == null || DeckButtonPrefab == null || GameConfig.Instance == null) return;
            foreach (Transform child in DeckListRoot)
            {
                Destroy(child.gameObject);
            }

            for (int i = 0; i < GameConfig.Instance.Decks.Count; i++)
            {
                int index = i;
                var deck = GameConfig.Instance.Decks[i];
                var btn = Instantiate(DeckButtonPrefab, DeckListRoot);
                var txt = btn.GetComponentInChildren<Text>();
                if (txt != null) txt.text = deck.Name;
                btn.onClick.AddListener(() => SelectDeck(index));
            }
        }

        private void SelectDeck(int index)
        {
            if (Player == null) return;
            Player.SetDeckIndex(index);
            if (CurrentDeckText != null)
            {
                var deck = GameConfig.Instance.Decks[index];
                CurrentDeckText.text = "Deck: " + deck.Name;
            }
        }
    }
}
