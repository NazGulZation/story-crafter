# Krea 2 Photoreal Generation Reference

This reference covers photorealistic image generation (including explicit adult NSFW) with
Krea 2-architecture diffusion pipelines via the ComfyUI REST API. Parent skill mechanics
(API vs. frontend format, polling, downloads, 5/5 validation loop) live in `../SKILL.md`.
NSFW emphasis / batch learnings live in the companion reference `krea2-nsfw.md`.

> **Verified instance (example).** Anything marked `[verified instance]` below — timings,
> resolutions, file names, seeds, scores — was observed on one ComfyUI instance
> (RTX 4080 SUPER, ComfyUI v0.35.0, 2026-09-12) and proves the recipe works. It is not
> normative: adapt all file names, sizes, and step counts to whatever your server actually
> hosts (check via `/models/<folder>`).

---

## 1. How Krea 2 Differs from Anima

| Aspect | Anima (`anima_absolute_cinema.json`) | Krea 2 (`krea2 t2i workflow correct.json`) |
| :--- | :--- | :--- |
| Prompt style | Structured Danbooru tags, 5 paragraphs, spaces not underscores | **Natural-language photo descriptions** (amateur/smartphone-photo paragraphs, camera + lighting anchors) |
| Text encoder | `qwen_3_06b_base.safetensors` | **Qwen3-VL-family weights** (e.g. `Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors` [verified instance]) with CLIPLoader `type: "krea2"` (uncensored build required for NSFW) |
| Conditioning | 1024-feature | **12x2560 = 30720-feature** (12-layer Qwen3-VL stack). Wrong encoder family = instant `ValueError` (see §4.1) |
| Sampler | High-step multi-pass + refiner | **Single pass: 10–15 steps, `euler` / `beta`, cfg `1.0`** via `KSamplerAdvanced` (10 = fast default, 15 = preferred for finals — see `krea2-nsfw.md` §4) |
| Resolution | 832x1216 base + 1.4x latent upscale | **Single pass at target size** (e.g. 888x1176 [verified instance]), **no upscale** (optional upscaler branch excluded — see §3) |
| Negative prompt | Long Danbooru ban list | **Empty string** (`""`) |

---

## 2. Model Requirements (check via `/models/<folder>`)

Before queuing anything, list what your server actually hosts. Krea 2 needs:

| Role | Folder | Requirement |
| :--- | :--- | :--- |
| UNET | `diffusion_models` | A **Krea2-architecture** checkpoint. The file name need not contain `krea2`. Acceptance test: it pairs with a Qwen3-VL `type: "krea2"` encoder with zero `node_errors` — a non-VL encoder fails against it with the §4.1 `ValueError`. |
| Text encoder | `text_encoders` | **Qwen3-VL-family** weights loaded with CLIPLoader `type: "krea2"`. For NSFW it must be an **uncensored/abliterated** build. Never substitute a non-VL encoder (e.g. Anima's). |
| VAE | `vae` | A compatible VAE (e.g. `qwen_image_vae.safetensors` [verified instance]). |
| LoRAs | `loras` | Optional — default to none unless a compatible LoRA is confirmed on-server. |
| Upscaler branch (e.g. SeedVR2) | vendor folder | Optional — if its models are absent server-side, exclude the whole branch from the API prompt (§3). |

> **Verified-instance snapshot (example, 2026-09-12).** UNET in use:
> `museByStableYogi_v35Int8Extended.safetensors` — despite the name, the server identifies
> this checkpoint as Krea2-architecture (Anima's `qwen_3_06b_base` encoder fails against it;
> the Huihui Qwen3-VL encoder with `type: "krea2"` queues cleanly and completes at 888x1176
> in ~10s). No file named `krea2*` existed in `diffusion_models/`; `seedvr2/` was empty.
> If nominal `krea2_turbo_bf16.safetensors` weights are ever uploaded, swap only `unet_name` —
> nothing else changes.

---

## 3. Minimal API Prompt

The bundled `krea2 t2i workflow correct.json` generally **cannot be queued as-is**:

1. `SetNode` / `GetNode` sampler-plumbing custom nodes may be **not installed** (check `/object_info`).
   Fix: delete the Set/Get chain and write sampler values **directly** into `KSamplerAdvanced`.
2. Frontend-bypassed nodes (`"mode": 4` — upscaler branch, `ModelAttentionBackend`, previews,
   comparers) must be **excluded** from the API prompt — the frontend→API converter drops the
   `mode` flag, so they would otherwise execute and fail on missing models.
3. Server-disk writers (e.g. `Image Save (was-ns)`) don't return bytes; for API retrieval add a
   standard `SaveImage` node and download via `/view`.

Minimal prompt (11 nodes). Copy verbatim; replace `UNET_NAME`, `CLIP_NAME`, `VAE_NAME`,
`PROMPT_TEXT`, `SEED`, `WIDTH`/`HEIGHT`, and `STEPS`:

```json
{
  "58": {"class_type": "UNETLoader", "inputs": {
    "unet_name": "UNET_NAME", "weight_dtype": "default"}},
  "37": {"class_type": "CLIPLoader", "inputs": {
    "clip_name": "CLIP_NAME",
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
    "width": WIDTH, "height": HEIGHT, "batch_size": 1}},
  "7": {"class_type": "KSamplerAdvanced", "inputs": {
    "add_noise": "enable", "noise_seed": SEED, "steps": STEPS, "cfg": 1.0,
    "sampler_name": "euler", "scheduler": "beta",
    "start_at_step": 0, "end_at_step": 10000, "return_with_leftover_noise": "disable",
    "model": ["39", 0], "positive": ["41", 0],
    "negative": ["67", 0], "latent_image": ["69", 0]}},
  "3": {"class_type": "VAELoader", "inputs": {"vae_name": "VAE_NAME"}},
  "10": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
  "save": {"class_type": "SaveImage", "inputs": {
    "images": ["10", 0], "filename_prefix": "krea2"}}
}
```

Node roles: `58` diffusion model · `37` uncensored text encoder · `39` LoRA passthrough (keep `loras: []`
unless a compatible LoRA is confirmed on-server) · `40` trigger passthrough · `41` positive prompt ·
`67` negative (always `""`) · `69` latent size · `7` sampler · `3`/`10` VAE decode · `save` API download hook.

Starting values [verified instance]: `WIDTH 888`, `HEIGHT 1176`, `STEPS 10` (15 for final-quality
runs — finer micro-detail at negligible extra cost, see `krea2-nsfw.md` §4), `cfg 1.0`,
`euler`/`beta`, negative `""`.

### Runner script

`../scripts/krea2_generate.py` builds exactly the prompt above (defaults: 888x1176, 10 steps,
`euler`/`beta`, cfg `1.0` — all overridable via flags) and handles queue → poll → download:

```powershell
# Prompt from file + random seed
python .agents/skills/comfyui-generation/scripts/krea2_generate.py `
  --server "<SERVER-URL>" `
  --prompt-file "prompt.txt" `
  --randomize-seed `
  --output-dir "<OUTPUT-DIR>"

# Inline prompt + fixed seed + custom steps (e.g. 15 for finals)
python .agents/skills/comfyui-generation/scripts/krea2_generate.py `
  --server "<SERVER-URL>" `
  --prompt "Amateur smartphone photo of ..." `
  --seed SEED --steps STEPS `
  --output-dir "<OUTPUT-DIR>"
```

> Verified-instance example: `--server "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/"`,
> `--output-dir "C:\StoryCrafter\assets"`, ~10s per image; first successful NSFW generation at
> seed `2148589397` (`assets/krea2_nsfw_test_00001_.png`, 4/5 — only miss: `twintails` rendered
> as single ponytail).

---

## 4. Failure Modes Seen in the Field (each: symptom → cause → fix)

1. **`Krea2 expects conditioning with 12x2560=30720 features ... but got 1024`**
   Cause: the UNET received conditioning from a non-VL encoder (e.g. Anima's `qwen_3_06b_base`).
   Fix: CLIPLoader must point at Qwen3-VL-family weights with `"type": "krea2"`.
   Never substitute a non-VL encoder on a Krea2-architecture UNET.
2. **`node_errors` naming `SetNode` / `GetNode` on queue.** Cause: the workflow file's
   sampler-plumbing custom nodes aren't installed server-side. Fix: strip them, hardcode
   `steps/cfg/sampler/scheduler` into `KSamplerAdvanced` (§3).
3. **Upscaler / attention-backend execution errors.** Cause: frontend-bypassed (`mode: 4`) nodes
   (upscaler branch, `ModelAttentionBackend`) leak into the API prompt with no backing models.
   Fix: exclude every `mode != 0` node.
4. **No images returned via `/view`.** Cause: relying on a server-disk writer node
   (e.g. `Image Save (was-ns)`). Fix: always include a core `SaveImage` node and filter
   downloads to `type == "output"`.

---

## 5. Krea 2 Prompting Guide (photoreal base; NSFW specialization in `krea2-nsfw.md`)

Write **3 natural-language paragraphs**, comma-separated photographic clauses — not Danbooru tags:

1. **Subject paragraph**: `Amateur <device> photo of <age band> <subject>, <hair>, <expression
   with moaning/embarrassment cues>, <skin>, <build + bust>, <pose anchored to furniture/other body>,
   <who touches what — disambiguate every hand>, <exact undress state per garment + act with
   (emphasis:1.1–1.4) if NSFW>.` Age bands only (`young adult woman`, `adult man`) — no exact
   numbers, no `fictional` (see `krea2-nsfw.md` §1). NSFW act anchors, emphasis weights, and
   clothing-suppression syntax: follow `krea2-nsfw.md` §§2, 5–6.
2. **Setting paragraph**: room, furniture, props, wall/ceiling details, light sources.
3. **Camera paragraph**: device aesthetic (`raw smartphone photo`, `flash photo`, `VHS camcorder`),
   shot scale/angle (rear-entry: side 3/4 at hip height — see `krea2-nsfw.md` §5 rule 3),
   depth of field, lighting direction + color temperature, film artifacts if wanted
   (`grain`, `scan lines`, `tracking distortion`), plus `(suppressions:0.4–0.8)` if needed.

Keep the negative prompt `""`. Randomize the seed every attempt
(`random.randint(0, 2**32 - 1)`). Composition: prefer 1–2 subjects with at most one sharp face
for first attempts; disambiguate or hide every hand per `krea2-nsfw.md` §5 rules 4–6.
Avoid real-person names/likenesses in sexual prompts.

Example archetypes [verified instance]: lakeside standing from-behind ·
kneeling oral selfie · multi-person party embarrassment scene · found-footage VHS dual-oral POV ·
rear-entry couch close-up looking back at camera. Latest proofs: see `krea2-nsfw.md` §§3–4.

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

## 7. Using Nominal Krea 2 Weights (optional)

Where the vendor publishes nominal weights (e.g. `Comfy-Org/Krea-2`: a `krea2_turbo`/`krea2_raw`
checkpoint for `diffusion_models/`, matching Qwen3-VL weights for `text_encoders/`, and a
compatible VAE for `vae/` — see the workflow file's Notes node for the exact set):

1. Download the checkpoints plus the matching text-encoder and VAE weights.
2. Upload them to the corresponding `models/` folders on your instance.
3. Re-verify via `/models/diffusion_models`, then swap only `58.inputs.unet_name` in §3 —
   encoder type stays `"krea2"`, sampler values unchanged. Re-run the §3 script as smoke test.
