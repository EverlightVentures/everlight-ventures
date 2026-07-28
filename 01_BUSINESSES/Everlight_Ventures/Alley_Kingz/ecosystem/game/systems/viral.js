/* AK-VIRAL -- the share/growth loop for Alley Kingz.
 * Turns any big cinematic moment (win, killstreak, raid takeover, chest, level-up)
 * into a downloadable 9:16 clip with a gold $BCARDD lower-third + an invite link
 * that carries a ?ref= code. Zero backend, zero Higgsfield credits.
 *
 * Public API (window.AK_VIRAL):
 *   shareMoment(kind, meta)  open the share card. kind: win|killstreak|raid_win|chest|levelup
 *                            meta: {title, sub, handle, cinematic, stat}
 *   refCode()                this device's stable invite code (localStorage ak_ref)
 *   inviteUrl(kind)          full https://alleykingz.online/?ref=..&m=.. link
 *   captureInboundRef()      read ?ref= off the URL, remember who referred us (auto-runs on load)
 *
 * Everything is feature-detected and guarded: no MediaRecorder / captureStream / share
 * just degrades to "copy the invite link" so it never breaks a phone that lacks the API.
 */
(function(){
  'use strict';
  if(window.AK_VIRAL) return;

  var GOLD='#e8b84b', GOLD_DEEP='#c8922e', INK='#0a0a0c', PAPER='#f3ead2';
  var SITE='alleykingz.online';
  var LINK_BASE='https://alleykingz.online/';

  // ---- referral identity -------------------------------------------------
  function rid(){
    var c=null; try{ c=localStorage.getItem('ak_ref'); }catch(_e){}
    if(!c){
      c=(Date.now().toString(36)+Math.random().toString(36).slice(2,6)).slice(-8);
      try{ localStorage.setItem('ak_ref',c); }catch(_e){}
    }
    return c;
  }
  function inviteUrl(kind){
    return LINK_BASE+'?ref='+encodeURIComponent(rid())+(kind?'&m='+encodeURIComponent(kind):'');
  }
  // Read an inbound ?ref= once, so the invited player is attributed to the inviter.
  function captureInboundRef(){
    try{
      var p=new URLSearchParams(location.search||'');
      var r=p.get('ref');
      if(r && r!==rid()){
        if(!localStorage.getItem('ak_referred_by')){
          localStorage.setItem('ak_referred_by',r);
          localStorage.setItem('ak_referred_at',String(Date.now()));
        }
      }
    }catch(_e){}
  }

  // First-run referral payout. If this device arrived through someone's invite
  // link (ak_referred_by set by captureInboundRef), pay the INVITEE a one-time
  // soft-currency welcome drop (client-side, no gems) and best-effort report the
  // inbound code so the INVITER can be credited server-side later. Guarded
  // end-to-end: a missing econ skips the grant but still BURNS the flag (so it
  // never loops) and still fires the report. Pays exactly once (ak_ref_claimed).
  function claimReferral(){
    try{
      var by=null; try{ by=localStorage.getItem('ak_referred_by'); }catch(_e){}
      if(!by) return;                                     // never referred -- nothing to pay
      var done=null; try{ done=localStorage.getItem('ak_ref_claimed'); }catch(_e){}
      if(done) return;                                    // already paid this device
      // Burn the once-only flag FIRST so a reload mid-grant can never double-pay.
      try{ localStorage.setItem('ak_ref_claimed','1'); }catch(_e){}
      var paid=false;
      try{
        var E=window.AK_ECON;
        if(E && E.mutateProfile){
          E.mutateProfile(function(p){                    // soft currency only -- gems untouched
            p.coins=Math.max(0,(p.coins|0)+250);          // +250 gold
            p.bones=Math.max(0,(p.bones|0)+10);           // +10 bones
            p.keys =Math.max(0,(p.keys |0)+1);            // +1 chest key
          });
          paid=true;
        }
      }catch(_e){}
      if(paid){ try{ toast('Welcome to the block -- here\'s a starter drop from your recruiter'); }catch(_e){} }
      // Best-effort inviter credit -- server grants later. No-op if the social
      // lane is absent/offline; guarded so it never throws.
      try{ if(window.AKSocial && AKSocial.reportReferral) AKSocial.reportReferral(by); }catch(_e){}
    }catch(_e){}
  }

  // Defer the payout until the page has settled so the econ + social lanes have
  // loaded (viral.js parses before social.js) and document.body exists for the
  // toast. Runs at most once; a no-show is a safe no-op.
  function scheduleReferralClaim(){
    var ran=false;
    function go(){ if(ran) return; ran=true; try{ claimReferral(); }catch(_e){} }
    try{
      if(document.readyState==='interactive' || document.readyState==='complete'){ setTimeout(go,0); }
      else { document.addEventListener('DOMContentLoaded',go); window.addEventListener('load',go); }
    }catch(_e){ try{ go(); }catch(_e2){} }
  }

  // ---- clip recorder -----------------------------------------------------
  // Composites the cinematic <video> onto a 720x1280 canvas with a painted
  // lower-third, then records ~6s to a WebM/MP4 blob via MediaRecorder.
  function pickMime(){
    var t=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm','video/mp4'];
    if(typeof MediaRecorder==='undefined' || !MediaRecorder.isTypeSupported) return '';
    for(var i=0;i<t.length;i++){ try{ if(MediaRecorder.isTypeSupported(t[i])) return t[i]; }catch(_e){} }
    return '';
  }
  function canRecord(){
    try{ return typeof MediaRecorder!=='undefined' && !!document.createElement('canvas').captureStream; }
    catch(_e){ return false; }
  }
  function wrapLines(ctx,text,maxW){
    var words=String(text||'').split(' '), lines=[], cur='';
    for(var i=0;i<words.length;i++){
      var t=cur?cur+' '+words[i]:words[i];
      if(ctx.measureText(t).width>maxW && cur){ lines.push(cur); cur=words[i]; }
      else cur=t;
    }
    if(cur) lines.push(cur);
    return lines;
  }
  // Draw the branded overlay onto the record canvas each frame.
  function paintOverlay(ctx,W,H,meta,t){
    var g=ctx.createLinearGradient(0,H*0.42,0,H);
    g.addColorStop(0,'rgba(8,8,12,0)'); g.addColorStop(0.55,'rgba(8,8,12,.55)'); g.addColorStop(1,'rgba(8,8,12,.94)');
    ctx.fillStyle=g; ctx.fillRect(0,H*0.42,W,H*0.58);
    var tg=ctx.createLinearGradient(0,0,0,H*0.18);
    tg.addColorStop(0,'rgba(8,8,12,.78)'); tg.addColorStop(1,'rgba(8,8,12,0)');
    ctx.fillStyle=tg; ctx.fillRect(0,0,W,H*0.18);
    ctx.textBaseline='alphabetic';
    ctx.fillStyle=GOLD; ctx.font='700 40px Georgia, serif';
    ctx.fillText('♛ ALLEY KINGZ', 46, 78);
    ctx.fillStyle=GOLD_DEEP; ctx.fillRect(46,96,270,3);
    ctx.fillStyle=PAPER; ctx.font='800 96px Georgia, serif';
    var title=String(meta.title||'ON THE BLOCK').toUpperCase();
    var tl=wrapLines(ctx,title,W-92);
    var y=H-360;
    for(var i=0;i<tl.length && i<2;i++){ ctx.fillText(tl[i],46,y); y+=104; }
    ctx.fillStyle=GOLD; ctx.fillRect(46,y-70,150,8);
    if(meta.sub){ ctx.fillStyle='rgba(243,234,210,.86)'; ctx.font='500 44px Georgia, serif';
      var sl=wrapLines(ctx,meta.sub,W-92);
      for(var j=0;j<sl.length && j<2;j++){ ctx.fillText(sl[j],46,y); y+=54; }
    }
    ctx.fillStyle=GOLD; ctx.font='700 40px Georgia, serif';
    var beat=0.5+0.5*Math.sin(t*3.2);
    ctx.globalAlpha=0.72+0.28*beat;
    ctx.fillText('▶ PLAY FREE · '+SITE, 46, H-58);
    ctx.globalAlpha=1;
    if(meta.handle){ ctx.fillStyle='rgba(243,234,210,.7)'; ctx.font='500 34px Georgia, serif';
      ctx.textAlign='right'; ctx.fillText(String(meta.handle), W-46, H-58); ctx.textAlign='left'; }
  }
  // Returns a Promise<{blob,ext}|null>. Records ~durMs of the given video element.
  function recordClip(videoEl, meta, durMs){
    return new Promise(function(resolve){
      if(!canRecord()){ resolve(null); return; }
      var mime=pickMime(); if(!mime){ resolve(null); return; }
      var W=720,H=1280;
      var cv=document.createElement('canvas'); cv.width=W; cv.height=H;
      var ctx=cv.getContext('2d');
      var stream, rec, chunks=[], t0=performance.now(), raf, stopped=false;
      try{ stream=cv.captureStream(30); }catch(_e){ resolve(null); return; }
      function frame(){
        if(stopped) return;
        var t=(performance.now()-t0)/1000;
        ctx.fillStyle=INK; ctx.fillRect(0,0,W,H);
        try{
          var vw=videoEl.videoWidth||16, vh=videoEl.videoHeight||9;
          var s=Math.max(W/vw,H/vh), dw=vw*s, dh=vh*s;
          ctx.drawImage(videoEl,(W-dw)/2,(H-dh)/2,dw,dh);
        }catch(_e){}
        paintOverlay(ctx,W,H,meta,t);
        raf=requestAnimationFrame(frame);
      }
      frame();
      try{
        rec=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:6000000});
      }catch(_e){ stopped=true; if(raf)cancelAnimationFrame(raf); resolve(null); return; }
      rec.ondataavailable=function(e){ if(e.data&&e.data.size) chunks.push(e.data); };
      rec.onstop=function(){
        stopped=true; if(raf)cancelAnimationFrame(raf);
        try{ stream.getTracks().forEach(function(tr){tr.stop();}); }catch(_e){}
        var ext=mime.indexOf('mp4')>=0?'mp4':'webm';
        var blob=chunks.length?new Blob(chunks,{type:mime.split(';')[0]}):null;
        resolve(blob?{blob:blob,ext:ext}:null);
      };
      try{ rec.start(); }catch(_e){ stopped=true; if(raf)cancelAnimationFrame(raf); resolve(null); return; }
      setTimeout(function(){ try{ if(rec.state!=='inactive') rec.stop(); }catch(_e){ resolve(null); } }, durMs||6000);
    });
  }

  // ---- toast -------------------------------------------------------------
  function toast(msg){
    try{
      var t=document.createElement('div');
      t.textContent=msg;
      t.style.cssText='position:fixed;left:50%;bottom:16%;transform:translateX(-50%);z-index:100002;'
        +'background:#12100a;color:'+GOLD+';border:1px solid '+GOLD_DEEP+';padding:11px 18px;border-radius:10px;'
        +'font:600 14px system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.6);max-width:82vw;text-align:center;';
      document.body.appendChild(t);
      setTimeout(function(){ t.style.transition='opacity .4s'; t.style.opacity='0'; setTimeout(function(){ try{t.remove();}catch(_e){} },420); }, 2200);
    }catch(_e){}
  }
  function copyText(s){
    try{ if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(s); return true; } }catch(_e){}
    try{ var ta=document.createElement('textarea'); ta.value=s; ta.style.cssText='position:fixed;opacity:0;';
      document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); return true; }catch(_e){}
    return false;
  }

  // ---- the share card ----------------------------------------------------
  var MEDIA={
    win:{cin:'assets/cinematics/win.mp4', title:'CROWN DEFENDED', tag:'I just ran the block'},
    killstreak:{cin:'assets/cinematics/ks_doggod.mp4', title:'DOG GOD', tag:'unstoppable streak'},
    raid_win:{cin:'assets/ui_mp4/raidend_win.mp4', title:'TAKEOVER', tag:'took their whole block'},
    chest:{cin:'assets/cinematics/chest_open.mp4', title:'LOOT PULLED', tag:'cracked the vault'},
    levelup:{cin:'assets/cinematics/story_intro.mp4', title:'RANKED UP', tag:'climbing the throne'}
  };
  var openCard=null;
  function shareMoment(kind, meta){
    try{
      if(openCard){ try{ openCard(); }catch(_e){} openCard=null; }
      meta=meta||{};
      var base=MEDIA[kind]||MEDIA.win;
      var cin=meta.cinematic||base.cin;
      var title=meta.title||base.title;
      var sub=meta.sub||('$BCARDD · '+(base.tag));
      var handle=meta.handle||'';
      var url=inviteUrl(kind);

      var back=document.createElement('div');
      back.style.cssText='position:fixed;inset:0;z-index:100000;background:rgba(4,4,7,.9);'
        +'display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;'
        +'backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);padding:14px;box-sizing:border-box;';
      var card=document.createElement('div');
      card.style.cssText='position:relative;height:min(70vh,560px);aspect-ratio:9/16;max-width:94vw;'
        +'border-radius:16px;overflow:hidden;border:2px solid '+GOLD_DEEP+';box-shadow:0 20px 70px rgba(0,0,0,.7);background:'+INK+';';
      var vid=document.createElement('video');
      vid.src=cin; vid.muted=true; vid.loop=true; vid.autoplay=true; vid.playsInline=true;
      vid.setAttribute('playsinline',''); vid.setAttribute('muted','');
      vid.crossOrigin='anonymous';
      vid.style.cssText='width:100%;height:100%;object-fit:cover;';
      vid.onerror=function(){ card.style.background='linear-gradient(160deg,#1a1408,#0a0a0c)'; };
      card.appendChild(vid);
      var lt=document.createElement('div');
      lt.style.cssText='position:absolute;inset:0;display:flex;flex-direction:column;justify-content:space-between;'
        +'padding:14px 16px;box-sizing:border-box;pointer-events:none;'
        +'background:linear-gradient(0deg,rgba(8,8,12,.94) 4%,rgba(8,8,12,0) 42%,rgba(8,8,12,0) 82%,rgba(8,8,12,.7) 100%);';
      lt.innerHTML=''
        +'<div style="font:700 15px Georgia,serif;color:'+GOLD+';letter-spacing:.06em;">♛ ALLEY KINGZ</div>'
        +'<div>'
        +'<div style="font:800 34px Georgia,serif;color:'+PAPER+';line-height:1.02;text-shadow:0 2px 10px #000;">'+esc(title)+'</div>'
        +'<div style="width:52px;height:4px;background:'+GOLD+';margin:8px 0;"></div>'
        +'<div style="font:500 15px Georgia,serif;color:rgba(243,234,210,.9);">'+esc(sub)+'</div>'
        +'<div style="font:700 14px Georgia,serif;color:'+GOLD+';margin-top:10px;">▶ PLAY FREE · '+SITE+'</div>'
        +'</div>';
      card.appendChild(lt);
      back.appendChild(card);

      var status=document.createElement('div');
      status.style.cssText='font:600 12px system-ui,sans-serif;color:'+GOLD+';opacity:.85;min-height:16px;letter-spacing:.04em;';
      status.textContent=canRecord()?'MAKING YOUR CLIP...':'';
      back.appendChild(status);

      var row=document.createElement('div');
      row.style.cssText='display:flex;gap:10px;flex-wrap:wrap;justify-content:center;max-width:94vw;';
      function btn(label, primary){
        var b=document.createElement('button'); b.textContent=label;
        b.style.cssText='font:700 13px system-ui,sans-serif;padding:12px 16px;border-radius:11px;cursor:pointer;'
          +'border:1px solid '+GOLD_DEEP+';'
          +(primary?('background:linear-gradient(180deg,'+GOLD+','+GOLD_DEEP+');color:#141005;')
                   :('background:#14120c;color:'+GOLD+';'));
        return b;
      }
      var bSave=btn('⬇ SAVE CLIP', true);
      var bShare=btn('⇪ SHARE', false);
      var bInvite=btn('\u{1f517} INVITE LINK', false);
      var bClose=btn('✕ CLOSE', false);
      row.appendChild(bSave); row.appendChild(bShare); row.appendChild(bInvite); row.appendChild(bClose);
      back.appendChild(row);

      var hint=document.createElement('div');
      hint.style.cssText='font:500 11px system-ui,sans-serif;color:rgba(243,234,210,.5);max-width:88vw;text-align:center;';
      hint.textContent='Post it. Every friend who taps your link lands straight in your block.';
      back.appendChild(hint);

      document.body.appendChild(back);
      try{ vid.play().catch(function(){}); }catch(_e){}

      var clipP=null;
      function ensureClip(){
        if(clipP) return clipP;
        clipP=recordClip(vid, {title:title, sub:sub, handle:handle}, 6000).then(function(r){
          if(r){ try{ status.textContent='CLIP READY'; }catch(_e){} }
          else { try{ status.textContent='Clip capture not supported here. Share the link'; }catch(_e){} }
          return r;
        });
        return clipP;
      }
      if(canRecord()){
        var started=false;
        function startWhenReady(){ if(started)return; started=true; ensureClip(); }
        if(vid.readyState>=2) startWhenReady();
        else { vid.addEventListener('loadeddata',startWhenReady); setTimeout(startWhenReady,1200); }
      }

      function fileName(){ return 'alleykingz_'+kind+'_'+Date.now(); }
      function download(r){
        try{
          var u=URL.createObjectURL(r.blob);
          var a=document.createElement('a'); a.href=u; a.download=fileName()+'.'+r.ext;
          document.body.appendChild(a); a.click(); a.remove();
          setTimeout(function(){ URL.revokeObjectURL(u); }, 4000);
          return true;
        }catch(_e){ return false; }
      }

      bSave.onclick=function(){
        if(!canRecord()){ copyText(url); toast('Clip needs a newer browser. Invite link copied'); return; }
        status.textContent='RENDERING...';
        ensureClip().then(function(r){
          if(r && download(r)) toast('Clip saved. Post it and tag the block');
          else { copyText(url); toast('Could not save clip. Invite link copied instead'); }
        });
      };
      bShare.onclick=function(){
        var shareText=title+' in Alley Kingz. '+SITE;
        ensureClip().then(function(r){
          if(r && navigator.canShare){
            try{
              var f=new File([r.blob], fileName()+'.'+r.ext, {type:r.blob.type});
              if(navigator.canShare({files:[f]})){
                navigator.share({files:[f], text:shareText, url:url}).then(function(){}).catch(function(){ copyFallback(); });
                return;
              }
            }catch(_e){}
          }
          if(navigator.share){ navigator.share({title:'Alley Kingz', text:shareText, url:url}).catch(function(){ copyFallback(); }); return; }
          copyFallback();
        });
        function copyFallback(){ copyText(url); toast('Invite link copied. Paste it anywhere'); }
      };
      bInvite.onclick=function(){ copyText(url); toast('Invite link copied'); };

      function close(){ try{ vid.pause(); }catch(_e){} try{ back.remove(); }catch(_e){} openCard=null; }
      bClose.onclick=close;
      back.addEventListener('click',function(e){ if(e.target===back) close(); });
      openCard=close;
    }catch(_e){ try{ copyText(inviteUrl(kind)); toast('Invite link copied'); }catch(_e2){} }
  }

  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){ return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'})[c]; }); }

  window.AK_VIRAL={ shareMoment:shareMoment, refCode:rid, inviteUrl:inviteUrl, captureInboundRef:captureInboundRef };
  try{ captureInboundRef(); }catch(_e){}
  scheduleReferralClaim();          // AK-REF: first-run welcome drop for the invitee + report the inviter
})();
