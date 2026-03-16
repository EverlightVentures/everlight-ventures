// ============================================================
// TableConfigSO.cs  --  Table limits, payouts, house rules
// Create via: Assets > Create > BlackjackVegas > TableConfig
// ============================================================
using UnityEngine;

namespace BlackjackVegas
{
    [CreateAssetMenu(fileName = "TableConfig_", menuName = "BlackjackVegas/TableConfig")]
    public class TableConfigSO : ScriptableObject
    {
        [Header("Bet Limits")]
        public int minBet       = 100;
        public int maxBet       = 10000;
        public int vipMinBet    = 1000;     // VIP table minimum

        [Header("Payouts")]
        public float blackjackPayout = 1.5f;    // standard 3:2
        public float insurancePayout = 2.0f;

        [Header("House Rules")]
        public bool dealerHitsOnSoft17  = true;  // Vegas strip rules
        public bool allowDoubleAfterSplit = true;
        public bool allowResplit         = true;
        public int  maxSplits            = 3;
        public bool allowSurrender       = false;

        [Header("Table Tier")]
        public TableTier tier    = TableTier.Standard;
        public string tableName  = "Main Floor";
        public int entryCostGems = 0;         // 0 = free, >0 = VIP gem door fee

        [Header("Subscription Gate")]
        public SubscriptionTier requiredSub = SubscriptionTier.Free;
    }

    public enum TableTier { Standard, Gold, VegasNight, HighRoller }
    public enum SubscriptionTier { Free, GoldTable, VIPPit }
}
