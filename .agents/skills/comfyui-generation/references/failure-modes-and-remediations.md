# Field-Tested Failure Modes & Proven Prompt Remediation Strategies

This reference catalogs recurring failure modes in SDXL/Pony/Anima diffusion workflows, along with their exact remediation rules, asymmetric dress state tagging standards, and uniform variant prompt hygiene.

---

## 1. Nudity & Asymmetric Dress State Tagging Standards

When composing prompt tags for sexual interactions or solo poses, ambiguous clothing states cause the diffusion model to default to partially clothed, mismatched, or spontaneously covered states. Use these explicit dress-state tags:

### Mandatory Dress State Protocols
1. **Both Characters Fully Nude / Solo Character Nude**:
   - Always include: `completely naked, bare skin`.
   - Add anatomical anchors: `bare breasts, nipples, exposed pussy` (for female) and `nude male, erect penis` (for male).
   - Negative prompt: `clothes, clothing, shirt, bra, sports bra, panties, bloomers, shorts, swimsuit, leotard`.

2. **Asymmetric State: Female Clothed, Male Nude**:
   - When the female partner is still wearing clothes (e.g. uniform, gym clothes, dress) while the male partner is stripped:
     - Always include tag: `clothed female nude male`.
     - Explicitly detail her clothing (`gym uniform, bloomers, skirt, jacket`).
     - Explicitly detail his nakedness (`nude male, bare chest, erect penis, no shirt, no pants`).
     - Negative prompt: `nude female, bare breasts, topless female, clothed male, male clothes`.

3. **Asymmetric State: Male Clothed, Female Nude**:
   - When the male partner remains clothed (e.g. suit, shirt, uniform) while the female partner is stripped:
     - Always include tag: `clothed male nude female`.
     - Explicitly detail his clothes (`fully clothed male, collared shirt, suit, pants`).
     - Explicitly detail her nakedness (`completely naked, bare breasts, nipples, exposed pussy, no clothes`).
     - Negative prompt: `nude male, shirtless male, clothed female, female clothes, bra, panties`.

---

## 2. Character Uniform Tag Variants & Redundant Clothing Suppression

When depicting a character in their canonical outfit, racewear, or school uniform:
- **Full Uniform Tag Variant**: Character variant tags such as `sakura bakushin o \(blossom in learning\) \(umamusume\)` represent the **complete canonical uniform** within the model's dataset.
- **Rule — Suppress Redundant Generic Clothing Prompts**:
  - Do **NOT** add generic clothing descriptors such as `jacket, sleeveless jacket, sports bra, gym bloomers, shirt, skirt` alongside the full uniform tag.
  - Adding generic clothing prompts creates competing conditioning tokens that override or distort the default uniform variant, resulting in garbled collar lines, mismatched patterns, incorrect color blocking, or double-layered vests.
  - **Exception**: Only include specific clothing modifiers if a distinct deviation from the default uniform is deliberately intended (e.g., `open jacket, unzipped jacket, torn clothes, lifted skirt`).
  - For standard clothed scenes, prompt the variant tag alone:
    `1girl, sakura bakushin o \(blossom in learning\) \(umamusume\), brown hair, ponytail, purple eyes, tiara, solo...`

---

## 3. The "Floor Chest / Collarbone" Glitch (POV Doggystyle in Vertical Format)

- **The Failure Mode**: When requesting rear-entry / doggystyle (`from behind`, `doggystyle`, `standing doggystyle`) in vertical aspect ratios (2:3, 9:16) with downward POV (`pov, pov hands, penis in pussy`), the model defaults to its ingrained missionary template. It renders a male chest/collarbone lying face-up on the floor at the bottom of the screen with an erect penis pointing upward into the girl, creating an absurd anatomical hybrid where she is supposedly taken from behind while a man lies underneath her on the floor.
- **Remediation Strategy**:
  - **Never use direct downward `pov` for standing rear-entry**.
  - **Switch to a Side 3/4 Perspective**: Use `side view, 3/4 view, standing sex, trainer standing behind, embracing from behind`.
  - **Negative Suppression**: Add `pov, top down view, male lying on back, chest at bottom, missionary, face up`.

---

## 4. The "Motion Lines / Bouncing" Breast Ghosting Trap

- **The Failure Mode**: Prompt tags such as `bouncing`, `motion lines`, or `motion blur` applied to female anatomy do not generate stylish action streaks; instead, the diffusion model interprets motion blur as **secondary flesh silhouettes**, generating **double breasts, dual contours, or ghosted pale bulges** beneath the chest. Furthermore, manga impact tags can manifest as spiky skin spurs along the outer hips and thighs.
- **Remediation Strategy**:
  - **Never prompt `bouncing`, `motion lines`, or `motion blur` on body parts**.
  - **Express Speed & Rhythm Through Diegetic Consequences**: Prompt physical reactions instead: `flying sweat droplets, dripping sweat, heavy panting, clenched teeth, arched back, intense rhythm, squelch, sexual fluids`.
  - **Enforce Clean Anatomy**: Use `natural breasts, firm breasts, bare breasts`.
  - **Negative Suppression**: Always include `motion lines, motion blur, ghosting, double breasts, dual breasts, extra nipples, spikes, impact lines`.

---

## 5. The Athletic Environment "Spontaneous Swimsuit / Leotard" Bias

- **The Failure Mode**: In athletic scenes (gymnasiums, equipment rooms, stretching on mats, wrists crossed behind head), the model has heavy latent associations with competitive sportswear (`school swimsuit, leotard, one-piece swimsuit`). Even if `bare breasts` or `topless` is prompted, the strong sports context can manifest a full one-piece swimsuit or singlet covering the torso.
- **Remediation Strategy**:
  - **Enforce Redundant Total Nudity Tags**: When the scene demands full undress, use: `completely nude, topless, bottomless, bare breasts, nipples, bare skin, no clothes`.
  - **Negative Suppression**: Explicitly ban athletic gear: `swimsuit, leotard, one-piece swimsuit, clothes, clothing, shirt, bra, sports bra, bloomers, shorts, panties`.

---

## 6. Multi-Partner / "2boys" Contamination in Complex Multi-Point Contact

- **The Failure Mode**: When a scene requires multiple simultaneous actions from the male partner (e.g., missionary penetration AND licking her armpit, or holding her hips AND reaching around to cup a breast), the model often splits the actions across two separate male bodies (e.g. one man lying down, another standing nearby).
- **Remediation Strategy**:
  - **Strict Singular Male Anchors**: Always include `1boy, solo male, only one male, single male, pov, close-up`.
  - **Negative Suppression**: Always include `2boys, multiple boys, multiple males, clone, extra heads, extra bodies, extra limbs, standing male` (if the partner is lying down).

---

## 7. Inverted Perspective Collapse in Post-Coital Aftermath Scenes

- **The Failure Mode**: In aftermath/collapse scenes on the floor, framing the camera from above the head looking down the body (inverted perspective) frequently confuses spatial orientation, causing inverted legs, extra limbs, or upright erect condoms protruding from the partner's back.
- **Remediation Strategy**:
  - **Ground the Scene in Natural Horizons**: Frame aftermaths from side angles: `lying on side, side view, cuddle, embracing, arm draped over waist, collapsed together on mat, spent, mutual exhaustion, used condom discarded on mat`.
  - **Negative Suppression**: Add `upside down, extra legs, extra limbs, penetration, erect penis, upright condom`.

---

## 8. Facesitting & Downward 69 Oral "Severed Head" Glitch

- **The Failure Mode**: When prompting direct downward or straight-on facesitting (`straddling face, sitting on face, pov, top down view`), the model often places the male head at the extreme bottom edge pinned between thighs, rendering it as a squashed, disembodied or severed head with distorted facial features, missing eyes/nose, or unnatural hand angles.
- **Remediation Strategy**:
  - **Never use direct straight-down top-down POV for facesitting / 69 positions**.
  - **Switch to a Dynamic Side 3/4 Perspective or Profile View**: Prompt `side view, 3/4 view, 1girl, completely naked, on knees, leaning forward, one arm raised high braced against wall, exposed underarm, glistening armpit, 1boy, lying on back on mat, tilting head back, mouth open, tongue out, licking her armpit, tongue on underarm`.
  - **Negative Suppression**: Always add `headless, severed head, squished face, upside down face, deformed face, bad eyes, bad mouth, extra heads, extra arms, extra limbs`.
