using UnityEngine;
using UnityEngine.EventSystems;
using ArenaAdvance.Managers;
using ArenaAdvance.Gameplay;
using ArenaAdvance.UI;

namespace ArenaAdvance.Core
{
    /// <summary>
    /// Handles touch/mouse input for card deployment during battles
    /// </summary>
    public class BattleInputHandler : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Camera battleCamera;
        [SerializeField] private BattleHUD battleHUD;
        [SerializeField] private LayerMask groundLayer;

        [Header("Drag Settings")]
        [SerializeField] private float dragThreshold = 10f;
        [SerializeField] private GameObject cardPreviewPrefab;
        [SerializeField] private Color validPlacementColor = new Color(0, 1, 0, 0.5f);
        [SerializeField] private Color invalidPlacementColor = new Color(1, 0, 0, 0.5f);

        [Header("Arena Bounds")]
        [SerializeField] private float minX = -8f;
        [SerializeField] private float maxX = 8f;
        [SerializeField] private float playerMinY = -14f;
        [SerializeField] private float playerMaxY = -1f;

        private BattleManager battleManager;
        private bool isDragging;
        private Vector2 dragStartPos;
        private GameObject currentPreview;
        private SpriteRenderer previewRenderer;

        private void Start()
        {
            battleManager = BattleManager.Instance;

            if (battleCamera == null)
                battleCamera = Camera.main;

            if (cardPreviewPrefab != null)
            {
                currentPreview = Instantiate(cardPreviewPrefab);
                currentPreview.SetActive(false);
                previewRenderer = currentPreview.GetComponent<SpriteRenderer>();
            }
        }

        private void Update()
        {
            if (battleManager?.State == null) return;
            if (battleManager.State.phase == BattlePhase.Countdown ||
                battleManager.State.phase == BattlePhase.Ended)
                return;

            HandleInput();
        }

        private void HandleInput()
        {
            // Handle both touch and mouse input
            if (Input.touchCount > 0)
            {
                HandleTouchInput();
            }
            else
            {
                HandleMouseInput();
            }
        }

        private void HandleTouchInput()
        {
            Touch touch = Input.GetTouch(0);

            switch (touch.phase)
            {
                case TouchPhase.Began:
                    OnInputDown(touch.position);
                    break;

                case TouchPhase.Moved:
                case TouchPhase.Stationary:
                    OnInputDrag(touch.position);
                    break;

                case TouchPhase.Ended:
                case TouchPhase.Canceled:
                    OnInputUp(touch.position);
                    break;
            }
        }

        private void HandleMouseInput()
        {
            if (Input.GetMouseButtonDown(0))
            {
                OnInputDown(Input.mousePosition);
            }
            else if (Input.GetMouseButton(0))
            {
                OnInputDrag(Input.mousePosition);
            }
            else if (Input.GetMouseButtonUp(0))
            {
                OnInputUp(Input.mousePosition);
            }
        }

        private void OnInputDown(Vector2 screenPos)
        {
            // Check if we're over UI
            if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject())
            {
                return;
            }

            dragStartPos = screenPos;
            isDragging = false;

            // Check if a card is selected
            if (battleHUD != null && battleHUD.HasSelectedCard)
            {
                isDragging = true;
                ShowPreview(screenPos);
            }
        }

        private void OnInputDrag(Vector2 screenPos)
        {
            if (!isDragging) return;

            // Check if we've moved enough to consider this a drag
            if (Vector2.Distance(screenPos, dragStartPos) < dragThreshold)
                return;

            UpdatePreview(screenPos);
        }

        private void OnInputUp(Vector2 screenPos)
        {
            if (isDragging && battleHUD != null && battleHUD.HasSelectedCard)
            {
                Vector3 worldPos = ScreenToWorldPosition(screenPos);

                if (IsValidPlacement(worldPos))
                {
                    // Play the card
                    bool success = battleManager.TryPlayCard(0, battleHUD.SelectedCardIndex, worldPos);

                    if (success)
                    {
                        battleHUD.ClearSelection();
                    }
                }
            }

            isDragging = false;
            HidePreview();
        }

        private void ShowPreview(Vector2 screenPos)
        {
            if (currentPreview == null) return;

            currentPreview.SetActive(true);
            UpdatePreview(screenPos);
        }

        private void UpdatePreview(Vector2 screenPos)
        {
            if (currentPreview == null) return;

            Vector3 worldPos = ScreenToWorldPosition(screenPos);

            // Clamp to arena bounds
            worldPos.x = Mathf.Clamp(worldPos.x, minX, maxX);
            worldPos.y = Mathf.Clamp(worldPos.y, playerMinY, playerMaxY);
            worldPos.z = 0;

            currentPreview.transform.position = worldPos;

            // Update color based on validity
            if (previewRenderer != null)
            {
                previewRenderer.color = IsValidPlacement(worldPos)
                ? validPlacementColor
                : invalidPlacementColor;
            }
        }

        private void HidePreview()
        {
            if (currentPreview != null)
            {
                currentPreview.SetActive(false);
            }
        }

        private Vector3 ScreenToWorldPosition(Vector2 screenPos)
        {
            if (battleCamera == null)
                return Vector3.zero;

            // For 2D games
            Vector3 worldPos = battleCamera.ScreenToWorldPoint(
                new Vector3(screenPos.x, screenPos.y, -battleCamera.transform.position.z)
            );
            worldPos.z = 0;

            return worldPos;
        }

        private bool IsValidPlacement(Vector3 worldPos)
        {
            // Check arena bounds
            if (worldPos.x < minX || worldPos.x > maxX)
                return false;

            // Check player's spawn zone
            if (worldPos.y < playerMinY || worldPos.y > playerMaxY)
                return false;

            // Could add additional checks:
            // - Not too close to existing units
            // - Not on obstacles
            // - etc.

            return true;
        }

        /// <summary>
        /// Quick play: tap a card then tap the arena
        /// </summary>
        public void OnArenaClicked(Vector3 worldPos)
        {
            if (battleHUD == null || !battleHUD.HasSelectedCard)
                return;

            if (!IsValidPlacement(worldPos))
                return;

            bool success = battleManager.TryPlayCard(0, battleHUD.SelectedCardIndex, worldPos);

            if (success)
            {
                battleHUD.ClearSelection();
            }
        }
    }

    /// <summary>
    /// Simple gesture recognizer for swipe-to-emote, etc.
    /// </summary>
    public class GestureRecognizer : MonoBehaviour
    {
        [SerializeField] private float swipeThreshold = 50f;
        [SerializeField] private float swipeTimeout = 0.5f;

        public event System.Action OnSwipeUp;
        public event System.Action OnSwipeDown;
        public event System.Action OnSwipeLeft;
        public event System.Action OnSwipeRight;
        public event System.Action OnDoubleTap;

        private Vector2 touchStartPos;
        private float touchStartTime;
        private float lastTapTime;

        private void Update()
        {
            if (Input.touchCount == 1)
            {
                Touch touch = Input.GetTouch(0);

                switch (touch.phase)
                {
                    case TouchPhase.Began:
                        touchStartPos = touch.position;
                        touchStartTime = Time.time;

                        // Check for double tap
                        if (Time.time - lastTapTime < 0.3f)
                        {
                            OnDoubleTap?.Invoke();
                        }
                        break;

                    case TouchPhase.Ended:
                        lastTapTime = Time.time;

                        // Check for swipe
                        if (Time.time - touchStartTime < swipeTimeout)
                        {
                            Vector2 swipe = touch.position - touchStartPos;

                            if (swipe.magnitude > swipeThreshold)
                            {
                                DetectSwipeDirection(swipe);
                            }
                        }
                        break;
                }
            }
        }

        private void DetectSwipeDirection(Vector2 swipe)
        {
            // Determine primary direction
            if (Mathf.Abs(swipe.x) > Mathf.Abs(swipe.y))
            {
                // Horizontal swipe
                if (swipe.x > 0)
                    OnSwipeRight?.Invoke();
                else
                    OnSwipeLeft?.Invoke();
            }
            else
            {
                // Vertical swipe
                if (swipe.y > 0)
                    OnSwipeUp?.Invoke();
                else
                    OnSwipeDown?.Invoke();
            }
        }
    }
}
