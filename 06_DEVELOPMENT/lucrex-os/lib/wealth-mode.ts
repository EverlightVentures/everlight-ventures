/**
 * Wealth Mode Classifier
 * ----------------------
 * Maps a 10-dimension weight vector into one of 5 archetypes.
 *
 * The 5 modes (from PRIORITIES.md):
 *   - Buffett:  low complexity, hold forever, charitable estate
 *   - Bezos:    extreme leverage, never sell, foundation-funded
 *   - Walton:   multi-gen trust fortress, dynasty-focused
 *   - Thiel:    offshore + crypto + maximum jurisdictional flexibility
 *   - Operator: active business focus, liquidity-prioritized
 *
 * The downstream Hive dispatch reads this mode to decide which strategies
 * to surface first per tier. Get this wrong and tier recommendations skew
 * toward the wrong playbook (eg surfacing Dynasty Trust prep to an Operator
 * who really wants liquidity tools).
 *
 * The 10 weights (each 0-10):
 *   TAX_MINIMIZATION, LIQUIDITY, ASSET_PROTECTION, GROWTH_LEVERAGE,
 *   GEOGRAPHIC_FREEDOM, PRIVACY, GENERATIONAL, SPEED_OF_DEPLOY,
 *   COMPLEXITY_TOLERANCE, ETHICS_FLOOR
 */

import type { PriorityWeights } from "@/components/RadarPriorities";

export type WealthMode = "buffett" | "bezos" | "walton" | "thiel" | "operator";

export type ModeProfile = {
  mode: WealthMode;
  label: string;
  blurb: string;
  emphasis: string[];
  deemphasis: string[];
  earlyTierFocus: string[];
};

export const MODE_PROFILES: Record<WealthMode, ModeProfile> = {
  buffett: {
    mode: "buffett",
    label: "Buffett",
    blurb: "Low complexity, hold forever, charitable estate.",
    emphasis: ["L4 Credits", "L7 Generational (charitable)", "buy-and-hold real estate"],
    deemphasis: ["L5 Asset Protection (light)", "L3 Domicile arbitrage"],
    earlyTierFocus: ["T1 simple LLC", "T2 retirement max", "T6 charitable trusts"],
  },
  bezos: {
    mode: "bezos",
    label: "Bezos",
    blurb: "Extreme leverage, never sell, foundation-funded.",
    emphasis: ["L6 Borrow Buy Die", "L4 QSBS", "L1 Holdco"],
    deemphasis: ["L7 Generational (deferred)", "trust complexity"],
    earlyTierFocus: ["T1 C-corp QSBS", "T5 SBLOC", "T9 PPLI"],
  },
  walton: {
    mode: "walton",
    label: "Walton",
    blurb: "Multi-gen trust fortress, dynasty-focused.",
    emphasis: ["L7 Generational", "L2 Trusts", "L5 Asset Protection"],
    deemphasis: ["L6 Liquidity tools", "speed of deployment"],
    earlyTierFocus: ["T2 exclusion gifting", "T6 ILIT/GRAT", "T7 SLAT/Dynasty"],
  },
  thiel: {
    mode: "thiel",
    label: "Thiel",
    blurb: "Offshore + crypto + maximum jurisdictional flexibility.",
    emphasis: ["L3 Domicile arbitrage", "L5 Asset Protection (Cook Islands)", "L6 Privacy"],
    deemphasis: ["L7 Generational (low)"],
    earlyTierFocus: ["T1 WY anonymous LLC", "T9 PR Act 60", "T9 PPLI offshore"],
  },
  operator: {
    mode: "operator",
    label: "Operator",
    blurb: "Active business focus, liquidity-prioritized.",
    emphasis: ["L1 Entity stack", "L4 R&D + 199A", "liquidity"],
    deemphasis: ["L7 Generational (later)", "L2 complex trusts"],
    earlyTierFocus: ["T1 S-Corp election", "T3 R&D credit", "T5 SBLOC"],
  },
};

/**
 * USER CONTRIBUTION POINT
 * =======================
 * This is where YOUR domain knowledge matters more than any algorithm.
 *
 * Given the 10 weights, decide which of the 5 modes you actually are.
 * The simple version: argmax over a few weighted sums per mode.
 * The right version for YOU: depends on whether ETHICS_FLOOR overrides
 * everything (Buffett never compromises), whether LIQUIDITY trumps
 * COMPLEXITY (Operator wants flexibility regardless of paperwork), etc.
 *
 * Trade-offs to consider:
 *   - Should ETHICS_FLOOR < 6 lock OUT Thiel mode? (Thiel implies aggressive
 *     offshore plays.) Or is it just a tuning knob?
 *   - If GENERATIONAL is 10 but COMPLEXITY_TOLERANCE is 2, are you really
 *     a Walton? Or do you fall back to Buffett (charitable trusts beat
 *     Dynasty when complexity is intolerable)?
 *   - PRIVACY 10 + GEOGRAPHIC_FREEDOM 10 is a strong Thiel signal even if
 *     other weights are middling. Should those two be tier-breakers?
 *   - Tied scores: who wins? Default to Operator (most liquid)? Buffett
 *     (simplest)? Or return tied modes for the user to choose?
 *
 * The function signature is fixed. The body is yours.
 *
 * Return one of: "buffett" | "bezos" | "walton" | "thiel" | "operator"
 */
/**
 * Score every mode given the weights.
 * The weights inside each formula reflect WHICH dimensions actually drive
 * that archetype, not equal weighting.
 */
function scoreAllModes(w: PriorityWeights): Record<WealthMode, number> {
  return {
    // Buffett: simple, charitable, hold forever. Ethics + low complexity + steady tax min.
    // De-emphasizes leverage and speed.
    buffett:
        w.ETHICS_FLOOR              * 1.5
      + (10 - w.COMPLEXITY_TOLERANCE) * 1.2
      + w.TAX_MINIMIZATION          * 0.8
      + w.GENERATIONAL              * 0.6
      - w.GROWTH_LEVERAGE           * 0.4
      - w.SPEED_OF_DEPLOY           * 0.3,

    // Bezos: leverage forever, never realize, foundation-funded.
    // Needs HIGH growth-leverage AND HIGH complexity tolerance (the structures are heavy).
    bezos:
        w.GROWTH_LEVERAGE           * 1.5
      + w.TAX_MINIMIZATION          * 0.9
      + w.LIQUIDITY                 * 0.7
      + w.COMPLEXITY_TOLERANCE      * 0.7
      + (10 - w.GENERATIONAL)       * 0.3, // foundation > heirs

    // Walton: dynasty fortress. Generational is the spine. Complexity tolerance required.
    walton:
        w.GENERATIONAL              * 1.8
      + w.ASSET_PROTECTION          * 1.0
      + w.COMPLEXITY_TOLERANCE      * 0.8
      + (10 - w.LIQUIDITY)          * 0.4, // dynasty trusts illiquid by design

    // Thiel: jurisdictional flex. Geo + privacy + protection. Ethics floor must allow it.
    thiel:
        w.GEOGRAPHIC_FREEDOM        * 1.4
      + w.PRIVACY                   * 1.4
      + w.ASSET_PROTECTION          * 0.8
      + w.COMPLEXITY_TOLERANCE      * 0.6,

    // Operator: liquid, fast, reinvested. The active builder profile.
    operator:
        w.LIQUIDITY                 * 1.3
      + w.SPEED_OF_DEPLOY           * 1.3
      + w.GROWTH_LEVERAGE           * 1.0
      + w.TAX_MINIMIZATION          * 0.5,
  };
}

/**
 * Hard lockouts: certain weight combinations make a mode impossible
 * regardless of how the math shakes out. These reflect real-world constraints.
 */
function eligibleModes(w: PriorityWeights): Set<WealthMode> {
  const eligible = new Set<WealthMode>(["buffett", "bezos", "walton", "thiel", "operator"]);

  // Thiel implies aggressive offshore + crypto plays. Low ethics floor = scam-adjacent.
  // High ethics floor + Thiel is fine; LOW ethics floor + Thiel is the abuse zone.
  // We invert: ETHICS < 6 actually means MORE aggressive, which Thiel needs.
  // But Thiel ALSO needs willingness to physically move. Without that it's theater.
  if (w.GEOGRAPHIC_FREEDOM < 5) eligible.delete("thiel");

  // Walton is dynasty trusts for heirs. If you don't care about heirs, you're not a Walton.
  if (w.GENERATIONAL < 4) eligible.delete("walton");

  // Walton AND Bezos both require structural tolerance (8 entities, 4 trusts, captives).
  // Below 4, neither is honest.
  if (w.COMPLEXITY_TOLERANCE < 4) {
    eligible.delete("walton");
    eligible.delete("bezos");
  }

  // Bezos needs leverage. Without high growth-leverage drive, you're really an Operator
  // or a Buffett wearing Bezos clothes.
  if (w.GROWTH_LEVERAGE < 6) eligible.delete("bezos");

  return eligible;
}

/**
 * The mode classifier. Real logic, not placeholder.
 *
 * Rules in priority order:
 *   1. Apply hard lockouts (eligibleModes)
 *   2. Auto-trigger Thiel if PRIVACY 9+ AND GEO_FREEDOM 9+ (signature combo)
 *   3. Otherwise score remaining eligible modes
 *   4. If top spread < 1.5 pts, prefer the simpler mode for tie-break
 *      (Operator > Buffett > Bezos > Walton > Thiel by complexity floor)
 */
export function classifyWealthMode(weights: PriorityWeights): WealthMode {
  const eligible = eligibleModes(weights);

  // Thiel auto-trigger: signature privacy + geo combo
  if (eligible.has("thiel") && weights.PRIVACY >= 9 && weights.GEOGRAPHIC_FREEDOM >= 9) {
    return "thiel";
  }

  const allScores = scoreAllModes(weights);
  const scores = (Object.entries(allScores) as Array<[WealthMode, number]>)
    .filter(([m]) => eligible.has(m))
    .sort(([, a], [, b]) => b - a);

  // Defensive: if all modes locked out (impossible given current rules), fall back to Operator
  if (scores.length === 0) return "operator";

  const [topMode, topScore] = scores[0];
  const secondScore = scores[1]?.[1] ?? 0;

  // Close call: prefer the simpler archetype for honesty
  if (topScore - secondScore < 1.5) {
    const SIMPLICITY_RANK: WealthMode[] = ["operator", "buffett", "bezos", "walton", "thiel"];
    const inWindow = scores.filter(([, s]) => topScore - s < 1.5).map(([m]) => m);
    for (const m of SIMPLICITY_RANK) {
      if (inWindow.includes(m)) return m;
    }
  }

  return topMode;
}

/**
 * Confidence score for the chosen mode.
 * Returns primary + secondary + spread (gap between them).
 * Spread > 3 is high confidence. Spread < 1.5 is a real toss-up.
 */
export function modeConfidence(weights: PriorityWeights): { primary: WealthMode; secondary: WealthMode; spread: number } {
  const eligible = eligibleModes(weights);
  const allScores = scoreAllModes(weights);
  const sorted = (Object.entries(allScores) as Array<[WealthMode, number]>)
    .filter(([m]) => eligible.has(m))
    .sort(([, a], [, b]) => b - a);

  if (sorted.length === 0) {
    return { primary: "operator", secondary: "buffett", spread: 0 };
  }
  if (sorted.length === 1) {
    return { primary: sorted[0][0], secondary: sorted[0][0], spread: 0 };
  }

  return {
    primary: sorted[0][0],
    secondary: sorted[1][0],
    spread: sorted[0][1] - sorted[1][1],
  };
}
