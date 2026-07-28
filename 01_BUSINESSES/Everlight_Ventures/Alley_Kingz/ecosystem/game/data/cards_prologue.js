/* AK-PROLOGUE: THE BLOCK cold open (bible 11.1) -- AK_STORIES['0000'].
   The first-run comic sequence that replaces the cold generic boot: night
   rooftops, a massive silhouette that eats a name off a wall, witnesses
   whispering, the handlers convening at THE KENNEL, and the promise --
   "Every pup picks a path. Yours starts tomorrow."
   CANON LAW: the thing on the rooftops is NEVER named on any page or panel
   (players piece it together across issue runs; the Section 8 Payoff
   Register carries the scheduled reveal). The Dealer obeys the tease law:
   edge of panel, face out of frame, never named on-panel beyond the chip.
   DATA CONTRACT: the hub lane's cold open consumes AK_STORIES['0000'] via
   the normal AK_CHRONICLES reader -- this file is a pure data sidecar and
   coordinates with the hub through that key ONLY. All 5 beats unlock
   'free' (a first-run player owns nothing yet; the cold open must read).
   SELF-REGISTERING: load order does not matter. If AK_STORIES already
   exists (cards_stories.js loaded first) the entry is appended in place;
   otherwise registration retries on DOMContentLoaded + a same-tick timer.
   window.AK_PROLOGUE always carries the entry directly as a fallback.
   Plain JS, headless-safe, window-guarded.
   NO em-dashes anywhere in this file (hook law); use -- instead. */
(function (global) {

  // Global style lock (bible 5.2) -- prepended to every panel prompt.
  // Mirrors data/cards_stories.js STYLE byte for byte.
  var STYLE = "gritty gold-cyberpunk noir comic panel, heavy inks, halftone shadow, hard rim light, Everlight gold accent #e8c55a against ink-black #06060a, wet asphalt reflections, anthropomorphic street dogs, no humans on panel";

  /* ================================================================
     0000 -- THE BLOCK (cold open, bible 11.1 beat 1: mystery before
     choice). Five pages, prepare / strike / relax tempo (bible 8.3),
     every panelPrompt declares a CAMERA (bible 8.5), the silhouette
     never shows a face.
     ================================================================ */
  var PROLOGUE = {
    codename: "THE BLOCK",
    metadata: {
      rarity: null,
      faction: null,
      cls: null,
      familyLine: null,
      district: null,
      timelineTags: ["T1_JUNKYARD_DYNASTY"],
      relationshipTags: [
        { keeper: "Goldie", rel: "witness", note: "Trophy Hall saw the light go out on the skyline and kept the story" },
        { handler: "The Mender", rel: "witness", note: "THE KENNEL convened the night the name came off the wall" }
      ],
      themes: ["mystery before choice", "the name that got eaten", "every pup picks a path"]
    },
    publicHook: "Something walks the rooftops.",
    coreWound: "A name that every dog on the block knew went up a wall in tag paint. By morning it was gone, and nobody remembers whose it was.",
    definingChoice: "The block can pretend it saw nothing, or send its pups out to learn what walks up there. It sends the pups.",
    secretTruth: "The street will not say what it saw. The street will only say what it heard: chewing.",
    beats: [
      {
        key: "rooftops",
        unlock: "free",
        text: "The block sleeps loud. Generators hum, neon buzzes, somewhere a chain-link fence rattles in a wind that is not wind. Up past the last working streetlight, past where the fire escapes stop pretending, the rooftops run black and wet all the way to the skyline. Nothing lives up there. Everybody knows that. So why do the pigeons keep leaving?",
        panelPrompt: STYLE + ", wide establishing camera, night skyline_rooftops stretched to the horizon under a sick yellow moon, antennas and water tanks in hard silhouette, one streetlight dead at the frame's edge, a spooked flock of pigeons bursting off a ledge, no figure visible, dread in the negative space"
      },
      {
        key: "silhouette",
        unlock: "free",
        text: "It comes over the roofline the way a building would, if a building decided to move. Massive. Quiet in a way that big things have no right to be. It stops at the wall where the block's proudest name is tagged ten feet tall in gold paint, leans in slow, and EATS. Paint, brick-dust, letters. When it lifts its head the wall is blank, and the name is nowhere, and the night keeps going like nothing was ever written there.",
        panelPrompt: STYLE + ", low-angle dread camera, high-contrast impact frame, single explosive moment, a MASSIVE dog silhouette pure ink-black with no face and no eyes hunched against a brick wall on skyline_rooftops, jaws closing over a huge gold #e8c55a tag-paint name half devoured mid-letter, paint dripping like light, motion lines, the silhouette bulk blotting out the moon"
      },
      {
        key: "witnesses",
        unlock: "free",
        text: "GOLDIE, TROPHY HALL, after hours: 'Keep your voice down, hon. Little one here saw it too, from the vents over FACTORY ROW. Big as a bus, he says. Didn't bark, didn't growl. Just chewed. And here's the part I'd drink to forget: come sunup, I couldn't tell you whose name that wall used to hold. I POLISHED trophies with that name on them. It's gone out of my head like a tooth. So no, I won't say what walks the rooftops. I'll say what it does. It eats names.'",
        panelPrompt: STYLE + ", over-the-shoulder camera past a trembling small stray pup, warm-lit TROPHY HALL interior in THE LOT after hours, a golden-coated keeper leaning close over the counter with a lantern turned low, gold #e8c55a case lighting on champion trophies, one trophy engraving inexplicably blank, both dogs' posture hushed and hackles half-risen, rain on the window"
      },
      {
        key: "kennel",
        unlock: "free",
        text: "Word moves faster than paws. By midnight THE KENNEL's lamps are lit and the handlers are around the map table, and nobody is joking. The Mender wants the pups counted and the Infirmary stocked. The Tracker has a scent profile with no card for it and hates that. The Shadow says whatever it is, it walks where cameras die. The Rigger wants the rooftop routes wired. The Bruiser just cracks his neck and watches the door. And at the table's far edge, out of the lamplight, a white paw sets one gold chip down on the map. Nobody saw him come in. Nobody ever does.",
        panelPrompt: STYLE + ", wide interior camera, THE KENNEL in THE LOT at midnight, five handler dogs convened around a lamplit map table of the block, a St. Bernard medic with green #7FE3A0 kit glow, a weathered Bloodhound pinning a memo, a lean dark hound in the doorway shadow, a wrench-collared rig dog unrolling schematics, a plated bruiser watching the door, and at the panel's far edge a sixth figure face out of frame showing only a white paw placing a gold #e8c55a chip on the map, Mama Bones' lantern warm in the back doorway"
      },
      {
        key: "path",
        unlock: "free",
        text: "Dawn comes up gold over the wet roofs, the way it always does, like the night never happened. The blank wall catches the first light. Down in THE LOT the handlers step out of THE KENNEL one by one and look at the same skyline you are looking at right now. Something up there eats names. So the block is going to grow some names too heavy to eat. Every pup picks a path. Yours starts tomorrow.",
        panelPrompt: STYLE + ", wide establishing camera at dawn, gold #e8c55a sunrise breaking over the block's skyline from THE LOT, the handlers small in frame stepping from THE KENNEL doorway into the light, the blank brick wall glowing on a far rooftop, a lone small pup silhouette watching from an alley mouth, hopeful gold flooding the ink-black, relax aftermath panel"
      }
    ],
    ambientBarks: {
      streetTalk: [
        "Ask anybody whose name was on that wall. Watch their face do the thing. Nobody's lying. Nobody KNOWS.",
        "Pigeons still won't roost past the last streetlight. Pigeons know something.",
        "Goldie keeps a blank trophy polished now. Says it's reserved. Won't say for what."
      ]
    }
  };

  // Self-registration: append to AK_STORIES when it exists (either order),
  // never clobber an existing '0000', retry on DOMContentLoaded + next tick
  // if cards_stories.js has not landed yet. AK_PROLOGUE is the direct-read
  // fallback so the hub cold open can consume the entry regardless.
  function register() {
    try {
      if (global && global.AK_STORIES) {
        if (!global.AK_STORIES["0000"]) global.AK_STORIES["0000"] = PROLOGUE;
        return true;
      }
    } catch (_) {}
    return false;
  }

  if (global) {
    global.AK_PROLOGUE = PROLOGUE;
    if (!register()) {
      try { if (typeof setTimeout === "function") setTimeout(register, 0); } catch (_) {}
      try {
        if (typeof document !== "undefined" && document.addEventListener) {
          document.addEventListener("DOMContentLoaded", register);
        }
      } catch (_) {}
    }
  }
})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
