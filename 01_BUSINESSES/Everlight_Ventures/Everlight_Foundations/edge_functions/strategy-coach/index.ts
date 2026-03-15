// strategy-coach: Hybrid blackjack strategy advisor
// Static chart lookups for analyze-hand + get-tip (free, instant, accurate)
// OpenAI GPT-4o-mini for freeform ask (cheap, conversational)

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

// --- EMBEDDED STRATEGY DATA (from blackjack_strategy_data.json) ---
const STRATEGY: Record<string, DeckStrategy> = {
  "single": {
    key: "single-deck-S17",
    rules: { decks: 1, soft17: "stand", DAS: true, surrender: "late", bj_pays: "3:2" },
    house_edge: "0.00% to 0.02%",
    hard: {
      "5":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "6":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "7":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "8":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "9":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "10":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "11":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"D","A":"D"},
      "12":{"2":"H","3":"H","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "13":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "14":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "15":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"Rh","A":"H"},
      "16":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"Rh","10":"Rh","A":"Rh"},
      "17":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "18":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "19":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "20":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    soft: {
      "A2":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A3":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A4":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A5":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A6":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A7":{"2":"S","3":"Ds","4":"Ds","5":"Ds","6":"Ds","7":"S","8":"S","9":"H","10":"H","A":"S"},
      "A8":{"2":"S","3":"S","4":"S","5":"S","6":"Ds","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "A9":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    pairs: {
      "AA":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "22":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "33":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "44":{"2":"H","3":"H","4":"H","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "55":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "66":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "77":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"H","10":"Rs","A":"H"},
      "88":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "99":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"S","8":"SP","9":"SP","10":"S","A":"S"},
      "TT":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    }
  },
  "double": {
    key: "double-deck-S17",
    rules: { decks: 2, soft17: "stand", DAS: true, surrender: "late", bj_pays: "3:2" },
    house_edge: "0.19% to 0.25%",
    hard: {
      "5":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "6":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "7":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "8":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "9":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "10":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "11":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"D","A":"D"},
      "12":{"2":"H","3":"H","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "13":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "14":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "15":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"Rh","A":"H"},
      "16":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"Rh","10":"Rh","A":"Rh"},
      "17":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "18":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "19":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "20":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    soft: {
      "A2":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A3":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A4":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A5":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A6":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A7":{"2":"S","3":"Ds","4":"Ds","5":"Ds","6":"Ds","7":"S","8":"S","9":"H","10":"H","A":"S"},
      "A8":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "A9":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    pairs: {
      "AA":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "22":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "33":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "44":{"2":"H","3":"H","4":"H","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "55":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "66":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "77":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "88":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "99":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"S","8":"SP","9":"SP","10":"S","A":"S"},
      "TT":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    }
  },
  "4-deck": {
    key: "4-deck-H17",
    rules: { decks: 4, soft17: "hit", DAS: true, surrender: "late", bj_pays: "3:2" },
    house_edge: "0.45% to 0.52%",
    hard: {
      "5":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "6":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "7":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "8":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "9":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "10":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "11":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"D","A":"D"},
      "12":{"2":"H","3":"H","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "13":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "14":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "15":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"Rh","A":"Rh"},
      "16":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"Rh","10":"Rh","A":"Rh"},
      "17":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"Rs"},
      "18":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "19":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "20":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    soft: {
      "A2":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A3":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A4":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A5":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A6":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A7":{"2":"Ds","3":"Ds","4":"Ds","5":"Ds","6":"Ds","7":"S","8":"S","9":"H","10":"H","A":"H"},
      "A8":{"2":"S","3":"S","4":"S","5":"S","6":"Ds","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "A9":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    pairs: {
      "AA":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "22":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "33":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "44":{"2":"H","3":"H","4":"H","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "55":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "66":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "77":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "88":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"Rh","A":"Rh"},
      "99":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"S","8":"SP","9":"SP","10":"S","A":"S"},
      "TT":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    }
  },
  "6-deck": {
    key: "6-deck-H17",
    rules: { decks: 6, soft17: "hit", DAS: true, surrender: "late", bj_pays: "3:2" },
    house_edge: "0.54% to 0.63%",
    hard: {
      "5":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "6":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "7":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "8":{"2":"H","3":"H","4":"H","5":"H","6":"H","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "9":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "10":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "11":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"D","A":"D"},
      "12":{"2":"H","3":"H","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "13":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "14":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "15":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"H","10":"Rh","A":"Rh"},
      "16":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"H","8":"H","9":"Rh","10":"Rh","A":"Rh"},
      "17":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"Rs"},
      "18":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "19":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "20":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    soft: {
      "A2":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A3":{"2":"H","3":"H","4":"H","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A4":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A5":{"2":"H","3":"H","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A6":{"2":"H","3":"D","4":"D","5":"D","6":"D","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "A7":{"2":"Ds","3":"Ds","4":"Ds","5":"Ds","6":"Ds","7":"S","8":"S","9":"H","10":"H","A":"H"},
      "A8":{"2":"S","3":"S","4":"S","5":"S","6":"Ds","7":"S","8":"S","9":"S","10":"S","A":"S"},
      "A9":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    },
    pairs: {
      "AA":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"SP","A":"SP"},
      "22":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "33":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "44":{"2":"H","3":"H","4":"H","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "55":{"2":"D","3":"D","4":"D","5":"D","6":"D","7":"D","8":"D","9":"D","10":"H","A":"H"},
      "66":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"H","8":"H","9":"H","10":"H","A":"H"},
      "77":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"H","9":"H","10":"H","A":"H"},
      "88":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"SP","8":"SP","9":"SP","10":"Rh","A":"Rh"},
      "99":{"2":"SP","3":"SP","4":"SP","5":"SP","6":"SP","7":"S","8":"SP","9":"SP","10":"S","A":"S"},
      "TT":{"2":"S","3":"S","4":"S","5":"S","6":"S","7":"S","8":"S","9":"S","10":"S","A":"S"}
    }
  }
};

interface DeckStrategy {
  key: string;
  rules: { decks: number; soft17: string; DAS: boolean; surrender: string; bj_pays: string };
  house_edge: string;
  hard: Record<string, Record<string, string>>;
  soft: Record<string, Record<string, string>>;
  pairs: Record<string, Record<string, string>>;
}

const ACTION_LEGEND: Record<string, string> = {
  "H": "Hit",
  "S": "Stand",
  "D": "Double (hit if not allowed)",
  "Ds": "Double (stand if not allowed)",
  "SP": "Split",
  "Rh": "Surrender (hit if not allowed)",
  "Rs": "Surrender (stand if not allowed)"
};

const COMMON_MISTAKES = [
  { hand: "Soft 18 (A,7) vs 9/10/A", wrong: "Stand", correct: "Hit", why: "18 loses to dealer 9/10/A more than people think. Your ace gives flexibility." },
  { hand: "Hard 12 vs 2 or 3", wrong: "Stand", correct: "Hit", why: "Dealer 2 and 3 are not weak enough to justify standing on 12." },
  { hand: "Hard 16 vs 10", wrong: "Stand", correct: "Hit or Surrender", why: "Both options lose, but hitting loses less than standing." },
  { hand: "8,8 vs 10 or A", wrong: "Hit (not splitting)", correct: "Split (or Surrender vs A in H17)", why: "16 is terrible; two fresh hands from 8 are better." },
  { hand: "Hard 11 vs A", wrong: "Hit", correct: "Double (H17 games)", why: "Wasted profit opportunity when dealer hits soft 17." },
  { hand: "Soft 17 (A,6)", wrong: "Stand on 17", correct: "Hit or Double vs 3-6", why: "You cannot bust and soft 17 is weak." },
  { hand: "9,9 vs 9", wrong: "Stand on 18", correct: "Split", why: "18 loses to 19; two hands starting from 9 are better." },
  { hand: "Hard 10 or 11", wrong: "Not doubling", correct: "Double vs dealer low cards", why: "Largest expected profit hands in the game." },
  { hand: "A,2 / A,3 vs 5,6", wrong: "Hit", correct: "Double", why: "Wasted profit opportunity against bust cards." },
  { hand: "Insurance/Even Money", wrong: "Taking it", correct: "Never take insurance", why: "7.7% house edge on the side bet." }
];

const TIPS_DB: Record<string, string[]> = {
  hard: [
    "Hard 12 vs dealer 2 or 3: always hit. The bust risk (31%) is lower than the cost of standing against a non-bust card.",
    "Hard 16 vs 10 is the most misplayed hand. Surrender if allowed, otherwise hit. Standing loses 54% of the time.",
    "Never stand on hard 12-16 against a dealer 7 or higher. The dealer already likely has a made hand.",
    "Hard 13-16 vs dealer 2-6: stand every time. Let the dealer bust -- they will 35-42% of the time.",
    "Hard 9 vs dealer 3-6: double down. You have no bust risk and the dealer is in the danger zone.",
    "Hard 10 vs dealer 2-9: always double. This is one of your highest-profit hands in the game.",
    "Hard 11: double against everything. In most shoe games, double even against a dealer Ace.",
    "Hard 15 vs dealer 10: surrender if the table allows it. This saves you about 4 cents per dollar bet.",
    "Hard 8 is almost always a hit. Only in single-deck do you double 8 vs dealer 5 or 6.",
    "Hard 17+ is locked in. Never hit, never surrender. Stand and hope for the best."
  ],
  soft: [
    "Soft 18 (A,7) vs dealer 9, 10, or Ace: hit, don't stand. 18 is not strong enough against these upcards.",
    "Soft 17 (A,6): never stand. Hit or double vs 3-6. Soft 17 is a weak hand masquerading as something decent.",
    "Soft 13-15 (A,2 through A,4): double only vs dealer 5-6. Otherwise just hit. Low softs need the best conditions to double.",
    "Soft 16-17 (A,5 and A,6): double vs dealer 3-6 in single deck, 4-6 in multi-deck. The doubling zone expands with fewer decks.",
    "Soft 19 (A,8): almost always stand. The only exception is doubling vs 6 in some games -- a small edge play.",
    "Soft 20 (A,9): always stand. Never get greedy with a 20. It wins the vast majority of hands.",
    "A,7 vs dealer 2: stand in S17 games, double in H17 games. The dealer hitting soft 17 changes this play.",
    "The key to soft hands: you cannot bust on one hit. Use that safety net aggressively when the dealer shows weakness."
  ],
  pairs: [
    "Always split Aces and 8s. Aces give you two shots at 21; 8s escape the worst hand in blackjack (16).",
    "Never split 5s or 10s. Pair of 5s is a hard 10 -- double it. Pair of 10s is 20 -- don't break up a winner.",
    "Split 9s against everything except 7, 10, and Ace. Against 7, your 18 already beats the dealer's likely 17.",
    "Pair of 4s: only split vs dealer 5-6 with DAS (double after split). Otherwise treat as hard 8 and hit.",
    "Pair of 6s: split vs dealer 2-6 in single deck, 2-6 (or just 3-6) in multi-deck. Never split against 7+.",
    "Pair of 2s and 3s: split vs dealer 2-7. These low pairs love attacking the full dealer stiff range.",
    "Pair of 7s: split vs 2-7. Against 8+, just hit your hard 14. In single deck, surrender 7,7 vs 10 if allowed.",
    "8,8 vs dealer Ace in H17 games: surrender if available. This is one of the few surrender-over-split spots."
  ],
  general: [
    "Never take insurance. It carries a 7.7% house edge -- worse than almost any bet on the table.",
    "Basic strategy reduces the house edge to under 0.5%. Card counting can flip it to a player edge of 0.5-1.5%.",
    "Bankroll rule: bring at least 40-50 minimum bets to a session. Short bankrolls lead to emotional decisions.",
    "Single deck has the lowest house edge (0.0-0.02%) but casinos compensate with worse rules like 6:5 blackjack payouts.",
    "Always check the table rules before sitting down: 3:2 blackjack, dealer stands on soft 17, and double after split are the key player-friendly rules.",
    "The dealer busts about 28% of the time overall. Against a 5 or 6 upcard, they bust over 40% of the time.",
    "Surrender saves more money long-term than almost any other play. If the table offers it, use it correctly.",
    "Betting systems (Martingale, Paroli, etc.) do not change the house edge. Only strategy and card counting affect your expected value.",
    "Deck penetration matters for counters: the deeper the cut card, the more profitable counting becomes. Look for 75%+ penetration.",
    "Tipping the dealer does not change your odds, but it creates goodwill. Tip by placing a bet for them on your hand."
  ]
};

const VALID_DECK_TYPES = ["single", "double", "4-deck", "6-deck"];
const VALID_CATEGORIES = ["hard", "soft", "pairs", "general"];

// --- Card parsing utilities ---
function normalizeCard(card: string): string {
  const c = card.trim().toUpperCase();
  if (c === "ACE" || c === "1") return "A";
  if (c === "JACK" || c === "QUEEN" || c === "KING" || c === "J" || c === "Q" || c === "K") return "10";
  if (c === "10" || c === "T") return "10";
  if (["2","3","4","5","6","7","8","9","A"].includes(c)) return c;
  // Try extracting number from strings like "5h", "10s", "As"
  const match = c.match(/^(10|[2-9]|[AJQK])/);
  if (match) {
    const v = match[1];
    if (["J","Q","K"].includes(v)) return "10";
    if (v === "A") return "A";
    return v;
  }
  return c;
}

function cardValue(card: string): number {
  const n = normalizeCard(card);
  if (n === "A") return 11;
  return parseInt(n) || 10;
}

function classifyHand(cards: string[]): { type: "pairs" | "soft" | "hard"; key: string; total: number } {
  const normalized = cards.map(normalizeCard);

  // Check pairs (only on exactly 2 cards)
  if (normalized.length === 2 && normalized[0] === normalized[1]) {
    const v = normalized[0];
    if (v === "10") return { type: "pairs", key: "TT", total: 20 };
    if (v === "A") return { type: "pairs", key: "AA", total: 12 };
    return { type: "pairs", key: `${v}${v}`, total: cardValue(v) * 2 };
  }

  // Calculate total
  let total = 0;
  let aces = 0;
  for (const c of normalized) {
    const v = cardValue(c);
    total += v;
    if (c === "A") aces++;
  }
  while (total > 21 && aces > 0) {
    total -= 10;
    aces--;
  }

  // Check soft (has ace counting as 11, only on 2 cards for chart lookup)
  if (normalized.length === 2 && aces > 0 && total <= 21) {
    const hasAce = normalized.includes("A");
    if (hasAce) {
      const other = normalized.find(c => c !== "A") ?? "A";
      const otherVal = other === "A" ? "A" : other;
      // Soft hand key: A + other card value
      if (otherVal !== "A") {
        return { type: "soft", key: `A${otherVal}`, total };
      }
    }
  }

  return { type: "hard", key: String(total), total };
}

function lookupAction(deckType: string, hand: { type: string; key: string }, dealerUp: string): string | null {
  const deck = STRATEGY[deckType];
  if (!deck) return null;

  const dealer = normalizeCard(dealerUp);
  const chart = deck[hand.type as keyof Pick<DeckStrategy, "hard" | "soft" | "pairs">] as Record<string, Record<string, string>> | undefined;
  if (!chart) return null;

  const row = chart[hand.key];
  if (!row) return null;

  return row[dealer] ?? null;
}

function expandAction(code: string): string {
  return ACTION_LEGEND[code] ?? code;
}

function generateExplanation(hand: { type: string; key: string; total: number }, dealerUp: string, actionCode: string, deckType: string): string {
  const dealer = normalizeCard(dealerUp);
  const dealerVal = parseInt(dealer) || (dealer === "A" ? 11 : 10);
  const dealerInBustZone = dealerVal >= 2 && dealerVal <= 6;
  const action = expandAction(actionCode);

  if (actionCode === "SP") {
    if (hand.key === "AA") return "Always split Aces. Two chances at 21 beats a soft 12.";
    if (hand.key === "88") return "Always split 8s. 16 is the worst hand in blackjack -- escape it.";
    if (hand.key === "TT") return "Never split 10s. 20 is too strong to break up.";
    return `Split because each ${hand.key[0]} starts a new hand with better potential than a combined ${hand.total} against dealer ${dealer}.`;
  }
  if (actionCode === "D" || actionCode === "Ds") {
    return `Double down -- you have a strong position (${hand.total}) and the dealer${dealerInBustZone ? " is in the bust zone" : " is vulnerable here"}. Maximize your profit.`;
  }
  if (actionCode === "S") {
    if (hand.total >= 17) return `Stand on ${hand.total}. This is a made hand -- no reason to risk busting.`;
    if (dealerInBustZone) return `Stand and let the dealer bust. Dealer shows ${dealer}, which busts 35-42% of the time.`;
    return `Stand on ${hand.total} against dealer ${dealer}. The risk of busting outweighs the potential gain.`;
  }
  if (actionCode === "H") {
    if (hand.total <= 11) return `Hit with no bust risk. Your ${hand.total} can only improve.`;
    if (!dealerInBustZone) return `Hit because dealer ${dealer} likely has a made hand (17-21). Standing on ${hand.total} loses more often.`;
    return `Hit to try to improve your ${hand.total}.`;
  }
  if (actionCode === "Rh" || actionCode === "Rs") {
    return `Surrender this hand -- ${hand.total} vs dealer ${dealer} is a losing position either way. Surrender saves half your bet. If surrender is not available, ${actionCode === "Rh" ? "hit" : "stand"}.`;
  }
  return `${action} is the mathematically optimal play for ${hand.key} vs dealer ${dealer} in ${deckType} blackjack.`;
}

// --- ANALYZE-HAND: pure chart lookup (FREE, instant, accurate) ---
function handleAnalyzeHand(body: Record<string, unknown>) {
  const { player_cards, dealer_upcard, deck_type, player_action } = body as {
    player_cards?: string[];
    dealer_upcard?: string;
    deck_type?: string;
    player_action?: string;
  };

  if (!player_cards || !Array.isArray(player_cards) || player_cards.length < 2) {
    return json({ error: "player_cards must be an array of at least 2 card strings" }, 400);
  }
  if (!dealer_upcard || typeof dealer_upcard !== "string") {
    return json({ error: "Missing dealer_upcard" }, 400);
  }
  if (!deck_type || !VALID_DECK_TYPES.includes(deck_type)) {
    return json({ error: `Invalid deck_type. Must be one of: ${VALID_DECK_TYPES.join(", ")}` }, 400);
  }
  if (!player_action || typeof player_action !== "string") {
    return json({ error: "Missing player_action" }, 400);
  }

  const hand = classifyHand(player_cards);
  const optimalCode = lookupAction(deck_type, hand, dealer_upcard);

  if (!optimalCode) {
    return json({
      correct: null,
      optimal_play: "unknown",
      explanation: `Could not find chart entry for ${hand.type} ${hand.key} vs ${normalizeCard(dealer_upcard)} in ${deck_type}.`,
      ev_impact: "",
      deck_type,
      player_cards,
      dealer_upcard,
      hand_classification: hand
    });
  }

  const optimalFull = expandAction(optimalCode);

  // Normalize player action for comparison
  const pa = player_action.trim().toLowerCase();
  const actionMap: Record<string, string[]> = {
    "H": ["hit", "h"],
    "S": ["stand", "s", "stay"],
    "D": ["double", "d", "double down", "dd"],
    "Ds": ["double", "d", "double down", "dd"],
    "SP": ["split", "sp", "p"],
    "Rh": ["surrender", "r", "give up", "rh"],
    "Rs": ["surrender", "r", "give up", "rs"]
  };

  const validActions = actionMap[optimalCode] ?? [];
  const isCorrect = validActions.includes(pa);

  // Check if the fallback action matches (e.g., player hit when surrender not available)
  let isFallbackCorrect = false;
  if (!isCorrect) {
    if ((optimalCode === "Rh") && pa === "hit") isFallbackCorrect = true;
    if ((optimalCode === "Rs") && (pa === "stand" || pa === "stay")) isFallbackCorrect = true;
    if ((optimalCode === "D" || optimalCode === "Ds") && (pa === "hit" || pa === "stand")) isFallbackCorrect = true;
  }

  const explanation = generateExplanation(hand, dealer_upcard, optimalCode, deck_type);

  let evNote = "";
  if (isCorrect) {
    evNote = "Optimal play. You're minimizing the house edge.";
  } else if (isFallbackCorrect) {
    evNote = `Acceptable if ${optimalCode === "Rh" || optimalCode === "Rs" ? "surrender" : "doubling"} is not available at this table.`;
  } else {
    evNote = "Suboptimal play. Over time this deviation costs you expected value.";
  }

  return json({
    correct: isCorrect || isFallbackCorrect,
    optimal_play: optimalFull,
    optimal_code: optimalCode,
    explanation,
    ev_impact: evNote,
    deck_type,
    player_cards,
    dealer_upcard,
    hand_classification: { type: hand.type, key: hand.key, total: hand.total }
  });
}

// --- GET-TIP: random static tip (FREE, instant) ---
function handleGetTip(body: Record<string, unknown>) {
  const { deck_type, category } = body as {
    deck_type?: string;
    category?: string;
  };

  if (!deck_type || !VALID_DECK_TYPES.includes(deck_type)) {
    return json({ error: `Invalid deck_type. Must be one of: ${VALID_DECK_TYPES.join(", ")}` }, 400);
  }
  if (!category || !VALID_CATEGORIES.includes(category)) {
    return json({ error: `Invalid category. Must be one of: ${VALID_CATEGORIES.join(", ")}` }, 400);
  }

  const tips = TIPS_DB[category];
  if (!tips || tips.length === 0) {
    return json({ error: "No tips available for this category" }, 500);
  }

  const tip = tips[Math.floor(Math.random() * tips.length)];
  const deck = STRATEGY[deck_type];

  return json({
    tip,
    deck_type,
    category,
    house_edge: deck?.house_edge ?? "unknown",
    rules: deck?.rules ?? null
  });
}

// --- CHART-LOOKUP: direct chart query (FREE, instant) ---
function handleChartLookup(body: Record<string, unknown>) {
  const { deck_type, hand_type, hand_key, dealer_upcard } = body as {
    deck_type?: string;
    hand_type?: string;
    hand_key?: string;
    dealer_upcard?: string;
  };

  if (!deck_type || !VALID_DECK_TYPES.includes(deck_type)) {
    return json({ error: `Invalid deck_type. Must be one of: ${VALID_DECK_TYPES.join(", ")}` }, 400);
  }

  const deck = STRATEGY[deck_type];

  // If no specific hand requested, return the full chart
  if (!hand_type && !hand_key) {
    return json({
      deck_type,
      rules: deck.rules,
      house_edge: deck.house_edge,
      hard: deck.hard,
      soft: deck.soft,
      pairs: deck.pairs,
      action_legend: ACTION_LEGEND
    });
  }

  if (!hand_type || !["hard","soft","pairs"].includes(hand_type)) {
    return json({ error: "hand_type must be one of: hard, soft, pairs" }, 400);
  }

  const chart = deck[hand_type as "hard" | "soft" | "pairs"];

  // Return full chart section
  if (!hand_key) {
    return json({ deck_type, hand_type, chart, action_legend: ACTION_LEGEND });
  }

  const row = chart[hand_key];
  if (!row) {
    return json({ error: `No chart entry for ${hand_type} ${hand_key} in ${deck_type}` }, 404);
  }

  // If dealer specified, return single cell
  if (dealer_upcard) {
    const dealer = normalizeCard(dealer_upcard);
    const action = row[dealer];
    if (!action) {
      return json({ error: `No entry for dealer ${dealer}` }, 404);
    }
    return json({
      deck_type, hand_type, hand_key,
      dealer_upcard: dealer,
      action_code: action,
      action: expandAction(action)
    });
  }

  // Return full row
  const expanded: Record<string, string> = {};
  for (const [k, v] of Object.entries(row)) {
    expanded[k] = `${v} (${expandAction(v)})`;
  }
  return json({ deck_type, hand_type, hand_key, actions: expanded });
}

// --- ASK: freeform via Perplexity Sonar (cheap, conversational, cites sources) ---
const SYSTEM_PROMPT =
  "You are the Everlight Strategy Coach, an expert blackjack instructor. " +
  "You teach basic strategy for single-deck, double-deck, 4-deck, and 6-deck blackjack. " +
  "Be concise (2-4 sentences max), precise, and encouraging. Use casino terminology naturally. " +
  "Reference specific chart positions when relevant. If asked about a specific hand, always state " +
  "the mathematically optimal play and briefly explain why. Keep the luxury casino vibe -- " +
  "you're a high-end private tutor, not a textbook.";

async function callPerplexity(
  systemPrompt: string,
  userMessage: string,
  maxTokens: number,
  temperature = 0.3,
): Promise<{ content: string; citations?: string[]; error?: string }> {
  const apiKey = Deno.env.get("PERPLEXITY_API_KEY");
  if (!apiKey) {
    return { content: "", error: "PERPLEXITY_API_KEY not configured" };
  }

  try {
    const response = await fetch("https://api.perplexity.ai/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "sonar",
        max_tokens: maxTokens,
        temperature,
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userMessage },
        ],
      }),
    });

    if (!response.ok) {
      const errBody = await response.text();
      console.error("Perplexity API error:", response.status, errBody);
      return { content: "", error: `Perplexity API returned ${response.status}` };
    }

    const data = await response.json();
    const text = data.choices?.[0]?.message?.content ?? "";
    const citations = data.citations ?? [];
    return { content: text, citations };
  } catch (err) {
    console.error("Perplexity API fetch error:", err);
    return { content: "", error: err.message ?? "Failed to reach Perplexity API" };
  }
}

async function handleAsk(body: Record<string, unknown>) {
  const { question, deck_type, context } = body as {
    question?: string;
    deck_type?: string;
    context?: string;
  };

  if (!question || typeof question !== "string" || question.trim().length === 0) {
    return json({ error: "Missing or empty 'question' field" }, 400);
  }

  if (!deck_type || !VALID_DECK_TYPES.includes(deck_type)) {
    return json({ error: `Invalid deck_type. Must be one of: ${VALID_DECK_TYPES.join(", ")}` }, 400);
  }

  let userMessage = `[Deck: ${deck_type}]\n\n${question.trim()}`;
  if (context && typeof context === "string" && context.trim().length > 0) {
    userMessage = `[Deck: ${deck_type}]\n[Previous context: ${context.trim()}]\n\n${question.trim()}`;
  }

  const result = await callPerplexity(SYSTEM_PROMPT, userMessage, 300);
  if (result.error) {
    return json({ error: result.error }, 502);
  }

  return json({
    answer: result.content,
    deck_type,
    citations: result.citations ?? [],
    powered_by: "perplexity-sonar"
  });
}

// --- ROUTER ---
Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  if (req.method !== "POST") {
    return json({ error: "Method not allowed. Use POST." }, 405);
  }

  try {
    const body = await req.json();
    const { action } = body;

    if (!action || typeof action !== "string") {
      return json({ error: "Missing or invalid 'action' field" }, 400);
    }

    switch (action) {
      case "ask":
        return await handleAsk(body);
      case "analyze-hand":
        return handleAnalyzeHand(body);
      case "get-tip":
        return handleGetTip(body);
      case "chart-lookup":
        return handleChartLookup(body);
      default:
        return json({
          error: `Unknown action: ${action}. Valid actions: ask, analyze-hand, get-tip, chart-lookup`
        }, 400);
    }
  } catch (err) {
    console.error("strategy-coach error:", err);
    return json({ error: err.message ?? "Internal server error" }, 500);
  }
});
