using UnityEngine;

namespace BCARDI
{
    public sealed class HitFlash : MonoBehaviour
    {
        public float Lifetime = 0.25f;
        public Color Color = new Color(0.1f, 1f, 0.9f, 1f);

        private float _time;
        private SpriteRenderer _sprite;

        private void Awake()
        {
            _sprite = GetComponent<SpriteRenderer>();
            if (_sprite != null)
            {
                _sprite.color = Color;
            }
        }

        private void Update()
        {
            _time += Time.deltaTime;
            if (_sprite != null)
            {
                float t = 1f - (_time / Lifetime);
                _sprite.color = new Color(Color.r, Color.g, Color.b, t);
            }
            if (_time >= Lifetime)
            {
                Destroy(gameObject);
            }
        }
    }
}
