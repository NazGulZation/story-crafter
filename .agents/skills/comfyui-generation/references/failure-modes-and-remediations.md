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

---

## 9. The "Vertical Monolith / Cock Pole" Foreshortening Glitch (Upward Frontal POV in Frottage/Straddling)

- **The Failure Mode**: When attempting pre-penetration, dry humping, or frottage with an upward vertical or low-angle frontal POV (`pov, upward view, looking up, straddling, penis against pussy, hand on penis`), extreme foreshortening causes the model to render an unnaturally upright, disembodied vertical shaft standing like a monolith in the foreground. The female partner's groin geometry becomes ambiguous or detached, and hands holding the shaft appear disjointed or floating.
- **Remediation Strategy**:
  - **Abandon Direct Upward Frontal POV**: Do not prompt upward camera angles with detached POV elements for close lap interactions.
  - **Switch to Seated / Reclined Side 3/4 Perspective**: Ground both bodies in space: `side view, side 3/4 angle, 1girl, straddling partner's lap, thighs apart, legs wrapped around partner's waist, arched back, leaning forward, looking at partner, 1boy, sitting up, hands on partner's hips, holding waist, muscular, large erect penis`.
  - **Explicitly Detail the Physical Contact**: Anchor the exact frictional interaction: `frottage, grinding, penis against pussy, shaft rubbing against clit, pre-penetration, dripping pussy juice, wet fluids, clitoral friction, intimate contact, hips pressed close`.
  - **Negative Suppression**: Always add `floating penis, detached penis, upward angle, direct vertical view, extreme foreshortening, distorted perspective`.

---

## 10. The "Multi-Arm Hallucination & Spontaneous Puddle" Trap (Intimate Close-Up Missionary)

- **The Failure Mode**: In intimate, close-up missionary compositions involving multiple simultaneous upper-body touch points (`forehead against partner, hands on partner's shoulders, hovering over`), the diffusion model frequently duplicates arm limbs, producing 4 distinct arms (e.g. two arms wrapping around the neck and two extra arms emerging from the torso or floor). Additionally, heavy arousal fluid tokens (`wet pussy, dripping fluids, pussy juice, puddle`) leak into the environmental background conditioning, causing spontaneous ponds, streams, baths, or blue water puddles to appear between the characters' legs even when outdoors in dry terrain.
- **Remediation Strategy**:
  - **Strictly Disambiguate Arm Placements for Each Subject**:
    - For the female subject: explicitly allocate one arm around partner and one arm grounded (`one arm around partner's neck, one hand braced on ground/moss`).
    - For the male subject: explicitly define his bracing (`hovering over, missionary, hands braced on ground beside her head`).
  - **Enforce Strict Multi-Limb Negative Bans**: Always include `extra limbs, extra arms, extra hands, 4 arms, multi-arms, floating limbs`.
  - **Liquid Landscape Negative Suppression for Dry Ground**: When scenes occur on dry ground (moss, bedding, futon, tatami, forest floor), explicitly ban liquid landscape tokens in negative prompt: `water, pond, river, stream, pool, onsen, hot spring, bath, puddle`.

---

## 11. The Protagonist / "You" Face & Feature Clash (Self-Insert Immersion)

- **The Failure Mode**: In second-person ("you") narratives (e.g. stories written from the perspective of the Trainer, Producer, Commander, Master, or reader), prompting a secondary character as a generic or named role (e.g. `1boy, trainer (umamusume)`) without an anonymity anchor causes two major defects:
  1. **Distracting Specific Faces**: The model renders a fully detailed, distinct, or idiosyncratic anime face that conflicts with reader self-insertion, often drawing visual attention away from the primary heroine.
  2. **Feature & Accessory Bleed**: When the heroine has unique biological or decorative features (e.g. horse ears, horns, halo, ear beads, unusual hair streaks), the absence of a `faceless` token frequently causes the model to mirror those non-human features onto the protagonist (e.g. generating horse ears or ear ornaments on the human Trainer).
- **Remediation Strategy**:
  - **Always Tag `faceless male` or `faceless female`**:
    - For male protagonist ("you"): `1boy, faceless male, [role/context if needed, e.g. trainer (umamusume)], muscular, short hair...`
    - For female protagonist ("you"): `1girl, faceless female, [role/context if needed]...`
  - **Enforce Human Feature Isolation**: Explicitly state `human ears, no animal ears, no horse ears` on the partner if the heroine has fantasy or animal traits.
  - **Negative Suppression**: Add `horse ears on boy, animal ears on male, ear ornament on male, multiple horse ears, deformed ears, 4 ears`.

---

## 12. The "Generic Casual / T-Shirt Fallback" on Elaborate Racing Silks & Variant Outfits (Iconic Component Decomposition)

- **The Failure Mode**: When prompting a character in a specific elaborate costume or racing silk (e.g., `matikane tannhauser (clippety-tippety-clop) (umamusume)`), relying solely on the variant tag without structural components often causes the model to fall back to generic casual wear (plain t-shirts, modern hoodies, or plain skirts) due to diluted text-encoder weights for the specific outfit variant.
- **Remediation Strategy**:
  - **Decompose the Costume into 3–5 Signature Structural Anchors**: Rather than using vague clothing terms (like `shirt, jacket, clothes`) which cause tag confusion, explicitly state the unique, iconic design components that define the costume:
    - *Example (Machitan Clippety-Tippety-Clop)*: `blue casquette cap, red corset, white blouse, cutaway shoulders, blue skirt, gold trim`.
    - *Example (Teio Beyond the Horizon)*: `blue tailcoat, white pants, gold epaulets, blue cape, white ascot`.
  - **Differentiate Generic Clothing Suppression from Iconic Anchoring**:
    - *Banned*: Adding generic tags like `shirt, jacket, pants` that compete with the costume logic.
    - *Mandatory*: Adding precise, unique silhouette pieces (`casquette cap, corset, cutaway shoulders`) that guide the diffusion model to reconstruct the exact canon outfit.
  - **Negative Suppression**: Add `t-shirt, casual clothes, gym uniform, school uniform, plain shirt, hoodie`.

---

## 13. Kinetic Speed & Racing Velocity vs. Anatomical Smearing

- **The Failure Mode**: In high-speed sports, sprinting, or turf racing sequences, prompting `motion blur`, `blur`, or `speed lines` often causes the model to blur the character's facial features, hands, and limb contours, producing melted anatomy or blurry smudges.
- **Remediation Strategy**:
  - **Isolate Motion Blur to the Environment**: Explicitly tag `motion blur background` or `blurred background` while keeping the character sharply focused:
    - *Character Anchors*: `running, sprinting, high speed, dynamic angle, clenched teeth, flying sweat, intense expression, horse ears pinned back, sharp focus on character`.
    - *Environmental Velocity*: `motion blur background, flying turf, kicking up dirt, speed lines in background, stadium lighting, racetrack`.
  - **Express Speed Through Diegetic Consequences**: Detail flying sweat droplets, flying dirt/turf clods from running shoes/hooves, fluttering ribbons/hair, and strained neck tendons.
  - **Negative Suppression**: Add `blurry character, blurry face, motion blur on body, melted limbs, deformed legs, extra legs, bad anatomy`.



