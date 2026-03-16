// ============================================================
// UIManager.cs  --  Single-source UI controller
// Wires state machine events to Canvas panels + DOTween anims
// Install DOTween (free) from Unity Asset Store before using
// ============================================================
using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
// using DG.Tweening;   // Uncomment after DOTween install

namespace BlackjackVegas
{
    public class UIManager : MonoBehaviour
    {
        public static UIManager Instance { get; private set; }

        [Header("Panels")]
        [SerializeField] private GameObject panelIdle;
        [SerializeField] private GameObject panelBetting;
        [SerializeField] private GameObject panelGame;
        [SerializeField] private GameObject panelResult;
        [SerializeField] private GameObject panelShop;
        [SerializeField] private GameObject panelLeaderboard;
        [SerializeField] private GameObject panelVIPUpsell;
        [SerializeField] private GameObject panelError;

        [Header("HUD")]
        [SerializeField] private TextMeshProUGUI txtChips;
        [SerializeField] private TextMeshProUGUI txtGems;
        [SerializeField] private TextMeshProUGUI txtCloutLevel;
        [SerializeField] private TextMeshProUGUI txtPlayerHand;
        [SerializeField] private TextMeshProUGUI txtDealerHand;
        [SerializeField] private TextMeshProUGUI txtResultLabel;
        [SerializeField] private TextMeshProUGUI txtErrorMessage;

        [Header("Betting UI")]
        [SerializeField] private Slider betSlider;
        [SerializeField] private TextMeshProUGUI txtBetAmount;
        [SerializeField] private Button btnDeal;

        [Header("Player Action Buttons")]
        [SerializeField] private Button btnHit;
        [SerializeField] private Button btnStand;
        [SerializeField] private Button btnDouble;
        [SerializeField] private Button btnSplit;

        [Header("Card Zones")]
        [SerializeField] private Transform playerHandZone;
        [SerializeField] private Transform dealerHandZone;
        [SerializeField] private GameObject cardPrefab;   // Prefab with front/back sprites

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
        }

        void Start()
        {
            // Subscribe to game events
            GameManager.Instance.OnCardDealt.AddListener(OnCardDealt);
            GameManager.Instance.OnStateChanged.AddListener(OnStateChanged);
            GameManager.Instance.OnRoundResolved.AddListener(OnRoundResolved);
            PlayerProfile.Instance.OnCloutLevelUp += OnCloutLevelUp;

            RefreshHUD();
        }

        // --------------------------------------------------------
        // State-driven UI switching
        // --------------------------------------------------------

        private void OnStateChanged(GameState state)
        {
            switch (state)
            {
                case GameState.IDLE:        ShowIdleScreen();   break;
                case GameState.BETTING:     /* handled via ShowBettingUI */ break;
                case GameState.DEALER_TURN: DisablePlayerActions(); break;
            }
        }

        public void ShowIdleScreen()
        {
            SetActivePanel(panelIdle);
            RefreshHUD();
        }

        public void ShowBettingUI(int minBet, int maxBet, int chips)
        {
            SetActivePanel(panelBetting);
            betSlider.minValue = minBet;
            betSlider.maxValue = Mathf.Min(maxBet, chips);
            betSlider.value    = minBet;
            txtBetAmount.text  = $"${minBet:N0}";
            betSlider.onValueChanged.AddListener(v => txtBetAmount.text = $"${(int)v:N0}");
            SetActivePanel(panelGame);
        }

        public void ShowPlayerActions(bool canDouble, bool canSplit)
        {
            btnHit.interactable    = true;
            btnStand.interactable  = true;
            btnDouble.interactable = canDouble;
            btnSplit.interactable  = canSplit;
        }

        public void DisablePlayerActions()
        {
            btnHit.interactable   = false;
            btnStand.interactable = false;
            btnDouble.interactable = false;
            btnSplit.interactable  = false;
        }

        public void ShowResult(RoundResult result, int payout)
        {
            SetActivePanel(panelResult);
            txtResultLabel.text = result switch
            {
                RoundResult.BLACKJACK        => "BLACKJACK!",
                RoundResult.WIN              => $"YOU WIN  +${payout:N0}",
                RoundResult.PUSH             => "PUSH -- BET RETURNED",
                RoundResult.BUST             => "BUST",
                RoundResult.LOSE             => "DEALER WINS",
                RoundResult.DEALER_BLACKJACK => "DEALER BLACKJACK",
                _                            => ""
            };
            // DOTween: txtResultLabel.DOScale(1.3f, 0.2f).SetLoops(2, LoopType.Yoyo);
            RefreshHUD();
        }

        public void ShowError(string msg)
        {
            txtErrorMessage.text = msg;
            panelError.SetActive(true);
            StartCoroutine(HideErrorAfter(2.5f));
        }

        public void ShowVIPUpsell() => SetActivePanel(panelVIPUpsell);
        public void ShowShop()       => SetActivePanel(panelShop);
        public void ShowLeaderboard() => SetActivePanel(panelLeaderboard);

        public void RevealDealerHole(CardData card)
        {
            // Flip the hole card in dealerHandZone
            // DOTween: card.transform.DORotate(new Vector3(0,90,0), 0.2f)
            //   .OnComplete(() => { flipSprite; DORotate back });
            Debug.Log($"[UI] Dealer hole revealed: {card.ShortCode}");
        }

        // --------------------------------------------------------
        // Card dealt animation hook
        // --------------------------------------------------------

        private void OnCardDealt(CardData card, bool isPlayer)
        {
            Transform zone = isPlayer ? playerHandZone : dealerHandZone;
            var cardObj    = Instantiate(cardPrefab, zone);

            // TODO: set front sprite from card, animate slide with DOTween
            // cardObj.transform.position = dealZone.position;
            // cardObj.transform.DOMove(zone.position, 0.3f).SetEase(Ease.OutCubic);

            RefreshHUD();
        }

        // --------------------------------------------------------
        // Round resolved
        // --------------------------------------------------------

        private void OnRoundResolved(RoundResult result)
        {
            PlayerProfile.Instance.RecordHand(result);
            RefreshHUD();
        }

        // --------------------------------------------------------
        // Clout level-up fanfare
        // --------------------------------------------------------

        private void OnCloutLevelUp(int newLevel)
        {
            Debug.Log($"[UI] CLOUT LEVEL UP → {newLevel}!");
            // Trigger particle burst, sound, banner
        }

        // --------------------------------------------------------
        // HUD refresh
        // --------------------------------------------------------

        private void RefreshHUD()
        {
            if (PlayerProfile.Instance == null) return;
            txtChips.text      = $"${PlayerProfile.Instance.Chips:N0}";
            txtGems.text       = $"{PlayerProfile.Instance.Gems:N0} GEMS";
            txtCloutLevel.text = $"LVL {PlayerProfile.Instance.CloutLevel}";
        }

        // --------------------------------------------------------
        // Helpers
        // --------------------------------------------------------

        private void SetActivePanel(GameObject target)
        {
            panelIdle?.SetActive(false);
            panelBetting?.SetActive(false);
            panelGame?.SetActive(false);
            panelResult?.SetActive(false);
            panelShop?.SetActive(false);
            panelLeaderboard?.SetActive(false);
            panelVIPUpsell?.SetActive(false);
            target?.SetActive(true);
        }

        private IEnumerator HideErrorAfter(float seconds)
        {
            yield return new WaitForSeconds(seconds);
            panelError?.SetActive(false);
        }
    }
}
