# $BCARDD Discord -- Setup + Run Guide

**For:** Rich's buddy running the server. Zero crypto-genius required. Follow this top to bottom.
**Voice:** dog energy, plain English, hype but real. Never promise anyone money.

> **Disclaimer (paste this anywhere $BCARDD is described -- bio, #rules, pinned posts):**
> "$BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited. Not financial advice."

---

## 1. Server name + description

**Server name:** `$BCARDD -- The Dog`

**Short description (the "About" blurb, under server settings):**
"Home of $BCARDD, the realest dog in crypto. He's got his own blackjack dealer. Memes, raids, and the squad live here. $BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited. Not financial advice."

**Server icon:** the 512x512 logo (`bcardi_logo_512.png` from the launch assets).

---

## 2. Channels (build these in order, top to bottom)

Group them under two category headers so the server reads clean.

### Category: INFO
| Channel | Type | One-line charter |
|---|---|---|
| `#announcements` | read-only (only mods post) | Official drops only -- launch, contract address, airdrops, big news. Nobody else types here. |
| `#rules` | read-only | The house rules + the disclaimer. Pinned, never changes without Rich's say-so. |
| `#how-to-buy` | read-only-ish (mods post the guide, pin it) | Dead-simple steps: get Phantom, get SOL, buy on pump.fun. Always shows the REAL contract address. |

### Category: COMMUNITY
| Channel | Type | One-line charter |
|---|---|---|
| `#general` | open chat | Main hangout -- talk dog, talk life, welcome the new folks. |
| `#price-chat` | open chat | Charts, market talk, "wen moon" energy. Keep the price hype OUT of #general so #general stays chill. |
| `#memes` | open chat | Bacardi memes, dog pics, dealer GIFs. The fuel of the whole thing. |
| `#raids` | open chat | Raid HQ -- mods drop the tweet/post link, squad goes and likes/retweets/comments. |
| `#holders-only` | locked, token-gated LATER | Verified holders only. Alpha, first looks, special airdrops. Stays empty/locked until the gating bot is set up post-launch (see section 8). |

Keep it to these 8. A server with 30 dead channels looks like a ghost town. Add more only when chat is overflowing.

---

## 3. Roles

Set up under Server Settings -> Roles. Give each a color so they pop in chat.

| Role | Color | Who gets it | What it does |
|---|---|---|---|
| `@holder` | gold | Anyone who proves they hold $BCARDD (auto-assigned by the gating bot later) | Unlocks `#holders-only`. The status role. |
| `@og` | purple | Day-one crew, early blackjack players, first 100 in the door | Bragging rights + first dibs on OG airdrops. Hand out by hand early on. |
| `@mod` | red | Trusted people who help you run the place | Can delete messages, ban, post in read-only channels, kick scammers. Give this to as few people as possible. |
| `@raider` | green | Anyone who shows up for raids regularly | Pinged when a raid drops. Opt-in -- let people self-assign with a reaction. |

**Mod power = trust.** Only hand `@mod` to people you'd give your house keys to. A bad mod can wreck the whole server in 5 minutes.

---

## 4. Welcome-bot message

Set this as the auto-message new members get (use Carl-bot, MEE6, or Discord's built-in welcome screen). Drop it in `#general` or a `#welcome` greeting.

```
GM and welcome to the $BCARDD pack 🐶

You found the realest dog in crypto. This is Bacardi -- a real dog with his own blackjack dealer and his own coin on Solana.

Start here:
1. Read #rules (30 seconds, do it).
2. Want in? #how-to-buy has the dead-simple steps + the ONLY real contract address.
3. Drop a dog pic in #memes so we know you're one of us.
4. Hang in #general. Raids run out of #raids -- jump in and we eat together.

House rule #1: we NEVER DM first. Anybody who DMs you "support" or a "deal" is a scammer. Report them.

$BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited. Not financial advice. We're here for the dog and the fun -- nobody here promises you money.

Now go say hi. 🃏
```

---

## 5. #rules channel text (pin this)

```
$BCARDD HOUSE RULES 🐶

1. Be cool. No racism, no hate, no harassment. Instant ban.
2. We NEVER DM first. Ever. If "a mod" or "support" DMs you, it's a scammer -- screenshot it in #general and we ban them.
3. ONE real contract address. It lives in #announcements and #how-to-buy and nowhere else. Anybody posting a different "CA" is trying to rob you.
4. No impersonators. If someone copies a mod or Rich's name/pic, report it -- we ban on sight.
5. No spamming other coins, no random links, no "send 1 get 2 back" scams.
6. Keep price talk in #price-chat. Keep memes in #memes. Keep #general chill.
7. Have fun. This is a dog meme coin with a blackjack table behind it. We hype the dog, not "get rich."

$BCARDD is a community meme coin inspired by Bacardi the dog. Not affiliated with Bacardi Limited. Not financial advice.
```

---

## 6. Moderator playbook (for the buddy)

### Anti-scam -- the stuff that keeps people from getting robbed
This is the #1 job. In a crypto server, scammers WILL show up the second there's hype. Drill these:

- **No first-DMs, ever.** You and every mod publicly say "we never DM first." Pin it. Repeat it weekly. Real support happens in public channels.
- **One contract address (CA).** The real CA lives ONLY in #announcements + #how-to-buy, posted by a mod. If anyone drops a different CA anywhere, delete it and ban -- that is a wallet-drainer link. Never post the CA yourself until Rich confirms it's the real one on launch day.
- **Ban impersonators on sight.** Scammers copy a mod's name + profile pic and DM members pretending to "help." When you see a clone of you, Rich, or any mod -- ban immediately, then post a heads-up in #general: "Heads up, someone's impersonating [name]. We never DM first. Block + report."
- **Lock the panic moments.** Right after launch and during any price spike is when scams flood in. Turn on slow-mode in #general (5-10s) and watch new joins.
- **Kill the fake links.** No "claim your airdrop here," no "connect your wallet to verify," no Google-form drainers. Real airdrops come ONLY from #announcements by Rich/mods.
- **New accounts = watch closely.** Discord accounts made days ago that immediately shill or DM = boot them.

### Daily cadence -- keep the room alive
A dead server kills a coin. Aim for a heartbeat every day:

- **Morning:** drop a "GM pack 🐶" in #general with a Bacardi pic or meme. Sets the tone.
- **Midday raid (the big one):** post the target in #raids -- usually the latest $BCARDD tweet or a post to reply to. Ping `@raider`. Format: "RAID 🚨 like + retweet + drop a 🐶 in the replies: [link]. Let's go." Run 1-2 a day, more on launch day.
- **Afternoon hype:** share a win -- new holder count, a funny meme someone made, a chart moment (in #price-chat). Real, never "we're going to $1." Celebrate the community, not promised gains.
- **Evening:** thank the memers, shout out the best meme of the day, welcome the new faces by name.
- **Always:** answer #how-to-buy questions fast and friendly. A confused newcomer who gets helped becomes a holder.

**Raid rules:** keep it legit -- like, retweet, genuine comments, dog emojis. No bots, no spam-botting (gets the account and the coin flagged). Quality engagement from real people beats fake numbers.

### Escalation -- ping Rich when:
Send Rich a DM (or tag him in a private mod channel) for any of these. Don't sit on them.

- **Anything about the contract / launch / money mechanics** -- if you're unsure whether a CA or claim is real, STOP and ask Rich before posting. Never guess on money.
- **A scam wave or coordinated raid against us** -- multiple impersonators or drainer links at once. Lock channels, then ping Rich.
- **A mod goes rogue** or you suspect a mod account got hacked (mass deletes, weird bans, posting links).
- **Anything legal-sounding** -- someone claiming "Bacardi the company" sent a notice, or a member threatening legal action. Do NOT reply. Screenshot, send to Rich.
- **Big press / influencer** wants to talk, or a partnership offer lands in the server.
- **Server-down / Discord outage** affecting announcements during launch or an airdrop.

Rule of thumb: **if it touches the contract, the money, the law, or could hurt the community -- ping Rich first, act second.** Everything else (memes, raids, day-to-day chat) you run yourself.

---

## 7. Bots to install (free, no coding)

| Bot | Job | When |
|---|---|---|
| **Carl-bot** or **MEE6** | Welcome message, auto-roles by reaction (let people grab `@raider` themselves), basic auto-mod (block invite links + spam) | Before launch |
| **Wick** or **Discord AutoMod** (built-in) | Catch raid-bots, scam links, mass-join floods | Before launch |
| Collab.Land or Vulcan (see below) | Token-gating for `@holder` + `#holders-only` | Post-launch only |

Built-in Discord AutoMod (Server Settings -> AutoMod) is free and catches a lot -- turn on the spam + mention-spam + link filters on day one.

---

## 8. Token-gating #holders-only (POST-LAUNCH, not now)

`#holders-only` and the `@holder` role stay locked until $BCARDD is live and has a real contract address. You CANNOT gate by a token that doesn't exist yet.

**After launch, set it up with one of these (both have free tiers):**
- **Collab.Land** -- the standard. Supports Solana SPL tokens (which $BCARDD is). Member connects their Phantom wallet, the bot checks they hold $BCARDD, auto-grants `@holder`, which unlocks `#holders-only`. Re-checks on a schedule so sellers lose the role.
- **Vulcan** -- alternative, also does Solana gating + holder roles.

**Setup (do this with Rich the day after launch, once the CA is final):**
1. Invite the bot to the server.
2. Give it the real $BCARDD contract address.
3. Set the minimum hold amount (e.g. "hold any $BCARDD" or "hold X to enter").
4. Point it at the `@holder` role and the `#holders-only` channel.
5. Test it with your own wallet before announcing.

Until that's done: leave `#holders-only` hidden/locked so nobody thinks it's broken.

---

## 9. Quick launch-day checklist for the buddy

- [ ] Server built: all 8 channels + 4 roles + colors set.
- [ ] Disclaimer pinned in #rules and in the server description.
- [ ] Welcome bot live (Carl-bot/MEE6).
- [ ] AutoMod on (spam + link filters).
- [ ] At least 2 trusted mods set, briefed on the anti-scam rules.
- [ ] #announcements + #how-to-buy locked to mods only.
- [ ] **Do NOT post the contract address until Rich confirms the real one.**
- [ ] Token-gating bot = scheduled for the day AFTER launch, with Rich.

---

*Built 2026-06-02 for the $BCARDD relaunch. Pairs with the launch plan + spec in `00_Core/`. The coin is the dog. The dog is the brand. We hype the dog -- never the money.*
