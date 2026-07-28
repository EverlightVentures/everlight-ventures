/* ev_state.js -- canonical localStorage for the Command Center (todo checks, prefs).
   ONE owner of client state; pages read/write through window.EV.state and listen for "ev:state". */
(function(){
  if(window.EV && window.EV.state) return;
  var KEY="ev.cc.v1";
  var _s=null;
  function load(){
    if(_s) return _s;
    try{ _s=JSON.parse(localStorage.getItem(KEY)||"")||{}; }catch(e){ _s={}; }
    if(!_s.todo) _s.todo={};   // {taskKey: true} -- user-completed overrides
    if(!_s.prefs) _s.prefs={};
    return _s;
  }
  function save(){ try{localStorage.setItem(KEY,JSON.stringify(load()));}catch(e){}
    dispatchEvent(new Event("ev:state")); return _s; }

  window.EV=window.EV||{};
  window.EV.state={
    get:function(k){ return load().prefs[k]; },
    set:function(k,v){ load().prefs[k]=v; return save(); },
    // todo done-state: keyed by a stable task string. Returns merged done flag.
    todoDone:function(key,fallback){ var t=load().todo; return (key in t)?t[key]:!!fallback; },
    todoToggle:function(key){ var t=load().todo; t[key]=!t[key]; save(); return t[key]; },
    todoSet:function(key,val){ load().todo[key]=!!val; return save(); },
    raw:load
  };
})();
