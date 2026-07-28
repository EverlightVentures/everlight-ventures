# Alley Kingz -- The Three-Layer Bond Spec

Operator direction, 2026-07-17, paraphrased (the brand guard blocks his exact word):
*dogs bond with dogs, rigs bond with rigs, and dogs bond with rigs. Multi strategies
and depths.*

You do not build a deck. You build **a deck and a garage**, each has its own internal
chemistry, and then the two cross. That is the double game.

---

## LAYER 1 -- PACK BONDS (dog to dog)

**Status:** planned. Zero art cost, data only.
**Source:** already written. Every one of the 106 books carries a `relationshipTags`
web of allies, rivals, keepers and bosses. The bonds are not invented, they are
extracted.

Each dog carries 2-3 `bondTags`. Matching tags in a deck fire a bond.

| Tag family | Examples | Where it comes from |
|---|---|---|
| Crew | BONEGUARD, SCRAPJAW, NIGHTSHIFT, K-CLUB, ASHLINE, SNAKE EYES, MUTT$, RUST HALO | the 8 crews |
| Arc | JUNKYARD_DYNASTY, CHOPSHOP_SPLIT, CROWN_CITADEL, EVERY_LEASH_BREAKS, BLOCK_WAR, MYTHICS | the 6 timeline arcs |
| Stance | COLLAR_RESISTANT, COLLAR_TOUCHED | who bent and who did not |
| Nature | ALPHA, RUNT, KEEPER, STRAY | the relationship web |
| Blood | breed, for mono-breed decks | 43 breeds |

Example bonds:
- `2x BONEGUARD` -- Home Turf: +10% defense on The Lot
- `3x COLLAR_RESISTANT` -- Break the Chain: when one dies, the others gain damage
- `1x ALPHA + 2x RUNT` -- Pack Mentality: the Alpha hits harder, the Runts survive longer
- `4x same breed` -- Pureblood: all stats up, but the deck is brittle

---

## LAYER 2 -- GARAGE BONDS (rig to rig)  **NEW**

**Status:** the pass that follows the rig bible. Cannot be authored until all 20 rigs
have a personality, because a garage bond is a relationship between two characters,
not two stat blocks.

Rigs are not equipment. They are the second cast. So they have opinions about each
other. A convoy is a social unit.

| Bond shape | Example | Reads as |
|---|---|---|
| Matched family | `3x muscle` -- **The Wall**: the convoy denies a lane outright | a rolling barricade |
| Matched family | `2x sport` -- **Slipstream**: the trailing rig drafts the leader, gains speed | street racing |
| Cross family | `1x van + 1x monster` -- **Spotter**: the van paints, the turret reaches further | forward observer |
| Cross family | `2x van` -- **Relay**: EMP range compounds, they bounce signal between dishes | signal warfare |
| Cross family | `1x monster + 1x muscle` -- **Siege Train**: the plow clears, the gun follows | armored column |
| Full set | `4 families in one garage` -- **Chop Shop Special**: a small bonus to everything | a real crew |
| Rivalry | two rigs whose stories put them on opposite sides of the Chopshop Split | a bond that FIGHTS itself, a real cost |

**The rivalry case matters.** If rigs have pride and history, some of them should refuse
to ride together. A garage that is all winners is a garage with no drama.

---

## LAYER 3 -- THE PAIRING (dog to rig)

**Status:** in the rig bible workflow now.

4 dog classes x 4 rig families = 16 builds. The diagonal is the signature pairing the
roster already implies; the other twelve are why players keep playing.

- **Signature** (matched): max the rig's specialty. Lore pays out as a stat.
- **Off-class** (crossed): a real build with a real tradeoff, never a punishment.
  A bruiser in a sport chassis closes distance fast and sheds plate to do it.

The rig also **re-roles the dog**: chassis family decides where the dog stands in the
lane. That is how you re-role a card you already own without buying anything.

---

## THE MULTIPLICATION

```
106 dogs  x  20 rigs  =  2,120 pairings
          x  3 bond layers firing at once
          =  the depth
```

A player picks 11 dogs, picks their rigs, and now has to solve three puzzles that talk
to each other: which dogs bond, which rigs ride together, and which dog belongs in
which seat. Change one card and all three layers shift.

**Zero of this needs art.** It is data and design on top of a roster that already
exists. The meshes make it look good. The bonds make it a game.

---

## RIG SCHEMA ADDITION (for the bonds pass)

```
rigBonds: [
  { with:   "<rig id, family, or tag>",
    name:   "<the bond's name>",
    effect: "<what fires>",
    kind:   "ally" | "rivalry",
    why:    "<the story reason these two ride together, or refuse to>" }
]
```

`why` is required. A bond without a story reason is a spreadsheet, and the whole point
of the rig layer is that these are characters who take pride in the fight.
