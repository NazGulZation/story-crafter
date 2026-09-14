---
name: comfyui-generation
description: >-
  Generate images and run diffusion workflows using local or remote ComfyUI instances (e.g. SaladCloud, RunPod, localhost:8188).
  Covers health check verification (/system_stats), automated conversion of frontend UI workflow JSON to ComfyUI API prompt format,
  dynamic parameter overrides (prompts, seeds, dimensions, samplers), portrait and landscape orientation control (base + LatentUpscale sizing),
  job queueing (/prompt), execution polling (/history/{prompt_id}),
  output asset retrieval (/view), Danbooru-tag prompt engineering, tag emphasis weighting ((tag:1.2)), asset naming conventions ({char}_{attrs}_{n}.png),
  visible validation scoring, prompt replacement/refinement on re-rolls (< 5/5), and visual quality verification loop (5/5 rating standard).
  Also covers Krea 2 photorealistic generation via references/krea2-generation.md and scripts/krea2_generate.py.
---

# ComfyUI Image Generation & Workflow Execution

Automate diffusion model image generation through ComfyUI instances over HTTP/REST API. Works seamlessly with local setups (`http://127.0.0.1:8188`) or cloud serverless/dedicated nodes (SaladCloud, RunPod, Vast.ai).

---

## 1. ComfyUI REST API Architecture

ComfyUI exposes a straightforward HTTP REST interface:

| Endpoint | Method | Purpose |
| :--- | :--- | :--- |
| `/system_stats` | `GET` | Health check: returns ComfyUI version, Python/PyTorch versions, GPU name, VRAM totals/free. |
| `/prompt` | `POST` | Queue a workflow prompt. Payload: `{"prompt": <api_prompt_dict>}`. Returns `{"prompt_id": "...", "number": int, "node_errors": {}}`. |
| `/history/{prompt_id}` | `GET` | Execution status and generated output metadata. Returns status (`success` \| `error`) and output file names. |
| `/view` | `GET` | Retrieve image files: `/view?filename=<name>&subfolder=<subfolder>&type=output`. |
| `/queue` | `GET` | Inspect current queue running and pending items. |
| `/interrupt` | `POST` | Abort current generation. |

---

## 2. Frontend Workflow JSON vs. API Prompt Format

Exported workflows from the ComfyUI canvas are in **Graph UI format** (containing `"nodes"` and `"links"`), which is **not** accepted directly by `/prompt`.

### API Prompt Format (Required by `/prompt`):
A flat JSON object mapping string `node_id` to its specification:
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
3. **Map Widget Inputs**: Pull inputs from `widgets_values_named`. Exclude UI-only controls.
4. **Resolve Connections**: For each entry in `node["inputs"]`, look up `link_id` and assign `[str(source_node_id), source_slot_index]`.

---

## 3. Reusable Runner Script & CLI Reference

A complete runner utility is provided at:
`.agents/skills/comfyui-generation/scripts/comfyui_runner.py`

### Key CLI Parameters:

| Flag | Type | Description |
| :--- | :--- | :--- |
| `--server` | URL | ComfyUI server base URL (e.g. `$env:COMFYUI_SERVER_URL` or `http://127.0.0.1:8188`). |
| `--workflow` | File | Path to workflow JSON file (UI or API format). |
| `--prompt` | String | Override positive prompt text in `CLIPTextEncode` nodes. |
| `--seed` | Int | Specific seed (0 to `4294967295`). |
| `--randomize-seed` | Flag | Generate a fresh random seed for this run. |
| `--steps` | Int | Override sampler step count. |
| `--width / --height` | Int | Override base latent dimensions (must be multiples of 8). |
| `--upscale-factor` | Float | Multiplier for auto-deriving `LatentUpscale` dimensions (default: `1.4`). |
| `--output-dir` | Path | Directory where generated images are saved (default: `assets/`). |
| `--stats-only` | Flag | Perform server health check without queuing jobs. |

### Command Examples:

```powershell
# 1. Health check
python .agents/skills/comfyui-generation/scripts/comfyui_runner.py `
  --server "$env:COMFYUI_SERVER_URL" `
  --workflow "anima_absolute_cinema.json" `
  --stats-only

# 2. Standard portrait run with random seed
python .agents/skills/comfyui-generation/scripts/comfyui_runner.py `
  --server "$env:COMFYUI_SERVER_URL" `
  --workflow "anima_absolute_cinema.json" `
  --prompt "masterpiece, best quality, 1girl, silver hair, glowing eyes, cinematic lighting" `
  --randomize-seed `
  --output-dir "assets"

# 3. Landscape run (auto-derives upscale to preserve orientation: 1216x832 -> 1704x1168)
python .agents/skills/comfyui-generation/scripts/comfyui_runner.py `
  --server "$env:COMFYUI_SERVER_URL" `
  --workflow "anima_absolute_cinema.json" `
  --width 1216 --height 832 `
  --randomize-seed `
  --output-dir "assets/landscape"
```

---

## 4. Python Implementation Pattern

When embedding generation into standalone scripts, use standard library `urllib` (zero external dependencies):

```python
import json, os, time, urllib.parse, urllib.request

def queue_workflow(server_url: str, api_prompt: dict) -> str:
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(f"{server_url}/prompt", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("node_errors"):
            raise ValueError(f"Node errors: {res['node_errors']}")
        return res["prompt_id"]

def wait_and_download(server_url: str, prompt_id: str, output_dir: str, poll_interval=5, timeout=600):
    elapsed = 0
    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval
        req = urllib.request.Request(f"{server_url}/history/{prompt_id}")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
        if prompt_id in data:
            res = data[prompt_id]
            if res.get("status", {}).get("status_str") == "error":
                raise RuntimeError(res["status"].get("messages"))
            for node_id, out in res.get("outputs", {}).items():
                for img in out.get("images", []):
                    if img.get("type") == "temp":
                        continue
                    params = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
                    dest = os.path.join(output_dir, img["filename"])
                    with urllib.request.urlopen(f"{server_url}/view?{params}", timeout=60) as r, open(dest, "wb") as f:
                        f.write(r.read())
            return
    raise TimeoutError("Prompt timed out")
```

---

## 5. Diffusion Prompt Architecture & Tagging Principles

Anima and modern diffusion text encoders achieve highest compositional fidelity when using structured Danbooru tags separated into 5 discrete paragraphs (`\n\n`):

### The 5-Block Prompt Template:
```text
masterpiece, best quality, ultra detailed anime coloring, anime screenshot,

{main_character_and_appearance}

{secondary_character_or_pov_protagonist}

{action_pose_or_contact_choreography}

{environment_lighting_and_background}
```

### Universal Tagging Principles:
1. **Dress State & Asymmetry**:
   - Both unclothed: explicitly tag `completely naked, bare skin`.
   - Asymmetric (female clothed, male nude): tag `clothed female nude male`.
   - Asymmetric (male clothed, female nude): tag `clothed male nude female`.
2. **Costume & Uniform Tag Handling**:
   - *Suppress Redundant Generics*: When using an official full uniform tag, remove vague generic descriptors (`jacket, shirt, skirt, clothes`) that create competing signals.
   - *Decompose Elaborate Costumes*: If an elaborate outfit defaults to plain clothes, decompose the attire into **3–5 iconic structural pieces** (e.g. specific headwear, corset/vest, collar, signature sleeves, skirt type).
3. **POV & Self-Insert Protagonist Tagging ("You")**:
   - In first-person or second-person scenes, **always tag `faceless male` or `faceless female`** with `eyes hidden`.
   - *What faceless means*: Eyes hidden or cropped out of frame, not head removed. A visible jaw, chin, or shoulder preserves scale while keeping focus on the partner.
   - Negate with `male eyes, detailed eyes on male` to prevent distracting eyes from breaking immersion.
4. **Tag Emphasis Syntax**:
   - Use `(tag:weight)` syntax to adjust attention: `(side view:1.2)`, `(pov:0.7)`. Useful range is `0.5` to `1.4`. Above `1.4` risks color burning.
5. **Standard Negative Prompt**:
   ```text
   worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, ugly, disfigured, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor
   ```

> For exhaustive character tag reference catalogs and pose libraries, see:
> **[references/anima-nsfw-prompting.md](references/anima-nsfw-prompting.md)**

---

## 6. Canonical Character Tag Research Protocol

When generating established fictional or media characters, **always perform tag research before building the prompt**:
1. **Identify the canonical Danbooru tag**: `[character_name]_(series)` (e.g. `reimu_hakurei`, `rem_(re_zero)`). Use `search_web` to verify tags.
2. **Verify canonical appearance attributes**: Hair color/length/style, eye color, signature clothing items, and accessories.
3. **Convert underscores to spaces**: Text encoders are trained on space-separated tokens. Replace `_` with a space: `reimu_hakurei` -> `reimu hakurei`.

---

## 7. Visual Quality Verification Loop (5/5 Rating Standard)

Every generated image must be inspected using `view_file` to evaluate prompt fidelity and anatomy:

### The 1 to 5 Rating Rubric:
- **1/5 (Severe Failure)**: Unrecognizable character, missing requested act, major body horror/deformity. -> *Regenerate & overhaul prompt*.
- **2/5 (Poor)**: Wrong pose/position, significant anatomical glitches (extra limbs, distorted face). -> *Regenerate & overhaul prompt*.
- **3/5 (Mediocre)**: Recognizable, but noticeable flaws (awkward hands, missing outfit details, floating contact). -> *Regenerate & refine prompt*.
- **4/5 (Good)**: Minor flaws only (slightly messy hair clipping, minor hand oddity, subdued expression). -> *Tune prompt/seed*.
- **5/5 (Flawless)**: Complete alignment with all prompt blocks, pristine anatomy, expressive face, perfect contact, clean lighting. -> **Accepted & Saved**.

### Mandatory Visible Scoring Protocol:
Whenever validating an image, write the score in the message output so the user can see it in real time:

```markdown
#### Visual Validation: `[image_name.png]`
- **Attempt**: #[N] (Seed: `[seed]`)
- **Score**: **`[X]/5`**
- **Prompt Fidelity**: [Character identity, undress state, requested action, background]
- **Anatomy & Aesthetics**: [Hands, facial expression, alignment, lighting]
- **Verdict**: [ACCEPTED (5/5) / REJECTED (< 5/5)]
- **Action**: [Saved to assets / Re-rolling with new seed and prompt adjustment]
```

### Prompt Replacement Strategies on Re-rolls (< 5/5):
- *Pose Overhaul*: Replace vague posture tags with concrete angle and body tags (e.g., `(side view:1.2), arched back, thighs apart`).
- *Subject Disambiguation*: If duplicate bodies appear in POV scenes, enforce `1boy, solo male, pov` and negative `2boys, multiple males, clone`.
- *Contact Anchors*: Anchor floating limbs to specific targets (`hands gripping partner's hips, deep penetration`).

---

## 8. Orientation & Landscape Management

Default diffusion workflows are often portrait-native (`832x1216` -> upscale `1168x1704`).

### The LatentUpscale Trap & Resolution:
- Overriding only the base `EmptyLatentImage` to landscape leaves the second-pass upscale node in portrait, causing the refiner to stretch the image back to portrait.
- The runner automatically sets **both** nodes: `--width/--height` sets the base, and `LatentUpscale` auto-derives as `round(base * --upscale-factor / 8) * 8` (default factor 1.4: `1216x832` -> `1704x1168`).
- **Prompting for Wide Frames**: Prefer horizontal compositions (reclined, side 3/4, wide bed setting); add `cinematic wide shot, horizontal composition` and negative `portrait, vertical composition, tall image`.

---

## 9. Asset Naming & Clean Deliverables

1. **Naming Format**: `{char}_{attrs}_{n}.png` (all lowercase, underscores only).
   - Examples: `heroine_naked_1.png`, `heroine_clothed_2.png`.
2. **Subfolder Organization**: Organize assets by character or story project under `assets/`.
3. **No Sidecars in Deliverables**: Delete ephemeral `.txt` seed logs before handover. Seeds belong in runner logs, not in final filenames.

---

## 10. Krea 2 Photoreal Generation (incl. Adult Content)

For photorealistic, natural-language smartphone-photo workflows (`krea2 t2i workflow correct.json`):
- Uses Qwen3-VL encoder pairing (`type: "krea2"`) with single-pass 10–15 step `euler`/`beta` sampling.
- Quick start via runner script:
  ```powershell
  python .agents/skills/comfyui-generation/scripts/krea2_generate.py `
    --server "$env:COMFYUI_SERVER_URL" `
    --prompt "Amateur smartphone photo of ..." `
    --randomize-seed `
    --output-dir "assets"
  ```
- Detailed mechanics and age-band prompt guides are documented in:
  - **[references/krea2-generation.md](references/krea2-generation.md)**
  - **[references/krea2-nsfw.md](references/krea2-nsfw.md)**
