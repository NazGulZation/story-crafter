# Krea 2 Photoreal Generation Reference

This reference covers photorealistic image generation (including explicit adult NSFW) with
Krea 2-architecture diffusion pipelines via the ComfyUI REST API. Parent skill mechanics
(API vs. frontend format, polling, downloads, 5/5 validation loop) live in `../SKILL.md`.

Field-tested against `https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/` (RTX 4080 SUPER,
ComfyUI v0.35.0) on 2026-09-12. First successful NSFW generation: seed `2148589397`,
`assets/krea2_nsfw_test_00001_.png` (scored 4/5 — only miss: `twintails` rendered as single ponytail).
Batch proof: 5 sexual-act images in one session, 2× 5/5 + 3× 4/5, ~10s each.

---

## 1. How Krea 2 Differs from Anima

| Aspect | Anima (`anima_absolute_cinema.json`) | Krea 2 (`krea2 t2i workflow correct.json`) |
| :--- | :--- | :--- |
| Prompt style | Structured Danbooru tags, 5 paragraphs, spaces not underscores | **Natural-language photo descriptions** (amateur/smartphone-photo paragraphs, camera + lighting anchors) |
| Text encoder | `qwen_3_06b_base.safetensors` | `Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors` with CLIPLoader `type: "krea2"` (uncensored — required for NSFW) |
| Conditioning | 1024-feature | **12x2560 = 30720-feature** (12-layer Qwen3-VL stack). Wrong encoder = instant `ValueError` (see §4) |
| Sampler | High-step multi-pass + refiner | **Single pass: 10 steps, `euler` / `beta`, cfg `1.0`** via `KSamplerAdvanced` |
| Resolution | 832x1216 base + 1.4x latent upscale | **Single pass 888x1176, no upscale** (SeedVR2 branch is bypassed) |
| Negative prompt | Long Danbooru ban list | **Empty string** (`""`) |

---

## 2. Server Model Inventory (verified 2026-09-12 via `/models/<folder>`)

| Folder | Present | Missing (do NOT reference) |
| :--- | :--- | :--- |
| `diffusion_models` | `museByStableYogi_v35Int8Extended.safetensors`, `divingAnima_v70.safetensors` | `krea2_turbo_bf16.safetensors`, `krea2_raw_bf16.safetensors` (no file named `krea2*` exists) |
| `text_encoders` | `Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors` ✅, `qwen_3_06b_base.safetensors` | `qwen3vl_4b_bf16.safetensors` |
| `vae` | `qwen_image_vae.safetensors` ✅ | `wan_2.1_vae.safetensors` |
| `loras` | assorted Anima character LoRAs | `krea2_turbo_lora_rank_64_bf16.safetensors` |
| `seedvr2` | (empty) | everything — SeedVR2 branch can never run here |

> [!IMPORTANT]
> **The UNET to use is `museByStableYogi_v35Int8Extended.safetensors`.** Despite the name, the
> server itself identifies this checkpoint as Krea2-architecture: pairing it with Anima's
> `qwen_3_06b_base` encoder fails with `Krea2 expects conditioning with 12x2560=30720 features
> (a 12-layer Qwen3-VL stack) but got 1024. Load the text encoder with CLIPLoader type 'krea2'.`
> Paired with the Huihui encoder (`type: "krea2"`) it queues with zero `node_errors` and
> completes in ~10s at 888x1176. If a real `krea2_turbo_bf16.safetensors` is ever uploaded to
> `models/diffusion_models/`, swap only the `unet_name` — nothing else changes.

---

## 3. Proven Minimal API Prompt

The file `krea2 t2i workflow correct.json` **cannot be queued as-is** on this server:

1. `SetNode` / `GetNode` custom node types are **not installed** (`/object_info` check: MISSING).
   Fix: delete the Set/Get chain and write sampler values **directly** into `KSamplerAdvanced`.
2. Nodes with `"mode": 4` (bypassed: all SeedVR2 nodes, `ModelAttentionBackend`, previews,
   comparers) must be **excluded** from the API prompt — the frontend→API converter drops the
   `mode` flag, so they would otherwise execute and fail on missing `seedvr2/` models.
3. `Image Save (was-ns)` writes to the server disk; for API retrieval add a standard
   `SaveImage` node and download via `/view`.

Minimal working prompt (11 nodes). Copy verbatim, replace `PROMPT_TEXT` and `SEED`:

```json
{
  "58": {"class_type": "UNETLoader", "inputs": {
    "unet_name": "museByStableYogi_v35Int8Extended.safetensors", "weight_dtype": "default"}},
  "37": {"class_type": "CLIPLoader", "inputs": {
    "clip_name": "Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors",
    "type": "krea2", "device": "default"}},
  "39": {"class_type": "Lora Loader (LoraManager)", "inputs": {
    "text": "", "loras": [], "model": ["58", 0], "clip": ["37", 0]}},
  "40": {"class_type": "TriggerWord Toggle (LoraManager)", "inputs": {
    "group_mode": true, "default_active": true, "allow_strength_adjustment": false,
    "toggle_trigger_words": [], "orinalMessage": "", "trigger_words": ["39", 2]}},
  "41": {"class_type": "Prompt (LoraManager)", "inputs": {
    "text": "PROMPT_TEXT", "clip": ["39", 1], "trigger_words1": ["40", 0]}},
  "67": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["39", 1]}},
  "69": {"class_type": "EmptyLatentImage", "inputs": {
    "width": 888, "height": 1176, "batch_size": 1}},
  "7": {"class_type": "KSamplerAdvanced", "inputs": {
    "add_noise": "enable", "noise_seed": SEED, "steps": 10, "cfg": 1.0,
    "sampler_name": "euler", "scheduler": "beta",
    "start_at_step": 0, "end_at_step": 10000, "return_with_leftover_noise": "disable",
    "model": ["39", 0], "positive": ["41", 0],
    "negative": ["67", 0], "latent_image": ["69", 0]}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
  "10": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
  "save": {"class_type": "SaveImage", "inputs": {
    "images": ["10", 0], "filename_prefix": "krea2"}}
}
```

Node roles: `58` diffusion model · `37` uncensored text encoder · `39` LoRA passthrough (keep `loras: []`
unless a compatible LoRA is confirmed on-server) · `40` trigger passthrough · `41` positive prompt ·
`67` negative (always `""`) · `69` latent size · `7` sampler · `3`/`10` VAE decode · `save` API download hook.

### Runner script

`../scripts/krea2_generate.py` builds exactly the prompt above and handles queue → poll → download:

```powershell
# NSFW test (proven 2026-09-12, ~10s on RTX 4080 SUPER)
python .agents/skills/comfyui-generation/scripts/krea2_generate.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/" `
  --prompt-file "prompt.txt" `
  --randomize-seed `
  --output-dir "C:\StoryCrafter\assets"

# Inline prompt + fixed seed + custom steps
python .agents/skills/comfyui-generation/scripts/krea2_generate.py `
  --server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/" `
  --prompt "Amateur smartphone photo of ..." `
  --seed 2148589397 --steps 10 `
  --output-dir "C:\StoryCrafter\assets"
```

---

## 4. Failure Modes Seen in the Field (all verified, with fixes)

1. **`Krea2 expects conditioning with 12x2560=30720 features ... but got 1024`**
   Cause: UNET got conditioning from `qwen_3_06b_base` (Anima's encoder) instead of a Qwen3-VL
   stack. Fix: CLIPLoader must be `Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors` with
   `"type": "krea2"`. Never substitute Anima's encoder on a Krea2-architecture UNET.
2. **`node_errors` naming `SetNode` / `GetNode` on queue.** Cause: workflow file's sampler-plumbing
   nodes aren't installed server-side. Fix: strip them, hardcode `steps/cfg/sampler/scheduler`
   into `KSamplerAdvanced` (§3).
3. **SeedVR2 / `ModelAttentionBackend` execution errors.** Cause: bypassed (`mode: 4`) frontend
   nodes leak into the API prompt with no backing models. Fix: exclude every `mode != 0` node.
4. **No images returned via `/view`.** Cause: relying on `Image Save (was-ns)`. Fix: always include
   a core `SaveImage` node and filter downloads to `type == "output"`.

---

## 5. Krea 2 Prompting Guide (photoreal + NSFW)

Write **2–4 natural-language paragraphs**, comma-separated photographic clauses — not Danbooru tags:

1. **Subject paragraph**: `Amateur <device> photo of <explicit adult age> <subject>, <hair>, <expression
   with moaning/embarrassment cues>, <skin>, <build + bust>, <pose anchored to furniture/other body>,
   <who touches what — disambiguate every hand>, <exact undress state per garment>.`
2. **Act paragraph** (NSFW): name the act, entry angle, and visible contact
   (`penetrating her from behind`, `hands spread her ass cheeks`, `saliva on penis`). State adult age
   explicitly (`fictional 21-year-old`, `25 years old`) in the prompt itself.
3. **Setting paragraph**: room, furniture, props, wall/ceiling details.
4. **Camera paragraph**: device aesthetic (`raw smartphone photo`, `flash photo`, `VHS camcorder`),
   shot scale/angle, depth of field, lighting direction + color temperature, film artifacts if wanted
   (`grain`, `scan lines`, `tracking distortion`).

Keep the negative prompt `""`. Randomize the seed every attempt
(`random.randint(0, 2**32 - 1)`). Multi-person scenes (3+ faces) smear anatomy — prefer 1–2 subjects
with at most one visible face for first attempts. Avoid real-person names/likenesses in sexual prompts.

Verified prompt archetypes (all generated 2026-09-12): lakeside standing from-behind ·
kneeling oral selfie · 4-person party missionary embarrassment scene · found-footage VHS dual-oral POV ·
rear-entry couch close-up looking back at camera.

---

## 6. Validation & Acceptance

1. Download only `type == "output"` images; inspect every result with the file-view tool.
2. Score visibly (Prompt Fidelity / Anatomy & Aesthetics / Artifacts), same 1–5 rubric as
   `../SKILL.md` §9 — photorealism replaces anime coloring as the style bar
   (skin texture, flash/VHS artifacts intentional only if prompted, no extra digits/limbs,
   genital-contact coherence, symmetric face unless expression demands otherwise).
3. Below 5/5: diagnose, rewrite the failing clause in plain language (pose, hand ownership,
   garment state, camera angle — never just re-roll the seed), pick a fresh seed, re-queue.
4. Log seed, sampler values, and prompt deltas per attempt so runs are reproducible.

---

## 7. Enabling Nominal Krea 2 (optional server upgrade)

1. Download `krea2_turbo_bf16.safetensors` (or raw) from `Comfy-Org/Krea-2`
   (`diffusion_models/`), plus `qwen3vl_4b_bf16.safetensors` (`text_encoders/`) and
   `wan_2.1_vae.safetensors` (`vae/`) per the workflow file's Notes node.
2. Upload to the corresponding `models/` folders on the SaladCloud instance.
3. Re-verify via `/models/diffusion_models`, then swap only `58.inputs.unet_name` in §3 —
   encoder type stays `"krea2"`, sampler values unchanged. Re-run the §3 script as smoke test.
