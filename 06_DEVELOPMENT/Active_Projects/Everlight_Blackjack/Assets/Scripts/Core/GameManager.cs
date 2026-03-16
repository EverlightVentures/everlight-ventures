using System.Collections;
using UnityEngine;
using UnityEngine.Events;

namespace Blackjack.Core
{
    public enum GameState { Idle, Betting, Dealing, PlayerTurn, DealerTurn, Resolution }

    public class GameManager : MonoBehaviour
    {
        [Header("References")]
        public Deck deck;
        public Hand playerHand;
        public Hand dealerHand;

        [Header("Settings")]
        public int startingMoney = 500;
        public int minBet        = 5;

        // Events -- UI subscribes; GameManager never touches UI directly
        public UnityEvent<GameState> onStateChanged;
        public UnityEvent<string>    onMessage;
        public UnityEvent<int>       onMoneyChanged;
        public UnityEvent<int>       onPotChanged;

        public GameState CurrentState { get; private set; } = GameState.Idle;
        public int Money  { get; private set; }
        public int Pot    { get; private set; }

        void Start()
        {
            Money = startingMoney;
            deck.Build();
            deck.Shuffle();
            SetState(GameState.Betting);
        }

        // --- Public API (called by UIManager) ---

        public void PlaceBet(int amount)
        {
            if (CurrentState != GameState.Betting) return;
            if (amount < minBet || amount > Money)
            {
                onMessage.Invoke($"Bet must be between {minBet} and {Money}.");
                return;
            }
            Money -= amount;
            Pot    = amount;
            onMoneyChanged.Invoke(Money);
            onPotChanged.Invoke(Pot);
            StartCoroutine(DealRound());
        }

        public void Hit()
        {
            if (CurrentState != GameState.PlayerTurn) return;
            playerHand.AddCard(deck.Draw());
            onMessage.Invoke($"Player: {playerHand.Value()}");

            if (playerHand.IsBust())
                StartCoroutine(Resolve());
        }

        public void Stand()
        {
            if (CurrentState != GameState.PlayerTurn) return;
            StartCoroutine(DealerPlay());
        }

        // --- Internal state machine ---

        private void SetState(GameState next)
        {
            CurrentState = next;
            onStateChanged.Invoke(next);
        }

        private IEnumerator DealRound()
        {
            SetState(GameState.Dealing);
            playerHand.Clear();
            dealerHand.Clear();

            // Deal: player, dealer, player, dealer (standard order)
            playerHand.AddCard(deck.Draw());
            dealerHand.AddCard(deck.Draw());
            playerHand.AddCard(deck.Draw());
            dealerHand.AddCard(deck.Draw());

            yield return new WaitForSeconds(0.5f);

            // Dealer peek -- natural blackjack check before player acts
            if (dealerHand.IsBlackjack())
            {
                onMessage.Invoke("Dealer has Blackjack!");
                yield return StartCoroutine(Resolve());
                yield break;
            }

            if (playerHand.IsBlackjack())
            {
                onMessage.Invoke("Blackjack! You win 1.5x!");
                int payout = Mathf.RoundToInt(Pot * 2.5f);
                EndRound(payout, "Blackjack!");
                yield break;
            }

            SetState(GameState.PlayerTurn);
            onMessage.Invoke($"Your hand: {playerHand.Value()} | Dealer shows: {dealerHand.Cards[0]}");
        }

        // Dealer AI: hits on 16 or less (including soft 17 -- casino standard)
        private IEnumerator DealerPlay()
        {
            SetState(GameState.DealerTurn);
            onMessage.Invoke("Dealer's turn...");
            yield return new WaitForSeconds(0.6f);

            while (dealerHand.Value() < 17 || dealerHand.IsSoft17())
            {
                dealerHand.AddCard(deck.Draw());
                onMessage.Invoke($"Dealer hits: {dealerHand.Value()}");
                yield return new WaitForSeconds(0.6f);
            }

            yield return StartCoroutine(Resolve());
        }

        private IEnumerator Resolve()
        {
            SetState(GameState.Resolution);
            yield return new WaitForSeconds(0.3f);

            int  pv           = playerHand.Value();
            int  dv           = dealerHand.Value();
            bool playerBust   = playerHand.IsBust();
            bool dealerBust   = dealerHand.IsBust();

            if (playerBust)
            {
                EndRound(0, $"Bust! You lose. (Player {pv} / Dealer {dv})");
            }
            else if (dealerBust || pv > dv)
            {
                EndRound(Pot * 2, $"You win! (Player {pv} / Dealer {dv})");
            }
            else if (pv == dv)
            {
                EndRound(Pot, $"Push -- bets returned. ({pv} each)");
            }
            else
            {
                EndRound(0, $"Dealer wins. (Player {pv} / Dealer {dv})");
            }
        }

        private void EndRound(int winnings, string message)
        {
            Money += winnings;
            Pot    = 0;
            onMessage.Invoke(message);
            onMoneyChanged.Invoke(Money);
            onPotChanged.Invoke(Pot);

            if (Money < minBet)
            {
                onMessage.Invoke("Out of money! Game over.");
                SetState(GameState.Idle);
                return;
            }

            SetState(GameState.Betting);
        }
    }
}
