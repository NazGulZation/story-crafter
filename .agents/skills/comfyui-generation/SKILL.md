---
name: comfyui-generation
description: >-
  Generate images and run diffusion workflows using local or remote ComfyUI instances (e.g. SaladCloud, RunPod, localhost:8188).
  Covers health check verification (/system_stats), automated conversion of frontend UI workflow JSON to ComfyUI API prompt format,
  dynamic parameter overrides (prompts, seeds, dimensions, samplers), job queueing (/prompt), execution polling (/history/{prompt_id}),
  output asset retrieval (/view), Anima Danbooru-tag NSFW prompt engineering, visible validation scoring (writing the score so the user can see it),
  prompt replacement/refinement on re-rolls (< 5/5), and visual quality/prompt-fidelity verification loop (5/5 rating standard).
---

# ComfyUI Image Generation & Workflow Execution

Automate diffusion model image generation through ComfyUI instances over HTTP/REST API. Works seamlessly with local setups (`http://127.0.0.1:8188`) or cloud serverless/dedicated nodes (e.g. SaladCloud, RunPod, Vast.ai).

---

## 1. ComfyUI REST API Architecture

ComfyUI exposes a simple HTTP REST and WebSocket interface:

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/system_stats` | `GET` | Health check: returns ComfyUI version, Python/PyTorch versions, GPU name, VRAM totals/free. |
| `/prompt` | `POST` | Queue a workflow prompt. Payload: `{"prompt": <api_prompt_dict>}`. Returns `{"prompt_id": "...", "number": int, "node_errors": {}}`. |
| `/history/{prompt_id}` | `GET` | Execution status and generated output metadata. Returns `{"<prompt_id>": {"status": {"status_str": "success"|"error"}, "outputs": {...}}}`. |
| `/view` | `GET` | Retrieve image files: `/view?filename=<name>&subfolder=<subfolder>&type=output`. |
| `/queue` | `GET` | Inspect current queue running/pending items. |
| `/interrupt` | `POST` | Abort current generation. |

---

## 2. Frontend Workflow JSON vs. API Prompt Format

When users save/export a workflow from the ComfyUI web interface, it is saved in **Graph UI format**, which is **NOT** directly accepted by `/prompt`.

### Graph UI Format (Exported from ComfyUI canvas):
- Contains top-level `"nodes"` (list) and `"links"` (list of `[link_id, from_node, from_slot, to_node, to_slot, type]`).
- Widget values stored in `"widgets_values"` (positional) or `"widgets_values_named"` (key-value dictionary).
- Contains layout metadata (`pos`, `size`, `order`, colors, notes).

### API Prompt Format (Required by `/prompt`):
- A flat JSON object mapping string `node_id` to its specification:
```json
{
  "prompt": {
    "11": {
      "class_type": "CLIPTextEncode",
      "inputs": {
        "text": "masterpiece, 1girl...",
        "clip": ["45", 0]
      }
    },
    "45": {
      "class_type": "CLIPLoader",
      "inputs": {
        "clip_name": "qwen_3_06b_base.safetensors",
        "type": "stable_diffusion",
        "device": "default"
      }
    }
  }
}
```

### Conversion Rules:
1. **Exclude Non-Executable Nodes**: Skip `Note`, `MarkdownNote`, and UI annotation nodes.
2. **Build Link Map**: Map each `link_id` to `(source_node_id, source_slot_index)`.
3. **Map Widget Inputs**: Pull inputs from `widgets_values_named`. Exclude UI-only controls (e.g. `control_after_generate`).
4. **Resolve Connections**: For each entry in `node["inputs"]`, lookup `link_id` and assign `[str(source_node_id), source_slot_index]`.

---

## 3. Reusable Runner Script

A complete, production-ready runner utility is included in this skill at:
`c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py`

### Command-Line Usage:

```powershell
# 1. Health check only
python c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud" `
  --workflow "C:\StoryCrafter\anima_absolute_cinema.json" `
  --stats-only

# 2. Run workflow and download output
python c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud" `
  --workflow "C:\StoryCrafter\anima_absolute_cinema.json" `
  --output-dir "C:\StoryCrafter\assets"

# 3. Run with parameter overrides (prompt, seed, steps, resolution)
python c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud" `
  --workflow "C:\StoryCrafter\anima_absolute_cinema.json" `
  --prompt "masterpiece, best quality, 1girl, silver hair, glowing eyes, cinematic lighting" `
  --seed 42 `
  --steps 35 `
  --output-dir "C:\StoryCrafter\assets"
```

---

## 4. Python Implementation Reference

When writing standalone scripts or subagents, use standard library `urllib` (no external `requests` package dependency needed):

```python
import json
import os
import time
import urllib.parse
import urllib.request

COMFYUI_URL = "https://your-instance.salad.cloud"


def queue_workflow(server_url, api_prompt):
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"{server_url}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("node_errors"):
            raise ValueError(f"Node errors: {res['node_errors']}")
        return res["prompt_id"]


def wait_and_download(server_url, prompt_id, output_dir, poll_interval=5, timeout=600):
    elapsed = 0
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval

        hist_req = urllib.request.Request(f"{server_url}/history/{prompt_id}")
        try:
            with urllib.request.urlopen(hist_req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue

        if prompt_id in data:
            prompt_res = data[prompt_id]
            if prompt_res.get("status", {}).get("status_str") == "error":
                raise RuntimeError(prompt_res["status"].get("messages"))

            # Download completed images
            for node_id, out in prompt_res.get("outputs", {}).items():
                for img in out.get("images", []):
                    if img.get("type") == "temp":
                        continue  # Skip temp previews
                    params = urllib.parse.urlencode({
                        "filename": img["filename"],
                        "subfolder": img.get("subfolder", ""),
                        "type": img.get("type", "output")
                    })
                    view_url = f"{server_url}/view?{params}"
                    dest = os.path.join(output_dir, img["filename"])
                    with urllib.request.urlopen(view_url, timeout=60) as r, open(dest, "wb") as f:
                        f.write(r.read())
                    print(f"Saved: {dest}")
            return
    raise TimeoutError("Prompt timed out")
```

---

## 5. Troubleshooting & Diagnostics

1. **`node_errors` in POST `/prompt`**:
   - ComfyUI validates node inputs upon queueing.
   - If an error mentions `Missing model`, verify that checkpoints, UNETs, VAEs, or text encoders exist in the server's `models/` directory matching the filename specified in the node.
2. **Missing Custom Nodes**:
   - Check `/system_stats` -> `comfy_package_versions` or error logs for missing custom nodes (e.g. `ModelPreviewOverrideKJ` requires `comfyui-kjnodes`).
3. **Filtering Output Images vs Temp Previews**:
   - Workflows with intermediate previews (e.g., `PreviewImage` or KJ previewers) produce images marked `type: "temp"`.
   - Always filter for `type == "output"` (from `SaveImage` nodes) unless intermediate inspection is explicitly requested.
4. **VRAM & Timeout Considerations**:
   - Multi-pass workflows (e.g. high-step base sampler + latent upscale + refiner) can take 45s to 3 minutes on high-end GPUs (RTX 4080/4090). Ensure polling timeouts are set to at least 600s.

---

## 6. Anima Danbooru NSFW Prompt Architecture

The **Anima** model (using Qwen 3 text encoder `qwen_3_06b_base.safetensors`) achieves optimal compositional fidelity and anatomical accuracy when using structured Danbooru tags separated into 5 discrete paragraphs (`\n\n`):

### Template:
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot,

{main_character}

{secondary_character}

{sexual act}

{background}
```

> [!IMPORTANT]
> **Mandatory Dress State & Asymmetry Protocol**:
> - **Fully Nude Characters**: When both characters (or a solo character) are unclothed, explicitly add `completely naked, bare skin`.
> - **Asymmetric State (Female Clothed, Male Nude)**: When the female partner is clothed (e.g. gym clothes, uniform) while the male partner is stripped, explicitly add `clothed female nude male`.
> - **Asymmetric State (Male Clothed, Female Nude)**: When the male partner remains clothed (e.g. shirt, suit) while the female partner is stripped, explicitly add `clothed male nude female`.

> [!IMPORTANT]
> **Uniform Tag Variants & Redundant Clothing Suppression**:
> - When using an official character full uniform tag variant (e.g. `sakura bakushin o \(blossom in learning\) \(umamusume\)`), **remove generic clothing descriptors** (`jacket, shirt, bloomers, skirt, sports bra`).
> - Generic clothing tokens create competing conditioning signals that override or distort the default uniform variant, causing mismatched textures or garbled patterns. Only include specific clothing tokens if a distinct modification is deliberately intended (e.g., `open jacket, unzipped jacket, torn clothes`).

### Reference Example:
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot, 

1girl, agnes tachyon \(casual\) \(umamusume\), large breasts, smug, grin, off shoulder, necklace, pendant, bottomless, pussy, pubic hair, leaning back, 

1boy, pov, pov hands, clothed female nude male, large penis

vaginal, sex, cowgirl position, straddling, 

scenery, bedroom, blurred background
```

### Standard Negative Prompt:
```text
worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, ugly, disfigured, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor
```

> For exhaustive tag tables, pose variations, fluid dynamics, camera perspectives, and multi-line script execution, see the detailed reference:
> **[references/anima-nsfw-prompting.md](references/anima-nsfw-prompting.md)**

---

## 7. Randomized Seeds

By default, workflows use fixed seeds from the JSON file. Always randomize seeds when:
- Generating **multiple images of the same prompt** to get distinct outputs.
- The user has not explicitly requested a specific seed.
- Running batch jobs where diversity is desired.

### Seed Range
ComfyUI accepts seeds in the range `0` to `2^32 - 1` (i.e., `0` to `4294967295`).

```python
import random

def random_seed() -> int:
    return random.randint(0, 2**32 - 1)
```

### In `comfyui_runner.py`

```powershell
# Randomize seed every run
python c:\StoryCrafter\.agents\skills\comfyui-generation\scripts\comfyui_runner.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud" `
  --workflow "C:\StoryCrafter\anima_absolute_cinema.json" `
  --randomize-seed `
  --output-dir "C:\StoryCrafter"
```

### In Batch Scripts
Generate a fresh seed per image iteration:

```python
for i in range(3):
    seed  = random.randint(0, 2**32 - 1)
    label = f"character_{i+1:02d}_seed{seed}"
    # override and queue ...
```

### Important: Apply Seed to ALL Sampler Nodes
Workflows with multiple samplers (e.g. `KSamplerAdvanced` base pass + `KSampler` refiner) must have the seed injected into **both** nodes or only the first pass will vary. Use `apply_overrides()` which handles this automatically by checking both `"seed"` and `"noise_seed"` keys in every sampler node's inputs.

---

## 8. Mandatory Character Tag Research Protocol

When a user requests images of a **named character from any media** (anime, manga, games, visual novels, etc.), **always perform Danbooru tag research before constructing the prompt**. Never rely on assumed or memorized tags.

### Why This Matters
- Danbooru tags use specific canonical formats (e.g. `reimu_hakurei` not `hakurei reimu`, `hakurei_reimu_(touhou)` for disambiguation).
- Character appearance details (hair color, eye color, outfit elements) differ significantly between characters and their variants/costumes.
- Using wrong or vague tags produces OOC (out-of-character) results — wrong hair color, wrong outfit, generic faces.

### Research Workflow

**Step 1: Identify the canonical Danbooru tag**
- Format: `[character_name]_(series)` — e.g. `reimu_hakurei`, `rem_(re_zero)`, `asuna_(sao)`
- Use `search_web` with query: `danbooru "[character name]" tag appearance`

**Step 2: Verify canonical appearance attributes**
Collect and verify these for the character:
- Hair: color, length (`short_hair` / `long_hair` / `medium_hair`), style (`twin_tails`, `ponytail`, `ahoge`)
- Eyes: color
- Outfit: key clothing items (e.g. `miko`, `detached_sleeves`, `school_uniform`, `armor`)
- Accessories: `hair_ribbon`, `hair_bow`, `glasses`, `hat`, `collar`

**Step 3: Convert Danbooru underscores to spaces for prompt input**
- Anima's text encoder was trained on space-separated tokens rather than underscores.
- Replace all `_` with a space: `reimu_hakurei` -> `reimu hakurei`, `brown_hair` -> `brown hair`, `detached_sleeves` -> `detached sleeves`.
```text
reimu hakurei, touhou, brown hair, long hair, hair ribbon, hair bow, red ribbon, brown eyes, miko, detached sleeves, red skirt
```

### Verified Reference Examples

| Character | Danbooru Tag (Search) | Anima Prompt Format (Spaces) | Series Tag | Key Appearance Tags (Prompt Ready) |
|-----------|-----------------------|------------------------------|------------|-----------------------------------|
| Reimu Hakurei | `reimu_hakurei` | `reimu hakurei` | `touhou` | `brown hair, long hair, hair bow, red ribbon, brown eyes, miko, detached sleeves, red skirt, sarashi` |
| Agnes Tachyon (casual) | `agnes_tachyon_(casual)_(umamusume)` | `agnes tachyon \(casual\) \(umamusume\)` | `umamusume` | `large breasts, smug, off shoulder sweater, necklace, pendant` |

> Add newly researched characters to the table above for future reference.

---

## 9. Visual Quality & Prompt-Fidelity Verification Loop (5/5 Rating Standard)

Every time an image is generated and downloaded, the agent **MUST** visually inspect it using the `view_file` tool to evaluate whether it accurately satisfies the prompt and meets high aesthetic/anatomical standards.

### The 1 to 5 Rating Rubric

Evaluate the image across three core dimensions:
1. **Prompt Fidelity**: Did all 5 blocks manifest? (character identity & features, undress state, sexual act/position, contact dynamics, background).
2. **Anatomical Integrity**: Check hands/fingers, eyes/face symmetry, genital alignment, penetration mechanics, and perspective coherence.
3. **Artifacts & Style**: Ensure clean lines, no unintended censorship overlays, no distorted/extra limbs, and proper lighting contrast.

| Score | Criteria | Action |
| :---: | :--- | :--- |
| **1/5** | Severe failure: unrecognizable character, missing requested act, major body horror/deformities. | **Regenerate & replace prompt** |
| **2/5** | Poor: wrong pose/position, significant anatomical glitches (e.g. 6+ fingers, distorted face, misplaced genitalia). | **Regenerate & replace prompt** |
| **3/5** | Mediocre: recognizable character and act, but noticeable flaws (awkward hands, missing key outfit/setting tags, weird contact points). | **Regenerate & refine prompt** |
| **4/5** | Good: accurate character, correct act and setting, but minor imperfections (e.g. slightly messy hair clipping, minor hand oddity, subdued expression). | **Regenerate & tune prompt/seed** |
| **5/5** | **Flawless**: Complete alignment with all prompt blocks, pristine anatomy, expressive face, perfect act/penetration contact, stunning lighting and composition, zero fatal artifacts. | **Accepted & Saved** |

---

### Mandatory Visible Scoring Protocol

Whenever validating an image (whether an initial attempt or a subsequent re-roll), the agent **MUST explicitly write the score in the message output so the user can see it in real-time**:

```markdown
#### Visual Validation: `[image_name.png]`
- **Attempt**: #[N] (Seed: `[seed]`)
- **Score**: **`[X]/5`**
- **Prompt Fidelity**: [Analysis of 5 blocks: character identity, undress state, requested sexual act, contact dynamics, background]
- **Anatomy & Aesthetics**: [Hands, fingers, facial expression, genital alignment, lighting, perspective]
- **Verdict**: [ACCEPTED (5/5) / REJECTED (< 5/5)]
- **Action**: [Saved to assets / Re-rolling with new seed and prompt adjustment]
```

Never silently evaluate images or hide validation scores in internal thoughts. The user must be able to track every attempt's score, reason for rejection, and the resulting prompt adjustments.

---

### Dynamic Prompt Replacement & Refinement on Re-rolls (< 5/5)

When an image scores **below 5/5**, the agent **is explicitly authorized and expected to replace, modify, or overhaul the prompt so it fits what was intended**:

> [!IMPORTANT]
> **Do Not Rely Solely on Random Seeds**:
> If an image fails due to pose confusion, missing characters, extra limbs, bad angles, or unwanted clothing, blindly re-rolling seeds with the identical prompt will often reproduce the same bias. Analyze the visual failure and adapt the prompt.

#### Prompt Replacement Strategies:
1. **Pose & Position Overhaul**: If the model generated an incorrect or awkward position (e.g., flat missionary instead of an arched cowgirl), replace vague position tags with unambiguous, concrete posture tags (e.g. replace `sex` with `cowgirl position, straddling, riding partner's lap, thighs apart, upright torso, arched back`).
2. **Disambiguate Subject & Partner**: If extra limbs, clones, or duplicate male bodies appear in POV scenes, add strict negative tags (`2boys, multiple boys, multiple males, clone, extra limbs`) and enforce explicit camera tags (`pov, first-person view, pov hands on waist`).
3. **Clothing & Undress State Precision**: If clothing tags linger inappropriately, strip out ambiguous clothing tags and enforce explicit undress tags (`bottomless, nude, lifted shirt, partially unzipped jacket, bare breasts, exposed underarms`).
4. **Anatomical & Tactile Contact Anchors**: If hands or penetration points float disconnectively, add specific anchor tags (`holding hands, gripping partner's hips, hands on headboard, vaginal penetration, deep penetration`).
5. **Expression & Atmosphere Tuning**: If the character looks generic or dull, inject character-specific emotion tags (`flushed cheeks, heavy breathing, breathless, intense competitive grin, open mouth`).
6. **Transparent Logging of Prompt Changes**: When re-rolling, explicitly show the prompt adjustments made:
   ```markdown
   - **Prompt Adjustment**: Replaced `[old_tags]` with `[new_tags]` to correct [specific issue observed in attempt #N].
   ```

---

### The Regeneration Loop Protocol

```text
[Generate Image with Seed S and Prompt P] 
                   │
                   ▼
       [Download to Local Directory]
                   │
                   ▼
      [Inspect visually via view_file]
                   │
                   ▼
     [Score 1 to 5 based on Rubric]
                   │
                   ▼
     ★ [WRITE SCORE VISIBLY TO USER] ★
                   │
             ┌─────┴─────┐
          < 5/5        5/5
             │           │
             ▼           ▼
   [Diagnose Failure Mode]   [Accept & Save]
             │
             ▼
   ★ [Replace/Refine Prompt ★
   ★   + Pick New Seed]     ★
             │
             ▼
     [Re-queue Workflow]
```

1. **Mandatory Threshold**: An image is **only accepted if it scores 5/5**.
2. **Automated Re-roll with Prompt Replacement**: If the score is below 5, do NOT stop or deliver the sub-par result. Diagnose the defect, replace/refine the prompt to guide the diffusion model toward the intended composition, pick a fresh random seed (`random.randint(0, 2**32 - 1)`), and re-run.
3. **Seed Handling**: Always use a fresh random seed on every attempt. Never re-use a failed seed.
4. **Transparent Audit in User Output**: Always present:
   - Attempt history and all attempt scores (`X/5`)
   - The final accepted score (`5/5`)
   - Prompt fidelity breakdown
   - Anatomy and aesthetic breakdown
   - Exact prompt changes applied across iterations.

---

## 10. Field-Tested Failure Modes & Proven Prompt Remediation Strategies

For comprehensive documentation on common SDXL/Pony/Anima diffusion failure modes, detailed diagnostic breakdowns, and field-tested remediation rules, refer to the dedicated reference guide:

> **[references/failure-modes-and-remediations.md](references/failure-modes-and-remediations.md)**

### Key Failure Modes Cataloged in Reference:
1. **The "Floor Chest / Collarbone" Glitch**: Downward vertical POV in rear-entry/doggystyle -> use Side 3/4 Perspective.
2. **The "Motion Lines / Bouncing" Breast Ghosting Trap**: Bouncing/motion tags cause secondary flesh silhouettes/dual breasts -> express speed through diegetic consequences (`flying sweat droplets, panting, arched back`).
3. **The Athletic Environment "Spontaneous Swimsuit / Leotard" Bias**: Sport contexts force unwanted swimwear -> enforce `completely naked, bare skin` and negative bans.
4. **Multi-Partner / "2boys" Contamination**: Complex multi-action contact generates duplicate males -> anchor with `1boy, solo male, single male`.
5. **Inverted Perspective Collapse**: Top-down head-first views in post-coital aftermath invert limbs -> ground scene with side angles (`lying on side, cuddle, mutual exhaustion`).
6. **Character Uniform Tag Variants & Redundant Clothing Suppression**: Full uniform tags represent complete outfits -> remove generic clothing descriptors (`jacket, shirt`) to avoid overriding default uniform patterns.
7. **Facesitting & Downward 69 Oral "Severed Head" Glitch**: Direct top-down POV pins squashed/severed heads at bottom border -> switch to dynamic Side 3/4 perspective with braced limbs.

