// ============================================================
// PitBossAuditor.cs  --  Logs every action to JSONL audit trail
// As a real Vegas pit boss: watches for anomalies, logs replays
// Output: StreamingAssets/game_audit.jsonl (or server endpoint)
// ============================================================
using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using UnityEngine;

namespace BlackjackVegas
{
    [Serializable]
    public class AuditEvent
    {
        public string   ts;         // ISO8601 timestamp
        public string   sessionId;
        public string   playerId;
        public string   eventType;  // BET, DEAL, HIT, STAND, DOUBLE, RESULT, PURCHASE
        public string   detail;     // JSON blob
    }

    public class PitBossAuditor : MonoBehaviour
    {
        public static PitBossAuditor Instance { get; private set; }

        private string sessionId;
        private string logPath;
        private StringBuilder buffer = new StringBuilder();
        private int flushEveryN = 5;
        private int eventCount  = 0;

        void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            sessionId = Guid.NewGuid().ToString("N")[..8];

#if UNITY_WEBGL && !UNITY_EDITOR
            // WebGL can't write local files -- buffer in memory, POST to server
            logPath = null;
#else
            logPath = Path.Combine(Application.streamingAssetsPath, "game_audit.jsonl");
            Directory.CreateDirectory(Path.GetDirectoryName(logPath));
#endif
            Debug.Log($"[PitBoss] Session {sessionId} open");
        }

        void OnApplicationQuit() => Flush();

        // --------------------------------------------------------
        // Public log methods
        // --------------------------------------------------------

        public void LogBet(int amount)
            => Write("BET", $"{{\"amount\":{amount}}}");

        public void LogDeal(List<CardData> player, List<CardData> dealer)
            => Write("DEAL", $"{{\"player\":\"{HandString(player)}\",\"dealer_up\":\"{dealer[1].ShortCode}\"}}");

        public void LogAction(string action, List<CardData> hand)
            => Write(action, $"{{\"hand\":\"{HandString(hand)}\",\"value\":{GameManager.HandValue(hand)}}}");

        public void LogBust(string who)
            => Write("BUST", $"{{\"who\":\"{who}\"}}");

        public void LogResult(RoundResult result, int pv, int dv, int bet, int payout)
        {
            Write("RESULT", $"{{\"result\":\"{result}\",\"playerValue\":{pv},\"dealerValue\":{dv},\"bet\":{bet},\"payout\":{payout}}}");

            // Anomaly detection: flag if payout math looks off
            if (result == RoundResult.WIN && payout != bet * 2)
                Debug.LogWarning($"[PitBoss] ANOMALY: WIN but payout={payout} bet={bet}");
        }

        public void LogPurchase(string itemId, float usdAmount, int gems)
            => Write("PURCHASE", $"{{\"item\":\"{itemId}\",\"usd\":{usdAmount},\"gems\":{gems}}}");

        // --------------------------------------------------------
        // Internal
        // --------------------------------------------------------

        private void Write(string eventType, string detail)
        {
            var ev = new AuditEvent
            {
                ts        = DateTime.UtcNow.ToString("o"),
                sessionId = sessionId,
                playerId  = PlayerProfile.Instance?.name ?? "anon",
                eventType = eventType,
                detail    = detail
            };
            string line = JsonUtility.ToJson(ev);
            buffer.AppendLine(line);
            eventCount++;

            if (eventCount % flushEveryN == 0) Flush();
        }

        private void Flush()
        {
            if (buffer.Length == 0) return;
            string data = buffer.ToString();
            buffer.Clear();

            if (logPath != null)
            {
                File.AppendAllText(logPath, data);
            }
            else
            {
                // WebGL: POST to audit endpoint
                // StartCoroutine(PostAuditLog(data));
                Debug.Log($"[PitBoss] Audit buffer ({data.Length} chars) -- POST not wired yet");
            }
        }

        private string HandString(List<CardData> hand)
        {
            var sb = new StringBuilder();
            foreach (var c in hand) sb.Append(c.ShortCode).Append(' ');
            return sb.ToString().Trim();
        }
    }
}
