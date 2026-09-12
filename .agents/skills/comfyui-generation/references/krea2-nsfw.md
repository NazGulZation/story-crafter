# Krea 2 NSFW Prompting — Emphasis & Batch Evidence

Companion to `krea2-generation.md`: NSFW-specific prompting — adult-age wording,
`(clause:weight)` emphasis/suppression, composition rules derived from explicit-generation
batches, and a minimal template. Base mechanics (API prompt, runner, validation) live in
`krea2-generation.md`; this file assumes them.

> **Verified instance (example).** The batches in §§3–4 ran on one ComfyUI instance
> (RTX 4080 SUPER, portrait latent, `euler`/`beta` cfg `1.0`, negative `""`) at roughly ~10s
> per image at both 10 and 15 steps. Treat timings, file names, and seeds as evidence the
> techniques work, not as requirements. Runner: `../scripts/krea2_generate.py`.

## 1. Age wording: bands, not numbers, no "fictional"

- `fictional` is redundant — the photo-style prompt already frames subjects as generated images.
- Exact ages (`24-year-old`) are unnecessary. Use bands: `young adult woman`, `young adult man`, `adult man`.
- Default pairing is young adult woman + adult man unless the scene demands otherwise.

## 2. Parentheses emphasis / deemphasis

A Qwen3-VL-family encoder loaded with CLIPLoader `type: "krea2"` respects `(clause:weight)`
(verified on an uncensored build — see `krea2-generation.md` §2). Example anchors that landed:

- **Emphasis `1.1–1.4`**: `(looking directly at camera:1.3)`, `(wet skin glistening with water droplets:1.3)`,
  `(watery pleading eyes looking up:1.25)`, `(deep oral sex with penis in mouth:1.25)`,
  `(explicit vaginal penetration visible:1.3)`, `(completely naked breasts exposed:1.3)`,
  `(penis fully inserted from behind... unambiguous deep entry:1.4)` (1.4 is safe for act anchors).
  Effect is strong and targeted — eye-contact and act anchors landed first-try in most tests.
- **Deemphasis `0.4–0.8`**: `(extra limbs:0.5)`, `(censor:0.4)`, `(distorted fingers:0.6)`,
  `(blurry background:0.8)`, `(overexposed sky:0.7)`, `(white t-shirt:0.4), (denim shorts:0.4)`, `(panties:0.4)`.
  Effect is real suppression — used to strip residual clothing and kill clones.
- Keep weights inside `0.4–1.4`. Above 1.4 risks overbaked expressions; below 0.4 risks erasing the subject.
- **Never put the banned noun in a negation.** `(hand reaching out of mirror:0.4)` and
  `(foreground bodies outside mirror:0.4)` primed the model to draw exactly that (6+ hands + edge fingers).
  Prefer positive-only phrasing (`tight crop with no fingers at the frame edges` also risks the noun —
  safest is describing only what IS present: `her arms lowered out of view at her sides`).

## 3. Example batch — 10 steps (verified instance: 5 + 1 fixup)

| File | Seed | Prompt core | Score |
| :--- | :--- | :--- | :---: |
| `krea2_learn01_00001_.png` | 771228143 | cowgirl flash bedroom, eye-contact emphasis | 5/5 |
| `krea2_learn02_00001_.png` | 614600306 | shower standing rear-entry, wet-skin emphasis | 5/5 |
| `krea2_learn03_00001_.png` | 2662084431 | car hood sunset, clothed kissing version | 3/5 — act missing (SFW fallback) |
| `krea2_learn03b_00001_.png` | 4014551482 | car hood re-roll: naked emphasis + clothing deemphasis | 5/5 |
| `krea2_learn04_00001_.png` | 1508841972 | couch missionary lamp close-up, extra-limbs ban | 4/5 — pose drifted to mating-press, still explicit |
| `krea2_learn05_00001_.png` | 608418387 | bathroom mirror oral selfie, twintails correct | 5/5 |

## 4. Example batch — 15 steps (verified instance: 5 + 2 fixups)

| File | Seed | Prompt core | Score |
| :--- | :--- | :--- | :---: |
| `krea2_s15_01_00001_.png` | 3366217545 | kitchen daylight counter rear-entry | 5/5 |
| `krea2_s15_02_00001_.png` | 2123315620 | tent lantern cowgirl | 5/5 |
| `krea2_s15_03_00001_.png` | 3047978163 | office desk, panties in-frame | 4/5 — contact obscured by fabric |
| `krea2_s15_03b_00001_.png` | 860194749 | office fix #1: panties to floor + side view | 4/5 — contact visible but reads adjacent |
| `krea2_s15_03c_00001_.png` | 1579064882 | office fix #2: low hip camera + legs apart + 1.4 entry | 5/5 |
| `krea2_s15_04_00001_.png` | 95566221 | bathtub direct-POV oral, arms hidden | 5/5 |
| `krea2_s15_05_00001_.png` | 1819901874 | VHS doggystyle look-back, scanlines | 5/5 |

On the verified instance 15 steps cost no meaningful extra time and rendered slightly finer
micro-detail (sweat, fabric weave, saliva). General rule: **prefer 15 steps for final-quality
runs, 10 for fast iteration**.

## 5. Rules derived

1. **Outdoor + clothed defaults to SFW.** Sunset car-hood with `t-shirt pulled up / shorts pushed aside`
   rendered clothed kissing (3/5). Fix: state nakedness positively
   `(completely naked breasts exposed:1.3)` + `(explicit vaginal penetration visible:1.3)`
   AND deemphasize each garment `(white t-shirt:0.4), (denim shorts:0.4)`.
2. **A garment in-frame occludes contact — remove it, don't just push it aside.** Office 4/5 had panties
   pulled aside covering the entry. Fix that worked: panties physically relocated
   (`lying on the floor beside her shoe`) + `(panties:0.4)`, pants `around ankles`.
3. **Drop the camera to the contact plane.** Raising emphasis alone left office entry reading adjacent;
   `low camera at hip level` + `legs slightly apart` + 1.4 entry anchor produced the 5/5.
   General rule: rear-entry wants side 3/4 at hip height, not a high wide shot.
4. **Disambiguate every hand; hide hands you don't need.** `her hands clutching his shoulders, his hands
   gripping her thighs` prevents merges. For oral POV, `her arms lowered out of view at her sides` kills
   the multi-arm trap better than any ban list. Combined with `(extra limbs:0.5)` it held in couch,
   bathtub, and tent close-ups.
5. **One sharp face max for first attempts.** Flash cowgirl, shower look-back, bathtub oral all landed 5/5
   with a single focused face. Two-face kissing is fine outdoors but costs act visibility.
6. **Mirror-plane mixing causes the reflection-hand paradox.** A mirror selfie mixing real foreground bodies
   with a reflection lets the reflection's arm touch the real head (seen in the `learn05` batch), and single-plane
   rewrites with negation nouns made it worse (6+ hands). Fixes in order of reliability:
   (a) drop the mirror — direct POV with simplified hands (all 5/5 geometry);
   (b) keep mirror but describe only hands present, positive-only, her arms hidden, tight crop.
7. **Pose drift is the common 4/5 mode.** Couch missionary came back as legs-held mating-press instead of
   legs-wrapped — anatomically clean, more explicit, acceptable. If exact pose matters, anchor with furniture
   (`forearms braced beside her head`, `hands flat on scattered papers`) rather than adding more act tags.

## 6. Minimal template — NSFW specialization of `krea2-generation.md` §5 (bands, no "fictional", no numbers)

```text
Amateur <device> photo of a <young adult woman / adult man> with <hair>, <expression>, <skin/build>,
<pose anchored to furniture/body>, <her hands ... , his hands ...>, <exact undress + act with (emphasis:1.2)>.

<Room/outdoor setting, furniture, props, light sources.>

<Device aesthetic, angle, framing, lighting color, grain/artifacts, (suppressions:0.5-0.8).>
```

Negative prompt: `""`. Randomize seed every run. Prefer 15 steps for finals, 10 for fast drafts.
