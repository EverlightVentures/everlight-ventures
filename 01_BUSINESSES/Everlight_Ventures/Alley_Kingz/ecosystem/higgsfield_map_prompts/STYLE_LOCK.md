# GLOBAL STYLE LOCK
## Prepend / append to EVERY prompt in this folder

Keeping one style lock across all 9 districts is what makes them read as one city
instead of nine unrelated images. Do not vary it per district. Vary only the
district-specific body text.

---

## STYLE PREFIX (prepend to every prompt)

```
Gritty gold-cyberpunk dog-city aesthetic, cinematic, 35mm film, anamorphic,
film grain, volumetric haze, practical light sources only, lived-in and weathered,
every surface has history
```

## NEGATIVE PROMPT (append to every prompt)

```
no cartoon, no anime, no clean CGI, no bright cheerful colors, no glossy render,
no stock-photo lighting, no humans, no text overlays, no watermarks
```

Note: "no humans" matters. This is a dog city. Human figures are an instant tell.

---

## CAMERA VOCABULARY (Higgsfield responds to explicit movement)

Always name the move. Never leave it implied.

| Move | Use for |
|---|---|
| `dolly push-in` | establishing a district's centerpiece building |
| `tracking shot` | walking a street, showing depth |
| `drone rising / pull-back` | scale reveals, skyline, full-grid shots |
| `handheld` | documentary grit, chase energy, stray POV |
| `static locked-off` | atmospheric loops, dread, surveillance feel |
| `slow descent` | going underground (Undercity only) |
| `steadicam walk` | the Strip, casino floor, crowd movement |

## LIGHTING VOCABULARY

Higgsfield responds strongly to: `volumetric`, `neon`, `fire-lit`, `golden hour`,
`cold clinical`, `sodium vapor`, `emergency red`, `bioluminescent`.

## DURATION

- Trailer beats: 4-5 seconds per prompt
- Atmospheric loops: 10 seconds
- Master/city shots: 8-10 seconds

## PER-DISTRICT COLOR DISCIPLINE

Each district's ambient light is its faction color from karma.js. This is the single
biggest consistency lever. A viewer should know which city they are in from a
one-frame glance:

| District | Ambient light color |
|---|---|
| THE LOT | warm gold `#e8c55a`, sodium vapor |
| DOWNTOWN | magenta `#FF2E88` |
| NEON HEIGHTS | teal `#00E0C0`, cold white |
| THE YARDS | rust `#C9772E`, amber |
| FACTORY ROW | rust `#C9772E`, forge orange |
| THE STRIP | magenta `#FF2E88`, excessive |
| THE DOCKS | violet `#7B5CFF`, cold |
| THE OVERLOOK | teal `#00E0C0`, harsh security white |
| THE UNDERCITY | violet `#7B5CFF`, emergency red |

## GROUND TYPES (from ZONES, keep the surface consistent)

- `uptown` -- THE LOT
- `midtown` -- DOWNTOWN, NEON HEIGHTS, THE OVERLOOK, THE UNDERCITY
- `docks` -- THE YARDS, FACTORY ROW, THE STRIP, THE DOCKS
