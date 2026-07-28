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

  // AK-SAVEGUARD 2026-07-18: keys that are ABOUT the save, never part of it.
  // Rescue slots live in localStorage under the ak_ prefix, so they must be
  // fenced out of snapshot() or a stash would recurse into the cloud blob.
  var META_KEY = "ak_save_meta";
  var RESCUE_KEY = "ak_rescue_save";      // newest stashed loser
  var RESCUE_PREV = "ak_rescue_prev";     // the one before that
  var SAVE_FMT = "alley-kingz-save";
  var SKIP = { ak_player_id: 1, ak_save_meta: 1, ak_rescue_save: 1, ak_rescue_prev: 1 };

  function hasLS() { try { return typeof localStorage !== "undefined" && !!localStorage; } catch (_) { return false; } }

  // ---- snapshot every ak_* key (the whole game state lives there) ----------
  function snapshot() {
    var o = {};
    if (!hasLS()) return o;
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf("ak_") === 0 && !SKIP[k]) o[k] = localStorage.getItem(k);
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

  // ==========================================================================
  // AK-SAVEGUARD 2026-07-18 -- nobody loses a run.
  // Two holes this closes:
  //   1. signed-out player clears cache = everything gone, no way out
  //   2. first sign-in used to let the cloud blow away hours of local play
  // Every path below is try/catch'd end to end. A save path NEVER throws.
  // ==========================================================================
  function num(v) { v = +v; return isFinite(v) ? v : 0; }
  function keyCount(o) { try { return (o && typeof o === "object") ? Object.keys(o).length : 0; } catch (_) { return 0; } }
  function sumVals(o) { var t = 0; try { for (var k in o) t += num(o[k]); } catch (_) {} return t; }
  function readProfile(save) {
    try { var p = JSON.parse((save && save.ak_profile) || "null"); return (p && typeof p === "object") ? p : null; }
    catch (_) { return null; }
  }

  // Weighted "how much run is in here". Only used to COMPARE two saves and to
  // pick a default when the player cannot be asked. Never a gate on gameplay.
  function progressScore(save) {
    var s = 0;
    try {
      if (!save || typeof save !== "object") return 0;
      var p = readProfile(save);
      if (p) {
        s += Math.max(0, num(p.level) - 1) * 120;
        s += num(p.xp) / 50;
        s += num(p.trophies) * 2;
        s += num(p.coins) / 100;
        s += num(p.spEarned) * 40;
        s += num(p.bones) / 10;
        s += Math.max(0, num(p.townHall) - 1) * 150;
        s += (Array.isArray(p.owned) ? p.owned.length : 0) * 25;
        s += keyCount(p.cardLvls) * 15;
        s += sumVals(p.cardLvls) * 8;
        s += keyCount(p.captures) * 5;
        s += keyCount(p.skills) * 10;
        s += (Array.isArray(p.builds) ? p.builds.length : 0) * 5;
        s += sumVals(p.chests) * 6;
        s += num(p.keys) * 6;
      }
      // story flags, decks, settings: each populated key is a little bit of run
      var n = 0;
      Object.keys(save).forEach(function (k) { if (k !== "ak_profile" && String(save[k] || "").length > 2) n++; });
      s += n * 3;
    } catch (_) {}
    return Math.max(0, Math.round(s));
  }

  // Hard signals that a HUMAN actually played. Deliberately ignores anything a
  // fresh boot writes on its own (name, settings, an empty profile), so the
  // choice prompt never fires on a clean install.
  function hasRealProgress(save) {
    try {
      var p = readProfile(save);
      if (!p) return false;
      if (num(p.level) > 1 || num(p.xp) > 0 || num(p.trophies) > 0) return true;
      if (num(p.townHall) > 1 || num(p.spEarned) > 0 || num(p.bones) > 0) return true;
      if (num(p.coins) > 0 || num(p.keys) > 0 || sumVals(p.chests) > 0) return true;
      if (Array.isArray(p.owned) && p.owned.length > 0) return true;
      if (keyCount(p.cardLvls) > 0 || keyCount(p.captures) > 0 || keyCount(p.skills) > 0) return true;
      var w = 0;
      try { for (var m in p.modes) { w += num(p.modes[m] && p.modes[m].wins) + num(p.modes[m] && p.modes[m].losses); } } catch (_) {}
      if (w > 0) return true;
    } catch (_) {}
    return false;
  }

  // one-line rap sheet for the choice prompt
  function summarize(save) {
    try {
      var p = readProfile(save);
      if (!p) return "empty";
      var bits = [];
      bits.push("LV " + Math.max(1, Math.floor(num(p.level) || 1)));
      bits.push(Math.floor(num(p.trophies)) + " TROPHIES");
      bits.push((Array.isArray(p.owned) ? p.owned.length : keyCount(p.cardLvls)) + " CARDS");
      bits.push(Math.floor(num(p.coins)) + " GOLD");
      if (num(p.townHall) > 1) bits.push("TH " + Math.floor(num(p.townHall)));
      return bits.join(" / ");
    } catch (_) { return "unreadable"; }
  }

  // ---- rescue stash: the losing side of any overwrite is kept, never torched -
  function envelope(save, why) {
    return JSON.stringify({
      fmt: SAVE_FMT, v: 1,
      exported_at: new Date().toISOString(),
      reason: why || "manual",
      player: (user && user.id) || "",
      score: progressScore(save),
      summary: summarize(save),
      keys: save || {},
    });
  }
  function stashRescue(save, why) {
    try {
      if (!hasLS() || !save || !Object.keys(save).length) return false;
      var body = envelope(save, why);
      try {
        var prev = localStorage.getItem(RESCUE_KEY);
        if (prev) localStorage.setItem(RESCUE_PREV, prev);
      } catch (_) {}
      try { localStorage.setItem(RESCUE_KEY, body); }
      catch (_) {
        // quota: drop the older slot and take one more swing
        try { localStorage.removeItem(RESCUE_PREV); localStorage.setItem(RESCUE_KEY, body); } catch (_e) { return false; }
      }
      console.warn("[ak_account] stashed rescue save (" + (why || "manual") + "):", summarize(save));
      return true;
    } catch (_) { return false; }
  }
  function listRescue() {
    var out = [];
    try {
      if (!hasLS()) return out;
      [RESCUE_KEY, RESCUE_PREV].forEach(function (k) {
        try {
          var raw = localStorage.getItem(k); if (!raw) return;
          var o = JSON.parse(raw);
          out.push({ slot: k, exported_at: o && o.exported_at, reason: o && o.reason, score: o && o.score, summary: o && o.summary });
        } catch (_) {}
      });
    } catch (_) {}
    return out;
  }
  function restoreRescue(slot, opts) {
    try {
      if (!hasLS()) return { ok: false, error: "no localStorage" };
      var raw = localStorage.getItem(slot === RESCUE_PREV ? RESCUE_PREV : RESCUE_KEY);
      if (!raw) return { ok: false, error: "that rescue slot is empty" };
      return importSave(raw, opts);
    } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
  }

  // ---- export / import: the offline lifeline -------------------------------
  // exportSave()   -> portable JSON string (also downloadable via downloadSave)
  // importSave(s)  -> validates, stashes the current save as rescue, applies
  function exportSave() {
    try { return envelope(snapshot(), "export"); }
    catch (_) { return JSON.stringify({ fmt: SAVE_FMT, v: 1, keys: {} }); }
  }
  function downloadSave(filename) {
    var body = exportSave();
    try {
      var name = filename || ("alley-kingz-save-" + new Date().toISOString().slice(0, 10) + ".json");
      var blob = new Blob([body], { type: "application/json" });
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = name; a.style.display = "none";
      (document.body || document.documentElement).appendChild(a);
      a.click();
      setTimeout(function () { try { a.parentNode.removeChild(a); URL.revokeObjectURL(url); } catch (_) {} }, 2000);
    } catch (_) { console.warn("[ak_account] download blocked -- use exportSave() and copy the string"); }
    return body;
  }
  // accepts the envelope OR a bare {ak_*: "..."} map (older hand-saved dumps)
  function parseImport(str) {
    if (typeof str !== "string") return { error: "save must be pasted as text" };
    var s = str.replace(/^\uFEFF/, "").trim();   // strip the BOM a downloaded file can carry
    if (!s) return { error: "nothing pasted" };
    if (s.length > 8000000) return { error: "that file is too big to be a save" };
    var o = null;
    try { o = JSON.parse(s); } catch (_) { return { error: "that is not a valid save file" }; }
    if (!o || typeof o !== "object" || Array.isArray(o)) return { error: "that is not a valid save file" };
    var raw = (o.keys && typeof o.keys === "object" && !Array.isArray(o.keys)) ? o.keys : o;
    if (o.fmt && o.fmt !== SAVE_FMT) return { error: "that save came from another game" };
    var keys = {}, n = 0;
    try {
      Object.keys(raw).forEach(function (k) {
        if (typeof k !== "string" || k.indexOf("ak_") !== 0 || SKIP[k]) return;
        var v = raw[k];
        if (v === null || v === undefined) return;
        var t = typeof v;
        if (t !== "string" && t !== "number" && t !== "boolean") return;
        v = String(v);
        if (v.length > 4000000) return;
        keys[k] = v; n++;
      });
    } catch (_) { return { error: "that save file is malformed" }; }
    if (!n) return { error: "no Alley Kingz progress found in that file" };
    if (!keys.ak_profile) return { error: "that save has no crew profile in it" };
    if (!readProfile(keys)) return { error: "that save's crew profile is corrupt" };
    return { keys: keys, count: n };
  }
  function importSave(str, opts) {
    try {
      opts = opts || {};
      if (!hasLS()) return { ok: false, error: "this browser has no local storage" };
      var parsed = parseImport(str);
      if (parsed.error) return { ok: false, error: parsed.error };
      stashRescue(snapshot(), "pre-import");            // current run keeps a body double
      applySnapshot(parsed.keys);
      var now = new Date().toISOString();
      try { localStorage.setItem(META_KEY, now); } catch (_) {}
      lastSnapshot = "";                                 // force the next cloud push
      try { if (user) push(); } catch (_) {}
      var res = { ok: true, keys: parsed.count, summary: summarize(parsed.keys), score: progressScore(parsed.keys) };
      if (opts.reload !== false) { try { setTimeout(function () { try { location.reload(); } catch (_) {} }, 60); } catch (_) {} }
      return res;
    } catch (e) { return { ok: false, error: String(e && e.message || e) }; }
  }

  // ---- the choice: two runs, one crown -------------------------------------
  // Resolves "local" or "cloud". Modal first; confirm() if the DOM is hostile;
  // bigger-score wins if the player cannot be asked at all. Never silent.
  function askWhichSave(localSave, cloudSave) {
    return new Promise(function (resolve) {
      var localTxt = summarize(localSave), cloudTxt = summarize(cloudSave);
      var done = false;
      function pick(w) { if (!done) { done = true; resolve(w); } }
      try {
        if (!document || !document.body) throw new Error("no dom");
        var wrap = document.createElement("div");
        wrap.id = "ak-savepick";
        wrap.style.cssText = "position:fixed;inset:0;z-index:2147483000;background:rgba(4,4,6,.92);display:flex;align-items:center;justify-content:center;padding:18px;font-family:system-ui,-apple-system,Segoe UI,sans-serif";
        var card = document.createElement("div");
        card.style.cssText = "max-width:420px;width:100%;background:#0b0b0d;border:1px solid #e8c063;border-radius:14px;padding:20px;color:#e8e8e8;box-shadow:0 18px 60px rgba(0,0,0,.8)";
        var h = document.createElement("div");
        h.style.cssText = "font-weight:800;letter-spacing:.06em;color:#e8c063;font-size:17px;margin-bottom:8px";
        h.textContent = "TWO SETS OF BOOKS";
        var p = document.createElement("div");
        p.style.cssText = "font-size:13px;line-height:1.5;color:#b9b9b9;margin-bottom:14px";
        p.textContent = "This phone is holding a run that never made it to the cloud. Your account is holding a different one. Only one keeps the crown. The other gets stashed in the safe house, not torched, and you can pull it back any time.";
        card.appendChild(h); card.appendChild(p);
        [["KEEP THIS DEVICE", localTxt, "local"], ["KEEP THE ACCOUNT", cloudTxt, "cloud"]].forEach(function (row) {
          var b = document.createElement("button");
          b.type = "button";
          b.style.cssText = "display:block;width:100%;margin:0 0 10px;padding:12px 14px;border-radius:10px;border:1px solid #444;background:#141418;color:#e8e8e8;text-align:left;cursor:pointer";
          var t = document.createElement("div");
          t.style.cssText = "font-weight:700;letter-spacing:.05em;color:#e8c063;font-size:13px";
          t.textContent = row[0];
          var s2 = document.createElement("div");
          s2.style.cssText = "font-size:12px;color:#9a9a9a;margin-top:3px";
          s2.textContent = row[1];
          b.appendChild(t); b.appendChild(s2);
          b.onclick = function () { try { wrap.parentNode.removeChild(wrap); } catch (_) {} pick(row[2]); };
          card.appendChild(b);
        });
        wrap.appendChild(card);
        document.body.appendChild(wrap);
        return;
      } catch (_) {}
      try {
        if (global.confirm) {
          var keep = confirm("Two saves found.\n\nOK = keep THIS DEVICE (" + localTxt + ")\nCancel = keep THE ACCOUNT (" + cloudTxt + ")\n\nThe other one gets stashed for recovery. Nothing is torched.");
          pick(keep ? "local" : "cloud");
          return;
        }
      } catch (_) {}
      pick(progressScore(cloudSave) > progressScore(localSave) ? "cloud" : "local");
    });
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
        else { try { localStorage.setItem(META_KEY, now); } catch (_) {} }
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

  // ---- merge policy ----------------------------------------------------------
  // AK-SAVEGUARD 2026-07-18: newest-wins USED to run unconditionally, so a
  // player who grinded for hours signed out got wiped the second they signed in
  // (no timestamp locally = "this device is fresh" = adopt cloud). Now: the
  // cloud only takes the wheel when local has nothing real to lose, or the
  // player says so. Every overwrite stashes the loser under ak_rescue_save.
  function adoptCloud(cloud, localSave) {
    try {
      if (localSave && Object.keys(localSave).length) stashRescue(localSave, "cloud-adopted");
      applySnapshot(cloud.save);
      try { localStorage.setItem(META_KEY, cloud.saved_at || new Date().toISOString()); } catch (_) {}
      lastSnapshot = "";
      var flagged = false;
      try { flagged = sessionStorage.getItem("ak_cloud_adopted") === "1"; } catch (_) {}
      if (!flagged) {
        try { sessionStorage.setItem("ak_cloud_adopted", "1"); } catch (_) {}
        try { location.reload(); return true; } catch (_) {}
      }
    } catch (_) {}
    return false;
  }
  // Keeping local overwrites the cloud row, so the cloud is the loser here.
  // force=true (a real fork: the player chose, or the two runs diverged) ALWAYS
  // stashes it, even when it scores lower, because a misclick has to be undoable.
  // Without force this is the routine login where the cloud is just an older
  // mirror of this same device, and stashing every time would burn quota for
  // nothing, so it only stashes when the cloud held run the device does not.
  function keepLocal(cloudSave, localSave, force) {
    try {
      if (cloudSave && Object.keys(cloudSave).length &&
          (force || progressScore(cloudSave) > progressScore(localSave || snapshot()))) stashRescue(cloudSave, "local-kept");
      lastSnapshot = "";                            // force the overwrite push
      push();
    } catch (_) {}
  }

  function syncOnLogin() {
    var localSave = {}, localTs = "";
    try { localSave = snapshot(); } catch (_) { localSave = {}; }
    try { localTs = localStorage.getItem(META_KEY) || ""; } catch (_) {}

    pull().then(function (cloud) {
      try {
        var cloudSave = (cloud && cloud.save && typeof cloud.save === "object") ? cloud.save : null;
        if (!cloudSave || !Object.keys(cloudSave).length) { push(); startWatch(); return; }  // nothing up there: seed it

        var localReal = hasRealProgress(localSave);
        if (!localReal) { if (adoptCloud(cloud, localSave)) return; startWatch(); return; }  // nothing to lose: safe adopt

        var lScore = progressScore(localSave), cScore = progressScore(cloudSave);
        var cloudNewer = !!(cloud.saved_at && localTs && cloud.saved_at > localTs);

        // The wipe case: real local run that has NEVER synced. Ask, never assume.
        // Also ask when the cloud is newer but this device is holding clearly
        // more run (offline grind that beat a stale cloud row).
        if (!localTs || (cloudNewer && lScore > cScore * 1.15)) {
          askWhichSave(localSave, cloudSave).then(function (w) {
            try {
              if (w === "cloud") { if (adoptCloud(cloud, localSave)) return; }
              else keepLocal(cloudSave, localSave, true);   // explicit fork: loser always gets a body double
            } catch (_) {}
            startWatch();
          });
          return;
        }

        if (cloudNewer) { if (adoptCloud(cloud, localSave)) return; startWatch(); return; }
        keepLocal(cloudSave, localSave);             // local is the truth -> refresh cloud
        startWatch();
      } catch (_) { try { startWatch(); } catch (_e) {} }
    }).catch(function (e) {
      console.warn("[ak_account] sync failed, staying local:", e && e.message);
      try { startWatch(); } catch (_) {}
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

  // AK-SAVEGUARD 2026-07-18: the rescue API mounts UNCONDITIONALLY, before boot.
  // The player who needs export/import most is the one whose CDN is dead or who
  // never signs in, so it can never hang off supabase loading. It gets its OWN
  // global: window.AKAccount staying undefined until the client exists is a
  // contract the onboarding poll in index.html reads as "supabase not ready
  // yet", and defining it early would make that poll skip its CDN grace period.
  var SAVE_API = {
    exportSave: exportSave,           // -> portable JSON string
    downloadSave: downloadSave,       // -> same string, also saved as a .json file
    importSave: importSave,           // (str, {reload:false}) -> {ok,error,keys,summary,score}
    listRescue: listRescue,           // -> [{slot,exported_at,reason,score,summary}]
    restoreRescue: restoreRescue,     // (slot) -> same shape as importSave
    rescueKeys: { latest: RESCUE_KEY, previous: RESCUE_PREV },
    progress: function () { try { return progressScore(snapshot()); } catch (_) { return 0; } },
    summary: function () { try { return summarize(snapshot()); } catch (_) { return ""; } },
  };
  global.AKSave = SAVE_API;

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
      // AK-SAVEGUARD: same rescue API, mirrored onto the account global so a UI
      // that already holds AKAccount does not need to know about AKSave.
      exportSave: exportSave, downloadSave: downloadSave, importSave: importSave,
      listRescue: listRescue, restoreRescue: restoreRescue,
      rescueKeys: SAVE_API.rescueKeys, progress: SAVE_API.progress, summary: SAVE_API.summary,
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
