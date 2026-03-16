// ============================================================
// DeckController.cs  --  Manages shuffle + deal from DeckData SO
// ============================================================
using System.Collections.Generic;
using UnityEngine;

namespace BlackjackVegas
{
    /// <summary>
    /// ScriptableObject holding the master card set.
    /// Assign your 52 CardData assets in the inspector.
    /// </summary>
    [CreateAssetMenu(fileName = "DeckData", menuName = "BlackjackVegas/DeckData")]
    public class DeckData : ScriptableObject
    {
        [Tooltip("Drag all 52 CardData SOs here")]
        public CardData[] allCards;
    }

    // --------------------------------------------------------

    public class DeckController : MonoBehaviour
    {
        [SerializeField] private DeckData deckData;
        [SerializeField] private int numberOfDecks = 6;   // Vegas 6-deck shoe

        private List<CardData> shoe = new List<CardData>();

        public int CardsRemaining => shoe.Count;

        void Awake() => Shuffle();

        public void Shuffle()
        {
            shoe.Clear();
            for (int d = 0; d < numberOfDecks; d++)
                foreach (var card in deckData.allCards)
                    shoe.Add(card);

            // Fisher-Yates shuffle
            for (int i = shoe.Count - 1; i > 0; i--)
            {
                int j = Random.Range(0, i + 1);
                (shoe[i], shoe[j]) = (shoe[j], shoe[i]);
            }

            // Auto-shuffle when < 25% remain (Vegas rule)
            Debug.Log($"[Deck] Shuffled {shoe.Count} cards ({numberOfDecks} decks)");
        }

        public CardData Deal()
        {
            if (shoe.Count == 0) Shuffle();

            // Auto-reshuffle at 25% penetration
            if (shoe.Count < deckData.allCards.Length * numberOfDecks * 0.25f)
                Shuffle();

            var card = shoe[0];
            shoe.RemoveAt(0);
            return card;
        }
    }
}
