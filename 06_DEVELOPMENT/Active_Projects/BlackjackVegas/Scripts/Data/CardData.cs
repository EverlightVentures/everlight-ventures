// ============================================================
// CardData.cs  --  ScriptableObject for a single card
// Create via: Assets > Create > BlackjackVegas > CardData
// ============================================================
using UnityEngine;

namespace BlackjackVegas
{
    public enum Suit { Hearts, Diamonds, Clubs, Spades }
    public enum Rank { Two=2, Three, Four, Five, Six, Seven, Eight, Nine, Ten,
                       Jack, Queen, King, Ace }
    public enum CardRarity { Standard, Gold, VegasNight, Diamond }

    [CreateAssetMenu(fileName = "Card_", menuName = "BlackjackVegas/CardData")]
    public class CardData : ScriptableObject
    {
        [Header("Identity")]
        public Suit  suit;
        public Rank  rank;

        [Header("Cosmetic")]
        public CardRarity rarity = CardRarity.Standard;
        public Sprite     frontSprite;
        public Sprite     backSprite;
        public Material   foilMaterial;   // null = no foil

        // --------------------------------------------------------
        // Computed properties
        // --------------------------------------------------------

        public bool IsAce => rank == Rank.Ace;

        public int BlackjackValue
        {
            get
            {
                if (rank == Rank.Ace)                return 11;   // GameManager handles soft/hard
                if (rank >= Rank.Jack)               return 10;
                return (int)rank;
            }
        }

        public string DisplayName => $"{rank} of {suit}";

        // Pit boss short code, e.g. "A♠", "K♥"
        public string ShortCode
        {
            get
            {
                string r = rank switch
                {
                    Rank.Ace   => "A",
                    Rank.King  => "K",
                    Rank.Queen => "Q",
                    Rank.Jack  => "J",
                    Rank.Ten   => "10",
                    _          => ((int)rank).ToString()
                };
                string s = suit switch
                {
                    Suit.Hearts   => "♥",
                    Suit.Diamonds => "♦",
                    Suit.Clubs    => "♣",
                    Suit.Spades   => "♠",
                    _             => "?"
                };
                return r + s;
            }
        }
    }
}
