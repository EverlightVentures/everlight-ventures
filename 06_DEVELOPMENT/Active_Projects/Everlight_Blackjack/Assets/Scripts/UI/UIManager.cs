using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Blackjack.Core;

namespace Blackjack.UI
{
    // UIManager only reads GameManager state via events.
    // It never writes game state directly.
    public class UIManager : MonoBehaviour
    {
        [Header("GameManager")]
        public GameManager gameManager;

        [Header("Buttons")]
        public Button dealButton;
        public Button hitButton;
        public Button standButton;

        [Header("Bet Input")]
        public TMP_InputField betInput;

        [Header("Labels")]
        public TMP_Text messageText;
        public TMP_Text moneyText;
        public TMP_Text potText;
        public TMP_Text playerScoreText;
        public TMP_Text dealerScoreText;

        void Start()
        {
            // Wire buttons
            dealButton.onClick.AddListener(OnDealClicked);
            hitButton.onClick.AddListener(OnHitClicked);
            standButton.onClick.AddListener(OnStandClicked);

            // Subscribe to GameManager events
            gameManager.onStateChanged.AddListener(OnStateChanged);
            gameManager.onMessage.AddListener(msg => messageText.text = msg);
            gameManager.onMoneyChanged.AddListener(amt => moneyText.text  = $"Money: ${amt}");
            gameManager.onPotChanged.AddListener(amt  => potText.text     = $"Pot: ${amt}");

            // Initial UI state
            OnStateChanged(GameState.Betting);
            moneyText.text = $"Money: ${gameManager.Money}";
            potText.text   = "Pot: $0";
        }

        void Update()
        {
            // Refresh score labels each frame (cheap text update)
            if (gameManager.playerHand != null)
                playerScoreText.text = $"Player: {gameManager.playerHand.Value()}";
            if (gameManager.dealerHand != null)
                dealerScoreText.text = $"Dealer: {gameManager.dealerHand.Value()}";
        }

        // --- Button handlers ---

        private void OnDealClicked()
        {
            if (!int.TryParse(betInput.text, out int bet))
            {
                messageText.text = "Enter a valid bet amount.";
                return;
            }
            gameManager.PlaceBet(bet);
        }

        private void OnHitClicked()   => gameManager.Hit();
        private void OnStandClicked() => gameManager.Stand();

        // --- State-driven button visibility ---

        private void OnStateChanged(GameState state)
        {
            bool betting      = state == GameState.Betting;
            bool playerTurn   = state == GameState.PlayerTurn;

            dealButton.gameObject.SetActive(betting);
            betInput.gameObject.SetActive(betting);
            hitButton.gameObject.SetActive(playerTurn);
            standButton.gameObject.SetActive(playerTurn);
        }
    }
}
