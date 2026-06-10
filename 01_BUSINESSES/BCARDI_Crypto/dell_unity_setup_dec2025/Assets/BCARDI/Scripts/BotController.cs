using UnityEngine;

namespace BCARDI
{
    public sealed class BotController : MonoBehaviour
    {
        public EnergySystem Energy;
        public int DeckIndex = 1;
        public float PlayInterval = 2.0f;
        private string[] _cards = new string[0];
        private float _timer;

        private void Start()
        {
            if (GameConfig.Instance != null && GameConfig.Instance.Decks.Count > DeckIndex)
            {
                _cards = GameConfig.Instance.Decks[DeckIndex].Cards.ToArray();
            }
        }

        private void Update()
        {
            if (_cards.Length == 0 || Energy == null) return;
            _timer += Time.deltaTime;
            if (_timer < PlayInterval) return;
            _timer = 0f;

            int index = Random.Range(0, _cards.Length);
            string cardName = _cards[index];
            if (!GameConfig.Instance.CardsByName.TryGetValue(cardName, out var card)) return;
            if (!Energy.Spend(card.Cost)) return;

            int lane = Random.Range(0, 3);
            ArenaManager.Instance.SpawnUnit(cardName, Team.Enemy, lane);
        }
    }
}
