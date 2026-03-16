// ============================================================
// GemManager.cs  --  Gem shop + IAP bridge
// Gems are the hard currency. Players buy with real money,
// spend on cosmetics, VIP table access, and status items.
// ============================================================
using System.Collections.Generic;
using UnityEngine;

namespace BlackjackVegas
{
    [System.Serializable]
    public class GemBundle
    {
        public string   id;             // "gems_100", "gems_500", etc.
        public string   displayName;    // "Starter Pack"
        public int      gemAmount;
        public float    usdPrice;
        public bool     isBestValue;
        public Sprite   icon;
    }

    [System.Serializable]
    public class ShopItem
    {
        public string   id;
        public string   displayName;
        public string   category;       // "card_back", "table_felt", "avatar", "chips"
        public int      gemCost;
        public int      chipCost;       // 0 = gems only
        public bool     isVIPOnly;
        public Sprite   preview;
    }

    [CreateAssetMenu(fileName = "GemShopConfig", menuName = "BlackjackVegas/GemShopConfig")]
    public class GemShopConfigSO : ScriptableObject
    {
        public List<GemBundle> bundles  = new List<GemBundle>();
        public List<ShopItem>  items    = new List<ShopItem>();
    }

    // --------------------------------------------------------

    public class GemManager : MonoBehaviour
    {
        public static GemManager Instance { get; private set; }

        [SerializeField] private GemShopConfigSO shopConfig;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
        }

        // Called by Unity IAP on successful purchase
        public void OnGemBundlePurchased(string bundleId)
        {
            var bundle = shopConfig.bundles.Find(b => b.id == bundleId);
            if (bundle == null)
            {
                Debug.LogError($"[Gems] Unknown bundle: {bundleId}");
                return;
            }
            PlayerProfile.Instance.AddGems(bundle.gemAmount);
            Debug.Log($"[Gems] +{bundle.gemAmount} gems from {bundle.displayName}");
            PitBossAuditor.Instance?.LogPurchase(bundleId, bundle.usdPrice, bundle.gemAmount);
        }

        public bool PurchaseItem(string itemId)
        {
            var item = shopConfig.items.Find(i => i.id == itemId);
            if (item == null) { Debug.LogError($"[Shop] Unknown item: {itemId}"); return false; }

            if (item.isVIPOnly && PlayerProfile.Instance.ActiveSubscription == SubscriptionTier.Free)
            {
                Debug.LogWarning("[Shop] VIP item -- show upsell modal");
                UIManager.Instance?.ShowVIPUpsell();
                return false;
            }

            // Try gems first, fallback to chips
            if (item.gemCost > 0)
            {
                if (!PlayerProfile.Instance.SpendGems(item.gemCost, itemId)) return false;
            }
            else if (item.chipCost > 0)
            {
                if (!PlayerProfile.Instance.DeductChips(item.chipCost)) return false;
            }

            // Unlock in player profile
            if (item.category == "card_back") PlayerProfile.Instance.UnlockCardBack(item.id);
            Debug.Log($"[Shop] Purchased: {item.displayName}");
            return true;
        }

        // --------------------------------------------------------
        // Gem-to-Chip conversion (safety valve for broke players)
        // --------------------------------------------------------
        public bool ConvertGemsToChips(int gemAmount)
        {
            int chipYield = gemAmount * 1000;   // 1 gem = 1,000 chips
            if (!PlayerProfile.Instance.SpendGems(gemAmount, "gem_to_chip_swap")) return false;
            PlayerProfile.Instance.AddChips(chipYield);
            return true;
        }
    }
}
