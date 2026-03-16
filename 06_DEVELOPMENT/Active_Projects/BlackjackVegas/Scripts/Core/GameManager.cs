// ============================================================
// GameManager.cs  --  Blackjack Vegas | Everlight Games
// State machine: IDLE → BETTING → DEALING → PLAYER_TURN
//                → DEALER_TURN → RESOLVE → PAYOUT
// ============================================================
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

namespace BlackjackVegas
{
    public enum GameState
    {
        IDLE,
        BETTING,
        DEALING,
        PLAYER_TURN,
        DEALER_TURN,
        RESOLVE,
        PAYOUT
    }

    public class GameManager : MonoBehaviour
    {
        public static GameManager Instance { get; private set; }

        [Header("State")]
        public GameState CurrentState { get; private set; } = GameState.IDLE;

        [Header("References")]
        [SerializeField] private DeckController deckController;
        [SerializeField] private UIManager uiManager;
        [SerializeField] private PitBossAuditor pitBoss;
        [SerializeField] private GemManager gemManager;
        [SerializeField] private SaveSystem saveSystem;

        [Header("Table Config")]
        [SerializeField] private TableConfigSO tableConfig;

        // Hands
        private List<CardData> playerHand = new List<CardData>();
        private List<CardData> dealerHand = new List<CardData>();

        // Round state
        private int currentBet = 0;
        private bool isDoubleDown = false;
        private bool isSplit = false;

        // Events -- UI and Sound listen to these
        public UnityEvent<CardData, bool> OnCardDealt;   // card, isPlayer
        public UnityEvent<GameState> OnStateChanged;
        public UnityEvent<RoundResult> OnRoundResolved;

        // --------------------------------------------------------
        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        void Start()
        {
            saveSystem.Load();
            TransitionTo(GameState.IDLE);
        }

        // --------------------------------------------------------
        // PUBLIC API -- called by UI buttons
        // --------------------------------------------------------

        public void StartBetting()
        {
            if (CurrentState != GameState.IDLE) return;
            TransitionTo(GameState.BETTING);
        }

        public void PlaceBet(int amount)
        {
            if (CurrentState != GameState.BETTING) return;
            if (amount < tableConfig.minBet || amount > tableConfig.maxBet)
            {
                uiManager.ShowError($"Bet must be ${tableConfig.minBet}–${tableConfig.maxBet}");
                return;
            }
            if (amount > PlayerProfile.Instance.Chips)
            {
                uiManager.ShowError("Not enough chips!");
                return;
            }
            currentBet = amount;
            PlayerProfile.Instance.DeductChips(amount);
            pitBoss.LogBet(amount);
            TransitionTo(GameState.DEALING);
        }

        public void PlayerHit()
        {
            if (CurrentState != GameState.PLAYER_TURN) return;
            var card = deckController.Deal();
            playerHand.Add(card);
            OnCardDealt?.Invoke(card, true);
            pitBoss.LogAction("HIT", playerHand);

            if (HandValue(playerHand) > 21)
            {
                pitBoss.LogBust("PLAYER");
                TransitionTo(GameState.RESOLVE);
            }
        }

        public void PlayerStand()
        {
            if (CurrentState != GameState.PLAYER_TURN) return;
            pitBoss.LogAction("STAND", playerHand);
            TransitionTo(GameState.DEALER_TURN);
        }

        public void PlayerDoubleDown()
        {
            if (CurrentState != GameState.PLAYER_TURN) return;
            if (playerHand.Count != 2) return;
            if (PlayerProfile.Instance.Chips < currentBet)
            {
                uiManager.ShowError("Not enough chips to double down!");
                return;
            }
            PlayerProfile.Instance.DeductChips(currentBet);
            currentBet *= 2;
            isDoubleDown = true;
            pitBoss.LogAction("DOUBLE_DOWN", playerHand);
            PlayerHit();
            if (CurrentState == GameState.PLAYER_TURN)
                PlayerStand();
        }

        // --------------------------------------------------------
        // STATE MACHINE
        // --------------------------------------------------------

        private void TransitionTo(GameState next)
        {
            CurrentState = next;
            OnStateChanged?.Invoke(next);

            switch (next)
            {
                case GameState.IDLE:
                    uiManager.ShowIdleScreen();
                    break;

                case GameState.BETTING:
                    ResetRound();
                    uiManager.ShowBettingUI(tableConfig.minBet, tableConfig.maxBet, PlayerProfile.Instance.Chips);
                    break;

                case GameState.DEALING:
                    StartCoroutine(DealInitialCards());
                    break;

                case GameState.PLAYER_TURN:
                    uiManager.ShowPlayerActions(CanDoubleDown(), CanSplit());
                    int pv = HandValue(playerHand);
                    // Auto-stand on blackjack
                    if (pv == 21) PlayerStand();
                    break;

                case GameState.DEALER_TURN:
                    StartCoroutine(RunDealerAI());
                    break;

                case GameState.RESOLVE:
                    ResolveRound();
                    break;

                case GameState.PAYOUT:
                    StartCoroutine(PayoutAndReset());
                    break;
            }
        }

        // --------------------------------------------------------
        // COROUTINES
        // --------------------------------------------------------

        private IEnumerator DealInitialCards()
        {
            deckController.Shuffle();

            // Deal: player, dealer (hole), player, dealer
            yield return DealCardTo(true);
            yield return new WaitForSeconds(0.4f);
            yield return DealCardTo(false);   // dealer hole card (face down)
            yield return new WaitForSeconds(0.4f);
            yield return DealCardTo(true);
            yield return new WaitForSeconds(0.4f);
            yield return DealCardTo(false);   // dealer up card (face up)
            yield return new WaitForSeconds(0.4f);

            pitBoss.LogDeal(playerHand, dealerHand);
            TransitionTo(GameState.PLAYER_TURN);
        }

        private IEnumerator RunDealerAI()
        {
            // Reveal hole card
            uiManager.RevealDealerHole(dealerHand[0]);
            yield return new WaitForSeconds(0.6f);

            // Dealer hits until ≥ 17 (Vegas soft-17 rule: hit on soft-17)
            while (HandValue(dealerHand) < 17)
            {
                yield return DealCardTo(false);
                yield return new WaitForSeconds(0.5f);
            }

            pitBoss.LogAction("DEALER_STAND", dealerHand);
            TransitionTo(GameState.RESOLVE);
        }

        private IEnumerator DealCardTo(bool isPlayer)
        {
            var card = deckController.Deal();
            if (isPlayer) playerHand.Add(card);
            else          dealerHand.Add(card);
            OnCardDealt?.Invoke(card, isPlayer);
            yield return new WaitForSeconds(0.05f);
        }

        private IEnumerator PayoutAndReset()
        {
            yield return new WaitForSeconds(1.5f);
            saveSystem.Save();
            yield return new WaitForSeconds(0.5f);
            TransitionTo(GameState.IDLE);
        }

        // --------------------------------------------------------
        // RESOLVE LOGIC
        // --------------------------------------------------------

        private void ResolveRound()
        {
            int pv = HandValue(playerHand);
            int dv = HandValue(dealerHand);
            bool playerBust  = pv > 21;
            bool dealerBust  = dv > 21;
            bool playerBJ    = IsBlackjack(playerHand);
            bool dealerBJ    = IsBlackjack(dealerHand);

            RoundResult result;

            if (playerBust)
            {
                result = RoundResult.BUST;
            }
            else if (dealerBust)
            {
                result = RoundResult.WIN;
            }
            else if (playerBJ && !dealerBJ)
            {
                result = RoundResult.BLACKJACK;
            }
            else if (dealerBJ && !playerBJ)
            {
                result = RoundResult.DEALER_BLACKJACK;
            }
            else if (pv > dv)
            {
                result = RoundResult.WIN;
            }
            else if (pv < dv)
            {
                result = RoundResult.LOSE;
            }
            else
            {
                result = RoundResult.PUSH;
            }

            int payout = CalculatePayout(result);
            PlayerProfile.Instance.AddChips(payout);

            // Award Clout XP
            PlayerProfile.Instance.AddCloutXP(CloutXPForResult(result));

            pitBoss.LogResult(result, pv, dv, currentBet, payout);
            OnRoundResolved?.Invoke(result);
            uiManager.ShowResult(result, payout);

            TransitionTo(GameState.PAYOUT);
        }

        private int CalculatePayout(RoundResult result)
        {
            return result switch
            {
                RoundResult.BLACKJACK        => Mathf.RoundToInt(currentBet * 2.5f),  // 3:2
                RoundResult.WIN              => currentBet * 2,
                RoundResult.PUSH             => currentBet,
                RoundResult.BUST             => 0,
                RoundResult.LOSE             => 0,
                RoundResult.DEALER_BLACKJACK => 0,
                _                            => 0
            };
        }

        private int CloutXPForResult(RoundResult result)
        {
            return result switch
            {
                RoundResult.BLACKJACK => 50,
                RoundResult.WIN       => 20,
                RoundResult.PUSH      => 5,
                _                     => 2
            };
        }

        // --------------------------------------------------------
        // HELPERS
        // --------------------------------------------------------

        public static int HandValue(List<CardData> hand)
        {
            int value = 0;
            int aces  = 0;
            foreach (var card in hand)
            {
                value += card.BlackjackValue;
                if (card.IsAce) aces++;
            }
            // Reduce aces from 11 → 1 to avoid bust
            while (value > 21 && aces > 0)
            {
                value -= 10;
                aces--;
            }
            return value;
        }

        private bool IsBlackjack(List<CardData> hand)
            => hand.Count == 2 && HandValue(hand) == 21;

        private bool CanDoubleDown()
            => playerHand.Count == 2 && PlayerProfile.Instance.Chips >= currentBet;

        private bool CanSplit()
            => playerHand.Count == 2 && playerHand[0].Rank == playerHand[1].Rank
               && PlayerProfile.Instance.Chips >= currentBet;

        private void ResetRound()
        {
            playerHand.Clear();
            dealerHand.Clear();
            currentBet   = 0;
            isDoubleDown = false;
            isSplit      = false;
        }
    }

    public enum RoundResult
    {
        WIN,
        LOSE,
        PUSH,
        BUST,
        BLACKJACK,
        DEALER_BLACKJACK
    }
}
