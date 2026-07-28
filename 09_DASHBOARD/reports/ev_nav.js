/* ev_nav.js -- sticky top bar (wordmark + route chips + live chips) + Cmd-K palette.
   Injects once per page. Reads window.EV_DATA (degrades if absent). Built with safe DOM
   construction (textContent only) -- no innerHTML with interpolated content. */
(function(){
  if(window.__EV_NAV__) return; window.__EV_NAV__=true;

  function el(tag,attrs,text){
    var n=document.createElement(tag);
    if(attrs) for(var k in attrs){ if(k==="class")n.className=attrs[k]; else if(k==="onclick")n.onclick=attrs[k]; else n.setAttribute(k,attrs[k]); }
    if(text!=null) n.textContent=text;
    return n;
  }
  function frag(){ var f=document.createDocumentFragment(); for(var i=0;i<arguments.length;i++) if(arguments[i]) f.appendChild(arguments[i]); return f; }

  var PAGES=[
    {label:"Hub",href:"ops.html",icon:"◈"},
    {label:"Kalshi",href:"cc_kalshi.html",icon:"⚡"},
    {label:"AI Tools",href:"cc_ai.html",icon:"✨"},
    {label:"To-Do",href:"cc_todo.html",icon:"☑"},
    {label:"Ops",href:"cc_ops.html",icon:"⛭"}
  ];
  var here=(location.pathname.split("/").pop()||"ops.html");

  var css=document.createElement("style");
  css.textContent=
  ".evnav{position:sticky;top:0;z-index:40;backdrop-filter:blur(14px);background:rgba(10,10,12,.82);border-bottom:1px solid rgba(255,255,255,.07)}"+
  ".evnav-in{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:14px;padding:10px 18px;flex-wrap:wrap}"+
  ".evbrand{font-family:'Playfair Display',serif;font-weight:900;letter-spacing:.04em;font-size:16px;color:#E8E8E8;white-space:nowrap;display:flex;gap:7px;align-items:baseline}"+
  ".evbrand b{color:#D4AF37}.evbrand small{color:#8a8a92;font-size:11px;font-family:'JetBrains Mono',monospace;font-weight:400}"+
  ".evroutes{display:flex;gap:4px;flex-wrap:wrap}"+
  ".evroute{font-family:'JetBrains Mono',monospace;font-size:12px;color:#8a8a92;padding:6px 11px;border-radius:999px;border:1px solid transparent;transition:all .2s;cursor:pointer}"+
  ".evroute:hover{color:#E8E8E8;border-color:rgba(255,255,255,.1)}"+
  ".evroute.on{color:#D4AF37;background:rgba(212,175,55,.12);border-color:rgba(212,175,55,.4)}"+
  ".evchips{margin-left:auto;display:flex;gap:7px;align-items:center;flex-wrap:wrap}"+
  ".evchip{font-family:'JetBrains Mono',monospace;font-size:11px;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);color:#E8E8E8}"+
  ".evchip i{color:#8a8a92;font-style:normal}"+
  ".evk{cursor:pointer;color:#8a8a92;border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:4px 9px;font-family:'JetBrains Mono',monospace;font-size:11px}"+
  ".evk:hover{color:#D4AF37;border-color:#D4AF37}"+
  ".evpal{position:fixed;inset:0;z-index:60;display:none;background:rgba(0,0,0,.6);backdrop-filter:blur(6px)}"+
  ".evpal.open{display:block}"+
  ".evpal-box{max-width:640px;margin:9vh auto 0;background:#111114;border:1px solid rgba(212,175,55,.3);border-radius:16px;overflow:hidden;box-shadow:0 30px 80px rgba(0,0,0,.6)}"+
  ".evpal input{width:100%;background:transparent;border:0;outline:0;color:#E8E8E8;font-size:16px;padding:18px 20px;border-bottom:1px solid rgba(255,255,255,.08);font-family:Inter,sans-serif}"+
  ".evpal-list{max-height:54vh;overflow:auto}"+
  ".evpal-row{display:flex;align-items:center;gap:11px;padding:11px 20px;cursor:pointer;border-left:3px solid transparent}"+
  ".evpal-row .t{color:#E8E8E8;font-size:14px}.evpal-row .s{color:#8a8a92;font-size:11px;font-family:'JetBrains Mono',monospace;margin-left:auto}"+
  ".evpal-row.sel{background:rgba(212,175,55,.1);border-left-color:#D4AF37}"+
  ".beast .evroute.on,.beast .evbrand b{color:#ff4d4d!important}";
  document.head.appendChild(css);

  function fmtUSD(n){ return (n==null||isNaN(n))?"--":("$"+Number(n).toFixed(2)); }
  function chipsEl(){
    var d=(window.EV_DATA||{}),k=d.kalshi||{},td=d.todo||[];
    var open=td.filter(function(x){return !x.done;}).length;
    var wr=(k.win_rate!=null)?Math.round(k.win_rate*100)+"%":"--";
    var box=el("div",{class:"evchips"});
    function chip(lab,val){ var c=el("span",{class:"evchip"}); c.appendChild(el("i",null,lab+" ")); c.appendChild(document.createTextNode(val)); return c; }
    box.appendChild(chip("bal",fmtUSD(k.balance)));
    box.appendChild(chip("win",wr));
    box.appendChild(chip("todo",open+" open"));
    var kbtn=el("span",{class:"evk",id:"evk"},"⌘K"); kbtn.onclick=open_; box.appendChild(kbtn);
    return box;
  }

  var brand=el("a",{class:"evbrand",href:"ops.html"});
  brand.appendChild(el("span",null,"EVER")); var b=el("b",null,"LIGHT"); brand.firstChild.after(b);
  brand.appendChild(el("small",null,"COMMAND CENTER"));
  var routes=el("div",{class:"evroutes"});
  PAGES.forEach(function(p){ routes.appendChild(el("a",{class:"evroute"+(p.href===here?" on":""),href:p.href},p.icon+" "+p.label)); });
  var inner=el("div",{class:"evnav-in"}); inner.appendChild(brand); inner.appendChild(routes); inner.appendChild(chipsEl());
  var nav=el("nav",{class:"evnav"}); nav.appendChild(inner);
  document.body.insertBefore(nav,document.body.firstChild);
  addEventListener("ev:state",function(){ try{ var old=nav.querySelector(".evchips"); old.replaceWith(chipsEl()); }catch(e){} });

  /* ---- Cmd-K palette ---- */
  var pal=el("div",{class:"evpal"});
  var box=el("div",{class:"evpal-box"});
  var input=el("input",{placeholder:"Jump to a page, report, or AI tool..."});
  var list=el("div",{class:"evpal-list"});
  box.appendChild(input); box.appendChild(list); pal.appendChild(box); document.body.appendChild(pal);
  var sel=0, items=[];

  function index(){
    var d=window.EV_DATA||{},out=[];
    PAGES.forEach(function(p){ out.push({t:p.icon+" "+p.label,s:"page",href:p.href}); });
    (d.ai_tools||[]).forEach(function(a){ out.push({t:"✨ "+a.name,s:"ai tool",href:"cc_ai.html"}); });
    (d.reports||[]).slice(0,120).forEach(function(r){ out.push({t:"\u{1F4C4} "+r.name,s:"report",href:r.file}); });
    return out;
  }
  function draw(q){
    q=(q||"").toLowerCase();
    items=index().filter(function(x){return x.t.toLowerCase().indexOf(q)>=0;}).slice(0,40);
    if(sel>=items.length) sel=0;
    list.textContent="";
    if(!items.length){ var none=el("div",{class:"evpal-row"}); none.appendChild(el("span",{class:"s"},"no matches")); list.appendChild(none); return; }
    items.forEach(function(x,i){
      var row=el("div",{class:"evpal-row"+(i===sel?" sel":"")});
      row.appendChild(el("span",{class:"t"},x.t)); row.appendChild(el("span",{class:"s"},x.s));
      row.onclick=function(){ go(i); }; list.appendChild(row);
    });
  }
  function go(i){ var x=items[i]; if(x){ if(x.href===here) close(); else location.href=x.href; } }
  function open_(){ pal.classList.add("open"); input.value=""; sel=0; draw(""); setTimeout(function(){input.focus();},30); }
  function close(){ pal.classList.remove("open"); }
  input.addEventListener("input",function(){ sel=0; draw(input.value); });
  input.addEventListener("keydown",function(e){
    if(e.key==="ArrowDown"){sel=Math.min(sel+1,items.length-1);draw(input.value);e.preventDefault();}
    else if(e.key==="ArrowUp"){sel=Math.max(sel-1,0);draw(input.value);e.preventDefault();}
    else if(e.key==="Enter"){go(sel);}
    else if(e.key==="Escape"){close();}
  });
  pal.addEventListener("click",function(e){ if(e.target===pal) close(); });
  addEventListener("keydown",function(e){
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); pal.classList.contains("open")?close():open_(); }
    else if(e.key==="/"&&!/input|textarea/i.test((e.target.tagName||""))){ e.preventDefault(); open_(); }
  });
})();
