/* ev_fx.js -- cursor halo, motes, scroll-reveal, Web Audio SFX, click-to-copy, Konami.
   Pure vanilla, no deps. Loaded defer on every Command Center page. */
(function(){
  if(window.__EV_FX__) return; window.__EV_FX__=true;

  /* cursor halo */
  var raf=null;
  addEventListener("pointermove",function(e){
    if(raf) return;
    raf=requestAnimationFrame(function(){
      document.body.style.setProperty("--fx-mx",e.clientX+"px");
      document.body.style.setProperty("--fx-my",e.clientY+"px");
      raf=null;
    });
  },{passive:true});

  /* motes */
  function motes(){
    var f=document.createElement("div"); f.id="fx-motes";
    for(var i=0;i<20;i++){
      var m=document.createElement("span"); m.className="fx-mote";
      m.style.left=(Math.random()*100)+"%";
      m.style.animationDuration=(15+Math.random()*16)+"s";
      m.style.animationDelay=(-Math.random()*20)+"s";
      m.style.setProperty("--drift",((Math.random()-.5)*140)+"px");
      f.appendChild(m);
    }
    document.body.appendChild(f);
  }

  /* scroll reveal */
  function reveal(){
    var io=new IntersectionObserver(function(es){
      es.forEach(function(en){ if(en.isIntersecting){en.target.classList.add("in");io.unobserve(en.target);} });
    },{threshold:.08});
    document.querySelectorAll(".reveal").forEach(function(el){io.observe(el);});
    // re-scan when Preact mounts later
    new MutationObserver(function(){
      document.querySelectorAll(".reveal:not(.in)").forEach(function(el){io.observe(el);});
    }).observe(document.body,{childList:true,subtree:true});
  }

  /* Web Audio SFX */
  var AC=null; function ac(){ if(!AC){try{AC=new (window.AudioContext||window.webkitAudioContext)();}catch(e){}} return AC; }
  function tone(freq,dur,vol,type){
    var c=ac(); if(!c)return; if(window.EV&&EV.state&&EV.state.get&&EV.state.get("muted"))return;
    var o=c.createOscillator(),g=c.createGain();
    o.type=type||"sine"; o.frequency.value=freq;
    g.gain.setValueAtTime(0,c.currentTime);
    g.gain.linearRampToValueAtTime(vol||.04,c.currentTime+.008);
    g.gain.exponentialRampToValueAtTime(.0001,c.currentTime+(dur||.08));
    o.connect(g).connect(c.destination); o.start(); o.stop(c.currentTime+(dur||.08));
  }
  var SFX={
    hover:function(){tone(1250,.035,.018,"sine");},
    click:function(){tone(640,.05,.05,"square");setTimeout(function(){tone(880,.04,.03,"sine");},16);},
    copy:function(){tone(880,.06,.05,"sine");setTimeout(function(){tone(1320,.07,.04,"sine");},45);},
    win:function(){[523,659,784,1047].forEach(function(f,i){setTimeout(function(){tone(f,.13,.06,"sine");},i*85);});}
  };
  window.EV_SFX=SFX;

  /* delegated: hover + click sounds on interactive bits, click-to-copy */
  document.addEventListener("pointerover",function(e){
    var t=e.target.closest(".tile,.btn-gold,.btn-ghost,.copybtn,[data-sfx]"); if(t)SFX.hover();
  });
  document.addEventListener("click",function(e){
    var cp=e.target.closest("[data-copy]");
    if(cp){
      var v=cp.getAttribute("data-copy");
      (navigator.clipboard?navigator.clipboard.writeText(v):Promise.reject()).then(function(){
        SFX.copy(); var o=cp.textContent; cp.classList.add("copied");
        cp.textContent=cp.getAttribute("data-copied")||"copied!";
        setTimeout(function(){cp.classList.remove("copied");cp.textContent=o;},1200);
      }).catch(function(){});
      return;
    }
    if(e.target.closest(".tile,.btn-gold,.btn-ghost")) SFX.click();
  });

  /* Konami -> beast mode (gold runs hot) */
  var seq=["ArrowUp","ArrowUp","ArrowDown","ArrowDown","ArrowLeft","ArrowRight","ArrowLeft","ArrowRight","b","a"],i=0;
  addEventListener("keydown",function(e){
    if(e.key.toLowerCase()===seq[i].toLowerCase()){ i++; if(i===seq.length){document.body.classList.toggle("beast");SFX.win();i=0;} } else i=0;
  });

  function init(){ motes(); reveal(); }
  if(document.readyState!=="loading") init(); else addEventListener("DOMContentLoaded",init);
})();
