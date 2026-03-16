using System.Collections.Generic;
using UnityEngine;

namespace Blackjack.Core
{
    public enum Suit { Hearts, Diamonds, Clubs, Spades }
    public enum Rank  { Two=2, Three, Four, Five, Six, Seven, Eight, Nine, Ten,
                        Jack, Queen, King, Ace }

    [System.Serializable]
    public class Card
    {
        public Suit suit;
        public Rank rank;

        public Card(Suit s, Rank r) { suit = s; rank = r; }

        // Base point value. Ace returns 11; caller reduces if bust.
        public int BaseValue()
        {
            if (rank == Rank.Ace)   return 11;
            if (rank >= Rank.Ten)   return 10;
            return (int)rank;
        }

        public override string ToString() => $"{rank} of {suit}";
    }

    public class Deck : MonoBehaviour
    {
        private List<Card> _cards = new();

        public int Remaining => _cards.Count;

        public void Build()
        {
            _cards.Clear();
            foreach (Suit s in System.Enum.GetValues(typeof(Suit)))
                foreach (Rank r in System.Enum.GetValues(typeof(Rank)))
                    _cards.Add(new Card(s, r));
        }

        // Fisher-Yates shuffle -- unbiased.
        public void Shuffle()
        {
            for (int i = _cards.Count - 1; i > 0; i--)
            {
                int j = Random.Range(0, i + 1);
                (_cards[j], _cards[i]) = (_cards[i], _cards[j]);
            }
        }

        public Card Draw()
        {
            if (_cards.Count == 0)
            {
                Debug.LogWarning("Deck empty -- rebuilding and shuffling.");
                Build();
                Shuffle();
            }
            Card top = _cards[^1];
            _cards.RemoveAt(_cards.Count - 1);
            return top;
        }
    }
}
