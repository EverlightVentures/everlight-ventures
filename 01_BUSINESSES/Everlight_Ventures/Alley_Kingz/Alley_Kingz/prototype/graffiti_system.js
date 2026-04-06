// ============================================================
// ALLEY KINGZ -- GRAFFITI / STREET ART SYSTEM
// Procedural canvas-drawn graffiti for arena side walls
// No images -- pure ctx fillText, paths, and drip effects
// ============================================================
// Integration: call renderGraffiti(ctx, arena, side, wallX, wallY, wallW, wallH, df)
//   inside renderBuildingSilhouettes3D(), once per building face.
//   - side: 'left' or 'right'
//   - wallX/wallY/wallW/wallH: pixel rect of the building face
//   - df: depth factor from getDepthFactor()
//
// Or call renderAllGraffiti(ctx, arena) as a standalone pass after
// renderBuildingSilhouettes3D() for a quick drop-in.
// ============================================================

const GRAFFITI_DB = {

  // -------------------------------------------------------
  // 1. COMPTON  (Lvl 1-10)  -- hood, orange/red neons
  // -------------------------------------------------------
  hood: {
    tags: [
      { text: 'CPT',     style: 'bubble',   size: 1.0  },
      { text: 'NO LACKIN', style: 'drip',   size: 0.55 },
      { text: 'BLOCK HOT', style: 'stencil', size: 0.6  },
    ],
    icon: 'crown',          // 5-point crown -- universal street royalty
    palette: {
      fill:   '#FF6600',    // n1
      stroke: '#FF9900',    // n2
      accent: '#FF4500',    // acc
      shadow: '#1a0010',    // sky2 used as shadow
    },
    dripChance: 0.7,        // 70% of tags get paint drips
    notes: 'Bubble letters with thick black outline, heavy drip. Raw and aggressive.',
  },

  // -------------------------------------------------------
  // 2. DETROIT  (Lvl 11-20) -- industrial, rust orange
  // -------------------------------------------------------
  industrial: {
    tags: [
      { text: 'MOTOR CITY', style: 'stencil', size: 0.65 },
      { text: 'RUST BELT',  style: 'block',   size: 0.7  },
      { text: 'D-TOWN',     style: 'drip',    size: 0.8  },
    ],
    icon: 'gear',           // industrial cog/gear
    palette: {
      fill:   '#FF6600',
      stroke: '#DD4400',
      accent: '#CC3300',
      shadow: '#181410',
    },
    dripChance: 0.4,
    notes: 'Stencil military font, drip looks like rust streaks. Factory grit.',
  },

  // -------------------------------------------------------
  // 3. CHICAGO  (Lvl 21-30) -- elevated trains, blue neons
  // -------------------------------------------------------
  elevated: {
    tags: [
      { text: 'CHI-TOWN',  style: 'wildstyle', size: 0.7  },
      { text: 'DRILL SZN', style: 'drip',      size: 0.55 },
      { text: 'SOUTH SIDE', style: 'stencil',  size: 0.5  },
    ],
    icon: 'star',           // 6-point star
    palette: {
      fill:   '#0066FF',
      stroke: '#0044CC',
      accent: '#0088FF',
      shadow: '#000820',
    },
    dripChance: 0.5,
    notes: 'Sharp wildstyle arrows, blue neon glow. L-train graffiti look.',
  },

  // -------------------------------------------------------
  // 4. BROOKLYN  (Lvl 31-40) -- rooftop, purple neons
  // -------------------------------------------------------
  rooftop: {
    tags: [
      { text: 'BK',        style: 'bubble',    size: 1.1  },
      { text: 'ALL DAY',   style: 'wildstyle', size: 0.6  },
      { text: 'BRIDGE CITY', style: 'stencil', size: 0.45 },
    ],
    icon: 'bridge',         // Brooklyn Bridge silhouette (simplified)
    palette: {
      fill:   '#AA00FF',
      stroke: '#8800CC',
      accent: '#CC44FF',
      shadow: '#120018',
    },
    dripChance: 0.55,
    notes: 'Fat bubble letters with purple glow halo. Rooftop handstyle.',
  },

  // -------------------------------------------------------
  // 5. ATLANTA  (Lvl 41-50) -- trap music, red neons
  // -------------------------------------------------------
  trap: {
    tags: [
      { text: 'ATL',       style: 'drip',     size: 0.9  },
      { text: 'TRAP OR DIE', style: 'block',  size: 0.5  },
      { text: 'DIRTY SOUTH', style: 'stencil', size: 0.45 },
    ],
    icon: 'diamond',        // diamond chain -- trap flex
    palette: {
      fill:   '#FF0033',
      stroke: '#CC0022',
      accent: '#FF2244',
      shadow: '#1a0005',
    },
    dripChance: 0.8,
    notes: 'Bloody drip effect, blood-red. Stenciled trap house aesthetic.',
  },

  // -------------------------------------------------------
  // 6. OAKLAND  (Lvl 51-60) -- harbor/bay, teal neons
  // -------------------------------------------------------
  harbor: {
    tags: [
      { text: 'THE TOWN',  style: 'bubble',   size: 0.8  },
      { text: 'BAY AREA',  style: 'stencil',  size: 0.6  },
      { text: 'HYPHY',     style: 'wildstyle', size: 0.7  },
    ],
    icon: 'anchor',         // harbor anchor
    palette: {
      fill:   '#00BBAA',
      stroke: '#009988',
      accent: '#00DDCC',
      shadow: '#001018',
    },
    dripChance: 0.45,
    notes: 'Ocean teal with bubble style. Wet look, harbor fog wash.',
  },

  // -------------------------------------------------------
  // 7. MIAMI  (Lvl 61-70) -- vice/neon, pink neons
  // -------------------------------------------------------
  neon: {
    tags: [
      { text: '305',       style: 'bubble',    size: 1.0  },
      { text: 'VICE CITY', style: 'neonOutline', size: 0.6 },
      { text: 'DALE',      style: 'drip',      size: 0.7  },
    ],
    icon: 'palm',           // palm tree silhouette
    palette: {
      fill:   '#FF44AA',
      stroke: '#FF0088',
      accent: '#FF66CC',
      shadow: '#100020',
    },
    dripChance: 0.3,
    notes: 'Neon outline glow letters, pink-on-black. Vice aesthetic, clean lines.',
  },

  // -------------------------------------------------------
  // 8. LAS VEGAS  (Lvl 71-80) -- casino/gold
  // -------------------------------------------------------
  casino: {
    tags: [
      { text: 'SIN CITY',  style: 'block',    size: 0.75 },
      { text: 'ALL IN',    style: 'neonOutline', size: 0.6 },
      { text: 'JACKPOT',   style: 'bubble',   size: 0.65 },
    ],
    icon: 'spade',          // playing card spade
    palette: {
      fill:   '#FFD700',
      stroke: '#FFAA00',
      accent: '#FFD700',
      shadow: '#100a00',
    },
    dripChance: 0.2,
    notes: 'Gold leaf block letters with casino sparkle. Marquee feel.',
  },

  // -------------------------------------------------------
  // 9. NEO TOKYO  (Lvl 81-90) -- cyberpunk, cyan/magenta
  // -------------------------------------------------------
  cyber: {
    tags: [
      { text: 'NEO',       style: 'neonOutline', size: 0.9  },
      { text: 'GHOST NET', style: 'wildstyle',  size: 0.55 },
      { text: 'HACK',      style: 'glitch',     size: 0.7  },
    ],
    icon: 'circuit',        // circuit board node pattern
    palette: {
      fill:   '#00FFFF',
      stroke: '#FF00FF',
      accent: '#00FFFF',
      shadow: '#000018',
    },
    dripChance: 0.15,
    notes: 'Glitch shift effect (offset duplication). Neon cyan + magenta split.',
  },

  // -------------------------------------------------------
  // 10. KINGZ COURT  (Lvl 91-100) -- throne/royalty
  // -------------------------------------------------------
  throne: {
    tags: [
      { text: 'KINGZ',     style: 'wildstyle', size: 1.0  },
      { text: 'LONG LIVE', style: 'block',     size: 0.55 },
      { text: 'CROWN ME',  style: 'drip',      size: 0.65 },
    ],
    icon: 'royalCrown',     // elaborate crown with jewels
    palette: {
      fill:   '#FFD700',
      stroke: '#CC44FF',
      accent: '#FFD700',
      shadow: '#150e00',
    },
    dripChance: 0.5,
    notes: 'Gold + purple wildstyle with jewel sparkles. Final boss energy.',
  },
};


// ============================================================
// GRAFFITI TEXT STYLE RENDERERS
// Each takes: (ctx, text, x, y, size, pal, df)
//   - x,y = pixel center of the tag
//   - size = base font size in px (pre-scaled by df)
//   - pal = palette object {fill, stroke, accent, shadow}
//   - df = depth factor for glow/blur scaling
// ============================================================

const GRAFFITI_STYLES = {

  // --- BUBBLE LETTERS ---
  // Fat rounded letters, thick black outline, solid fill
  bubble(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = 'bold ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Black outline (drawn multiple offsets)
    ctx.fillStyle = '#000';
    const offsets = [-2,-1,0,1,2];
    for (const ox of offsets) {
      for (const oy of offsets) {
        if (ox === 0 && oy === 0) continue;
        ctx.fillText(text, x + ox * df, y + oy * df);
      }
    }
    // Main fill
    ctx.fillStyle = pal.fill;
    ctx.fillText(text, x, y);
    // Inner highlight (shifted up-left for 3D pop)
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = '#FFF';
    ctx.fillText(text, x - df, y - df);
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- DRIP STYLE ---
  // Letters with paint dripping down from the bottom
  drip(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = 'bold italic ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Shadow
    ctx.fillStyle = pal.shadow;
    ctx.fillText(text, x + 2 * df, y + 2 * df);
    // Main text
    ctx.fillStyle = pal.fill;
    ctx.fillText(text, x, y);
    // Drip lines from bottom of text
    const metrics = ctx.measureText(text);
    const tw = metrics.width;
    const dripStartX = x - tw / 2;
    const dripTop = y + fs * 0.35;
    const dripCount = Math.max(2, Math.floor(tw / (8 * df)));
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 2 * df);
    ctx.lineCap = 'round';
    // Seeded drip pattern based on text hash
    let hash = 0;
    for (let i = 0; i < text.length; i++) hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
    for (let d = 0; d < dripCount; d++) {
      const seed = Math.abs((hash * (d + 1) * 7) % 100) / 100;
      const dx = dripStartX + seed * tw;
      const dLen = (10 + seed * 25) * df;
      ctx.globalAlpha = 0.6 + seed * 0.4;
      ctx.beginPath();
      ctx.moveTo(dx, dripTop);
      ctx.lineTo(dx + (seed - 0.5) * 3 * df, dripTop + dLen);
      ctx.stroke();
      // Drip bead at bottom
      ctx.fillStyle = pal.fill;
      ctx.beginPath();
      ctx.arc(dx + (seed - 0.5) * 3 * df, dripTop + dLen, 1.5 * df, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- STENCIL ---
  // Clean cut-out look, uppercase, slight spray overshoot
  stencil(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(7, Math.floor(size));
    ctx.save();
    ctx.font = '900 ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.letterSpacing = (3 * df) + 'px';
    // Spray haze behind
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = pal.fill;
    const metrics = ctx.measureText(text);
    const tw = metrics.width;
    ctx.fillRect(x - tw / 2 - 6 * df, y - fs / 2 - 4 * df, tw + 12 * df, fs + 8 * df);
    ctx.globalAlpha = 1;
    // Stencil text
    ctx.fillStyle = pal.accent;
    ctx.fillText(text, x, y);
    // Faded edges (spray overshoot dots)
    ctx.globalAlpha = 0.2;
    let hash = 0;
    for (let i = 0; i < text.length; i++) hash = ((hash << 5) - hash + text.charCodeAt(i)) | 0;
    for (let s = 0; s < 8; s++) {
      const seed = Math.abs((hash * (s + 1) * 13) % 100) / 100;
      const sx2 = x - tw / 2 + seed * tw;
      const sy2 = y + (seed - 0.5) * fs * 1.3;
      ctx.fillStyle = pal.fill;
      ctx.beginPath();
      ctx.arc(sx2, sy2, 1 * df, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- BLOCK LETTERS ---
  // Thick geometric uppercase, solid with drop shadow
  block(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = '900 ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // 3D offset shadow (stack)
    const depth = Math.max(1, Math.floor(3 * df));
    for (let d = depth; d > 0; d--) {
      ctx.fillStyle = pal.shadow;
      ctx.fillText(text, x + d, y + d);
    }
    // Main fill
    ctx.fillStyle = pal.fill;
    ctx.fillText(text, x, y);
    // Top highlight line
    ctx.globalAlpha = 0.25;
    ctx.fillStyle = '#FFF';
    const metrics = ctx.measureText(text);
    ctx.fillRect(x - metrics.width / 2, y - fs / 2, metrics.width, 2 * df);
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- WILDSTYLE ---
  // Overlapping, rotated, with arrows and connections
  wildstyle(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = 'bold italic ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Slight rotation
    ctx.translate(x, y);
    ctx.rotate(-0.08);
    // Outer glow
    ctx.shadowColor = pal.fill;
    ctx.shadowBlur = 6 * df;
    // Background arrow accent
    ctx.strokeStyle = pal.accent + '55';
    ctx.lineWidth = 2 * df;
    ctx.beginPath();
    const tw2 = fs * text.length * 0.35;
    ctx.moveTo(-tw2 - 8 * df, 0);
    ctx.lineTo(-tw2 - 2 * df, -6 * df);
    ctx.moveTo(-tw2 - 8 * df, 0);
    ctx.lineTo(-tw2 - 2 * df, 6 * df);
    ctx.moveTo(tw2 + 8 * df, 0);
    ctx.lineTo(tw2 + 2 * df, -6 * df);
    ctx.moveTo(tw2 + 8 * df, 0);
    ctx.lineTo(tw2 + 2 * df, 6 * df);
    ctx.stroke();
    // Outline
    ctx.strokeStyle = pal.stroke;
    ctx.lineWidth = Math.max(1, 3 * df);
    ctx.strokeText(text, 0, 0);
    // Fill
    ctx.fillStyle = pal.fill;
    ctx.fillText(text, 0, 0);
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- NEON OUTLINE ---
  // Only stroke, no fill -- glowing tube letters
  neonOutline(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = 'bold ' + fs + 'px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Double glow
    ctx.shadowColor = pal.fill;
    ctx.shadowBlur = 12 * df;
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 2 * df);
    ctx.strokeText(text, x, y);
    // Inner brighter pass
    ctx.shadowBlur = 4 * df;
    ctx.strokeStyle = '#FFFFFF88';
    ctx.lineWidth = Math.max(1, 1 * df);
    ctx.strokeText(text, x, y);
    ctx.shadowBlur = 0;
    ctx.restore();
  },

  // --- GLITCH ---
  // Offset RGB split -- cyberpunk data corruption look
  glitch(ctx, text, x, y, size, pal, df) {
    const fs = Math.max(8, Math.floor(size));
    ctx.save();
    ctx.font = '900 ' + fs + 'px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    // Cyan layer (shifted left)
    ctx.globalAlpha = 0.6;
    ctx.fillStyle = '#00FFFF';
    ctx.fillText(text, x - 2 * df, y - 1 * df);
    // Magenta layer (shifted right)
    ctx.fillStyle = '#FF00FF';
    ctx.fillText(text, x + 2 * df, y + 1 * df);
    // White core
    ctx.globalAlpha = 0.85;
    ctx.fillStyle = '#FFFFFF';
    ctx.fillText(text, x, y);
    // Scanline slice
    ctx.globalAlpha = 0.15;
    ctx.fillStyle = pal.fill;
    ctx.fillRect(x - fs * text.length * 0.3, y - 1 * df, fs * text.length * 0.6, 2 * df);
    ctx.globalAlpha = 1;
    ctx.restore();
  },
};


// ============================================================
// GRAFFITI ICON RENDERERS
// Each takes: (ctx, cx, cy, size, pal, df)
//   - cx,cy = pixel center
//   - size = base size in px (pre-scaled)
//   - pal = palette
//   - df = depth factor
// ============================================================

const GRAFFITI_ICONS = {

  // --- 5-POINT CROWN (Compton) ---
  crown(ctx, cx, cy, sz, pal, df) {
    const w = sz, h = sz * 0.65;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    ctx.beginPath();
    ctx.moveTo(-w/2, h/2);             // bottom-left
    ctx.lineTo(-w/2, -h/6);            // up left
    ctx.lineTo(-w/3, h/6);             // dip
    ctx.lineTo(-w/6, -h/2);            // point
    ctx.lineTo(0, h/6);                // center dip
    ctx.lineTo(w/6, -h/2);             // point
    ctx.lineTo(w/3, h/6);              // dip
    ctx.lineTo(w/2, -h/6);             // up right
    ctx.lineTo(w/2, h/2);              // bottom-right
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    // Jewel dots on tips
    ctx.fillStyle = pal.accent;
    [[-w/6, -h/2], [0, -h/2 + h/3], [w/6, -h/2]].forEach(([px, py]) => {
      ctx.beginPath(); ctx.arc(px, py, 2 * df, 0, Math.PI * 2); ctx.fill();
    });
    ctx.restore();
  },

  // --- GEAR (Detroit) ---
  gear(ctx, cx, cy, sz, pal, df) {
    const r = sz / 2, teeth = 8, toothH = sz * 0.18;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    ctx.beginPath();
    for (let i = 0; i < teeth; i++) {
      const a1 = (i / teeth) * Math.PI * 2;
      const a2 = ((i + 0.35) / teeth) * Math.PI * 2;
      const a3 = ((i + 0.65) / teeth) * Math.PI * 2;
      const a4 = ((i + 1) / teeth) * Math.PI * 2;
      const outerR = r + toothH, innerR = r - toothH * 0.3;
      if (i === 0) ctx.moveTo(Math.cos(a1) * outerR, Math.sin(a1) * outerR);
      ctx.lineTo(Math.cos(a2) * outerR, Math.sin(a2) * outerR);
      ctx.lineTo(Math.cos(a2) * innerR, Math.sin(a2) * innerR);
      ctx.lineTo(Math.cos(a3) * innerR, Math.sin(a3) * innerR);
      ctx.lineTo(Math.cos(a3) * outerR, Math.sin(a3) * outerR);
      ctx.lineTo(Math.cos(a4) * outerR, Math.sin(a4) * outerR);
    }
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Center hole
    ctx.fillStyle = pal.shadow;
    ctx.beginPath(); ctx.arc(0, 0, r * 0.3, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  },

  // --- 6-POINT STAR (Chicago) ---
  star(ctx, cx, cy, sz, pal, df) {
    const outerR = sz / 2, innerR = sz / 4, points = 6;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    ctx.beginPath();
    for (let i = 0; i < points * 2; i++) {
      const a = (i * Math.PI) / points - Math.PI / 2;
      const r2 = i % 2 === 0 ? outerR : innerR;
      if (i === 0) ctx.moveTo(Math.cos(a) * r2, Math.sin(a) * r2);
      else ctx.lineTo(Math.cos(a) * r2, Math.sin(a) * r2);
    }
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Neon glow
    ctx.shadowColor = pal.fill;
    ctx.shadowBlur = 5 * df;
    ctx.stroke();
    ctx.shadowBlur = 0;
    ctx.restore();
  },

  // --- BRIDGE silhouette (Brooklyn) ---
  bridge(ctx, cx, cy, sz, pal, df) {
    const w = sz * 1.2, h = sz * 0.7;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 2 * df);
    ctx.fillStyle = pal.fill + '44';
    // Main deck
    ctx.beginPath();
    ctx.moveTo(-w/2, h * 0.1);
    ctx.lineTo(w/2, h * 0.1);
    ctx.lineTo(w/2, h * 0.25);
    ctx.lineTo(-w/2, h * 0.25);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Two towers
    [[-w * 0.2], [w * 0.2]].forEach(([tx]) => {
      ctx.strokeStyle = pal.fill;
      ctx.beginPath();
      ctx.moveTo(tx - sz * 0.06, h * 0.1);
      ctx.lineTo(tx - sz * 0.04, -h * 0.45);
      ctx.lineTo(tx + sz * 0.04, -h * 0.45);
      ctx.lineTo(tx + sz * 0.06, h * 0.1);
      ctx.stroke();
      // Gothic arch
      ctx.beginPath();
      ctx.arc(tx, -h * 0.15, sz * 0.06, Math.PI, 0);
      ctx.stroke();
    });
    // Suspension cables
    ctx.strokeStyle = pal.accent + '66';
    ctx.lineWidth = Math.max(1, 1 * df);
    for (let cable = 0; cable < 6; cable++) {
      const frac = cable / 5;
      const cableX = -w/2 + frac * w;
      const towerX = cableX < 0 ? -w * 0.2 : w * 0.2;
      ctx.beginPath();
      ctx.moveTo(towerX, -h * 0.4);
      ctx.lineTo(cableX, h * 0.1);
      ctx.stroke();
    }
    ctx.restore();
  },

  // --- DIAMOND (Atlanta) ---
  diamond(ctx, cx, cy, sz, pal, df) {
    const w = sz * 0.7, h = sz;
    ctx.save();
    ctx.translate(cx, cy);
    // Faceted diamond shape
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    ctx.beginPath();
    ctx.moveTo(0, -h/2);              // top point
    ctx.lineTo(w/2, -h/6);            // top right
    ctx.lineTo(w/3, h/2);             // bottom right
    ctx.lineTo(-w/3, h/2);            // bottom left
    ctx.lineTo(-w/2, -h/6);           // top left
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Inner facet line
    ctx.strokeStyle = pal.accent + '88';
    ctx.beginPath();
    ctx.moveTo(-w/2, -h/6);
    ctx.lineTo(0, h/6);
    ctx.lineTo(w/2, -h/6);
    ctx.stroke();
    // Sparkle
    ctx.fillStyle = '#FFF';
    ctx.globalAlpha = 0.6;
    ctx.beginPath(); ctx.arc(-w/6, -h/4, 1.5 * df, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- ANCHOR (Oakland) ---
  anchor(ctx, cx, cy, sz, pal, df) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 2.5 * df);
    ctx.lineCap = 'round';
    const h = sz * 0.9, w = sz * 0.6;
    // Vertical shaft
    ctx.beginPath();
    ctx.moveTo(0, -h/2 + sz * 0.15);
    ctx.lineTo(0, h/2);
    ctx.stroke();
    // Cross bar
    ctx.beginPath();
    ctx.moveTo(-w * 0.35, -h/4);
    ctx.lineTo(w * 0.35, -h/4);
    ctx.stroke();
    // Bottom curve (flukes)
    ctx.beginPath();
    ctx.arc(0, h/3, w/2, 0, Math.PI);
    ctx.stroke();
    // Fluke tips (pointed)
    ctx.beginPath();
    ctx.moveTo(-w/2, h/3);
    ctx.lineTo(-w/2 - 4 * df, h/3 + 4 * df);
    ctx.moveTo(w/2, h/3);
    ctx.lineTo(w/2 + 4 * df, h/3 + 4 * df);
    ctx.stroke();
    // Ring at top
    ctx.beginPath();
    ctx.arc(0, -h/2 + sz * 0.1, sz * 0.08, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  },

  // --- PALM TREE (Miami) ---
  palm(ctx, cx, cy, sz, pal, df) {
    ctx.save();
    ctx.translate(cx, cy);
    const trunkH = sz * 0.6;
    // Trunk (curved)
    ctx.strokeStyle = pal.shadow || '#442200';
    ctx.lineWidth = Math.max(2, 3 * df);
    ctx.beginPath();
    ctx.moveTo(0, sz * 0.35);
    ctx.quadraticCurveTo(sz * 0.08, 0, -sz * 0.03, -sz * 0.2);
    ctx.stroke();
    // Fronds (5 radiating arcs)
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 2 * df);
    const frondBase = {x: -sz * 0.03, y: -sz * 0.2};
    const angles = [-2.2, -1.6, -1.0, -0.4, 0.2];
    angles.forEach(a => {
      ctx.beginPath();
      ctx.moveTo(frondBase.x, frondBase.y);
      const endX = frondBase.x + Math.cos(a) * sz * 0.4;
      const endY = frondBase.y + Math.sin(a) * sz * 0.35;
      const cpX = frondBase.x + Math.cos(a) * sz * 0.25;
      const cpY = frondBase.y + Math.sin(a) * sz * 0.1;
      ctx.quadraticCurveTo(cpX, cpY, endX, endY);
      ctx.stroke();
    });
    ctx.restore();
  },

  // --- SPADE (Las Vegas) ---
  spade(ctx, cx, cy, sz, pal, df) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    // Spade shape via two arcs + triangle
    ctx.beginPath();
    ctx.moveTo(0, -sz * 0.45);
    // Left bulge
    ctx.bezierCurveTo(-sz * 0.5, -sz * 0.35, -sz * 0.5, sz * 0.15, 0, sz * 0.15);
    // Right bulge
    ctx.bezierCurveTo(sz * 0.5, sz * 0.15, sz * 0.5, -sz * 0.35, 0, -sz * 0.45);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Stem
    ctx.fillStyle = pal.fill;
    ctx.beginPath();
    ctx.moveTo(-sz * 0.06, sz * 0.1);
    ctx.lineTo(sz * 0.06, sz * 0.1);
    ctx.lineTo(sz * 0.1, sz * 0.4);
    ctx.lineTo(-sz * 0.1, sz * 0.4);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Sparkle
    ctx.fillStyle = '#FFF';
    ctx.globalAlpha = 0.4;
    ctx.beginPath(); ctx.arc(-sz * 0.1, -sz * 0.15, 1.5 * df, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
    ctx.restore();
  },

  // --- CIRCUIT NODE (Neo Tokyo) ---
  circuit(ctx, cx, cy, sz, pal, df) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.strokeStyle = pal.fill;
    ctx.lineWidth = Math.max(1, 1.5 * df);
    // Central node
    ctx.fillStyle = pal.fill;
    ctx.beginPath(); ctx.arc(0, 0, sz * 0.12, 0, Math.PI * 2); ctx.fill();
    // Radiating traces
    const traces = [
      [0, -1], [0.7, -0.7], [1, 0], [0.7, 0.7],
      [0, 1], [-0.7, 0.7], [-1, 0], [-0.7, -0.7],
    ];
    ctx.shadowColor = pal.fill;
    ctx.shadowBlur = 4 * df;
    traces.forEach(([dx, dy], i) => {
      const len = (i % 2 === 0 ? 0.4 : 0.3) * sz;
      ctx.beginPath();
      ctx.moveTo(dx * sz * 0.15, dy * sz * 0.15);
      // Right-angle trace
      if (i % 2 === 0) {
        ctx.lineTo(dx * len, dy * len);
      } else {
        const mid = len * 0.6;
        ctx.lineTo(dx * mid, dy * mid);
        ctx.lineTo(dx * len + dy * sz * 0.08, dy * len - dx * sz * 0.08);
      }
      ctx.stroke();
      // End node
      ctx.fillStyle = pal.accent;
      const ex = i % 2 === 0 ? dx * len : dx * len + dy * sz * 0.08;
      const ey = i % 2 === 0 ? dy * len : dy * len - dx * sz * 0.08;
      ctx.beginPath(); ctx.arc(ex, ey, 2 * df, 0, Math.PI * 2); ctx.fill();
    });
    ctx.shadowBlur = 0;
    ctx.restore();
  },

  // --- ROYAL CROWN (Kingz Court) ---
  royalCrown(ctx, cx, cy, sz, pal, df) {
    const w = sz * 1.1, h = sz * 0.75;
    ctx.save();
    ctx.translate(cx, cy);
    // Base band
    ctx.fillStyle = pal.fill;
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(1, 1.5 * df);
    ctx.fillRect(-w/2, h * 0.15, w, h * 0.2);
    ctx.strokeRect(-w/2, h * 0.15, w, h * 0.2);
    // Crown peaks (5 tall points with jewels)
    ctx.beginPath();
    ctx.moveTo(-w/2, h * 0.15);
    ctx.lineTo(-w/2, -h * 0.1);
    ctx.lineTo(-w * 0.3, -h * 0.45);   // peak 1
    ctx.lineTo(-w * 0.15, -h * 0.05);
    ctx.lineTo(0, -h * 0.5);            // peak 2 (center, tallest)
    ctx.lineTo(w * 0.15, -h * 0.05);
    ctx.lineTo(w * 0.3, -h * 0.45);     // peak 3
    ctx.lineTo(w/2, -h * 0.1);
    ctx.lineTo(w/2, h * 0.15);
    ctx.closePath();
    ctx.fill(); ctx.stroke();
    // Jewels on peaks
    ctx.fillStyle = pal.stroke; // purple jewels
    [[-w * 0.3, -h * 0.38], [0, -h * 0.43], [w * 0.3, -h * 0.38]].forEach(([jx, jy]) => {
      ctx.beginPath(); ctx.arc(jx, jy, 2.5 * df, 0, Math.PI * 2); ctx.fill();
      ctx.strokeStyle = '#000'; ctx.stroke();
    });
    // Band jewels
    ctx.fillStyle = pal.stroke;
    for (let j = -2; j <= 2; j++) {
      ctx.beginPath(); ctx.arc(j * w * 0.18, h * 0.25, 1.5 * df, 0, Math.PI * 2); ctx.fill();
    }
    // Sparkle glow
    ctx.shadowColor = pal.fill;
    ctx.shadowBlur = 8 * df;
    ctx.fillStyle = pal.fill + '44';
    ctx.beginPath(); ctx.arc(0, -h * 0.3, sz * 0.25, 0, Math.PI * 2); ctx.fill();
    ctx.shadowBlur = 0;
    ctx.restore();
  },
};


// ============================================================
// MAIN RENDER FUNCTION
// Call this per building face during renderBuildingSilhouettes3D
// ============================================================

/**
 * Render graffiti onto a single building wall face.
 *
 * @param {CanvasRenderingContext2D} ctx
 * @param {object} arena     - CITY_ARENAS[i] object
 * @param {string} side      - 'left' or 'right'
 * @param {number} bldgIndex - which building (0-7), used to pick which tag
 * @param {number} wallX     - pixel X of the wall rect
 * @param {number} wallY     - pixel Y of the top of the wall
 * @param {number} wallW     - pixel width of the wall
 * @param {number} wallH     - pixel height of the wall
 * @param {number} df        - depth factor from getDepthFactor()
 */
function renderGraffiti(ctx, arena, side, bldgIndex, wallX, wallY, wallW, wallH, df) {
  const data = GRAFFITI_DB[arena.style];
  if (!data) return;

  ctx.save();
  ctx.globalAlpha = 0.6; // graffiti is weathered, not full blast

  // Clip to wall rect so nothing bleeds outside the building
  ctx.beginPath();
  ctx.rect(wallX, wallY, wallW, wallH);
  ctx.clip();

  const pal = data.palette;

  // Decide what to draw on this building face
  // Even-indexed buildings on left get tag[0], odd get tag[1], etc.
  // Right side gets the icon on building 2 or 3
  const tagIdx = bldgIndex % data.tags.length;
  const tag = data.tags[tagIdx];

  const cx = wallX + wallW / 2;
  const cy = wallY + wallH * 0.45;

  // Draw tag text
  const baseFontSize = wallW * tag.size * 0.7;
  const styleFn = GRAFFITI_STYLES[tag.style] || GRAFFITI_STYLES.block;
  styleFn(ctx, tag.text, cx, cy, baseFontSize, pal, df);

  // Draw icon on specific buildings (index 1 on left, index 2 on right)
  const iconSlot = side === 'left' ? 1 : 2;
  if (bldgIndex === iconSlot) {
    const iconFn = GRAFFITI_ICONS[data.icon];
    if (iconFn) {
      const iconY = wallY + wallH * 0.75;
      const iconSz = wallW * 0.5;
      iconFn(ctx, cx, iconY, iconSz, pal, df);
    }
  }

  ctx.restore();
}


// ============================================================
// DROP-IN REPLACEMENT for renderBuildingSilhouettes3D
// Adds graffiti to the existing building loop.
// Copy this function over the original to get graffiti on walls.
// ============================================================

/**
 * Enhanced building renderer with graffiti.
 * Drop-in replacement: swap renderBuildingSilhouettes3D with this.
 *
 * Requires globals: CITY_BUILDINGS, ARENA_W, ARENA_H, H, scale,
 *                   animT, toScr3D, getDepthFactor
 */
function renderBuildingSilhouettes3D_withGraffiti(arena) {
  const bCount = 8;
  for (let i = 0; i < bCount; i++) {
    const gy = i * (ARENA_H / bCount);
    const df = getDepthFactor(gy);
    const bh = CITY_BUILDINGS[i % CITY_BUILDINGS.length] * H * 0.4 * df;
    const bw = scale * 1.5 * df;

    // === LEFT SIDE BUILDINGS ===
    const [lx, ly] = toScr3D(-0.5, gy);
    const leftWallX = lx - bw;
    const leftWallY = ly - bh;
    ctx.fillStyle = arena.sky2;
    ctx.fillRect(leftWallX, leftWallY, bw, bh);

    // Windows (flickering with trig)
    for (let row = 0; row < 3; row++) {
      for (let col = 0; col < 2; col++) {
        const flicker = Math.sin(animT * 2 + i + row) > 0.3 ? 1 : 0.4;
        ctx.fillStyle = 'rgba(255,240,120,' + (0.15 + flicker * 0.15) + ')';
        ctx.fillRect(leftWallX + col * (bw / 2.5) + 4, leftWallY + row * (bh / 3.5) + 8, bw * 0.2, bh * 0.08);
      }
    }

    // Neon accent strip
    if (i % 2 === 0) {
      ctx.fillStyle = arena.n1 + '44';
      ctx.fillRect(leftWallX + 2, leftWallY + bh * 0.5, bw - 4, 2 * df);
    }

    // >>> GRAFFITI on left wall <<<
    if (i % 2 === 0 || i === 1) { // Draw on select buildings, not every one
      renderGraffiti(ctx, arena, 'left', i, leftWallX, leftWallY, bw, bh, df);
    }

    // === RIGHT SIDE BUILDINGS ===
    const [rx] = toScr3D(ARENA_W + 0.5, gy);
    const rightBh = bh * 0.8;
    ctx.fillStyle = arena.sky2;
    ctx.fillRect(rx, ly - rightBh, bw, rightBh);

    for (let row = 0; row < 3; row++) {
      for (let col = 0; col < 2; col++) {
        const flicker2 = Math.sin(animT * 2.3 + i * 3 + row) > 0.2 ? 1 : 0.4;
        ctx.fillStyle = 'rgba(255,240,120,' + (0.15 + flicker2 * 0.15) + ')';
        ctx.fillRect(rx + col * (bw / 2.5) + 4, ly - rightBh + row * (rightBh / 3.5) + 8, bw * 0.2, rightBh * 0.06);
      }
    }

    // >>> GRAFFITI on right wall <<<
    if (i % 2 === 1 || i === 2) { // Offset pattern from left
      renderGraffiti(ctx, arena, 'right', i, rx, ly - rightBh, bw, rightBh, df);
    }
  }
}


// ============================================================
// INTEGRATION INSTRUCTIONS
// ============================================================
//
// OPTION A (Quick drop-in):
//   In game_v6.html, find the call to renderBuildingSilhouettes3D(arena)
//   inside renderArena3D(). Replace it with:
//     renderBuildingSilhouettes3D_withGraffiti(arena);
//
// OPTION B (Granular):
//   In the existing renderBuildingSilhouettes3D loop, after drawing
//   each building rect, call:
//     renderGraffiti(ctx, arena, 'left', i, leftX, leftY, bw, bh, df);
//     renderGraffiti(ctx, arena, 'right', i, rightX, rightY, bw, bh, df);
//
// OPTION C (Script tag include):
//   <script src="graffiti_system.js"></script>
//   Then use Option A or B above.
// ============================================================
