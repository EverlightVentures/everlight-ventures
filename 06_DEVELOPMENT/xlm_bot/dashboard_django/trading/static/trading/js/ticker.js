/**
 * Live spot price ticker -- fetches from Coinbase public API.
 * Display-only; does not affect bot trading logic.
 */
(function() {
  const PRODUCT_ID = 'XLM-USD';
  const INTERVAL_MS = 2000;
  const URL = `https://api.exchange.coinbase.com/products/${PRODUCT_ID}/ticker`;

  let lastPrice = 0;
  let lastTime = 0;
  let prevPrice = 0;

  const priceEl = document.getElementById('live-price');
  const ageEl = document.getElementById('live-price-age');

  if (!priceEl) return;

  async function tick() {
    try {
      const r = await fetch(URL, { cache: 'no-store' });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const j = await r.json();
      const p = Number(j.price);
      if (!Number.isFinite(p)) throw new Error('bad price');

      prevPrice = lastPrice;
      lastPrice = p;
      lastTime = Date.now();

      priceEl.textContent = '$' + p.toFixed(6);

      // Flash green/red on change
      if (prevPrice && prevPrice !== p) {
        priceEl.style.color = p > prevPrice ? '#34d399' : '#f87171';
        setTimeout(() => { priceEl.style.color = '#e5e7eb'; }, 800);
      }
    } catch (e) {
      // Silently fail -- price stays at last known value
    }
  }

  function updateAge() {
    if (!ageEl || !lastTime) return;
    const age = Math.floor((Date.now() - lastTime) / 1000);
    ageEl.textContent = age + 's ago';
  }

  tick();
  setInterval(tick, INTERVAL_MS);
  setInterval(updateAge, 1000);
})();
