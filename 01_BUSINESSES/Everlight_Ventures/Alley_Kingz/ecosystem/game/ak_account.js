/* ==========================================================================
   ALLEY KINGZ -- ACCOUNT + CLOUD SAVE
   Google sign-in via Supabase Auth, mirroring the blackjack flow on the same
   Supabase project but as a fully SEPARATE product surface (own table, own
   localStorage namespace, no shared money rail).

   What it does:
   - "Sign in with Google" -> Supabase OAuth -> session.
   - ak_player_id = auth uid -> the Chop Shop flips from demo to online.
   - Cloud save: every ak_* localStorage key is mirrored into
     public.ak_player_saves (one jsonb row per user). Pulled on login
     (newest-wins vs local), pushed debounced on change + on pagehide.
   - Degrades silently: signed out = exactly today's localStorage game;
     table missing (migration pending) = console warn only, zero UI breakage.

   Vanilla JS + supabase-js v2 UMD. No bundler (phone-proot safe).
   Include on BOTH index.html and shop/shop.html, BEFORE shop.js.
   ========================================================================== */
(function (global) {
  "use strict";

  var SB_URL = "https://mfghdobptredxxhbjwyz.supabase.co";
  var SB_ANON = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1mZ2hkb2JwdHJlZHh4aGJqd3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEyMDMxOTUsImV4cCI6MjA5Njc3OTE5NX0.mThNDsN_ulCcFe8jvR7-Pmu15xcyUUlaKNaGWl5wc44";
  var CDN = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js";
  var TABLE = "ak_player_saves";

  // the anon key is public-by-design; exposing it arms the shop's online mode
  global.AK_SUPABASE_ANON_KEY = SB_ANON;

  var sb = null, user = null, pushTimer = null, lastSnapshot = "", pollTimer = null;

  function hasLS() { try { return typeof localStorage !== "undefined" && !!localStorage; } catch (_) { return false; } }

  // ---- snapshot every ak_* key (the whole game state lives there) ----------
  function snapshot() {
    var o = {};
    if (!hasLS()) return o;
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf("ak_") === 0 && k !== "ak_player_id" && k !== "ak_save_meta") o[k] = localStorage.getItem(k);
      }
    } catch (_) {}
    return o;
  }
  function applySnapshot(save) {
    if (!hasLS() || !save || typeof save !== "object") return;
    try {
      Object.keys(save).forEach(function (k) {
        if (k.indexOf("ak_") === 0) localStorage.setItem(k, String(save[k]));
      });
    } catch (_) {}
  }

  // ---- cloud pull/push ------------------------------------------------------
  function pull() {
    if (!sb || !user) return Promise.resolve(null);
    return sb.from(TABLE).select("save,saved_at").eq("user_id", user.id).maybeSingle()
      .then(function (r) {
        if (r.error) { console.warn("[ak_account] cloud pull:", r.error.message); return null; }
        return r.data || null;
      });
  }
  function push() {
    if (!sb || !user || !hasLS()) return;
    var save = snapshot();
    var snapStr = JSON.stringify(save);
    if (snapStr === lastSnapshot) return;        // nothing changed
    lastSnapshot = snapStr;
    var now = new Date().toISOString();
    sb.from(TABLE).upsert({ user_id: user.id, save: save, saved_at: now })
      .then(function (r) {
        if (r.error) console.warn("[ak_account] cloud push:", r.error.message);
        else { try { localStorage.setItem("ak_save_meta", now); } catch (_) {} }
      });
  }
  function schedulePush() { clearTimeout(pushTimer); pushTimer = setTimeout(push, 4000); }

  // change detection: poll the snapshot hash (works no matter which surface writes)
  function startWatch() {
    if (pollTimer) return;
    lastSnapshot = JSON.stringify(snapshot());
    pollTimer = setInterval(function () {
      if (JSON.stringify(snapshot()) !== lastSnapshot) schedulePush();
    }, 5000);
    try {
      global.addEventListener("pagehide", push);
      document.addEventListener("visibilitychange", function () { if (document.hidden) push(); });
    } catch (_) {}
  }

  // ---- merge policy: newest wins --------------------------------------------
  function syncOnLogin() {
    pull().then(function (cloud) {
      var localTs = "";
      try { localTs = localStorage.getItem("ak_save_meta") || ""; } catch (_) {}
      if (cloud && cloud.save && Object.keys(cloud.save).length &&
          (!localTs || (cloud.saved_at && cloud.saved_at > localTs))) {
        // cloud is newer (or this device is fresh): adopt it, reload once so the
        // lobby/deck-lab re-read the restored state. Session flag prevents loops.
        var flagged = false;
        try { flagged = sessionStorage.getItem("ak_cloud_adopted") === "1"; } catch (_) {}
        applySnapshot(cloud.save);
        try { localStorage.setItem("ak_save_meta", cloud.saved_at || new Date().toISOString()); } catch (_) {}
        if (!flagged) {
          try { sessionStorage.setItem("ak_cloud_adopted", "1"); } catch (_) {}
          try { location.reload(); return; } catch (_) {}
        }
      } else {
        push();                                   // local is the truth -> seed/refresh cloud
      }
      startWatch();
    });
  }

  // ---- auth ------------------------------------------------------------------
  function onSession(session) {
    user = (session && session.user) || null;
    if (user) {
      try { localStorage.setItem("ak_player_id", user.id); } catch (_) {}
      // default street name from the Google profile (only if never customized)
      try {
        if (!localStorage.getItem("ak_name")) {
          var nm = ((user.user_metadata || {}).name || "").split(" ")[0];
          if (nm) localStorage.setItem("ak_name", nm.toUpperCase().slice(0, 14));
        }
      } catch (_) {}
      syncOnLogin();
      // shop standalone page: re-open online now that identity exists
      try {
        if (global.AKShop && document.body && document.body.dataset.akshopStandalone === "1") {
          global.AKShop.open({ playerId: user.id, anonKey: SB_ANON });
        }
      } catch (_) {}
    }
    renderBtn();
    try { global.dispatchEvent(new CustomEvent("ak-auth", { detail: { user: user } })); } catch (_) {}
  }

  function signIn() {
    if (!sb) return;
    sb.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: location.origin + location.pathname },
    }).then(function (r) { if (r.error) console.warn("[ak_account] signIn:", r.error.message); });
  }
  function signOut() {
    if (!sb) return;
    push();
    sb.auth.signOut().then(function () {
      user = null;
      try { localStorage.removeItem("ak_player_id"); } catch (_) {}
      renderBtn();
    });
  }

  // ---- tiny auth chip (self-mounting; lobby places it via #ak-auth) ----------
  function renderBtn() {
    var el = document.getElementById("ak-auth");
    if (!el) return;
    el.textContent = "";
    var b = document.createElement("button");
    b.type = "button";
    b.id = "ak-auth-btn";
    if (user) {
      b.className = "ak-auth-in";
      b.textContent = "☁ SAVED"; // cloud glyph
      b.title = "Signed in as " + (user.email || "Google") + " -- progress saves to your Google account. Tap to sign out.";
      b.onclick = function () {
        if (global.confirm && confirm("Sign out? Progress stays on this device and in your Google cloud save.")) signOut();
      };
    } else {
      b.className = "ak-auth-out";
      b.textContent = "SIGN IN WITH GOOGLE";
      b.title = "Sign in with Google -- save your crew, gems and trophies to your account";
      b.onclick = signIn;
    }
    el.appendChild(b);
  }

  // ---- boot: load supabase-js UMD, restore session ---------------------------
  function boot() {
    if (!global.supabase || !global.supabase.createClient) return;   // CDN failed: stay offline-only
    sb = global.supabase.createClient(SB_URL, SB_ANON);
    global.AKAccount = {
      signIn: signIn, signOut: signOut,
      user: function () { return user; },
      pushNow: push,
      // AK-SOCIAL: expose the shared client so social.js can use Realtime +
      // functions.invoke (which auto-attaches the signed-in user's JWT). One
      // client, one session -- never spin up a second GoTrue instance.
      client: function () { return sb; },
    };
    sb.auth.getSession().then(function (r) { onSession(r.data && r.data.session); });
    sb.auth.onAuthStateChange(function (_evt, session) { onSession(session); });
  }

  if (global.supabase) { boot(); }
  else {
    var s = document.createElement("script");
    s.src = CDN; s.async = true;
    s.onload = boot;
    s.onerror = function () { console.warn("[ak_account] supabase-js CDN unreachable -- offline mode"); renderBtn(); };
    (document.head || document.documentElement).appendChild(s);
  }
  try { document.addEventListener("DOMContentLoaded", renderBtn); } catch (_) {}
})(typeof window !== "undefined" ? window : this);
