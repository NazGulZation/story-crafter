import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

COMFYUI_URL = "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud"
WORKFLOW_PATH = r"C:\StoryCrafter\anima_absolute_cinema.json"
OUTPUT_DIR = r"c:\StoryCrafter\obon_night_and_race_day_with_machitan\assets"
os.makedirs(OUTPUT_DIR, exist_ok=True)

NEG_PROMPT = (
    "worst quality, low quality, early, old, score_1, score_2, score_3, "
    "cartoon, graphic, painting, crayon, graphite, abstract, glitch, "
    "deformed, mutated, ugly, disfigured, bad anatomy, bad hands, "
    "missing fingers, extra fingers, extra digits, fewer digits, cropped, "
    "very displeasing, artist name, blurry, jpeg artifacts, lowres, censor"
)

def random_seed() -> int:
    return random.randint(0, 2**32 - 1)

def load_and_convert_workflow():
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        wf = json.load(f)
    link_map = {l[0]: (str(l[1]), l[2]) for l in wf.get("links", [])}
    api = {}
    for n in wf.get("nodes", []):
        ctype = n.get("type", "")
        if ctype in ("Note", "MarkdownNote"):
            continue
        nid = str(n["id"])
        inp = {}
        for k, v in n.get("widgets_values_named", {}).items():
            if k == "control_after_generate":
                continue
            inp[k] = v
        for c in n.get("inputs", []):
            lid = c.get("link")
            if lid in link_map:
                inp[c["name"]] = list(link_map[lid])
        api[nid] = {"class_type": ctype, "inputs": inp}
    return api

def queue_prompt(api_prompt):
    data = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode("utf-8"))
        if res.get("node_errors"):
            raise RuntimeError(f"Node errors: {res['node_errors']}")
        return res["prompt_id"]

def wait_and_download(prompt_id, filename, timeout=600, poll=4):
    elapsed = 0
    dest = os.path.join(OUTPUT_DIR, filename)
    while elapsed < timeout:
        time.sleep(poll)
        elapsed += poll
        try:
            req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
                if prompt_id in data:
                    pdata = data[prompt_id]
                    if pdata.get("status", {}).get("status_str") == "error":
                        raise RuntimeError(pdata["status"].get("messages"))
                    for nid, out in pdata.get("outputs", {}).items():
                        for img in out.get("images", []):
                            if img.get("type") == "temp":
                                continue
                            params = urllib.parse.urlencode({
                                "filename": img["filename"],
                                "subfolder": img.get("subfolder", ""),
                                "type": img.get("type", "output")
                            })
                            view_url = f"{COMFYUI_URL}/view?{params}"
                            with urllib.request.urlopen(view_url, timeout=60) as vr, open(dest, "wb") as f:
                                f.write(vr.read())
                            print(f"[SUCCESS] Saved to: {dest}")
                            return dest
        except urllib.error.HTTPError:
            continue
        except Exception as e:
            print(f"Warning: {e}")
            continue
    raise TimeoutError(f"Generation timed out after {timeout}s")

def generate_image(pos_prompt, filename, seed=None, extra_neg=None, width=832, height=1216):
    if seed is None:
        seed = random_seed()
    print(f"\n==================================================")
    print(f"Generating: {filename}")
    print(f"Seed: {seed}")
    print(f"Resolution: {width}x{height}")
    print(f"==================================================")

    neg_text = NEG_PROMPT
    if extra_neg:
        neg_text = f"{NEG_PROMPT}, {extra_neg}"

    api = load_and_convert_workflow()
    for nid, n in api.items():
        ctype = n.get("class_type", "")
        if ctype == "CLIPTextEncode":
            if nid == "11":
                n["inputs"]["text"] = pos_prompt
            elif nid == "12":
                n["inputs"]["text"] = neg_text
        elif ctype in ("KSampler", "KSamplerAdvanced"):
            if "seed" in n["inputs"]:
                n["inputs"]["seed"] = seed
            if "noise_seed" in n["inputs"]:
                n["inputs"]["noise_seed"] = seed
        elif ctype == "EmptyLatentImage":
            n["inputs"]["width"] = width
            n["inputs"]["height"] = height

    prompt_id = queue_prompt(api)
    print(f"Queued with prompt ID: {prompt_id}")
    dest = wait_and_download(prompt_id, filename)
    return dest, seed

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    with open(args.prompt_file, "r", encoding="utf-8") as f:
        p = f.read()
    generate_image(p, args.filename, seed=args.seed)
