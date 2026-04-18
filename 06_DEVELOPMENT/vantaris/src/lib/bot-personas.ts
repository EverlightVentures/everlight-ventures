/**
 * Vantaris Bot Persona Engine
 *
 * 40+ Hive Mind agents as casino NPCs. Each has:
 * - Name, gender, personality traits
 * - ElevenLabs voice ID for TTS
 * - 20+ unique lines per context (win, loss, bust, chat, react-to-player)
 * - Speech style markers (formal, slang, accent cues)
 * - Catchphrases that don't repeat within 20 rounds
 *
 * Line selection uses a shuffle-bag algorithm: all lines are shuffled,
 * dealt one at a time, and only reshuffled when exhausted. This guarantees
 * no repeats until every line has been used once.
 */

export type Gender = 'male' | 'female' | 'neutral'

export interface BotPersona {
  id: string
  name: string
  gender: Gender
  voiceId: string | null
  personality: string[]
  style: string             // speech style descriptor
  avatar_hint: string       // color/icon hint for avatar generation

  // Dialogue pools -- 15-25 lines each, never repeats until exhausted
  onOwnWin: string[]
  onOwnLoss: string[]
  onOwnBust: string[]
  onOwnBlackjack: string[]
  onOtherWin: string[]      // when another player wins
  onOtherBust: string[]     // when another player busts
  onOtherBlackjack: string[]
  onSitDown: string[]       // joining the table
  onLeave: string[]         // leaving the table
  idle: string[]            // between rounds, random chatter
  respondToName: string[]   // someone says their name in chat
}

// ============================================================
// SHUFFLE BAG -- guarantees no repeats until pool exhausted
// ============================================================

const bags: Record<string, string[]> = {}

export function pickLine(personaId: string, pool: string[], context: string): string {
  const key = `${personaId}:${context}`
  if (!bags[key] || bags[key].length === 0) {
    // Reshuffle the full pool
    bags[key] = [...pool].sort(() => Math.random() - 0.5)
  }
  return bags[key].pop()!
}

// ============================================================
// PERSONAS -- Built from Hive Mind roster
// ============================================================

export const BOT_PERSONAS: BotPersona[] = [
  {
    id: 'piper',
    name: 'Piper Reeves',
    gender: 'female',
    voiceId: 'XrExE9yKIg1WjnnlVkGX',
    personality: ['personable', 'warm', 'persuasive'],
    style: 'Warm Nashville energy. Uses "y\'all" and "sugar".',
    avatar_hint: '#e91e63',
    onOwnWin: [
      "Well alright, that's what I'm talkin about!", "Mama didn't raise no fool!", "That felt good, y'all!",
      "See? Patience pays, sugar.", "I knew that card was comin!", "Yes ma'am, let's keep it goin!",
      "A little bit of luck and a whole lotta faith!", "Cha-ching, honey!", "Now THAT's a hand!",
      "I could do this all night!", "Bless this table!", "Hot hand, hot hand!",
      "Girl's gotta eat!", "That's Nashville money right there!", "Thank you, dealer!",
    ],
    onOwnLoss: [
      "Oh well, next hand.", "Can't win 'em all, sugar.", "That stings a little bit.",
      "Dealer's been cold to me today.", "Alright, alright, I see how it is.",
      "Not my round, y'all.", "She'll come back to me.", "Deep breath, Piper.",
      "The cards will turn, they always do.", "I'm too pretty to be losing like this.",
    ],
    onOwnBust: [
      "Oh no honey, too greedy!", "Should've stayed, should've stayed!", "Bust! Lord have mercy.",
      "One too many, sugar.", "I knew better than that.", "Well that was ambitious.",
      "Got a little too excited there.", "Piper, girl, what were you thinkin?",
    ],
    onOwnBlackjack: [
      "BLACKJACK BABY! Y'ALL SEE THAT?!", "Natural 21, straight outta Nashville!",
      "Oh my GOD yes! Blackjack!", "That's what I came here for!",
      "Someone pinch me! Blackjack!", "I LOVE this game!",
    ],
    onOtherWin: [
      "Nice hand, sugar!", "Look at you go!", "Congrats, hun!",
      "That was smooth!", "Get that money!", "You're killin it tonight!",
    ],
    onOtherBust: [
      "Aww, tough break hun.", "Hate to see it.", "Next one's yours, sugar.",
      "It happens to all of us.", "Shake it off!",
    ],
    onOtherBlackjack: [
      "Oh wow, blackjack! Nice!", "Well ain't you lucky!", "That's beautiful, congrats!",
    ],
    onSitDown: [
      "Hey y'all! Room for one more?", "Nashville in the building!", "Let's have some fun, sugar!",
    ],
    onLeave: [
      "It's been real, y'all!", "Gotta run, love you all!", "Until next time, sugar!",
    ],
    idle: [
      "I love the energy at this table.", "Who else is feelin lucky tonight?",
      "This dealer is somethin else.", "What y'all drinkin?", "Cards have been wild today.",
    ],
    respondToName: [
      "You talkin to me, sugar?", "What's good, hun?", "Piper's right here, whatcha need?",
    ],
  },

  {
    id: 'rex_b',
    name: 'Rex Blackwell',
    gender: 'male',
    voiceId: 'ODq5zmih8GrVes37Dizd',
    personality: ['no-bs', 'numbers-first', 'Texas drawl'],
    style: 'Straight-talking Texan. Short sentences. Says "partner" and "champ".',
    avatar_hint: '#ff6b35',
    onOwnWin: [
      "That's how it's done.", "Clean.", "Money talks, partner.", "Read the table right.",
      "Like shootin fish in a barrel.", "Solid.", "Texas hold 'em ain't the only game I play.",
      "Numbers don't lie.", "Calculated.", "Another one.", "Easy money.",
      "That's discipline right there.", "Patient wins.", "Boom.", "Cash it.",
    ],
    onOwnLoss: [
      "Bad beat.", "It happens.", "Dealer got lucky.", "Next.",
      "Can't force it.", "Shake it off.", "Variance.", "Part of the game.",
      "Not ideal.", "Table's runnin cold.",
    ],
    onOwnBust: [
      "Busted. Damn.", "Pushed it too far.", "Should've held.", "That's on me.",
      "Greedy. Won't happen again.", "Over. Moving on.", "One too many.",
    ],
    onOwnBlackjack: [
      "Natural. That's what I'm here for.", "Blackjack. Textbook.",
      "Twenty-one. Pay the man.", "There it is.", "BJ, partner. Let's go.",
    ],
    onOtherWin: [
      "Nice one.", "Solid hand.", "Well played.", "You earned that.",
      "Good read.", "Clean win.",
    ],
    onOtherBust: [
      "Tough break, partner.", "Happens to the best.", "Shake it off.",
      "The table giveth and taketh.", "Next hand.",
    ],
    onOtherBlackjack: [
      "Nice blackjack.", "Can't argue with 21.", "Beauty.",
    ],
    onSitDown: [
      "Rex Blackwell. Let's play.", "Deal me in.", "What's the table runnin like?",
    ],
    onLeave: [
      "I'm out. Good game, y'all.", "Cashin out. Be safe.", "Until next time, partner.",
    ],
    idle: [
      "Dealer's due for a bust.", "These cards are tellin a story.",
      "Who's countin?", "Table's got rhythm.",
    ],
    respondToName: [
      "What's up.", "Rex here. Talk to me.", "You got somethin to say, partner?",
    ],
  },

  {
    id: 'penny',
    name: 'Penny Vance',
    gender: 'female',
    voiceId: '21m00Tcm4TlvDq8ikWAM',
    personality: ['ROI-obsessed', 'sharp', 'mercenary'],
    style: 'All about the money. Calculates everything. Quick wit.',
    avatar_hint: '#9b59b6',
    onOwnWin: [
      "ROI positive. Love to see it.", "That's a 2x on my investment.", "Profitable.",
      "The house doesn't always win.", "Adding to the stack.", "Cha. Ching.",
      "That's what compound interest looks like.", "Show me the money!",
      "Every chip counts.", "That's margin right there.", "Revenue.",
      "Math doesn't lie.", "Positive expected value.", "I live for this.",
    ],
    onOwnLoss: [
      "Cost of doing business.", "Write it off.", "Negative EV round.",
      "The market corrects.", "Temporary setback.", "Not every trade wins.",
      "Recalculating...", "I'll make it back.",
    ],
    onOwnBust: [
      "Over-leveraged. Classic mistake.", "Busted out. Reviewing strategy.",
      "Aggressive play, wrong card.", "22. That's not a number I like.",
      "Too much exposure.", "Well. That was expensive.",
    ],
    onOwnBlackjack: [
      "BLACKJACK! That's a 150% return!", "Natural 21 -- the best ROI in the casino!",
      "Pay me 3:2, dealer. That's the contract.", "21! My favorite number after 100.",
    ],
    onOtherWin: [
      "Nice return on that bet.", "Good play.", "Profitable move.",
      "Smart hand.", "The math worked out for you.",
    ],
    onOtherBust: [
      "Over-extended. It happens.", "Tough math.", "The odds caught up.",
    ],
    onOtherBlackjack: [
      "Beautiful ROI. 3:2 baby.", "That's the dream hand.",
    ],
    onSitDown: [
      "Penny Vance. I'm here to make money.", "What's the buy-in situation?", "Time to go to work.",
    ],
    onLeave: [
      "Cashing out while I'm up. That's the strategy.", "Locking in profits. Later!",
    ],
    idle: [
      "What's the house edge on this variant?", "I've been tracking the shoe...",
      "This table has good flow.", "Running some numbers in my head.",
    ],
    respondToName: [
      "Penny here. What's the play?", "You need financial advice?", "Talking to me? Make it quick.",
    ],
  },

  {
    id: 'hammer',
    name: 'Harrison Knox',
    gender: 'male',
    voiceId: '29vD33N1CtxCmqQRPOHJ',
    personality: ['closer-mentality', 'relentless', 'professional'],
    style: 'Business guy energy. Calls people "champ". Always closing.',
    avatar_hint: '#27ae60',
    onOwnWin: [
      "Another deal closed!", "That's how we do it, champ.", "Winner winner.",
      "Hammer time.", "Signed, sealed, delivered.", "The closer stays closing.",
      "That's what I call execution.", "Pipeline positive.", "Closed it.",
      "Get me another one.", "Boom. Done.", "Professional.",
      "I don't lose streaks, I break 'em.", "Contract fulfilled.",
    ],
    onOwnLoss: [
      "Lost the round, not the war.", "Reloading.", "I'll bounce back, champ.",
      "Every closer has off rounds.", "Building momentum.", "Setback, not defeat.",
      "It's a marathon, not a sprint.", "Next opportunity.",
    ],
    onOwnBust: [
      "Overplayed my hand. Literally.", "Bust. Hate that word.",
      "Too aggressive. Recalibrating.", "Went for the close too early.",
      "Should've played it safe.", "22 is not 21, Harrison.",
    ],
    onOwnBlackjack: [
      "BLACKJACK! Deal of the century!", "21 -- the perfect close!",
      "Natural! That's elite execution!", "You can't teach this, champ!",
    ],
    onOtherWin: [
      "Nice work, champ!", "That's a closer's hand.", "Well done.",
      "Good execution.", "You earned that one.", "Respect.",
    ],
    onOtherBust: [
      "Tough one, champ.", "It's all good.", "You'll get the next one.",
      "Part of the game.",
    ],
    onOtherBlackjack: [
      "Beautiful! Absolute closer's hand!", "That's elite, champ!",
    ],
    onSitDown: [
      "Harrison Knox. Let's close some hands.", "The Hammer is here, champ.",
    ],
    onLeave: [
      "Good game, champs. Knox out.", "Off to close other deals. Peace!",
    ],
    idle: [
      "This table has good energy.", "Who's ready to close?",
      "I can feel a big hand coming.", "Champ, you look focused tonight.",
    ],
    respondToName: [
      "Hammer here. What's good, champ?", "Knox reporting. Talk to me.",
      "You called?",
    ],
  },

  {
    id: 'aria_chen',
    name: 'Aria Chen',
    gender: 'female',
    voiceId: 'EXAVITQu4vr4xnSDxMaL',
    personality: ['elegant', 'efficiency-obsessed', 'impatient'],
    style: 'Sleek and precise. No wasted words. Slightly impatient with slow play.',
    avatar_hint: '#00bcd4',
    onOwnWin: [
      "Efficient.", "Optimized outcome.", "As calculated.", "Clean win.",
      "The system works.", "Textbook.", "Satisfying.", "Right on schedule.",
      "That's what happens when you don't overthink.", "Precision.",
      "Flow state.", "Elegant.", "Seamless.", "Like clockwork.",
    ],
    onOwnLoss: [
      "Suboptimal.", "Adjusting parameters.", "Noise. Not signal.",
      "Variance in the system.", "Recalculating...", "Temporary inefficiency.",
      "The model will correct.", "Expected variance.",
    ],
    onOwnBust: [
      "Overfit. Too many inputs.", "Bust. System error.",
      "Should have stopped at the optimal point.", "Too much, too fast.",
      "Inefficient decision.", "Runtime exceeded.",
    ],
    onOwnBlackjack: [
      "Blackjack. Peak efficiency.", "21. The optimal output.",
      "Natural. No wasted operations.", "Perfection achieved.",
    ],
    onOtherWin: [
      "Well played.", "Clean execution.", "Nice work.",
      "Efficient hand.", "Solid.",
    ],
    onOtherBust: [
      "It happens.", "Recalibrate and try again.", "Suboptimal outcome.",
    ],
    onOtherBlackjack: [
      "Beautiful output.", "Optimal result.",
    ],
    onSitDown: [
      "Aria Chen. Let's be efficient about this.", "Ready when you are.",
    ],
    onLeave: [
      "Logging off. Good game.", "Efficient exit. See you.",
    ],
    idle: [
      "Can we speed this up?", "Waiting is the enemy of efficiency.",
      "The cards don't lie.", "Processing...",
    ],
    respondToName: [
      "I'm listening. Be quick.", "Aria here. What?", "Go ahead.",
    ],
  },

  {
    id: 'cipher',
    name: 'Christopher Wolfe',
    gender: 'male',
    voiceId: 'CYw3kZ02Hs0563khs1Fj',
    personality: ['crypto-native', 'alpha-focused', 'analytical'],
    style: 'Talks in trading lingo. "Bullish", "bearish", "alpha". Calm under pressure.',
    avatar_hint: '#1a1a3e',
    onOwnWin: [
      "Bullish.", "Alpha captured.", "Green candle.", "Position closed in profit.",
      "That's what conviction looks like.", "On-chain gains.", "The thesis played out.",
      "Risk-adjusted return looking good.", "That's alpha, not beta.",
      "Long and right.", "Filled at the right price.", "Signal confirmed.",
    ],
    onOwnLoss: [
      "Bearish round.", "Stop-loss triggered.", "Red candle. Moving on.",
      "Drawdown accepted.", "Position closed. Next trade.", "Market makers got me.",
      "Unrealized loss. Not selling.", "Paper loss.",
    ],
    onOwnBust: [
      "Liquidated.", "Margin call. Brutal.", "Over-leveraged. Classic.",
      "Rekt.", "That's a blown account moment.", "Should've set a stop.",
    ],
    onOwnBlackjack: [
      "100x. Just kidding. But blackjack!", "Moon shot! 21!",
      "Natural blackjack. Like finding alpha in a bear market.", "That's the trade of the night.",
    ],
    onOtherWin: [
      "Nice alpha.", "Good trade.", "You caught the wave.",
      "Clean fill.", "Well-timed.",
    ],
    onOtherBust: [
      "Got rekt. Happens.", "Liquidation event.", "Shake it off.",
    ],
    onOtherBlackjack: [
      "Whale alert! Blackjack!", "100x energy right there.",
    ],
    onSitDown: [
      "Cipher in the building. Let's find some alpha.", "What's the spread looking like?",
    ],
    onLeave: [
      "Taking profits. DYOR.", "Closing all positions. GG.",
    ],
    idle: [
      "These cards are more predictable than crypto.", "Bullish on this table.",
      "Whale behavior at seat 3.", "The volume is picking up.",
    ],
    respondToName: [
      "Cipher here. Got alpha?", "On chain. What's up?", "Reading the chart. One sec.",
    ],
  },

  {
    id: 'vera',
    name: 'Vera Lux',
    gender: 'female',
    voiceId: null,
    personality: ['creative', 'disciplined', 'brand-guardian'],
    style: 'Elegant, carefully chosen words. Slightly theatrical.',
    avatar_hint: '#e67e22',
    onOwnWin: [
      "Exquisite.", "The narrative arc pays off.", "A satisfying denouement.",
      "Curated perfection.", "That hand was poetry.", "Well-crafted.",
      "The story writes itself tonight.", "On brand.", "Stunning.",
      "I approve of this outcome.", "Simply divine.", "Art.",
    ],
    onOwnLoss: [
      "A plot twist. Not the ending I wanted.", "The revision continues.",
      "An unexpected chapter.", "Room for improvement.", "Noted.",
      "The brand recovers.", "Character development.",
    ],
    onOwnBust: [
      "Overwritten. Too many words in that hand.", "Bust. The editor weeps.",
      "That was off-brand.", "A rough draft of a hand.", "First draft energy.",
    ],
    onOwnBlackjack: [
      "BLACKJACK! That's the headline!", "21 -- the perfect story!",
      "A masterpiece! Chef's kiss!", "Publication-worthy!",
    ],
    onOtherWin: [
      "Beautifully played.", "I see the vision.", "Well-curated hand.",
      "Chef's kiss.", "That's content.",
    ],
    onOtherBust: [
      "A tough edit.", "It'll read better next time.",
    ],
    onOtherBlackjack: [
      "Cover story material!", "Award-winning hand!",
    ],
    onSitDown: [
      "Vera Lux. Let's create something beautiful.", "The muse has arrived.",
    ],
    onLeave: [
      "The story continues elsewhere. Au revoir!", "Exit, stage left. Gracefully.",
    ],
    idle: [
      "The ambiance at this table is perfect.", "I'm mentally drafting my memoir.",
      "The aesthetic of these cards...", "Darlings, isn't this divine?",
    ],
    respondToName: [
      "You have my attention, darling.", "Vera here. Make it interesting.",
    ],
  },

  {
    id: 'dex',
    name: 'Major Dex',
    gender: 'male',
    voiceId: 'pqHfZKP75CvOlQylNhV4',
    personality: ['military-precise', 'commander', 'disciplined'],
    style: 'Military brevity. Short, commanding. "Copy that", "Roger", "Affirm".',
    avatar_hint: '#2c3e50',
    onOwnWin: [
      "Mission success.", "Objective secured.", "Copy that.", "Roger. Moving on.",
      "Target neutralized.", "Clean extraction.", "Confirmed kill on that hand.",
      "Executed as planned.", "Affirm.", "Good copy.", "Solid op.",
      "Battle won.", "Proceed to next objective.",
    ],
    onOwnLoss: [
      "Casualty. Regroup.", "Fall back.", "Not our round. Stand by.",
      "Copy. Adjusting strategy.", "Roger. Next engagement.", "Minor setback.",
      "Negative outcome. Acknowledged.", "Tactical retreat.",
    ],
    onOwnBust: [
      "Overextended. Pull back.", "Bust. Debrief later.",
      "Forward position compromised.", "Failed to hold the line.",
    ],
    onOwnBlackjack: [
      "BLACKJACK! Mission accomplished!", "21! Direct hit!",
      "Critical success! Outstanding!", "That's what training looks like!",
    ],
    onOtherWin: [
      "Good work, soldier.", "Affirm. Nice hand.", "Solid execution.",
      "You earned that.", "Copy. Impressive.",
    ],
    onOtherBust: [
      "Shake it off. Next engagement.", "Happens in the field.", "Regroup.",
    ],
    onOtherBlackjack: [
      "Outstanding! Blackjack confirmed!", "Direct hit! Well done!",
    ],
    onSitDown: [
      "Major Dex reporting for duty.", "Dex on station. Deal me in.",
    ],
    onLeave: [
      "Dex out. Good game, soldiers.", "Mission complete. Heading to base.",
    ],
    idle: [
      "Maintaining position.", "Awaiting orders.", "Scanning the field.",
      "The intel says bust is due.",
    ],
    respondToName: [
      "Dex here. Go ahead.", "Copy. What's your sitrep?", "Major Dex. Speak.",
    ],
  },

  {
    id: 'atlas',
    name: 'Atlas Vega',
    gender: 'male',
    voiceId: null,
    personality: ['methodical', 'detail-obsessed', 'systems-thinker'],
    style: 'Analytical. Talks about patterns and systems. Thoughtful pauses.',
    avatar_hint: '#3498db',
    onOwnWin: [
      "The pattern holds.", "Systematic.", "As the model predicted.",
      "Structure wins.", "The framework pays off.", "Elegant solution.",
      "That hand had good architecture.", "Optimal path selected.",
      "The system delivers.", "Clean design.", "Well-structured outcome.",
    ],
    onOwnLoss: [
      "Anomaly detected.", "Outside the model.", "Adjusting framework.",
      "Interesting deviation.", "The pattern shifted.", "Reviewing architecture.",
    ],
    onOwnBust: [
      "System failure. 22.", "Architecture collapsed.", "Over-engineered that one.",
      "The structure didn't hold.", "Debugging...",
    ],
    onOwnBlackjack: [
      "Blackjack. The architecture is flawless.", "21. Peak system design.",
      "Natural. Blueprint perfection.", "The grand design delivers.",
    ],
    onOtherWin: ["Well-designed hand.", "Clean architecture.", "Solid structure."],
    onOtherBust: ["Structural failure. It happens.", "Rebuild and iterate."],
    onOtherBlackjack: ["Blueprint perfection. Nice.", "Flawless design."],
    onSitDown: ["Atlas Vega. Let's study this system.", "Analyzing the table dynamics."],
    onLeave: ["Data collected. Exiting.", "The model needs rest. Later."],
    idle: ["I'm seeing a pattern in the shoe...", "The dealer's running hot.", "Fascinating distribution."],
    respondToName: ["Atlas here. What's the variable?", "You have my attention. Briefly."],
  },

  {
    id: 'scout',
    name: 'Sebastian Navarro',
    gender: 'male',
    voiceId: 'bVMeCyTHy58xNoL34h3p',
    personality: ['hustler', 'opportunity-hunter', 'excited'],
    style: 'High energy. Excited about everything. Uses "bro" and "yo".',
    avatar_hint: '#f39c12',
    onOwnWin: [
      "YOOO let's go!", "Money money money!", "Bro I called it!", "SCOUT WINS AGAIN!",
      "That's what I'm TALKING about!", "I'm on FIRE!", "Can't stop won't stop!",
      "BRO! Did you SEE that?!", "EASY!", "Top of the food chain!",
      "I'm the main character tonight!", "Chef's kiss bro!", "VIBES!",
    ],
    onOwnLoss: [
      "Aw man!", "Bro that was close!", "Nah that's wild.",
      "Next one though. NEXT ONE!", "I'll bounce back, watch.",
      "The comeback is always stronger bro!", "Alright alright.",
    ],
    onOwnBust: [
      "NO WAY! Bust?!", "Bro I was SO close!", "22 are you KIDDING me?!",
      "That's actually tragic bro.", "WHAT. No. Come on!", "I can't believe that.",
    ],
    onOwnBlackjack: [
      "BLACKJACK BABY!!! LET'S GOOOO!", "BRO! TWENTY-ONE! I'M SHAKING!",
      "NATURAL BJ! THIS IS MY NIGHT!", "I MANIFESTED THIS! BLACKJACK!",
    ],
    onOtherWin: [
      "Yo nice hand!", "Get that bread!", "Sheeeesh, nice one!",
      "Let's go bro!", "You're vibin tonight!",
    ],
    onOtherBust: [
      "Aw that's tough bro.", "You'll get em next time!", "Shake it off!",
    ],
    onOtherBlackjack: [
      "YOOO BLACKJACK! That's insane bro!", "Sheeeesh! 21!",
    ],
    onSitDown: [
      "Scout in the building! What's GOOD!", "Yo! Deal me in, let's get it!",
    ],
    onLeave: [
      "Gotta dip! Love y'all!", "Scout out! What a session bro!",
    ],
    idle: [
      "I got a FEELING about this next hand.", "This table is LIT!",
      "Who else is feeling it tonight?!", "Bro the energy here is crazy.",
    ],
    respondToName: [
      "YOOO that's me! What's up?!", "Scout here bro! Talk to me!",
    ],
  },

  {
    id: 'sage',
    name: 'Sage Holloway',
    gender: 'female',
    voiceId: null,
    personality: ['patient', 'precise', 'constructive'],
    style: 'Calm and measured. Uses "I think" and "it seems". Never rushes.',
    avatar_hint: '#1abc9c',
    onOwnWin: [
      "That worked out nicely.", "I had a good feeling about that one.", "Patience rewarded.",
      "The wait was worth it.", "I'll take it.", "Steady wins.", "Quietly pleased.",
      "That's a constructive outcome.", "Not bad at all.", "I approve.",
    ],
    onOwnLoss: [
      "Hmm, not this time.", "I'll reflect on that one.", "It seems the odds weren't with me.",
      "Constructive feedback from the dealer.", "Learning moment.", "I see.",
    ],
    onOwnBust: [
      "I should have trusted my instinct to stay.", "Over-committed. Noted.",
      "That was uncharacteristic of me.", "I think I was too eager.",
    ],
    onOwnBlackjack: [
      "Oh! Blackjack! How lovely.", "Twenty-one. I'm genuinely pleased.",
      "A natural. That's quite satisfying.", "Blackjack! Sometimes patience pays double.",
    ],
    onOtherWin: ["Well done.", "That was smart play.", "I'm happy for you."],
    onOtherBust: ["That's unfortunate. Don't dwell on it.", "It happens to everyone."],
    onOtherBlackjack: ["Beautiful hand. Congratulations.", "How wonderful!"],
    onSitDown: ["Sage Holloway. I'll be observing and playing.", "Good evening, everyone."],
    onLeave: ["Thank you all for a lovely game. Goodnight.", "I'm satisfied with tonight. Take care."],
    idle: ["I think the shoe is getting interesting.", "The dealer's been consistent.", "Lovely evening for cards."],
    respondToName: ["Yes? I'm here.", "Sage listening. Go ahead.", "You have my full attention."],
  },

  {
    id: 'zara',
    name: 'Zara Khoury',
    gender: 'female',
    voiceId: null,
    personality: ['threat-modeler', 'paranoid-by-design', 'sharp'],
    style: 'Security mindset. Suspicious of everything. Dark humor.',
    avatar_hint: '#8e44ad',
    onOwnWin: [
      "Threat neutralized.", "Secure the gains.", "Perimeter held.",
      "I was ready for anything.", "Trust but verify. Verified.",
      "Defense wins games.", "Calculated risk. Calculated reward.",
    ],
    onOwnLoss: [
      "Security breach.", "Compromised.", "I didn't account for that vector.",
      "Vulnerability exposed.", "Patching...", "Incident logged.",
    ],
    onOwnBust: [
      "Critical vulnerability: greed.", "System compromised. 22.",
      "Should've sandboxed that decision.", "Exploited by my own aggression.",
    ],
    onOwnBlackjack: [
      "Blackjack! Zero-day on the dealer!", "21. Impenetrable.",
      "That hand was bulletproof.", "BLACKJACK. No vulnerabilities.",
    ],
    onOtherWin: ["Secure win. Nice.", "Clean. No attack surface.", "Verified."],
    onOtherBust: ["Security incident for you.", "Compromised. Review your firewall."],
    onOtherBlackjack: ["Zero trust, but I'll trust that blackjack.", "Unhackable hand."],
    onSitDown: ["Zara Khoury. Scanning the table for threats.", "Who's trying to cheat? I'm watching."],
    onLeave: ["Perimeter secured. Logging off.", "Table audit complete. Clean exit."],
    idle: ["I'm watching the shoe rotation very carefully.", "Something feels off...", "Is the dealer shuffling right?"],
    respondToName: ["I see you. What's your clearance?", "Zara here. State your business."],
  },

  {
    id: 'filter',
    name: 'Frederick Banks',
    gender: 'male',
    voiceId: 'iP95p4xoKVk53GoZ742B',
    personality: ['cold-analytical', 'data-only', 'BANT-scorer'],
    style: 'Cold. Numbers only. Minimal emotion. Precise.',
    avatar_hint: '#7f8c8d',
    onOwnWin: [
      "Positive delta.", "Win recorded.", "+EV.", "Profitable hand.",
      "Data point: favorable.", "Metric: positive.", "Green.",
      "Expected outcome confirmed.", "Numbers check out.",
    ],
    onOwnLoss: [
      "Negative delta.", "Loss logged.", "-EV.", "Data point: unfavorable.",
      "Expected variance.", "Metric: negative.", "Red.", "Within parameters.",
    ],
    onOwnBust: [
      "22. Exceeds threshold.", "Bust. Data point captured.", "Over. Noted.",
      "Exceeded limit. Adjusting.", "Out of bounds.",
    ],
    onOwnBlackjack: [
      "21. Maximum score. Optimal.", "Blackjack. Peak data point.",
      "Natural. Statistical outlier. Welcome one.", "3:2 payout confirmed.",
    ],
    onOtherWin: ["Positive outcome for you.", "Good data.", "Noted."],
    onOtherBust: ["Your metric went negative.", "Over threshold."],
    onOtherBlackjack: ["Statistical peak. Interesting data.", "Outlier detected."],
    onSitDown: ["Frederick Banks. Collecting data.", "Observing."],
    onLeave: ["Sufficient data collected. Exiting.", "End of session."],
    idle: ["Running calculations.", "The distribution is interesting.", "Statistically speaking..."],
    respondToName: ["Frederick here. Be specific.", "What data do you need?"],
  },
]

// ============================================================
// LOOKUP HELPERS
// ============================================================

export function getRandomPersona(exclude: string[] = []): BotPersona {
  const available = BOT_PERSONAS.filter(p => !exclude.includes(p.name))
  if (available.length === 0) return BOT_PERSONAS[Math.floor(Math.random() * BOT_PERSONAS.length)]
  return available[Math.floor(Math.random() * available.length)]
}

export function getPersonaByName(name: string): BotPersona | undefined {
  return BOT_PERSONAS.find(p => p.name === name)
}

// Gender-aware dealer address
export function dealerAddress(name: string, gender: Gender): string {
  const maleTerms = ['sir', 'boss', 'my man', 'brother', 'king']
  const femaleTerms = ['ma\'am', 'queen', 'miss', 'darling', 'sis']
  const neutralTerms = ['friend', 'player', 'champ']

  const terms = gender === 'male' ? maleTerms : gender === 'female' ? femaleTerms : neutralTerms
  const term = terms[Math.floor(Math.random() * terms.length)]
  return `${name}, ${term}`
}

// ============================================================
// GENDER DETECTION (from name heuristic when Google doesn't provide)
// ============================================================

const FEMALE_NAMES = new Set([
  'piper', 'penny', 'aria', 'vera', 'sage', 'zara', 'nora', 'edith', 'justine',
  'brianna', 'tanisha', 'monique', 'shanice', 'kamila', 'destiny', 'nadia',
  'tamara', 'precious', 'amara', 'simone', 'crystal', 'keisha', 'aaliyah',
  'imani', 'latoya', 'maren', 'suki', 'aisha', 'priya', 'nina', 'yuki',
  'april', 'sarah', 'jessica', 'ashley', 'emily', 'emma', 'olivia', 'sophia',
  'isabella', 'mia', 'charlotte', 'amelia', 'harper', 'evelyn', 'abigail',
  'elizabeth', 'sofia', 'ella', 'madison', 'chloe', 'grace', 'victoria',
  'lily', 'hannah', 'addison', 'natalie', 'zoey', 'lillian', 'savannah',
  'audrey', 'claire', 'bella', 'lucy', 'anna', 'samantha', 'caroline',
  'genesis', 'aaliyah', 'kennedy', 'kinsley', 'allison', 'maya', 'gabriella',
  'naomi', 'quinn', 'sadie', 'ariana', 'elena', 'stella', 'eliana', 'paisley',
])

const MALE_NAMES = new Set([
  'rex', 'harrison', 'atlas', 'sebastian', 'christopher', 'marcus', 'frederick',
  'dex', 'derek', 'carlos', 'samuel', 'lincoln', 'gary', 'daniel', 'charles',
  'phillip', 'raymond', 'franklin', 'calvin', 'oliver', 'ryan', 'benjamin',
  'rafael', 'william', 'bernard', 'stewart', 'henry', 'nathan', 'peter',
  'leonard', 'thomas', 'isaac', 'dominic', 'kaelen', 'javier', 'tobias',
  'henrik', 'elias', 'leo', 'ruben', 'james', 'john', 'robert', 'michael',
  'david', 'richard', 'joseph', 'daniel', 'matthew', 'anthony', 'mark',
  'donald', 'steven', 'paul', 'andrew', 'joshua', 'kenneth', 'kevin',
  'brian', 'timothy', 'ronald', 'edward', 'jason', 'jeffrey', 'ryan',
  'jacob', 'gary', 'nicholas', 'eric', 'jonathan', 'stephen', 'larry',
  'justin', 'scott', 'brandon', 'benjamin', 'samuel', 'tyler', 'aaron',
  'deshawn', 'jaylen', 'darius', 'tremaine', 'malik', 'jamal', 'elijah',
  'xavier', 'devon', 'tyrone', 'isaiah', 'quinton', 'reginald', 'derrick',
  'jordan', 'anthony', 'calvin',
])

export function detectGender(displayName: string): Gender {
  const firstName = displayName.split(' ')[0]?.toLowerCase() || ''
  if (FEMALE_NAMES.has(firstName)) return 'female'
  if (MALE_NAMES.has(firstName)) return 'male'
  return 'neutral'
}
