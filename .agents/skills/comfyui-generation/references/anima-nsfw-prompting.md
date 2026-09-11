# Anima Model Danbooru NSFW Prompt Engineering Reference

This reference outlines the canonical Danbooru-tag prompt architecture for the **Anima** diffusion model (paired with the Qwen 3 text encoder `qwen_3_06b_base.safetensors`).

---

## 1. Core 5-Block Prompt Template

The prompt structure separates concerns into discrete semantic paragraphs separated by double newlines (`\n\n`). This modular layout allows the text encoder to distinguish global quality cues, character identity, interaction framing, explicit acts, and environmental setting without tag interference.

```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot,

{main_character}

{secondary_character}

{sexual act}

{background}
```

> [!IMPORTANT]
> **No Underscores Required — Use Spaces**:
> While Danbooru and similar boorus index tags using underscores (`reimu_hakurei`, `brown_hair`, `detached_sleeves`, `cowgirl_position`), **the Anima model was trained with spaces rather than underscores**.
> - Always replace underscores with regular spaces in your prompts.
> - Examples: `reimu hakurei` (not `reimu_hakurei`), `brown hair` (not `brown_hair`), `hair bow` (not `hair_bow`), `detached sleeves` (not `detached_sleeves`), `cowgirl position` (not `cowgirl_position`).
> - The Qwen 3 text encoder parses natural space-delimited English phrases far more effectively than concatenated underscore strings.

---

## 2. Block-by-Block Specification

### Block 1: Quality, Aesthetic & Style Anchors
Establishes the clean rendering fidelity, anime screenshot aesthetic, and vibrant coloring:
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot,
```
- `masterpiece, best quality`: Enforces high baseline generation quality.
- `ultra detailed anime coloring`: Produces rich, clean cel-shading, vibrant skin tones, and detailed shading without grainy textures.
- `anime screenshot`: Enforces authentic, clean anime cinematography, crisp lineart, and television/film-grade composition.

---

### Block 2: Primary Character (`{main_character}`)
Defines identity, franchise, physique, expression, and primary pose:
- **Count & Identity**: `1girl`, `[character_name] \([variant]\) \([franchise]\)` *(remember to escape parentheses with `\(` and `\)`)*
- **Body & Features**: `large breasts` / `medium breasts` / `flat chest`, `wide hips`, `navel`, `collarbone`
- **Expression & Gaze**: `smug`, `grin`, `blush`, `parted lips`, `heavy breathing`, `drooling`, `looking at viewer`, `half-closed eyes`, `aroused`
- **Attire & State of Undress**: `off shoulder`, `necklace`, `pendant`, `bottomless`, `clothed female nude male`, `lifted shirt`, `undressing`
- **Genital & Intimate Details**: `pussy`, `pubic hair` / `shaved pussy`, `clitoris`, `wet`, `cameltoe`
- **Body Posture**: `leaning back`, `arched back`, `legs apart`, `on back`, `spread legs`

---

### Block 3: Secondary Character & Framing (`{secondary_character}`)
Defines the partner, perspective, and bodily presence in the scene:
- **Count & Identity**: `1boy`, `faceless male`, `tall male`, `trainer \([umamusume]\)`
- **Camera Perspective**: `pov`, `pov hands`, `first-person view`, `from behind`, `close-up`, `low angle`
- **Interaction Contact**: `hands on hips`, `grabbing thighs`, `holding hands`, `pov hands on waist`
- **Partner State**: `clothed female nude male`, `shirtless male`, `large penis`, `erection`, `veiny penis`, `precum`

---

### Block 4: Sexual Act & Dynamic Interaction (`{sexual act}`)
Specifies the exact mechanical position, penetration status, fluids, and physiological reactions:
- **Acts & Mechanics**: `vaginal`, `anal`, `oral`, `sex`, `penetration`, `insertion`, `deep penetration`
- **Positions**:
  - `cowgirl position`, `straddling`, `riding`
  - `missionary`, `legs over head`, `mating press`
  - `doggy style`, `from behind`, `all fours`, `prone bone`
  - `standing sex`, `against wall`, `lifted legs`
  - `fellatio`, `blowjob`, `cunnilingus`, `fingering`, `handjob`
- **Fluids & Effects**: `sweat`, `steaming body`, `dripping fluids`, `saliva trail`, `pussy juice`, `cum`, `internal cumshot`, `after sex`

---

### Block 5: Setting & Camera Environment (`{background}`)
Grounds the scene in a tangible space without cluttering the foreground subjects:
- **Scenery**: `scenery, bedroom`, `hotel room`, `tatami room`, `onsen`, `office`, `locker room`, `dungeon`, `dimly lit room`
- **Focal Elements**: `bed`, `bed sheets`, `pillows`, `mattress`, `sofa`
- **Depth & Optics**: `blurred background`, `depth of field`, `soft lighting`, `rim lighting`, `cinematic lighting`, `sunlight through window`

---

## 3. Standard Negative Prompt

The Anima model uses a curated negative string to suppress low-quality artifacts, outdated training styles, and unwanted anatomical deformations:

```text
worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, ugly, disfigured, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor
```

> **Note on Censorship**: Including `censor` in the negative prompt prevents mosaic, bar, or shadow censorship overlays from being generated by default.

---

## 4. Concrete Workflow Examples

### Example A: Cowgirl / Straddling (POV)
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot, 

1girl, agnes tachyon \(casual\) \(umamusume\), large breasts, smug, grin, off shoulder, necklace, pendant, bottomless, pussy, pubic hair, leaning back, 

1boy, pov, pov hands, clothed female nude male, large penis

vaginal, sex, cowgirl position, straddling, 

scenery, bedroom, blurred background
```

### Example B: Missionary / Intense Passion
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot, 

1girl, blue hair, long hair, blue eyes, blush, heavy breathing, parted lips, tears, arched back, large breasts, bare shoulders, on back, legs apart, pussy, wet, 

1boy, pov, pov hands, gripping hips, muscular male, large penis, 

vaginal, sex, missionary, deep penetration, intense, sweat, steaming body, trembling, 

scenery, hotel room, disheveled bed sheets, pillows, soft morning lighting, depth of field
```

### Example C: Doggy Style / From Behind
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot, 

1girl, blonde hair, twin tails, red eyes, looking back, open mouth, blushing, doggy style, on all fours, arched spine, wide hips, round buttocks, pussy, pubic hair, 

1boy, pov, pov hands on waist, standing behind, veiny erection, large penis, 

vaginal, sex, from behind, penetration, hard thrusting, sweat, dripping, 

scenery, private room, tatami, dim ambient lighting, blurred background
```

---

## 5. Integration with `comfyui_runner.py`

When passing these multi-line block prompts via CLI or Python script:

```powershell
$prompt = @"
masterpiece, best quality, ultra detailed anime coloring, anime screenshot, 

1girl, agnes tachyon \(casual\) \(umamusume\), large breasts, smug, grin, off shoulder, necklace, pendant, bottomless, pussy, pubic hair, leaning back, 

1boy, pov, pov hands, clothed female nude male, large penis

vaginal, sex, cowgirl position, straddling, 

scenery, bedroom, blurred background
"@

python c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud" `
  --workflow "C:\StoryCrafter\anima_absolute_cinema.json" `
  --prompt "$prompt" `
  --randomize-seed `
  --output-dir "C:\StoryCrafter\assets"
```

---

## 6. Post-Generation Visual Inspection & 5/5 Rating Standard

Once an image is generated and saved:
1. **Mandatory Visual Inspection**: Always use `view_file` to visually audit the result.
2. **Score on 1-5 Scale**:
   - Check all 5 blocks (character accuracy, state of undress, requested sexual act, contact dynamics, background).
   - Check anatomy (hands, fingers, eyes, facial expression, genital alignment).
3. **Mandatory Visible Scoring**: Always explicitly write the score (e.g. `Score: X/5`) in the output so the user can observe the evaluation in real-time.
4. **The 5/5 Rule & Prompt Replacement on Re-rolls**:
   - If the score is **5/5**, accept and save the image.
   - If the score is **below 5/5**, do NOT accept it. Diagnose the visual defect, **replace or refine the prompt** (adjust position tags, clarify undress state, add negative tags for extra limbs/partners, or sharpen focus) to ensure the model produces what was intended, pick a fresh random seed, and re-queue.
   - Repeat the cycle until a **5/5** image is produced.

---

## 7. Critical Prompting Guidelines & Failure Prevention

1. **Doggystyle / Rear-Entry in Vertical Aspect Ratio**:
   - **Do NOT use vertical POV**: Downward vertical POV (`pov, pov hands, from behind`) causes the model to generate a missionary male chest/collarbone lying on the floor at the bottom of the frame with an erect penis pointing up.
   - **Always use Side 3/4 Perspective**: Prompt `side view, 3/4 view, standing doggystyle, standing sex, embracing from behind`. Negate `pov, top down view, male lying on back, chest at bottom, missionary`.

2. **Bouncing & Motion Lines**:
   - **Never prompt `bouncing`, `motion lines`, or `motion blur` on anatomy**: The model interprets motion lines as secondary contours/flesh, causing double breasts or ghosted bulges.
   - **Express violent rhythm through consequences**: Use `flying sweat droplets, dripping sweat, clenched teeth, heavy panting, arched back, intense rhythm, squelch`. Negate `motion lines, motion blur, ghosting, double breasts, dual breasts`.

3. **Athletic Environment Nudity Enforcement**:
   - Athletic context (`gym mats, stretching, arms raised`) strongly biases the model toward drawing `one-piece swimsuits` or `leotards`.
   - In full undress scenes, explicitly prompt `completely nude, topless, bottomless, bare breasts, bare skin, no clothes` and negate `swimsuit, leotard, one-piece swimsuit, clothes, clothing, shirt, bra, sports bra, bloomers`.

4. **Multi-Point Contact Disambiguation**:
   - Multi-action contact (penetration + armpit licking or breast cupping) easily spawns two male partners (`2boys` glitch).
   - Anchor the scene with `1boy, solo male, only one male, single male` and negate `2boys, multiple boys, multiple males, clone, standing male` (when lying down).



