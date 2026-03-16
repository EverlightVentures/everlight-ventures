using System.Collections.Generic;
using UnityEngine;

namespace Blackjack.Core
{
    public class Hand : MonoBehaviour
    {
        private List<Card> _cards = new();

        public IReadOnlyList<Card> Cards => _cards;
        public int CardCount => _cards.Count;

        public void Clear() => _cards.Clear();

        public void AddCard(Card card) => _cards.Add(card);

        // Recalculation loop: count Aces as 11, reduce to 1 while bust.
        public int Value()
        {
            int total = 0;
            int aces  = 0;

            foreach (Card c in _cards)
            {
                total += c.BaseValue();
                if (c.rank == Rank.Ace) aces++;
            }

            while (total > 21 && aces > 0)
            {
                total -= 10;
                aces--;
            }

            return total;
        }

        public bool IsBust()       => Value() > 21;
        public bool IsBlackjack()  => CardCount == 2 && Value() == 21;
        public bool IsSoft17()
        {
            // Soft 17: value == 17 and at least one Ace counted as 11
            if (Value() != 17) return false;
            int total = 0;
            foreach (Card c in _cards) total += c.BaseValue();
            return total != 17; // if raw total differs, an Ace is being reduced
        }
    }
}
