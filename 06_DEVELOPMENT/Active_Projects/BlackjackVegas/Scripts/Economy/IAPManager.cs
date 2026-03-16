// ============================================================
// IAPManager.cs  --  Unity IAP bridge (subscriptions + gems)
// Requires: com.unity.purchasing from Package Manager
// Supports: WebGL via Stripe Checkout redirect
// ============================================================
using System;
using System.Collections.Generic;
using UnityEngine;
// using UnityEngine.Purchasing;       // Uncomment after IAP install
// using UnityEngine.Purchasing.Extension;

namespace BlackjackVegas
{
    // ---- Subscription product IDs (match App Store / Stripe) ----
    public static class ProductIDs
    {
        // Gems (consumable)
        public const string GEMS_100   = "bj_gems_100";
        public const string GEMS_500   = "bj_gems_500";
        public const string GEMS_1200  = "bj_gems_1200";
        public const string GEMS_6500  = "bj_gems_6500";

        // Subscriptions (non-consumable / renewable)
        public const string SUB_GOLD   = "bj_sub_gold_monthly";    // $4.99/mo
        public const string SUB_VIP    = "bj_sub_vip_monthly";     // $9.99/mo
    }

    // ---- Gem bundle definitions ----
    public static class GemBundleDefs
    {
        public static readonly Dictionary<string, int> GemAmounts = new Dictionary<string, int>
        {
            { ProductIDs.GEMS_100,  100  },   // $0.99
            { ProductIDs.GEMS_500,  550  },   // $4.99  (+10% bonus)
            { ProductIDs.GEMS_1200, 1400 },   // $9.99  (+16% bonus)
            { ProductIDs.GEMS_6500, 8000 },   // $49.99 (+23% bonus -- BEST VALUE)
        };
    }

    // --------------------------------------------------------

    public class IAPManager : MonoBehaviour  // , IStoreListener
    {
        public static IAPManager Instance { get; private set; }

        // private IStoreController   storeController;
        // private IExtensionProvider extensions;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
            InitIAP();
        }

        private void InitIAP()
        {
            // TODO: uncomment when Unity IAP package is installed
            /*
            var builder = ConfigurationBuilder.Instance(StandardPurchasingModule.Instance());

            // Gem bundles
            builder.AddProduct(ProductIDs.GEMS_100,  ProductType.Consumable);
            builder.AddProduct(ProductIDs.GEMS_500,  ProductType.Consumable);
            builder.AddProduct(ProductIDs.GEMS_1200, ProductType.Consumable);
            builder.AddProduct(ProductIDs.GEMS_6500, ProductType.Consumable);

            // Subscriptions
            builder.AddProduct(ProductIDs.SUB_GOLD,  ProductType.Subscription);
            builder.AddProduct(ProductIDs.SUB_VIP,   ProductType.Subscription);

            UnityPurchasing.Initialize(this, builder);
            */
            Debug.Log("[IAP] Init stub -- install com.unity.purchasing to activate");
        }

        public void BuyProduct(string productId)
        {
            // storeController?.InitiatePurchase(productId);
            Debug.Log($"[IAP] Purchase initiated: {productId}");

            // DEVELOPMENT STUB -- simulate purchase for testing
#if UNITY_EDITOR
            SimulatePurchase(productId);
#endif
        }

        private void SimulatePurchase(string productId)
        {
            if (GemBundleDefs.GemAmounts.TryGetValue(productId, out int gems))
            {
                GemManager.Instance?.OnGemBundlePurchased(productId);
                Debug.Log($"[IAP] SIMULATED: +{gems} gems");
                return;
            }
            if (productId == ProductIDs.SUB_GOLD)
            {
                Debug.Log("[IAP] SIMULATED: Gold Table subscription activated");
                return;
            }
            if (productId == ProductIDs.SUB_VIP)
            {
                Debug.Log("[IAP] SIMULATED: VIP Pit subscription activated");
            }
        }

        // IStoreListener callbacks -- uncomment with IAP package
        /*
        public void OnInitialized(IStoreController controller, IExtensionProvider extensions)
        {
            storeController = controller;
            this.extensions = extensions;
            Debug.Log("[IAP] Initialized");
        }

        public void OnInitializeFailed(InitializationFailureReason error)
            => Debug.LogError($"[IAP] Init failed: {error}");

        public PurchaseProcessingResult ProcessPurchase(PurchaseEventArgs args)
        {
            string id = args.purchasedProduct.definition.id;

            if (GemBundleDefs.GemAmounts.ContainsKey(id))
                GemManager.Instance?.OnGemBundlePurchased(id);
            else if (id is ProductIDs.SUB_GOLD or ProductIDs.SUB_VIP)
                ActivateSubscription(id);

            return PurchaseProcessingResult.Complete;
        }

        public void OnPurchaseFailed(Product product, PurchaseFailureReason reason)
            => Debug.LogError($"[IAP] Purchase failed: {product.definition.id} -- {reason}");
        */

        private void ActivateSubscription(string subId)
        {
            // Set subscription tier + expiry in PlayerProfile
            Debug.Log($"[IAP] Subscription activated: {subId}");
        }
    }
}
