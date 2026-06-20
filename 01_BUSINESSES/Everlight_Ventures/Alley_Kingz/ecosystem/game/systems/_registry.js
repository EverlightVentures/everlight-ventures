/* ALLEY KINGZ -- AK_SYSTEMS plug-in registry (host-owned; loaded FIRST, before any wave module).
   Each wave module self-registers via AK_SYSTEMS.register({id,init,onEnterBuilding,onTick,onDrawWorld}).
   The hub (index.html) builds AK_CTX once and calls initAll/enterBuilding/tickAll/drawAll.
   See specs/MODULE_CONTRACT.md S1.1 + specs/WAVE_INTEGRATION.md. */
window.AK_SYSTEMS = (function () {
  var list = [], byId = {};
  function warn(id, e){ try{ console.warn('[AK_SYSTEMS]', id, e); }catch(_){} }
  return {
    // module self-registration (load-time). Dupe id or bad shape = ignored.
    register: function (m) {
      if (!m || typeof m !== 'object' || !m.id || byId[m.id]) return false;
      byId[m.id] = m; list.push(m); return true;
    },
    get:  function (id) { return byId[id] || null; },
    all:  function () { return list.slice(); },
    // ---- host dispatch (called by the hub only) ----
    initAll: function (ctx) { list.forEach(function (m) { try { m.init && m.init(ctx); } catch (e) { warn(m.id, e); } }); },
    enterBuilding: function (b, ctx) {            // first module to claim wins
      for (var i = 0; i < list.length; i++) { try { if (list[i].onEnterBuilding && list[i].onEnterBuilding(b, ctx) === true) return true; } catch (e) { warn(list[i].id, e); } }
      return false;
    },
    tickAll: function (dt, ctx) { for (var i = 0; i < list.length; i++) { try { list[i].onTick && list[i].onTick(dt, ctx); } catch (e) { warn(list[i].id, e); } } },
    drawAll: function (ctx)     { for (var i = 0; i < list.length; i++) { try { list[i].onDrawWorld && list[i].onDrawWorld(ctx); } catch (e) { warn(list[i].id, e); } } }
  };
})();
