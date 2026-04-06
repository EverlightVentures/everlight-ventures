// ============================================================
// ALLEY KINGZ -- COMBAT UPGRADE SYSTEMS
// System 1: Unit State Machine
// System 2: Enhanced VFX System
//
// INTEGRATION GUIDE:
//   These are exact code replacements and additions for game_v6.html.
//   Each block is labeled with an INSERTION MARKER showing where
//   it goes relative to existing code (line numbers from v6).
// ============================================================


// ============================================================
// SYSTEM 1: UNIT STATE MACHINE
// ============================================================


// ─────────────────────────────────────────────────────────────
// MARKER [A]: Replace Unit constructor (lines 435-470)
//   Old: class Unit { constructor(card,owner,x,y){ ... } ... }
//   New: adds this.state, this.stateTimer, this.prevX/prevY,
//        this.deployScale, this.acquireTarget
// ─────────────────────────────────────────────────────────────

// Unit states enum
const USTATE = {
  DEPLOY:  'deploy',
  MOVE:    'move',
  ACQUIRE: 'acquire',
  WINDUP:  'windup',
  ATTACK:  'attack',
  RECOVER: 'recover',
  HIT:     'hit',
  DIE:     'die'
};

class Unit {
  constructor(card, owner, x, y) {
    this.id = _uid++; this.card = card; this.owner = owner; this.x = x; this.y = y;
    this.maxHp = card.hp; this.hp = card.hp; this.dmg = card.dmg;
    // Physics: current velocity starts at 0, accelerates to card.speed
    // Calculus: v(t) = v_max * (1 - e^(-accel*t))
    this.maxSpeed = card.speed; this.currentSpeed = 0;
    this.accel = card.accel || 2.0; this.armor = card.armor || 0;
    this.range = card.range; this.atkSpd = card.atkSpd; this.atkCD = 0; this.abilityCD = card.abilityCD || 0;
    this.target = null; this.alive = true;
    this.angle = owner === 0 ? -Math.PI / 2 : Math.PI / 2;
    this.targetAngle = this.angle; // smooth rotation
    this.nitroActive = false; this.nitroTimer = 0; this.bobOffset = Math.random() * Math.PI * 2;
    this.stealthTimer = card.ability === 'STEALTH' ? 3 : 0; this.stunTimer = 0; this.slowTimer = 0;
    this.spawnTime = 0; // starts at 0 now -- DEPLOY state handles the intro
    this.hitFlash = 0;
    this.deathTimer = -1; // -1=alive, 0+=dying animation
    this.zHeight = 0; // for 3D jump effects

    // --- STATE MACHINE (new) ---
    this.state = USTATE.DEPLOY;
    this.stateTimer = 0;
    this.deployScale = 0;     // 0->1 scale-up during DEPLOY
    this.prevX = x;           // previous frame position for trail VFX
    this.prevY = y;
    this.acquireTarget = null; // locked target during ACQUIRE->WINDUP->ATTACK
    this.windupOffset = 0;    // visual pullback during WINDUP (-1 to 0)
    this.hitKnockX = 0;       // knockback displacement during HIT state
    this.hitKnockY = 0;
    this.hitSourceAngle = 0;  // angle from which damage came
    this.deathPhase = 0;      // 0=freeze, 1=flash+shockwave, 2=debris
  }

  takeDamage(d, sourceX, sourceY) {
    if (!this.alive) return;
    // Apply armor reduction ONLY (Algebra): effective = raw * 100/(100+armor)
    const effective = Math.floor(d * 100 / (100 + (this.armor || 0)));
    this.hp = Math.max(0, this.hp - effective);
    this.hitFlash = 0.12;

    // Trigger HIT state interrupt (only if alive after damage)
    if (this.hp > 0 && this.state !== USTATE.DIE && this.state !== USTATE.DEPLOY) {
      this.state = USTATE.HIT;
      this.stateTimer = 0;
      // Calculate knockback direction from source
      if (sourceX !== undefined && sourceY !== undefined) {
        this.hitSourceAngle = Math.atan2(this.y - sourceY, this.x - sourceX);
      } else {
        this.hitSourceAngle = this.angle + Math.PI; // fallback: knocked backward
      }
      this.hitKnockX = 0;
      this.hitKnockY = 0;
    }

    // VFX: big damage pop for heavy hits
    if (effective >= 150) {
      addBigDamagePop(this.x, this.y, effective);
    }

    if (this.hp <= 0) {
      this.hp = 0; this.alive = false; this.deathTimer = 0;
      this.state = USTATE.DIE; this.stateTimer = 0; this.deathPhase = 0;
      sfxDeath();
      // Death VFX handled by state machine, not here anymore
    }
  }

  dist(ox, oy) { return Math.hypot(this.x - ox, this.y - oy); }

  // Calculus: current speed based on acceleration curve
  // v(t) = v_max * (1 - e^(-accel * t))
  getSpeed() {
    const base = this.maxSpeed * (1 - Math.exp(-this.accel * this.spawnTime));
    if (this.nitroActive) return base * 1.5;
    if (this.slowTimer > 0) return base * 0.5;
    return base;
  }
}


// ─────────────────────────────────────────────────────────────
// MARKER [B]: Replace updateUnits() (lines 834-874)
//   Old: implicit state logic with if/else chains
//   New: explicit state machine with transitions
// ─────────────────────────────────────────────────────────────

function updateUnits(dt) {
  for (const u of units) {
    // --- DEAD UNIT: just tick death timer ---
    if (!u.alive) {
      if (u.deathTimer >= 0) u.deathTimer += dt;
      if (u.state === USTATE.DIE) updateDeathState(u, dt);
      continue;
    }

    // --- TICK COMMON TIMERS ---
    u.spawnTime += dt;
    if (u.abilityCD > 0) u.abilityCD -= dt;
    if (u.stealthTimer > 0) u.stealthTimer -= dt;
    if (u.hitFlash > 0) u.hitFlash -= dt;
    if (u.slowTimer > 0) u.slowTimer -= dt;
    if (u.nitroActive) { u.nitroTimer -= dt; if (u.nitroTimer <= 0) { u.nitroActive = false; } }

    // --- STUN overrides all states except DEPLOY/DIE ---
    if (u.stunTimer > 0) {
      u.stunTimer -= dt;
      continue; // frozen in place
    }

    // Save previous position for trail VFX
    u.prevX = u.x;
    u.prevY = u.y;

    // Bobbing animation (always runs)
    u.bobOffset += dt * 3;

    // Smooth angle rotation (Trigonometry: angular interpolation)
    const angleDiff = ((u.targetAngle - u.angle + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
    u.angle += angleDiff * Math.min(1, dt * 8);

    // Increment state timer
    u.stateTimer += dt;

    // --- STATE MACHINE ---
    switch (u.state) {

      case USTATE.DEPLOY:
        updateDeployState(u, dt);
        break;

      case USTATE.MOVE:
        updateMoveState(u, dt);
        break;

      case USTATE.ACQUIRE:
        updateAcquireState(u, dt);
        break;

      case USTATE.WINDUP:
        updateWindupState(u, dt);
        break;

      case USTATE.ATTACK:
        updateAttackState(u, dt);
        break;

      case USTATE.RECOVER:
        updateRecoverState(u, dt);
        break;

      case USTATE.HIT:
        updateHitState(u, dt);
        break;

      case USTATE.DIE:
        // Should not reach here if alive, but guard
        break;
    }
  }
}

// --- Individual state update functions ---

function enterState(u, state) {
  u.state = state;
  u.stateTimer = 0;
}

function updateDeployState(u, dt) {
  // 0-0.3s: unit appears with scale-up animation + deploy ring
  const DEPLOY_DUR = 0.3;
  u.deployScale = Math.min(1, u.stateTimer / DEPLOY_DUR);

  // Spawn deploy ring VFX once at start
  if (u.stateTimer < dt * 1.5) {
    addDeployRingVFX(u.x, u.y, u.card.carColor || '#fff');
  }

  if (u.stateTimer >= DEPLOY_DUR) {
    u.deployScale = 1;
    enterState(u, USTATE.MOVE);
  }
}

function updateMoveState(u, dt) {
  // Chop Shop spawner (building override)
  if (u.card.id === 'chop_shop' && u.card.type === 'building') {
    if (u.abilityCD <= 0) {
      u.abilityCD = 12; const sc = CARS['rust_bucket'];
      if (sc) units.push(new Unit(sc, u.owner, u.x + (Math.random() - 0.5), u.y + (u.owner === 0 ? -1 : 1)));
      addEffect('ability', u.x, u.y, 'SPAWN!', '#AA6633', 0.8);
    }
    return;
  }

  // Buildings: find target and attack directly
  if (u.card.type === 'building') {
    if (u.atkCD > 0) { u.atkCD -= dt; return; }
    findTarget(u);
    if (u.target) {
      u.acquireTarget = u.target;
      enterState(u, USTATE.ACQUIRE);
    }
    return;
  }

  // Tick attack cooldown during movement
  if (u.atkCD > 0) u.atkCD -= dt;

  // Find target
  findTarget(u);

  if (u.target) {
    const hitRange = u.range + (u.target instanceof Tower ? 1.0 : 0.3);
    const d = u.dist(u.target.x, u.target.y);
    if (d <= hitRange) {
      if (u.atkCD <= 0) {
        // In range and ready: transition to ACQUIRE
        u.acquireTarget = u.target;
        enterState(u, USTATE.ACQUIRE);
      }
      // else: in range but on cooldown, idle (stay in MOVE but don't walk)
    } else {
      // Walk toward target
      moveToward(u, u.target.x, u.target.y, dt);
    }
  } else {
    // No target: walk toward enemy king
    const ek = (u.owner === 0 ? opponent : player).towers.find(t => t.type === 'king');
    if (ek) moveToward(u, ek.x, ek.y, dt);
  }
}

function updateAcquireState(u, dt) {
  // 0.1s brief pause when locking onto target
  const ACQUIRE_DUR = 0.1;

  // Validate target still exists
  if (!u.acquireTarget || (u.acquireTarget.hp !== undefined && u.acquireTarget.hp <= 0) ||
      (u.acquireTarget instanceof Tower && u.acquireTarget.destroyed) ||
      (!(u.acquireTarget instanceof Tower) && !u.acquireTarget.alive)) {
    // Target died during acquire, go back to MOVE
    u.acquireTarget = null;
    enterState(u, USTATE.MOVE);
    return;
  }

  // Face the target during acquire
  const dx = u.acquireTarget.x - u.x, dy = u.acquireTarget.y - u.y;
  u.targetAngle = Math.atan2(dy, dx);

  if (u.stateTimer >= ACQUIRE_DUR) {
    enterState(u, USTATE.WINDUP);
  }
}

function updateWindupState(u, dt) {
  // 0.15s anticipation: unit pulls back slightly before strike
  const WINDUP_DUR = 0.15;

  // Validate target
  if (!isTargetValid(u.acquireTarget)) {
    u.acquireTarget = null;
    u.windupOffset = 0;
    enterState(u, USTATE.MOVE);
    return;
  }

  // Visual pullback: ease out from 0 to -1 and back
  const prog = u.stateTimer / WINDUP_DUR;
  u.windupOffset = -Math.sin(prog * Math.PI) * 0.15; // slight backward pull in game units

  if (u.stateTimer >= WINDUP_DUR) {
    enterState(u, USTATE.ATTACK);
  }
}

function updateAttackState(u, dt) {
  // Instant frame: trigger damage + VFX + SFX, then go to RECOVER
  u.windupOffset = 0; // snap forward

  // Validate target one more time
  if (!isTargetValid(u.acquireTarget)) {
    u.acquireTarget = null;
    enterState(u, USTATE.MOVE);
    return;
  }

  // Set the .target for unitAttack compatibility
  u.target = u.acquireTarget;

  // Execute the attack
  unitAttack(u);

  // Melee impact puff VFX
  if (u.range <= 2 && u.target) {
    addImpactPuff(u.target.x, u.target.y, u.card.carColor || '#fff');
  }

  // Transition to RECOVER
  enterState(u, USTATE.RECOVER);
}

function updateRecoverState(u, dt) {
  // Wait for atkCD to expire, then return to MOVE
  if (u.atkCD > 0) u.atkCD -= dt;

  if (u.atkCD <= 0) {
    u.acquireTarget = null;
    enterState(u, USTATE.MOVE);
  }
}

function updateHitState(u, dt) {
  // 0.08s flash + knockback when taking damage
  const HIT_DUR = 0.08;
  const KNOCK_DIST = 0.12; // game units knockback

  // Apply knockback displacement (decaying)
  const prog = u.stateTimer / HIT_DUR;
  const knockProg = 1 - prog; // strongest at start, fades
  u.hitKnockX = Math.cos(u.hitSourceAngle) * KNOCK_DIST * knockProg;
  u.hitKnockY = Math.sin(u.hitSourceAngle) * KNOCK_DIST * knockProg;

  // Apply knockback to position (tiny, just visual weight)
  u.x += u.hitKnockX * dt * 10;
  u.y += u.hitKnockY * dt * 10;

  if (u.stateTimer >= HIT_DUR) {
    u.hitKnockX = 0;
    u.hitKnockY = 0;
    // Return to whatever makes sense: if had a target, go back to MOVE
    enterState(u, USTATE.MOVE);
  }
}

function updateDeathState(u, dt) {
  // 3-phase death sequence
  const t = u.deathTimer; // total time since death
  if (t < 0.1) {
    // Phase 0: time freeze (slight pause effect) -- handled by deathTimer ticking slowly
    u.deathPhase = 0;
  } else if (t < 0.3) {
    // Phase 1: white flash + expanding shockwave ring
    if (u.deathPhase < 1) {
      u.deathPhase = 1;
      addDeathShockwave(u.x, u.y, u.card.carColor || '#FF4400');
    }
  } else if (t < 0.5) {
    // Phase 2: debris scatter + smoke plume
    if (u.deathPhase < 2) {
      u.deathPhase = 2;
      addDeathDebris(u.x, u.y, u.card.carColor || '#FF4400');
    }
  }
}

function isTargetValid(target) {
  if (!target) return false;
  if (target instanceof Tower) return !target.destroyed;
  return target.alive;
}


// ─────────────────────────────────────────────────────────────
// MARKER [C]: Patch unitAttack() -- NO structural change needed
//   The existing unitAttack() function at line 916 stays as-is.
//   The state machine calls it from updateAttackState().
//   Only change: unitAttack no longer sets u.atkCD since
//   RECOVER state handles it. WAIT -- actually unitAttack
//   already sets u.atkCD=1/u.atkSpd, which is fine. RECOVER
//   just waits for it to count down. No change needed.
// ─────────────────────────────────────────────────────────────


// ─────────────────────────────────────────────────────────────
// MARKER [D]: Patch renderUnits3D() -- add deploy scale +
//   windup offset to the render. Insert these modifications
//   into the existing function at line 1560.
//
//   After line 1572 (const bob=...), add:
// ─────────────────────────────────────────────────────────────

// INSERT AFTER: const bob=Math.sin(u.bobOffset)*scale*0.04*df;
// ADD THESE LINES:
//
//   // STATE MACHINE: deploy scale-up
//   const deployScale = (u.state === USTATE.DEPLOY) ? u.deployScale : 1;
//   // STATE MACHINE: windup pullback offset (in facing direction)
//   const windupOff = (u.windupOffset || 0) * scale * df;
//
// THEN modify the ctx.translate line (line 1598) from:
//   ctx.translate(sx, sy + bob - zOff);
// TO:
//   ctx.translate(sx + Math.cos(u.angle) * windupOff, sy + bob - zOff + Math.sin(u.angle) * windupOff);
//   if (deployScale < 1) { ctx.scale(deployScale, deployScale); }

// Here is the complete patched renderUnits3D function for clarity:

function renderUnits3D_UPGRADED() {
  // Depth sort: render far units first (lower Y = farther)
  const sorted = [...units].filter(u => u.alive || u.deathTimer < 0.5).sort((a, b) => a.y - b.y);
  for (const u of sorted) {
    if (u.stealthTimer > 0 && u.owner === 1) continue;

    const [sx, sy, df] = toScr3D(u.x, u.y); const card = u.card;
    // Depth-scaled body dimensions
    const bW = (card.bodyW || 0.9) * scale * df;
    const bH = (card.bodyH || 0.55) * scale * df;
    const bodyH3D = bH * 0.5; // 3D height of car body
    // Trigonometry: bobbing using sin wave
    const bob = Math.sin(u.bobOffset) * scale * 0.04 * df;
    // Jump height for abilities
    const zOff = u.zHeight * scale * df;

    // STATE MACHINE: deploy scale-up
    const deployScale = (u.state === USTATE.DEPLOY) ? u.deployScale : 1;
    // STATE MACHINE: windup pullback offset (in facing direction)
    const windupOff = (u.windupOffset || 0) * scale * df;

    // ---- ENHANCED VFX: Status auras (drawn UNDER the unit) ----
    if (u.alive) {
      renderStatusAuras(u, sx, sy, bW, bH, df);
    }

    // Death animation: upgraded 3-phase sequence
    if (!u.alive && u.deathTimer >= 0) {
      renderDeathVFX(u, sx, sy, bW, bH, bodyH3D, df);
      continue;
    }

    // Stealth: semi-transparent
    if (u.stealthTimer > 0) ctx.globalAlpha = 0.3;

    // Ground shadow (Geometry: ellipse scaled by depth)
    ctx.globalAlpha = u.stealthTimer > 0 ? 0.1 : 0.35;
    ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.ellipse(sx + bW * 0.08, sy + bH * 0.1, bW * 0.5 * deployScale, bH * 0.2 * deployScale, 0, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = u.stealthTimer > 0 ? 0.3 : 1;

    ctx.save();
    ctx.translate(sx + Math.cos(u.angle) * windupOff, sy + bob - zOff + Math.sin(u.angle) * windupOff);

    // Deploy scale-up animation
    if (deployScale < 1) {
      ctx.scale(deployScale, deployScale);
    }

    // Rotate car body (Trigonometry: angle-based rotation)
    const drawAngle = u.angle + Math.PI / 2;
    ctx.rotate(drawAngle);

    // Hit flash effect
    const flashAmt = u.hitFlash > 0 ? 0.4 : 0;
    const baseColor = flashAmt > 0 ? lerpColor(card.carColor || '#888', '#fff', flashAmt) : (card.carColor || '#888');

    // HIT state: additional white overlay
    const hitFlashMult = (u.state === USTATE.HIT) ? 0.6 : 0;
    const renderColor = hitFlashMult > 0 ? lerpColor(baseColor, '#ffffff', hitFlashMult) : baseColor;

    // 3D Car body: main face
    ctx.fillStyle = renderColor;
    rr(-bW / 2, -bH / 2, bW, bH, bH * 0.25); ctx.fill();

    // 3D top face (lighter -- creates volume illusion)
    const topShade = lightenColor(renderColor, 0.3);
    ctx.fillStyle = topShade;
    ctx.beginPath();
    ctx.moveTo(-bW / 2, -bH / 2);
    ctx.lineTo(-bW / 2 + bW * 0.1, -bH / 2 - bodyH3D);
    ctx.lineTo(bW / 2 - bW * 0.1, -bH / 2 - bodyH3D);
    ctx.lineTo(bW / 2, -bH / 2);
    ctx.closePath(); ctx.fill();

    // Side face (darker)
    ctx.fillStyle = darkenColor(renderColor, 0.5);
    ctx.beginPath();
    ctx.moveTo(bW / 2, -bH / 2);
    ctx.lineTo(bW / 2 - bW * 0.1, -bH / 2 - bodyH3D);
    ctx.lineTo(bW / 2 - bW * 0.1, bH / 2 - bodyH3D * 0.3);
    ctx.lineTo(bW / 2, bH / 2);
    ctx.closePath(); ctx.fill();

    // Windshield (reflective)
    ctx.fillStyle = 'rgba(150,220,255,0.45)';
    ctx.fillRect(-bW * 0.25, -bH / 2 - bodyH3D * 0.8, bW * 0.5, bodyH3D * 0.6);

    // Owner border glow
    ctx.strokeStyle = u.owner === 0 ? '#4488FF' : '#FF4444';
    ctx.lineWidth = u.nitroActive ? 2.5 * df : 1.5 * df;
    if (u.nitroActive) { ctx.shadowColor = '#00BFFF'; ctx.shadowBlur = 8 * df; }
    if (u.stunTimer > 0) { ctx.strokeStyle = '#FFFF00'; ctx.lineWidth = 3 * df; }
    if (u.slowTimer > 0) { ctx.strokeStyle = '#666'; ctx.lineWidth = 2 * df; }
    rr(-bW / 2, -bH / 2, bW, bH, bH * 0.25); ctx.stroke();
    ctx.shadowBlur = 0;

    // Wheels (3D ellipses)
    ctx.fillStyle = '#111';
    const wheelW = bW * 0.18, wheelH = bH * 0.15;
    ctx.beginPath(); ctx.ellipse(-bW * 0.38, -bH * 0.35, wheelW, wheelH, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(bW * 0.38, -bH * 0.35, wheelW, wheelH, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(-bW * 0.38, bH * 0.35, wheelW, wheelH, 0, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.ellipse(bW * 0.38, bH * 0.35, wheelW, wheelH, 0, 0, Math.PI * 2); ctx.fill();

    // Speed trail (Trigonometry: sin-wave exhaust)
    if (u.getSpeed() > 0.5 && u.alive) {
      ctx.globalAlpha = 0.3; ctx.fillStyle = u.nitroActive ? '#00BFFF' : '#888';
      for (let ti = 1; ti <= 3; ti++) {
        const trailAlpha = 0.3 - ti * 0.08;
        ctx.globalAlpha = Math.max(0, trailAlpha);
        const ty2 = bH / 2 + ti * bH * 0.3;
        const tw = bW * 0.15 * (1 - ti * 0.2);
        const wobble = Math.sin(animT * 15 + ti * 2) * tw * 0.3;
        ctx.beginPath(); ctx.arc(wobble, ty2, tw, 0, Math.PI * 2); ctx.fill();
      }
    }

    ctx.restore();
    ctx.globalAlpha = 1;

    // HP bar above unit (3D positioned)
    if (u.alive) {
      const barW = bW * 0.9, barH = 3 * df, barX = sx - barW / 2, barY = sy + bob - zOff - bH / 2 - bodyH3D - 6 * df;
      ctx.fillStyle = '#1a1a1a'; ctx.fillRect(barX, barY, barW, barH);
      const hpPct = u.hp / u.maxHp; ctx.fillStyle = u.owner === 0 ? '#4488FF' : '#FF4444';
      ctx.fillRect(barX, barY, barW * hpPct, barH);
    }
    // Stun indicator
    if (u.stunTimer > 0 && u.alive) {
      ctx.fillStyle = '#FFFF00'; ctx.font = (scale * 0.3 * df) + 'px Arial';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText('\u{1F4AB}', sx, sy - bH - bodyH3D);
    }
  }
}


// ============================================================
// SYSTEM 2: ENHANCED VFX SYSTEM
// ============================================================


// ─────────────────────────────────────────────────────────────
// 2A: IMPACT PUFFS -- melee hit dust cloud
// ─────────────────────────────────────────────────────────────

function addImpactPuff(gx, gy, color) {
  // Expanding white ring
  particles.push({
    x: gx, y: gy, z: 0.1,
    vx: 0, vy: 0, vz: 0,
    color: '#ffffff',
    t: 0, dur: 0.25,
    type: 'impact_ring',
    sz: 0.05
  });

  // 3-4 small debris particles
  const count = 3 + Math.floor(Math.random() * 2);
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const spd = 0.8 + Math.random() * 1.5;
    particles.push({
      x: gx, y: gy, z: 0.05 + Math.random() * 0.1,
      vx: Math.cos(angle) * spd,
      vy: Math.sin(angle) * spd,
      vz: 1 + Math.random() * 2,
      color: color || '#aaa',
      t: 0, dur: 0.3 + Math.random() * 0.15,
      type: 'debris',
      sz: 0.03 + Math.random() * 0.03
    });
  }

  // Dust cloud (small smoke)
  for (let i = 0; i < 2; i++) {
    particles.push({
      x: gx + (Math.random() - 0.5) * 0.3,
      y: gy + (Math.random() - 0.5) * 0.2,
      z: 0.15,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.3,
      vz: 0.5 + Math.random(),
      color: '#ccc',
      t: 0, dur: 0.35,
      type: 'smoke',
      sz: 0.06
    });
  }
}


// ─────────────────────────────────────────────────────────────
// 2B: STATUS AURAS -- colored rings/effects around units
//   Called from renderUnits3D_UPGRADED, drawn UNDER unit body
// ─────────────────────────────────────────────────────────────

function renderStatusAuras(u, sx, sy, bW, bH, df) {
  const t = animT; // global animation time

  // --- STUN: yellow lightning bolts orbiting the unit ---
  if (u.stunTimer > 0) {
    ctx.save();
    const numBolts = 3;
    for (let i = 0; i < numBolts; i++) {
      const orbitAngle = t * 6 + (i * Math.PI * 2 / numBolts);
      const orbR = bW * 0.55;
      const bx = sx + Math.cos(orbitAngle) * orbR;
      const by = sy + Math.sin(orbitAngle) * orbR * 0.5; // flattened orbit for 3D

      ctx.strokeStyle = '#FFFF00';
      ctx.lineWidth = 1.5 * df;
      ctx.globalAlpha = 0.8;
      ctx.shadowColor = '#FFFF00';
      ctx.shadowBlur = 6 * df;

      // Draw tiny lightning bolt (3 segments)
      ctx.beginPath();
      const boltSz = bW * 0.12;
      ctx.moveTo(bx, by - boltSz);
      ctx.lineTo(bx + boltSz * 0.3, by - boltSz * 0.2);
      ctx.lineTo(bx - boltSz * 0.2, by + boltSz * 0.1);
      ctx.lineTo(bx + boltSz * 0.1, by + boltSz);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  // --- SLOW: blue ice crystals below unit ---
  if (u.slowTimer > 0) {
    ctx.save();
    const numCrystals = 4;
    ctx.globalAlpha = 0.6;
    for (let i = 0; i < numCrystals; i++) {
      const cAngle = (i * Math.PI * 2 / numCrystals) + t * 0.5;
      const cR = bW * 0.45;
      const cx2 = sx + Math.cos(cAngle) * cR;
      const cy2 = sy + bH * 0.15 + Math.sin(cAngle) * cR * 0.3;
      const cSz = bW * 0.06;

      // Diamond shape for ice crystal
      ctx.fillStyle = '#88CCFF';
      ctx.shadowColor = '#4488FF';
      ctx.shadowBlur = 4 * df;
      ctx.beginPath();
      ctx.moveTo(cx2, cy2 - cSz * 1.5);
      ctx.lineTo(cx2 + cSz, cy2);
      ctx.lineTo(cx2, cy2 + cSz * 0.8);
      ctx.lineTo(cx2 - cSz, cy2);
      ctx.closePath();
      ctx.fill();
    }
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  // --- NITRO: cyan speed lines trailing behind ---
  if (u.nitroActive) {
    ctx.save();
    ctx.globalAlpha = 0.4;
    const trailAngle = u.angle + Math.PI; // behind the unit
    for (let i = 0; i < 3; i++) {
      const offset = (i - 1) * bW * 0.2;
      const tx = sx + Math.cos(trailAngle) * bW * (0.4 + i * 0.15) + Math.cos(trailAngle + Math.PI / 2) * offset;
      const ty = sy + Math.sin(trailAngle) * bW * (0.4 + i * 0.15) + Math.sin(trailAngle + Math.PI / 2) * offset;
      const len = bW * (0.25 + Math.random() * 0.15);

      ctx.strokeStyle = '#00DDFF';
      ctx.lineWidth = (2 - i * 0.4) * df;
      ctx.shadowColor = '#00BFFF';
      ctx.shadowBlur = 4 * df;
      ctx.beginPath();
      ctx.moveTo(tx, ty);
      ctx.lineTo(tx + Math.cos(trailAngle) * len, ty + Math.sin(trailAngle) * len);
      ctx.stroke();
    }
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  // --- STEALTH: ghostly transparent shimmer ---
  if (u.stealthTimer > 0 && u.owner === 0) { // only show for player units
    ctx.save();
    const shimmer = Math.sin(t * 8) * 0.15 + 0.15;
    ctx.globalAlpha = shimmer;
    ctx.strokeStyle = '#AADDFF';
    ctx.lineWidth = 1 * df;
    ctx.setLineDash([3 * df, 5 * df]);
    ctx.beginPath();
    ctx.ellipse(sx, sy, bW * 0.55, bH * 0.35, 0, 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
    ctx.restore();
  }

  // --- LOW HP (<25%): red pulsing danger glow ---
  if (u.hp / u.maxHp < 0.25 && u.hp > 0) {
    ctx.save();
    const pulse = (Math.sin(t * 10) + 1) / 2; // 0-1 pulsing
    ctx.globalAlpha = 0.15 + pulse * 0.2;
    ctx.fillStyle = '#FF0000';
    ctx.shadowColor = '#FF0000';
    ctx.shadowBlur = 12 * df;
    ctx.beginPath();
    ctx.ellipse(sx, sy, bW * 0.6, bH * 0.4, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    ctx.restore();
  }
}


// ─────────────────────────────────────────────────────────────
// 2C: CRIT/BIG DAMAGE POP + COMBO TEXT
// ─────────────────────────────────────────────────────────────

function addBigDamagePop(gx, gy, amount) {
  // Enlarged red bouncing number with exclamation mark
  effects.push({
    type: 'bigdmg',
    x: gx, y: gy,
    text: '-' + amount + '!',
    color: '#FF2222',
    dur: 1.0,
    t: 0,
    alive: true
  });
}

function addComboText(gx, gy, multiplier) {
  // Gold "COMBO!" text when multiplier > 1.5x
  effects.push({
    type: 'combopop',
    x: gx, y: gy,
    text: multiplier.toFixed(1) + 'x COMBO!',
    color: '#FFD700',
    dur: 1.2,
    t: 0,
    alive: true
  });
}

// MARKER [E]: Patch renderEffects() to handle new effect types.
// Add these cases inside the renderEffects for-loop, after the
// existing 'tshot' case (before the closing } of the loop):

function renderEnhancedEffects_CASES(e, sx, sy, df, p) {
  // This function shows the logic to ADD to renderEffects().
  // Call this for e.type === 'bigdmg' or 'combopop'.

  if (e.type === 'bigdmg') {
    // Bouncing enlarged red damage number
    const bounce = Math.abs(Math.sin(p * Math.PI * 3)) * (1 - p) * 0.5;
    const fontScale = 1.0 + (1 - p) * 0.5; // starts big, shrinks
    ctx.globalAlpha = 1 - p * p;
    ctx.fillStyle = e.color;
    ctx.shadowColor = '#FF0000';
    ctx.shadowBlur = 8 * df;
    ctx.font = 'bold ' + (scale * 0.75 * df * fontScale) + 'px Arial';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(e.text, sx, sy - p * scale * 2 * df - bounce * scale * df);
    // White outline for readability
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 1.5 * df;
    ctx.strokeText(e.text, sx, sy - p * scale * 2 * df - bounce * scale * df);
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
  }

  if (e.type === 'combopop') {
    // Gold combo text with scale pulse
    const pulse = 1 + Math.sin(p * Math.PI * 2) * 0.15;
    ctx.globalAlpha = (1 - p) * 0.9;
    ctx.save();
    ctx.translate(sx, sy - p * scale * 2.5 * df);
    ctx.scale(pulse, pulse);
    ctx.fillStyle = '#FFD700';
    ctx.shadowColor = '#FF8800';
    ctx.shadowBlur = 10 * df;
    ctx.font = 'bold ' + (scale * 0.6 * df) + 'px Arial';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(e.text, 0, 0);
    ctx.strokeStyle = '#AA6600';
    ctx.lineWidth = 1 * df;
    ctx.strokeText(e.text, 0, 0);
    ctx.restore();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
  }
}


// ─────────────────────────────────────────────────────────────
// 2D: DEATH VFX UPGRADE -- 3-phase death sequence
// ─────────────────────────────────────────────────────────────

function addDeployRingVFX(gx, gy, color) {
  // Deploy ring: expanding colored circle at spawn point
  particles.push({
    x: gx, y: gy, z: 0,
    vx: 0, vy: 0, vz: 0,
    color: color,
    t: 0, dur: 0.4,
    type: 'deploy_ring',
    sz: 0.1
  });
}

function addDeathShockwave(gx, gy, color) {
  // White flash particle
  particles.push({
    x: gx, y: gy, z: 0.1,
    vx: 0, vy: 0, vz: 0,
    color: '#ffffff',
    t: 0, dur: 0.3,
    type: 'death_flash',
    sz: 0.3
  });
  // Expanding shockwave ring
  particles.push({
    x: gx, y: gy, z: 0,
    vx: 0, vy: 0, vz: 0,
    color: color,
    t: 0, dur: 0.35,
    type: 'death_shockwave',
    sz: 0.15
  });
  // Screen flash
  triggerFlash('#ffffff', 0.15, 0.08);
}

function addDeathDebris(gx, gy, color) {
  // Debris scatter: 8-12 pieces flying out
  const count = 8 + Math.floor(Math.random() * 5);
  for (let i = 0; i < count; i++) {
    const angle = Math.random() * Math.PI * 2;
    const spd = 2 + Math.random() * 4;
    particles.push({
      x: gx, y: gy, z: 0.3 + Math.random() * 0.4,
      vx: Math.cos(angle) * spd,
      vy: Math.sin(angle) * spd,
      vz: 3 + Math.random() * 5,
      color: color,
      t: 0, dur: 0.6 + Math.random() * 0.4,
      type: 'death_debris',
      sz: 0.04 + Math.random() * 0.06
    });
  }
  // Smoke plume: 4-6 rising smoke puffs
  for (let i = 0; i < 5; i++) {
    particles.push({
      x: gx + (Math.random() - 0.5) * 0.6,
      y: gy + (Math.random() - 0.5) * 0.3,
      z: 0.5 + Math.random() * 0.5,
      vx: (Math.random() - 0.5) * 0.4,
      vy: -0.2 - Math.random() * 0.3,
      vz: 2 + Math.random() * 2,
      color: '#444',
      t: 0, dur: 0.8 + Math.random() * 0.5,
      type: 'smoke',
      sz: 0.1 + Math.random() * 0.08
    });
  }
}

// Death VFX render (called from renderUnits3D_UPGRADED instead
// of the old simple shrink+ring)
function renderDeathVFX(u, sx, sy, bW, bH, bodyH3D, df) {
  const t = u.deathTimer;

  // Phase 0 (0-0.1s): time freeze -- show unit frozen, slight white overlay
  if (t < 0.1) {
    const freezeProg = t / 0.1;
    ctx.globalAlpha = 1;
    // Draw a white overlay that intensifies
    ctx.fillStyle = 'rgba(255,255,255,' + (freezeProg * 0.4) + ')';
    ctx.beginPath();
    ctx.ellipse(sx, sy, bW * 0.5, bH * 0.35, 0, 0, Math.PI * 2);
    ctx.fill();
    // Draw the unit body shrinking slightly
    ctx.globalAlpha = 1 - freezeProg * 0.1;
    ctx.fillStyle = u.card.carColor || '#888';
    const shrink = 1 - freezeProg * 0.05;
    ctx.save();
    ctx.translate(sx, sy);
    ctx.scale(shrink, shrink);
    rr(-bW / 2, -bH / 2, bW, bH, bH * 0.25); ctx.fill();
    ctx.restore();
  }
  // Phase 1 (0.1-0.3s): white flash + expanding shockwave ring
  else if (t < 0.3) {
    const phase1Prog = (t - 0.1) / 0.2;
    // White flash fading out
    ctx.globalAlpha = (1 - phase1Prog) * 0.6;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(sx, sy, bW * (0.4 + phase1Prog * 0.8), 0, Math.PI * 2);
    ctx.fill();
    // Expanding ring
    ctx.globalAlpha = (1 - phase1Prog) * 0.8;
    ctx.strokeStyle = u.card.carColor || '#FF4400';
    ctx.lineWidth = (3 - phase1Prog * 2) * df;
    ctx.beginPath();
    ctx.arc(sx, sy, bW * phase1Prog * 2.5, 0, Math.PI * 2);
    ctx.stroke();
  }
  // Phase 2 (0.3-0.5s): debris scatter + smoke (handled by particles)
  else {
    const phase2Prog = (t - 0.3) / 0.2;
    // Faint ghost of the unit shape dissolving
    ctx.globalAlpha = Math.max(0, 0.2 - phase2Prog * 0.2);
    ctx.strokeStyle = u.card.carColor || '#FF4400';
    ctx.lineWidth = 1 * df;
    ctx.setLineDash([2 * df, 4 * df]);
    ctx.beginPath();
    ctx.arc(sx, sy, bW * (1 + phase2Prog), 0, Math.PI * 2);
    ctx.stroke();
    ctx.setLineDash([]);
  }
  ctx.globalAlpha = 1;
}


// ─────────────────────────────────────────────────────────────
// MARKER [F]: Patch renderParticles() to handle new particle types
//   Add these cases to the renderParticles() forEach loop,
//   after the existing 'neon' case.
// ─────────────────────────────────────────────────────────────

function renderEnhancedParticles_CASES(p, sx, sy, df, prog, sz, zOff) {
  // This function shows the logic to ADD to renderParticles().
  // Call for new particle types.

  if (p.type === 'impact_ring') {
    // Expanding white semi-transparent ring
    const ringR = sz + prog * scale * 0.4 * df;
    ctx.globalAlpha = (1 - prog) * 0.5;
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = (2 - prog * 1.5) * df;
    ctx.beginPath();
    ctx.arc(sx, sy - zOff, ringR, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  if (p.type === 'debris') {
    // Small colored squares tumbling
    ctx.globalAlpha = (1 - prog) * 0.8;
    ctx.fillStyle = p.color;
    ctx.save();
    ctx.translate(sx, sy - zOff);
    ctx.rotate(prog * Math.PI * 4); // tumble
    const half = Math.max(1, sz * (1 - prog * 0.5));
    ctx.fillRect(-half, -half, half * 2, half * 2);
    ctx.restore();
    ctx.globalAlpha = 1;
  }

  if (p.type === 'deploy_ring') {
    // Colored expanding ring with inner glow
    const ringR = prog * scale * 1.2 * df;
    ctx.globalAlpha = (1 - prog) * 0.6;
    ctx.strokeStyle = p.color;
    ctx.lineWidth = (3 - prog * 2.5) * df;
    ctx.shadowColor = p.color;
    ctx.shadowBlur = 6 * df;
    ctx.beginPath();
    ctx.arc(sx, sy - zOff, ringR, 0, Math.PI * 2);
    ctx.stroke();
    // Inner filled glow
    ctx.globalAlpha = (1 - prog) * 0.15;
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(sx, sy - zOff, ringR, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
  }

  if (p.type === 'death_flash') {
    // Bright white expanding flash
    const flashR = sz * df * scale * (0.5 + prog * 2);
    ctx.globalAlpha = (1 - prog * prog) * 0.7;
    ctx.fillStyle = '#ffffff';
    ctx.shadowColor = '#ffffff';
    ctx.shadowBlur = 15 * df;
    ctx.beginPath();
    ctx.arc(sx, sy - zOff, flashR, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
  }

  if (p.type === 'death_shockwave') {
    // Colored expanding ring with thick stroke
    const ringR = prog * scale * 2 * df;
    ctx.globalAlpha = (1 - prog) * 0.6;
    ctx.strokeStyle = p.color;
    ctx.lineWidth = (4 - prog * 3) * df;
    ctx.beginPath();
    ctx.arc(sx, sy - zOff, ringR, 0, Math.PI * 2);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  if (p.type === 'death_debris') {
    // Similar to spark but with tumbling rotation
    ctx.globalAlpha = (1 - prog) * 0.85;
    ctx.fillStyle = p.color;
    ctx.save();
    ctx.translate(sx, sy - zOff);
    ctx.rotate(prog * Math.PI * 6);
    const half = Math.max(1, sz * (1 - prog * 0.3));
    ctx.fillRect(-half, -half, half * 2, half * 2);
    ctx.restore();
    // Hot center glow
    if (prog < 0.3) {
      ctx.globalAlpha = (0.3 - prog) * 2;
      ctx.fillStyle = '#FFD700';
      ctx.beginPath();
      ctx.arc(sx, sy - zOff, Math.max(1, sz * 0.6), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }
}


// ============================================================
// INTEGRATION INSTRUCTIONS
// ============================================================
//
// To wire everything into game_v6.html, apply these edits:
//
// 1. UNIT CONSTRUCTOR (line 435):
//    Replace entire `class Unit { ... }` block (lines 435-470)
//    with the new class above (includes USTATE enum before it).
//
// 2. updateUnits (line 834):
//    Replace entire `function updateUnits(dt){ ... }` (lines 834-874)
//    with the new updateUnits() and all the state handler functions.
//    Keep findTarget() and moveToward() unchanged.
//
// 3. renderUnits3D (line 1560):
//    Replace entire `function renderUnits3D(){ ... }` (lines 1560-1679)
//    with renderUnits3D_UPGRADED() -- rename it to renderUnits3D.
//
// 4. renderParticles (line 517):
//    Inside the particles.forEach loop, after the 'neon' else-if
//    block (line 535), add:
//
//      else { renderEnhancedParticles_CASES(p, sx, sy, df, prog, sz, zOff); }
//
//    This catches all new particle types through the helper.
//
// 5. renderEffects (line 1707):
//    Inside the for-loop, after the 'tshot' else-if (line 1734),
//    add:
//
//      else { const[sx2,sy2,df2]=toScr3D(e.x,e.y); renderEnhancedEffects_CASES(e, sx2, sy2, df2, p); }
//
//    (Note: sx, sy, df, p are already computed at line 1709.)
//    Simplified: just add after line 1734:
//
//      else { renderEnhancedEffects_CASES(e, sx, sy, df, p); }
//
// 6. unitAttack COMBO TEXT (line 920):
//    After `const comboMult=getComboMultiplier();` add:
//
//      if(comboMult > 1.5 && u.target){
//        addComboText(u.target.x, u.target.y - 0.5, comboMult);
//      }
//
// 7. takeDamage CALLSITES:
//    The new takeDamage(d, sourceX, sourceY) has optional source
//    coordinates. Existing calls with just takeDamage(d) still
//    work because sourceX/sourceY default to undefined, and the
//    HIT state falls back to u.angle + PI for knockback direction.
//    For better VFX, update melee attacks in unitAttack() to pass
//    the attacker position:
//
//      u.target.takeDamage(d, u.x, u.y);  // instead of u.target.takeDamage(d)
//
// 8. PARTICLE CAP: The existing cap of 200 at line 514 may need
//    bumping to 300 since we add more VFX particles:
//
//      if(particles.length>300)particles=particles.slice(-300);
//
// ============================================================
