/* AK-CODEX: Alley Kingz encyclopedia (Wave 7 lane L8, contract L8.3).
   A browsable reference surface covering every card (stats, class, elevation,
   CC subtype, combos, lore, storyline ties), the four factions, the combat-class
   divisions, the build divisions, elevation rules and the synergy reference.

   ONE SOURCE OF TRUTH (no duplicated stat literals): everything renders from the
   existing data objects --
     - stats           : window.CANON_CARDS / CANON_SPELLS / CANON_META (canon.js)
     - lore             : window.AK_LORE_GET (cards_lore.js)
     - class/arch/CC     : window.AK_CLASS_GET + AK.getCards() (classes.js + engine.js L2)
     - elevation         : card.domain / card.targets (engine + canon annotateCombat)
     - combos            : AK.NAMED_SYNERGY + AK.SYNERGY (engine.js L2)
     - storyline         : window.AK_STORY (index.html STORY_ACTS) + AK.SECTION_HOOKS
   Reference COPY (class fantasy, elevation rules, build notes) is authored here;
   only STATS are forbidden from being hand-copied, and none are.

   Lazy-loaded on first open (index.html injects the tag). Headless-safe: every
   DOM touch is guarded and the module no-ops if the data globals are absent.
   NO em-dash characters anywhere (hook law); use -- instead. */
(function (global) {
  'use strict';

  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(m){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]; }); }
  function ak(){ return global.AK || {}; }
  function canonCards(){ return (global.CANON_CARDS || []); }
  function canonSpells(){ return (global.CANON_SPELLS || []); }
  function canonMeta(){ return (global.CANON_META || {}); }
  function engCards(){ try{ var f=ak().getCards; return f ? (f()||{}) : {}; }catch(_e){ return {}; } }
  function loreOf(num){ try{ return global.AK_LORE_GET ? global.AK_LORE_GET(num) : null; }catch(_e){ return null; } }
  function classOf(num){ try{ return global.AK_CLASS_GET ? global.AK_CLASS_GET(num) : null; }catch(_e){ return null; } }
  function story(){ return global.AK_STORY || {}; }
  function rarityCol(r){ try{ return (ak().RARITY_COL && ak().RARITY_COL[r]) || '#9aa9b5'; }catch(_e){ return '#9aa9b5'; } }
  function factionCol(f){ try{ return (ak().FACTION_COL && ak().FACTION_COL[f]) || '#D4AF37'; }catch(_e){ return '#D4AF37'; } }

  // ---- reference COPY (authored here; not stats) ----------------------------
  var FACTION_ORDER = ['boneguard_crew','zoomie_syndicate','leashbreak_tactix','k9_circuitry'];
  var FACTION_INFO = {
    boneguard_crew:   { name:'Boneguard Crew',    short:'BONE', creed:'Walls fall down. We do not.', blurb:'The crown birthplace -- loyalty, walls, taking the hit and staying up. Pain is tuition.', acts:[0,6,9] },
    zoomie_syndicate: { name:'Zoomie Syndicate',  short:'ZOOM', creed:'Fast where it counts.',       blurb:'Speed, contracts, fast money. The alley rewards the dog who is fast WHERE IT COUNTS, not the fastest dog.', acts:[1,4,7] },
    leashbreak_tactix:{ name:'Leashbreak Tactix', short:'LEASH',creed:'Every leash breaks.',         blurb:'The chains are literal -- and so is breaking them. Sabotage is mercy with timing; control is not the same as care.', acts:[2,8] },
    k9_circuitry:     { name:'K9 Circuitry',      short:'K9',   creed:'Hardware is honest. Owners are not.', blurb:'Smuggled tech, drone crates, the iron that builds the war. Intel is a weapon exactly as loyal as its wiring.', acts:[3,5] }
  };
  // crew-synergy multiplier text is read live off AK.SYNERGY (label + numbers).
  function crewSynLine(fid){
    try{
      var s = ak().SYNERGY && ak().SYNERGY[fid]; if(!s) return '';
      var bits=[];
      if(s.speed && s.speed!==1) bits.push('+'+Math.round((s.speed-1)*100)+'% move');
      if(s.damage && s.damage!==1) bits.push('+'+Math.round((s.damage-1)*100)+'% damage');
      if(s.cdRefresh && s.cdRefresh!==1) bits.push('+'+Math.round((s.cdRefresh-1)*100)+'% cooldown refresh');
      if(s.shieldPct) bits.push('+'+Math.round(s.shieldPct*100)+'% max-HP shield');
      return s.label+': '+(bits.join(', ')||'team buff')+' (field '+(ak().SYNERGY_MIN||3)+'+ of the crew)';
    }catch(_e){ return ''; }
  }

  var CLASS_ORDER = ['BRUISER','ASSASSIN','CASTER','MARKSMAN','SUPPORT','SUMMONER','STRUCTURE'];
  var CLASS_INFO = {
    BRUISER:  { tag:'Front-line muscle', desc:'Soaks the hit and holds the block. Walls and brawlers that get up.' },
    ASSASSIN: { tag:'Contract killer',   desc:'In, kill, gone. Burst single-target damage and blink mobility.' },
    CASTER:   { tag:'Signal warfare',    desc:'Disrupts and controls -- jams, snares, blackouts. The block runs on signal.' },
    MARKSMAN: { tag:'Range supremacy',   desc:'Picks a window from distance. Long reach, soft frame.' },
    SUPPORT:  { tag:'Corner clinic',     desc:'Heals, shields and buffs the crew. Keeps the pack standing.' },
    SUMMONER: { tag:'Numbers game',      desc:'Floods the field with tokens. Strength in strays.' },
    STRUCTURE:{ tag:'Planted iron',      desc:'Static turrets, nests and pylons. Out-ranged by towers, never by units (mostly).' }
  };
  var ARCH_INFO = {
    ramper:  { name:'RAMPING DAMAGE', desc:'Damage climbs per consecutive hit on the SAME target, resets on retarget.' },
    turret:  { name:'STATIC TURRET',  desc:'Flat damage plus a timed burst-fire window.' },
    lockdown:{ name:'LOCKDOWN',       desc:'Snare beam holds one unit and keeps a 35% slow field on the rest.' },
    nest:    { name:'SPAWNER NEST',   desc:'Planted den, repeating token spawn, four alive tokens per nest.' },
    pylon:   { name:'AURA PYLON',     desc:'Planted battery, +15% attack speed to allied structures within 3.5 tiles.' }
  };
  var CC_INFO = {
    lock:   { name:'LOCK',   desc:'Hard stop -- stun or root. The unit cannot act.' },
    slow:   { name:'SLOW',   desc:'Drags move and attack speed down for a window.' },
    knock:  { name:'KNOCK',  desc:'Physical knockback -- resets positioning and pathing.' },
    silence:{ name:'SILENCE',desc:'Cuts abilities and tower fire -- no backup, no calls.' },
    denial: { name:'DENIAL', desc:'Blind / reveal -- information control, not hard CC (excluded from CC payoffs).' }
  };
  var BUILD_INFO = [
    { key:'ORIGINAL', name:'ORIGINAL', desc:'The stock dog, canon-balanced -- the baseline of its line.' },
    { key:'HEAVY',    name:'HEAVY',    desc:'The bunkered chop-shop build: up-armored, slower, near-unkillable. Trades bite and speed for a soak frame.' },
    { key:'STREET',   name:'STREET',   desc:'The stripped glass-cannon build: more damage, quicker, but folds to one clean shot.' }
  ];

  // ---- merged card record (canon stats + engine derivations + class + lore) ---
  function cardRecord(cc){
    var num = cc.cardNumber;
    var eng = engCards()[cc.name] || null;
    var kc  = classOf(num) || {};
    var lore = loreOf(num) || {};
    return {
      num:num, name:cc.name, breed:cc.breed||'', faction:cc.factionId, factionName:cc.class,
      rarity:cc.rarity, cost:cc.cost, role:cc.role,
      hp:cc.hp, dmg:cc.damage, atkspd:cc.attack_speed, range:cc.range,          // canon stats, verbatim
      domain:(eng&&eng.domain)||cc.domain||'ground',
      targets:(eng&&eng.targets)||cc.targets||(cc.range>=2?'both':'ground'),
      splash:!!((eng&&eng.splash)||cc.splash),
      cls:(eng&&eng.combatClass)||kc.cls||null,
      arch:(eng&&eng.structArch)||kc.arch||null,
      ccsub:(eng&&eng.ccSubtype)||kc.cc||null,
      variant:cc.variant||'ORIGINAL', family:cc.family||null,
      ability:cc.ability||{name:'',description:''}, queen:!!cc.queen_target, isMythic:!!cc.isMythic,
      tagline:(lore&&lore.tagline)||'', bio:(lore&&lore.bio)||'', desc:cc.desc||''
    };
  }
  function spellRecord(s){
    var lore = loreOf(s.spellNumber) || {};
    return {
      num:s.spellNumber, name:s.name, faction:s.factionId, factionName:s.class, rarity:s.rarity,
      cost:s.cost, role:'Spell', dmg:s.damage||0, range:s.radius||0, isSpell:true,
      ability:{name:s.short||s.name, description:s.description||''},
      tagline:(lore&&lore.tagline)||'', bio:(lore&&lore.bio)||'', desc:s.description||''
    };
  }

  // ---- which named combos a card can power (heuristic by class/role/faction).
  // Reads AK.NAMED_SYNERGY for the LABEL/REQ/EFFECT text -- never re-types it. ----
  function combosFor(rec){
    var list = []; var ns = ak().NAMED_SYNERGY || [];
    var ids = {};
    var cls = rec.cls, role = rec.role, fac = rec.faction;
    function add(id){ ids[id]=1; }
    if(cls==='BRUISER') add('bruiser_wall');
    if(cls==='ASSASSIN'){ add('hit_squad'); add('lock_and_key'); }
    if(cls==='CASTER') add('street_sorcery');
    if(cls==='MARKSMAN'){ add('firing_line'); add('spotter'); }
    if(cls==='SUPPORT'){ add('street_medics'); add('bodyguard_detail'); add('spotter'); }
    if(cls==='SUMMONER') add('puppy_mill');
    if(cls==='STRUCTURE'){ add('turret_net'); add('full_battery'); add('wrecking_crew'); }
    if(rec.ccsub==='silence') add('dead_air');
    if(fac==='boneguard_crew' && rec.isMythic) add('alpha_pack');
    if(role==='Vanguard') add('shield_wall');
    if(role==='Lancer') add('skewer_line');
    if(rec.cost<=3) add('pup_swarm');
    if(rec.rarity==='Epic'||rec.rarity==='Legendary'||rec.rarity==='Mythic') add('big_dog');
    add('chaos_crew');
    for(var i=0;i<ns.length;i++){ if(ids[ns[i].id]) list.push(ns[i]); }
    return list;
  }

  // faction -> the acts it anchors (storyline tie, sourced from AK_STORY titles)
  function storyTie(fid){
    var info = FACTION_INFO[fid]; if(!info) return '';
    var acts = (story().acts)||[];
    var roman = ['I','II','III','IV','V','VI','VII','VIII','IX','X'];
    var names = (info.acts||[]).map(function(i){
      var a = acts[i]; var t = a ? a.title : null;
      return 'Act '+(roman[i]||(i+1))+(t?(' -- '+t):'');
    });
    return info.creed + (names.length ? (' Anchors '+names.join('; ')+'.') : '');
  }

  // ============================ STATE + NAV ===================================
  var state = { tab:'roster', q:'', fFac:'all', fCls:'all', open:null };
  var TABS = [['roster','Roster'],['factions','Crews'],['divisions','Divisions'],['elevation','Elevation'],['combos','Combos'],['story','Story']];

  function navHtml(){
    var t = TABS.map(function(a){
      return '<button class="cdx-tab'+(state.tab===a[0]?' on':'')+'" data-cact="tab" data-tab="'+a[0]+'">'+esc(a[1])+'</button>';
    }).join('');
    return '<div class="cdx-nav">'+t+'</div>';
  }

  // ---------------------------- ROSTER ----------------------------------------
  function rosterHtml(){
    var cards = canonCards().map(cardRecord);
    var spells = canonSpells().map(spellRecord);
    var q = state.q.trim().toLowerCase();
    var facChips = [['all','All']].concat(FACTION_ORDER.map(function(f){ return [f, FACTION_INFO[f].short]; })).concat([['spell','Spells']]);
    var clsChips = [['all','All']].concat(CLASS_ORDER.map(function(c){ return [c, c.slice(0,3)]; }));
    var html = '<div class="cdx-filters">'+
      '<input id="cdx-search" class="cdx-search" type="text" placeholder="Search the roster" value="'+esc(state.q)+'">'+
      '<div class="cdx-chiprow">'+facChips.map(function(c){ return '<button class="cdx-chip'+(state.fFac===c[0]?' on':'')+'" data-cact="ffac" data-val="'+c[0]+'">'+esc(c[1])+'</button>'; }).join('')+'</div>'+
      '<div class="cdx-chiprow">'+clsChips.map(function(c){ return '<button class="cdx-chip'+(state.fCls===c[0]?' on':'')+'" data-cact="fcls" data-val="'+c[0]+'">'+esc(c[1])+'</button>'; }).join('')+'</div>'+
    '</div>';
    var rows = [];
    function match(rec){
      if(state.fFac==='spell'){ if(!rec.isSpell) return false; }
      else if(state.fFac!=='all' && rec.faction!==state.fFac) return false;
      if(state.fCls!=='all' && (rec.isSpell || rec.cls!==state.fCls)) return false;
      if(q){
        var hay = (rec.name+' '+(rec.breed||'')+' '+(rec.factionName||'')+' '+(rec.role||'')+' '+(rec.cls||'')+' '+(rec.tagline||'')).toLowerCase();
        if(hay.indexOf(q)<0) return false;
      }
      return true;
    }
    var all = cards.concat(spells).filter(match);
    all.forEach(function(rec){
      var col = rarityCol(rec.rarity);
      var sub = rec.isSpell ? ('Spell -- '+esc(FACTION_INFO[rec.faction]?FACTION_INFO[rec.faction].short:'NEUTRAL'))
        : (esc(rec.cls||rec.role)+' -- '+esc(rec.role)+(rec.variant&&rec.variant!=='ORIGINAL'?(' -- '+esc(rec.variant)):''));
      rows.push('<button class="cdx-row" data-cact="open" data-num="'+esc(rec.num)+'" style="border-left-color:'+col+'">'+
        '<span class="cdx-rname">'+(rec.isMythic?'<b class="cdx-crown">&#9819;</b> ':'')+esc(rec.name)+'</span>'+
        '<span class="cdx-rsub">'+sub+'</span>'+
        '<span class="cdx-rcost">'+rec.cost+'</span></button>');
    });
    if(!rows.length) rows.push('<div class="cdx-empty">No dogs match that. Try another filter.</div>');
    return html + '<div class="cdx-count">'+all.length+' entries</div><div class="cdx-rows">'+rows.join('')+'</div>';
  }

  // ---------------------------- CARD DETAIL -----------------------------------
  function cardDetailHtml(num){
    var cc = null, sp = null;
    canonCards().forEach(function(c){ if(c.cardNumber===num) cc=c; });
    canonSpells().forEach(function(s){ if(s.spellNumber===num) sp=s; });
    var rec = cc ? cardRecord(cc) : (sp ? spellRecord(sp) : null);
    if(!rec) return '<div class="cdx-empty">No file on this one.</div>';
    var col = rarityCol(rec.rarity);
    var h = '<button class="cdx-back" data-cact="closecard">&larr; Roster</button>';
    h += '<div class="cdx-detail" style="border-color:'+col+'">';
    h += '<div class="cdx-dtop"><div class="cdx-dname">'+(rec.isMythic?'<b class="cdx-crown">&#9819;</b> ':'')+esc(rec.name)+'</div><div class="cdx-dcost">'+rec.cost+'</div></div>';
    h += '<div class="cdx-dmeta">'+esc(rec.rarity)+' &middot; '+esc(rec.factionName||'Neutral')+' &middot; '+esc(rec.role)+(rec.breed?(' &middot; '+esc(rec.breed)):'')+'</div>';
    if(rec.tagline) h += '<div class="cdx-dtag">&quot;'+esc(rec.tagline)+'&quot;</div>';
    // stats (canon verbatim)
    var stats = [];
    if(!rec.isSpell) stats.push(['HP', rec.hp]);
    stats.push(['DMG', rec.dmg]);
    if(!rec.isSpell) stats.push(['ATK/S', rec.atkspd]);
    stats.push([rec.isSpell?'RADIUS':'RANGE', rec.range]);
    h += '<div class="cdx-dstats">'+stats.map(function(s){ return '<div class="cdx-dstat"><b>'+esc(s[1])+'</b><span>'+esc(s[0])+'</span></div>'; }).join('')+'</div>';
    // identity chips: class / archetype / elevation / CC / build
    var chips = [];
    if(rec.cls){ var an = rec.arch ? (ARCH_INFO[rec.arch] ? ARCH_INFO[rec.arch].name : rec.arch) : ''; chips.push('class: '+rec.cls+(an?(' / '+an):'')); }
    if(!rec.isSpell) chips.push((rec.domain==='air'?'AIR':'GROUND')+' -- hits '+(rec.targets==='both'?'ground + air':rec.targets));
    if(rec.ccsub && CC_INFO[rec.ccsub]) chips.push('control: '+CC_INFO[rec.ccsub].name);
    if(rec.splash) chips.push('splash');
    if(rec.queen) chips.push('can strike the Den');
    if(rec.variant && rec.variant!=='ORIGINAL') chips.push('build: '+rec.variant+(rec.family?(' of '+rec.family):''));
    h += '<div class="cdx-dchips">'+chips.map(function(c){ return '<span>'+esc(c)+'</span>'; }).join('')+'</div>';
    // ability
    if(rec.ability && rec.ability.name) h += '<div class="cdx-dability"><b>'+esc(rec.ability.name)+':</b> '+esc(rec.ability.description||'')+'</div>';
    // bio / desc
    if(rec.bio) h += '<div class="cdx-dbio">'+esc(rec.bio)+'</div>';
    else if(rec.desc) h += '<div class="cdx-dbio">'+esc(rec.desc)+'</div>';
    // combos this dog can power
    if(!rec.isSpell){
      var combos = combosFor(rec);
      if(combos.length){
        h += '<div class="cdx-dhead">COMBOS THIS DOG CAN POWER</div><div class="cdx-combos">'+
          combos.map(function(s){ return '<div class="cdx-combo"><b>'+esc(s.label)+'</b><small>'+esc(s.req)+'</small><span>'+esc(s.effect)+'</span></div>'; }).join('')+'</div>';
      }
    }
    // storyline tie (by faction)
    var tie = storyTie(rec.faction);
    if(tie) h += '<div class="cdx-dhead">STORYLINE TIE</div><div class="cdx-dtie">'+esc(tie)+'</div>';
    h += '</div>';
    return h;
  }

  // ---------------------------- FACTIONS --------------------------------------
  function factionsHtml(){
    var counts = {}; canonCards().forEach(function(c){ counts[c.factionId]=(counts[c.factionId]||0)+1; });
    var meta = canonMeta();
    var mythics = (meta.mythics||[]).join(', ');
    var h = '<div class="cdx-lead">Four crews run the city. Commit to one and the crew synergy lights up; mix them and CHAOS CREW pays out instead.</div>';
    FACTION_ORDER.forEach(function(fid){
      var info = FACTION_INFO[fid]; if(!info) return;
      var col = factionCol(fid);
      h += '<div class="cdx-fac" style="border-left-color:'+col+'">';
      h += '<div class="cdx-facname" style="color:'+col+'">'+esc(info.name)+' <small>'+(counts[fid]||0)+' dogs</small></div>';
      h += '<div class="cdx-faccreed">&quot;'+esc(info.creed)+'&quot;</div>';
      h += '<div class="cdx-facblurb">'+esc(info.blurb)+'</div>';
      var cs = crewSynLine(fid); if(cs) h += '<div class="cdx-facsyn">'+esc(cs)+'</div>';
      h += '<div class="cdx-factie">'+esc(storyTie(fid))+'</div>';
      h += '</div>';
    });
    if(mythics) h += '<div class="cdx-lead">Mythics: '+esc(mythics)+'. The dealer himself stays a rumor -- a crown mark, a white paw, a card nobody sees turned.</div>';
    return h;
  }

  // ---------------------------- DIVISIONS -------------------------------------
  function divisionsHtml(){
    var counts = {}; var archCounts = {}; var buildCounts = {};
    canonCards().forEach(function(c){
      var rec = cardRecord(c);
      if(rec.cls) counts[rec.cls]=(counts[rec.cls]||0)+1;
      if(rec.arch) archCounts[rec.arch]=(archCounts[rec.arch]||0)+1;
      buildCounts[rec.variant||'ORIGINAL']=(buildCounts[rec.variant||'ORIGINAL']||0)+1;
    });
    var h = '<div class="cdx-lead">CLASS is the fighting style stacked on top of role. Seven divisions split the whole roster.</div>';
    CLASS_ORDER.forEach(function(cls){
      var info = CLASS_INFO[cls]; if(!info) return;
      h += '<div class="cdx-div"><div class="cdx-divname">'+esc(cls)+' <small>'+(counts[cls]||0)+' dogs -- '+esc(info.tag)+'</small></div>'+
        '<div class="cdx-divdesc">'+esc(info.desc)+'</div></div>';
    });
    h += '<div class="cdx-head2">STRUCTURE ARCHETYPES</div><div class="cdx-lead">Planted iron splits five ways.</div>';
    Object.keys(ARCH_INFO).forEach(function(a){
      h += '<div class="cdx-div"><div class="cdx-divname">'+esc(ARCH_INFO[a].name)+' <small>'+(archCounts[a]||0)+'</small></div>'+
        '<div class="cdx-divdesc">'+esc(ARCH_INFO[a].desc)+'</div></div>';
    });
    h += '<div class="cdx-head2">CHOP-SHOP BUILDS</div><div class="cdx-lead">Most lines run three builds off the same frame.</div>';
    BUILD_INFO.forEach(function(b){
      h += '<div class="cdx-div"><div class="cdx-divname">'+esc(b.name)+' <small>'+(buildCounts[b.key]||0)+'</small></div>'+
        '<div class="cdx-divdesc">'+esc(b.desc)+'</div></div>';
    });
    h += '<div class="cdx-head2">CONTROL SUBTYPES</div>';
    Object.keys(CC_INFO).forEach(function(k){
      h += '<div class="cdx-div"><div class="cdx-divname">'+esc(CC_INFO[k].name)+'</div><div class="cdx-divdesc">'+esc(CC_INFO[k].desc)+'</div></div>';
    });
    return h;
  }

  // ---------------------------- ELEVATION -------------------------------------
  function elevationHtml(){
    var flyers = []; var antiair = 0; var ground = 0;
    canonCards().forEach(function(c){
      var rec = cardRecord(c);
      if(rec.domain==='air') flyers.push(rec);
      else ground++;
      if(rec.targets==='both' || rec.targets==='air') antiair++;
    });
    var byFac = {};
    flyers.forEach(function(r){ (byFac[r.faction]=byFac[r.faction]||[]).push(r.name); });
    var h = '<div class="cdx-lead">Two elevations: GROUND and AIR. Melee (range 1) hits ground only. Every ranged card (range 2+) is anti-air by default, so no crew is helpless against flyers.</div>';
    h += '<div class="cdx-rule"><b>GROUND</b> -- '+ground+' dogs. The default. Eats ground hazards (flood bands) but rides nothing over them.</div>';
    h += '<div class="cdx-rule"><b>AIR</b> -- '+flyers.length+' flyers. Floats over ground-only armies and ground hazards. Folds to light anti-air.</div>';
    h += '<div class="cdx-rule"><b>ANTI-AIR</b> -- '+antiair+' cards can hit air (every range 2+ unit plus most spells).</div>';
    h += '<div class="cdx-head2">THE FLYERS</div>';
    FACTION_ORDER.forEach(function(fid){
      var list = byFac[fid]; if(!list||!list.length) return;
      h += '<div class="cdx-div"><div class="cdx-divname">'+esc(FACTION_INFO[fid].name)+' <small>'+list.length+'</small></div>'+
        '<div class="cdx-divdesc">'+esc(list.join(', '))+'</div></div>';
    });
    return h;
  }

  // ---------------------------- COMBOS ----------------------------------------
  function combosHtml(){
    var ns = ak().NAMED_SYNERGY || [];
    var h = '<div class="cdx-lead">CREW SYNERGY rewards committing to one faction. NAMED COMBOS reward class and role mixes. Both are symmetric -- the enemy earns the exact same buffs.</div>';
    h += '<div class="cdx-head2">CREW SYNERGY</div>';
    FACTION_ORDER.forEach(function(fid){
      var cs = crewSynLine(fid); if(cs) h += '<div class="cdx-syn"><b style="color:'+factionCol(fid)+'">'+esc(FACTION_INFO[fid].name)+'</b><span>'+esc(cs)+'</span></div>';
    });
    h += '<div class="cdx-head2">NAMED COMBOS</div>';
    if(!ns.length) h += '<div class="cdx-empty">Combo table not loaded.</div>';
    ns.forEach(function(s){
      h += '<div class="cdx-syn"><b>'+esc(s.label)+'</b><small>'+esc(s.req||'')+'</small><span>'+esc(s.effect||'')+'</span>'+
        (s.hint?('<em>'+esc(s.hint)+'</em>'):'')+'</div>';
    });
    return h;
  }

  // ---------------------------- STORY -----------------------------------------
  function storyHtml(){
    var acts = (story().acts)||[];
    var hooks = (ak().SECTION_HOOKS)||(story().hooks)||[];
    var roman = ['I','II','III','IV','V','VI','VII','VIII','IX','X'];
    var h = '<div class="cdx-lead">Ten cities stand between the dirt you were born in and the gold chair somebody keeps warm. The climb is the frame; YOUR run is the picture. No two strays climb the same.</div>';
    if(!acts.length) h += '<div class="cdx-empty">Storyline not loaded yet.</div>';
    acts.forEach(function(a,i){
      if(!a) return;
      h += '<div class="cdx-act">';
      h += '<div class="cdx-actname">ACT '+(roman[i]||(i+1))+' -- '+esc(a.title||'')+'</div>';
      if(a.intro) h += '<div class="cdx-actintro">'+esc(a.intro)+'</div>';
      if(a.boss){
        h += '<div class="cdx-boss"><b>CITY BOSS -- '+esc(a.boss.name||'')+'</b>'+
          (a.boss.title?('<small>'+esc(a.boss.title)+'</small>'):'')+
          (a.boss.intro?('<span>'+esc(a.boss.intro)+'</span>'):'')+'</div>';
      }
      if(a.clear) h += '<div class="cdx-clear">&quot;'+esc(a.clear)+'&quot;</div>';
      h += '</div>';
    });
    if(hooks && hooks.length){
      var districts = ['THE LOT','NEON NIGHT','INDUSTRIAL','RAIN DOCKS'];
      h += '<div class="cdx-head2">DISTRICT HOOKS (the convoy ride)</div>';
      hooks.forEach(function(line,i){ if(!line) return; h += '<div class="cdx-syn"><b>'+esc(districts[i]||('DISTRICT '+(i+1)))+'</b><span>&quot;'+esc(line)+'&quot;</span></div>'; });
    }
    return h;
  }

  // ============================ RENDER + EVENTS ===============================
  function bodyHtml(){
    if(state.tab==='roster' && state.open) return cardDetailHtml(state.open);
    switch(state.tab){
      case 'roster':    return rosterHtml();
      case 'factions':  return factionsHtml();
      case 'divisions': return divisionsHtml();
      case 'elevation': return elevationHtml();
      case 'combos':    return combosHtml();
      case 'story':     return storyHtml();
      default:          return rosterHtml();
    }
  }

  var _root = null, _wired = false;
  function paint(){
    if(!_root) return;
    try{ _root.innerHTML = '<div class="cdx-wrap">'+navHtml()+'<div class="cdx-body">'+bodyHtml()+'</div></div>'; }catch(_e){}
    // keep focus + caret on the search box across re-renders (browser only)
    try{
      if(state.tab==='roster' && !state.open && typeof document!=='undefined'){
        var s = document.getElementById('cdx-search');
        if(s){
          s.addEventListener('input', function(){ state.q = s.value; clearTimeout(paint._t); paint._t = setTimeout(paint, 140); });
          if(s.value){ s.focus(); try{ s.setSelectionRange(s.value.length, s.value.length); }catch(_e2){} }
        }
      }
    }catch(_e){}
  }
  function onClick(ev){
    try{
      var node = ev.target && ev.target.closest ? ev.target.closest('[data-cact]') : null;
      if(!node) return;
      var act = node.getAttribute('data-cact');
      if(act==='tab'){ state.tab = node.getAttribute('data-tab'); state.open=null; paint(); }
      else if(act==='ffac'){ state.fFac = node.getAttribute('data-val'); paint(); }
      else if(act==='fcls'){ state.fCls = node.getAttribute('data-val'); paint(); }
      else if(act==='open'){ state.open = node.getAttribute('data-num'); paint(); try{ _root.scrollTop=0; }catch(_e){} }
      else if(act==='closecard'){ state.open = null; paint(); }
    }catch(_e){}
  }

  function injectStyle(){
    try{
      if(typeof document==='undefined') return;
      if(document.getElementById('akcodex-style')) return;
      var st = document.createElement('style'); st.id='akcodex-style';
      st.textContent = [
        '#akcodexscreen{ justify-content:flex-start; padding:0; }',
        '#akcodexroot{ width:100%; max-width:480px; height:100%; overflow-y:auto; -webkit-overflow-scrolling:touch; padding:14px 12px 90px; }',
        '.cdx-wrap{ display:flex; flex-direction:column; gap:10px; }',
        '.cdx-nav{ position:sticky; top:0; z-index:2; display:flex; flex-wrap:wrap; gap:5px; padding:6px 0; background:rgba(5,5,7,0.96); }',
        '.cdx-tab{ flex:1 1 auto; min-width:62px; padding:7px 6px; font:600 11px Inter,sans-serif; letter-spacing:0.04em; color:var(--gold-lo,#b9962f); background:rgba(212,175,55,0.06); border:1px solid rgba(212,175,55,0.3); border-radius:8px; cursor:pointer; }',
        '.cdx-tab.on{ color:#0a0a0a; background:var(--gold-hi,#F2E2A8); border-color:var(--gold-hi,#F2E2A8); }',
        '.cdx-body{ text-align:left; }',
        '.cdx-lead{ font:italic 600 12px "Playfair Display",serif; color:var(--gold-lo,#b9962f); margin:4px 2px 8px; line-height:1.5; }',
        '.cdx-head2{ font:800 13px Cinzel,serif; color:var(--gold-hi,#F2E2A8); letter-spacing:0.06em; margin:14px 2px 6px; }',
        '.cdx-filters{ display:flex; flex-direction:column; gap:6px; }',
        '.cdx-search{ width:100%; padding:9px 11px; font:500 13px Inter,sans-serif; color:#E8E8E8; background:rgba(255,255,255,0.05); border:1px solid rgba(212,175,55,0.3); border-radius:9px; }',
        '.cdx-chiprow{ display:flex; flex-wrap:wrap; gap:5px; }',
        '.cdx-chip{ padding:5px 9px; font:600 11px Inter,sans-serif; color:var(--gold-lo,#b9962f); background:rgba(212,175,55,0.05); border:1px solid rgba(212,175,55,0.25); border-radius:20px; cursor:pointer; }',
        '.cdx-chip.on{ color:#0a0a0a; background:var(--gold-hi,#F2E2A8); border-color:var(--gold-hi,#F2E2A8); }',
        '.cdx-count{ font:600 10px Inter,sans-serif; color:#6f7681; letter-spacing:0.1em; margin:8px 2px 4px; }',
        '.cdx-rows{ display:flex; flex-direction:column; gap:5px; }',
        '.cdx-row{ display:flex; align-items:center; gap:8px; width:100%; text-align:left; padding:9px 11px; background:rgba(255,255,255,0.035); border:1px solid rgba(212,175,55,0.14); border-left:3px solid #9aa9b5; border-radius:8px; cursor:pointer; }',
        '.cdx-row:active{ transform:scale(0.99); }',
        '.cdx-rname{ flex:1 1 auto; font:700 13px Inter,sans-serif; color:#E8E8E8; }',
        '.cdx-rsub{ font:600 10px Inter,sans-serif; color:#8b929c; letter-spacing:0.03em; text-transform:uppercase; }',
        '.cdx-rcost{ font:800 14px Cinzel,serif; color:var(--gold-hi,#F2E2A8); min-width:18px; text-align:right; }',
        '.cdx-crown{ color:var(--gold-hi,#F2E2A8); }',
        '.cdx-empty{ font:600 12px Inter,sans-serif; color:#8b929c; padding:18px 4px; }',
        '.cdx-back{ font:700 12px Inter,sans-serif; color:var(--gold-hi,#F2E2A8); background:none; border:none; cursor:pointer; padding:4px 0 8px; }',
        '.cdx-detail{ border:1px solid #9aa9b5; border-radius:12px; padding:14px; background:rgba(255,255,255,0.03); }',
        '.cdx-dtop{ display:flex; align-items:center; justify-content:space-between; }',
        '.cdx-dname{ font:800 19px Cinzel,serif; color:#fff; }',
        '.cdx-dcost{ font:800 18px Cinzel,serif; color:var(--gold-hi,#F2E2A8); }',
        '.cdx-dmeta{ font:600 11px Inter,sans-serif; color:#8b929c; letter-spacing:0.03em; text-transform:uppercase; margin-top:2px; }',
        '.cdx-dtag{ font:italic 600 13px "Playfair Display",serif; color:var(--gold-lo,#b9962f); margin:8px 0; }',
        '.cdx-dstats{ display:flex; gap:8px; margin:10px 0; }',
        '.cdx-dstat{ flex:1; text-align:center; padding:7px 2px; background:rgba(212,175,55,0.06); border-radius:8px; }',
        '.cdx-dstat b{ display:block; font:800 16px Cinzel,serif; color:#E8E8E8; }',
        '.cdx-dstat span{ font:700 9px Inter,sans-serif; color:#8b929c; letter-spacing:0.08em; }',
        '.cdx-dchips{ display:flex; flex-wrap:wrap; gap:5px; margin:8px 0; }',
        '.cdx-dchips span{ font:600 10px Inter,sans-serif; color:var(--gold-lo,#b9962f); background:rgba(212,175,55,0.07); border:1px solid rgba(212,175,55,0.22); border-radius:6px; padding:3px 7px; }',
        '.cdx-dability{ font:500 12px Inter,sans-serif; color:#cdd3da; margin:8px 0; }',
        '.cdx-dability b{ color:var(--gold-hi,#F2E2A8); }',
        '.cdx-dbio{ font:500 12px Inter,sans-serif; color:#aab0b8; line-height:1.5; margin:8px 0; }',
        '.cdx-dhead{ font:800 11px Cinzel,serif; color:var(--gold-hi,#F2E2A8); letter-spacing:0.06em; margin:10px 0 5px; }',
        '.cdx-combos{ display:flex; flex-direction:column; gap:5px; }',
        '.cdx-combo{ padding:7px 9px; background:rgba(212,175,55,0.05); border-radius:7px; }',
        '.cdx-combo b{ font:700 12px Inter,sans-serif; color:#E8E8E8; }',
        '.cdx-combo small{ display:block; font:600 10px Inter,sans-serif; color:#8b929c; margin:1px 0; }',
        '.cdx-combo span{ font:500 11px Inter,sans-serif; color:var(--gold-lo,#b9962f); }',
        '.cdx-dtie{ font:italic 600 12px "Playfair Display",serif; color:#aab0b8; line-height:1.5; }',
        '.cdx-fac,.cdx-div,.cdx-syn,.cdx-rule,.cdx-act{ padding:10px 12px; background:rgba(255,255,255,0.035); border:1px solid rgba(212,175,55,0.14); border-radius:9px; margin-bottom:7px; }',
        '.cdx-fac{ border-left:3px solid #D4AF37; }',
        '.cdx-facname{ font:800 15px Cinzel,serif; }',
        '.cdx-facname small{ font:600 10px Inter,sans-serif; color:#8b929c; }',
        '.cdx-faccreed{ font:italic 600 12px "Playfair Display",serif; color:var(--gold-lo,#b9962f); margin:3px 0; }',
        '.cdx-facblurb,.cdx-divdesc{ font:500 12px Inter,sans-serif; color:#aab0b8; line-height:1.5; }',
        '.cdx-facsyn{ font:600 11px Inter,sans-serif; color:var(--gold-hi,#F2E2A8); margin-top:5px; }',
        '.cdx-factie{ font:500 11px Inter,sans-serif; color:#8b929c; margin-top:4px; }',
        '.cdx-divname{ font:700 13px Inter,sans-serif; color:#E8E8E8; }',
        '.cdx-divname small{ font:600 10px Inter,sans-serif; color:#8b929c; }',
        '.cdx-rule b{ color:var(--gold-hi,#F2E2A8); }',
        '.cdx-rule{ font:500 12px Inter,sans-serif; color:#aab0b8; }',
        '.cdx-syn{ display:flex; flex-direction:column; gap:1px; }',
        '.cdx-syn b{ font:700 12px Inter,sans-serif; color:#E8E8E8; }',
        '.cdx-syn small{ font:600 10px Inter,sans-serif; color:#8b929c; }',
        '.cdx-syn span{ font:500 11px Inter,sans-serif; color:var(--gold-lo,#b9962f); }',
        '.cdx-syn em{ font:italic 500 10px "Playfair Display",serif; color:#6f7681; }',
        '.cdx-actname{ font:800 14px Cinzel,serif; color:var(--gold-hi,#F2E2A8); }',
        '.cdx-actintro{ font:500 12px Inter,sans-serif; color:#aab0b8; line-height:1.55; margin:5px 0; }',
        '.cdx-boss{ margin:6px 0; padding:7px 9px; background:rgba(212,175,55,0.05); border-radius:7px; }',
        '.cdx-boss b{ font:700 12px Inter,sans-serif; color:#E8E8E8; }',
        '.cdx-boss small{ display:block; font:italic 600 11px "Playfair Display",serif; color:var(--gold-lo,#b9962f); margin:1px 0; }',
        '.cdx-boss span{ font:500 11px Inter,sans-serif; color:#aab0b8; line-height:1.5; }',
        '.cdx-clear{ font:italic 700 12px "Playfair Display",serif; color:var(--gold-hi,#F2E2A8); margin-top:5px; }'
      ].join('\n');
      document.head.appendChild(st);
    }catch(_e){}
  }

  function render(container){
    _root = container || (typeof document!=='undefined' ? document.getElementById('akcodexroot') : null);
    if(!_root) return;
    injectStyle();
    state.open = null; state.tab = state.tab || 'roster';
    if(!_wired){ try{ _root.addEventListener('click', onClick); _wired=true; }catch(_e){} }
    paint();
  }

  global.AK_CODEX = { render: render, _state: state };
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
