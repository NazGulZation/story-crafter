"""
Generate Rem (Re:Zero) NSFW image with randomized seed.
Applies:
  - Canonical Danbooru tag research (Rem from Re:Zero)
  - No underscores in prompt tags (spaces used)
  - 5-block Danbooru prompt architecture
  - Randomized seed (0 to 2^32 - 1)
"""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFYUI_URL   = "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud"
WORKFLOW_PATH = r"C:\StoryCrafter\anima_absolute_cinema.json"
OUTPUT_DIR    = r"C:\StoryCrafter"

NEG_PROMPT = (
    "worst quality, low quality, early, old, score_1, score_2, score_3, "
    "cartoon, graphic, painting, crayon, graphite, abstract, glitch, "
    "deformed, mutated, ugly, disfigured, bad anatomy, bad hands, "
    "missing fingers, extra fingers, extra digits, fewer digits, cropped, "
    "very displeasing, artist name, blurry, jpeg artifacts, lowres, censor"
)

# 5-Block Danbooru Architecture (No underscores, spaces only)
REM_PROMPT = (
    "masterpiece, best quality, score_9, score_8, score_7, year 2025, newest, highres, absurdres, very aesthetic,\n\n"
    "1girl, rem \\(re:zero\\), re:zero, blue hair, short hair, hair ornament, hair ribbon, maid headdress, blue eyes, "
    "blush, heavy breathing, parted lips, drooling, maid apron, maid collar, detached sleeves, lifted skirt, no panties, "
    "large breasts, pussy, shaved pussy, on back, spread legs, arched back,\n\n"
    "1boy, pov, pov hands, large penis, gripping thighs, clothed female nude male,\n\n"
    "vaginal, sex, missionary, deep penetration, hard thrusting, dripping fluids, pussy juice, sweat, trembling, steaming body,\n\n"
    "scenery, mansion bedroom, roswaal mansion, luxurious bed, velvet sheets, pillows, candelabra, warm ambient lighting, depth of field"
)

def random_seed():
    return random.randint(0, 2**32 - 1)

def load_workflow(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def convert_to_api(workflow):
    link_map = {}
    for lnk in workflow.get("links", []):
        link_map[lnk[0]] = (str(lnk[1]), lnk[2])

    api = {}
    for node in workflow.get("nodes", []):
        ctype = node.get("type", "")
        if ctype in ("Note", "MarkdownNote"):
            continue
        nid = str(node["id"])
        inp = {}
        for k, v in node.get("widgets_values_named", {}).items():
            if k == "control_after_generate":
                continue
            inp[k] = v
        for conn in node.get("inputs", []):
            lid = conn.get("link")
            if lid is not None and lid in link_map:
                inp[conn["name"]] = list(link_map[lid])
        api[nid] = {"class_type": ctype, "inputs": inp}
    return api

def override_prompts(api, pos_text, neg_text, seed):
    for nid, node in api.items():
        ctype = node["class_type"]
        inp   = node["inputs"]
        if ctype == "CLIPTextEncode":
            if nid == "11":
                inp["text"] = pos_text
            elif nid == "12":
                inp["text"] = neg_text
        if ctype in ("KSampler", "KSamplerAdvanced"):
            for key in ("seed", "noise_seed"):
                if key in inp:
                    inp[key] = seed
    return api

def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def get_json(url, timeout=15):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def queue_and_wait(api_prompt, label, timeout=600, poll=5):
    resp = post_json(f"{COMFYUI_URL}/prompt", {"prompt": api_prompt})
    if resp.get("node_errors"):
        raise RuntimeError(f"Node errors: {resp['node_errors']}")
    pid = resp["prompt_id"]
    print(f"Queued -> prompt_id: {pid}")

    elapsed = 0
    while elapsed < timeout:
        time.sleep(poll)
        elapsed += poll
        try:
            hist = get_json(f"{COMFYUI_URL}/history/{pid}")
        except Exception:
            continue
        if pid not in hist:
            print(f"Waiting... ({elapsed}s)", end="\r", flush=True)
            continue
        status_str = hist[pid].get("status", {}).get("status_str", "unknown")
        if status_str == "error":
            raise RuntimeError(f"Generation error: {hist[pid]['status'].get('messages')}")
        if status_str == "success":
            print(f"\nDone in ~{elapsed}s!")
            return hist[pid].get("outputs", {})
        print(f"Waiting... ({elapsed}s)", end="\r", flush=True)
    raise TimeoutError(f"Timed out after {timeout}s")

def download_outputs(outputs, label):
    saved = []
    for nid, out in outputs.items():
        for img in out.get("images", []):
            if img.get("type") == "temp":
                continue
            params = urllib.parse.urlencode({
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output"),
            })
            url  = f"{COMFYUI_URL}/view?{params}"
            dest = os.path.join(OUTPUT_DIR, f"{label}_{img['filename']}")
            with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
                raw = r.read()
            with open(dest, "wb") as f:
                f.write(raw)
            print(f"Saved -> {dest} ({len(raw):,} bytes)")
            saved.append(dest)
    return saved

def generate_one(seed=None):
    if seed is None:
        seed = random_seed()
    label = f"rem_rezero_seed{seed}"
    print(f"\n--- Generating {label} (Seed: {seed}) ---")
    
    base_workflow = load_workflow(WORKFLOW_PATH)
    api = convert_to_api(base_workflow)
    api = override_prompts(api, REM_PROMPT, NEG_PROMPT, seed)
    
    outputs = queue_and_wait(api, label)
    saved = download_outputs(outputs, label)
    return seed, saved

if __name__ == "__main__":
    seed_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    seed, saved = generate_one(seed_arg)
    print(f"\nSUCCESS: Seed={seed}, Files={saved}")
