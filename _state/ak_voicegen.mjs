// Generate ElevenLabs voice mp3s for all 111 Alley Kingz lore taglines.
// Runs on e5-mother (has internet). Idempotent + resumable (skips existing mp3s).
import fs from 'node:fs';
import path from 'node:path';
const GAME = process.env.AK_GAME || (process.env.HOME + '/ak_deploy/game');
const KEY = process.env.ELEVENLABS_API_KEY;
if(!KEY){ console.log('NO ELEVENLABS_API_KEY'); process.exit(2); }
const OUT = path.join(GAME, 'assets', 'voices');
fs.mkdirSync(OUT, { recursive: true });

// --- parse cards_lore.js -> { num: tagline } ---
const lore = fs.readFileSync(path.join(GAME, 'cards_lore.js'), 'utf8');
const taglines = {};
for(const m of lore.matchAll(/"([0-9]{4}|S[0-9]{3})"\s*:\s*\{\s*tagline:\s*"((?:[^"\\]|\\.)*)"/g)){
  taglines[m[1]] = m[2].replace(/\\"/g,'"');
}

// --- parse canon.js -> { num: {breed, faction} } ---
const canon = fs.readFileSync(path.join(GAME, 'canon.js'), 'utf8');
const meta = {};
for(const c of canon.matchAll(/\{[^{}]*?"cardNumber"\s*:\s*"([0-9]{4})"[^{}]*?\}/g)){
  const blk=c[0], num=c[1];
  const breed=(blk.match(/"breed"\s*:\s*"([^"]*)"/)||[])[1]||'';
  const faction=(blk.match(/"faction"\s*:\s*"([^"]*)"/)||[])[1]||'';
  meta[num]={breed,faction};
}

const SIZE = { 'Chihuahua':0,'Pomeranian':0,'Toy Poodle':0,'Dachshund':1,'Beagle':1,'Corgi':1,'Jack Russell':1,'Whippet':1,
  'Border Collie':2,'Husky':2,'Boxer':2,'Pit Bull':2,'Bulldog':2,'Doberman':3,'German Shepherd':3,'Rottweiler':3,'Akita':3,'Dogo Argentino':3,
  'Mastiff':4,'Saint Bernard':4,'Great Dane':4,'Cane Corso':4 };
const V = { adam:'pNInz6obpgDQGcFmaJgB', arnold:'VR6AewLTigWG4xSOukaG', antoni:'ErXwobaYiN019PkySvjV',
  josh:'TxGEqnHWrfWFTfGW9XjX', sam:'yoZ06aMxZJJ28mfd3POQ', clyde:'2EiwWnXFnvU5JabPnv8n',
  bella:'EXAVITQu4vr4xnSDxMaL', rachel:'21m00Tcm4TlvDq8ikWAM', domi:'AZnzlk1XvdvUeBnXmlld' };
function pickVoice(num){
  const md=meta[num]||{}; const f=md.faction||''; const sz=SIZE[md.breed]!=null?SIZE[md.breed]:2;
  if(sz>=4) return V.arnold;
  if(/Boneguard/i.test(f)) return sz>=3?V.arnold:V.adam;
  if(/Zoomie/i.test(f))    return sz<=1?V.josh:V.antoni;
  if(/Leashbreak/i.test(f))return sz<=1?V.sam:V.antoni;
  if(/K9|Circuit/i.test(f))return V.clyde;
  return V.sam;
}

const nums = Object.keys(taglines);
console.log('taglines:', nums.length, '| out:', OUT);
let made=0, skip=0, fail=0;
for(const num of nums){
  const out = path.join(OUT, num + '.mp3');
  if(fs.existsSync(out) && fs.statSync(out).size > 2000){ skip++; continue; }
  const voice = pickVoice(num);
  const body = JSON.stringify({ text: taglines[num], model_id:'eleven_multilingual_v2',
    voice_settings:{ stability:0.45, similarity_boost:0.8, style:0.15, use_speaker_boost:true } });
  try{
    const r = await fetch('https://api.elevenlabs.io/v1/text-to-speech/'+voice,
      { method:'POST', headers:{ 'xi-api-key':KEY, 'content-type':'application/json', 'accept':'audio/mpeg' }, body });
    if(!r.ok){ fail++; console.log('FAIL', num, r.status, (await r.text()).slice(0,80)); if(r.status===401){break;} continue; }
    const buf = Buffer.from(await r.arrayBuffer());
    fs.writeFileSync(out, buf);
    made++; if(made%15===0) console.log('  ...',made,'made');
  }catch(e){ fail++; console.log('ERR', num, String(e).slice(0,80)); }
  await new Promise(r=>setTimeout(r,250));
}
console.log('VOICEGEN DONE made='+made+' skipped='+skip+' fail='+fail+' total='+nums.length);
