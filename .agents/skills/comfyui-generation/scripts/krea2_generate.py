#!/usr/bin/env python3
"""
Krea 2 minimal generation runner (see ../references/krea2-generation.md section 3).

Builds the proven 11-node Krea2-architecture API prompt, queues it via POST /prompt,
polls GET /history/{prompt_id}, and downloads type=="output" images via GET /view.

Proven 2026-09-12 against https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/
(RTX 4080 SUPER, ~10s at 888x1176, 10 steps). Seed 2148589397 -> 4/5 NSFW pass.

Standard library only (urllib) -- no extra dependencies.
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

DEFAULT_SERVER = "https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud/"


def random_seed() -> int:
    """ComfyUI valid seed range: 0 .. 2^32 - 1."""
    return random.randint(0, 2**32 - 1)


def build_prompt(
    positive: str,
    negative: str = "",
    seed: int = 1,
    steps: int = 10,
    cfg: float = 1.0,
    sampler: str = "euler",
    scheduler: str = "beta",
    width: int = 888,
    height: int = 1176,
    prefix: str = "krea2",
) -> Dict[str, Any]:
    """Minimal Krea2-architecture API prompt (references/krea2-generation.md section 3)."""
    return {
        "58": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "museByStableYogi_v35Int8Extended.safetensors",
            "weight_dtype": "default"}},
        "37": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "Huihui-Qwen3-VL-4B-Instruct-abliterated.safetensors",
            "type": "krea2", "device": "default"}},
        "39": {"class_type": "Lora Loader (LoraManager)", "inputs": {
            "text": "", "loras": [],
            "model": ["58", 0], "clip": ["37", 0]}},
        "40": {"class_type": "TriggerWord Toggle (LoraManager)", "inputs": {
            "group_mode": True, "default_active": True,
            "allow_strength_adjustment": False,
            "toggle_trigger_words": [], "orinalMessage": "",
            "trigger_words": ["39", 2]}},
        "41": {"class_type": "Prompt (LoraManager)", "inputs": {
            "text": positive, "clip": ["39", 1],
            "trigger_words1": ["40", 0]}},
        "67": {"class_type": "CLIPTextEncode", "inputs": {
            "text": negative, "clip": ["39", 1]}},
        "69": {"class_type": "EmptyLatentImage", "inputs": {
            "width": width, "height": height, "batch_size": 1}},
        "7": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": seed,
            "steps": steps, "cfg": cfg,
            "sampler_name": sampler, "scheduler": scheduler,
            "start_at_step": 0, "end_at_step": 10000,
            "return_with_leftover_noise": "disable",
            "model": ["39", 0], "positive": ["41", 0],
            "negative": ["67", 0], "latent_image": ["69", 0]}},
        "3": {"class_type": "VAELoader", "inputs": {
            "vae_name": "qwen_image_vae.safetensors"}},
        "10": {"class_type": "VAEDecode", "inputs": {
            "samples": ["7", 0], "vae": ["3", 0]}},
        "save": {"class_type": "SaveImage", "inputs": {
            "images": ["10", 0], "filename_prefix": prefix}},
    }


def queue_prompt(server: str, api_prompt: Dict[str, Any]) -> str:
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")
    req = urllib.request.Request(
        f"{server.rstrip('/')}/prompt", data=payload,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} queueing prompt: {e.read().decode('utf-8')}")
    if res.get("node_errors"):
        raise RuntimeError(
            f"ComfyUI node validation errors: {json.dumps(res['node_errors'], indent=2)}")
    return res["prompt_id"]


def poll_outputs(server: str, prompt_id: str,
                 poll_interval: int = 5, max_wait: int = 600) -> Dict[str, Any]:
    url = f"{server.rstrip('/')}/history/{prompt_id}"
    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                history = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise
        if prompt_id in history:
            status = history[prompt_id].get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"Generation error: {status.get('messages', [])}")
            if status.get("status_str") == "success":
                print(f"Generation completed in ~{elapsed}s.")
                return history[prompt_id].get("outputs", {})
        print(f"Waiting for generation... ({elapsed}s elapsed)")
    raise TimeoutError(f"Job {prompt_id} did not finish within {max_wait}s")


def download_images(server: str, outputs: Dict[str, Any],
                    output_dir: str) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)
    saved: List[str] = []
    for _node_id, node_out in outputs.items():
        for img in node_out.get("images", []):
            if img.get("type") == "temp":
                continue
            params = urllib.parse.urlencode({
                "filename": img["filename"],
                "subfolder": img.get("subfolder", ""),
                "type": img.get("type", "output")})
            with urllib.request.urlopen(
                    f"{server.rstrip('/')}/view?{params}", timeout=60) as resp:
                data = resp.read()
            dest = os.path.join(output_dir, img["filename"])
            with open(dest, "wb") as f:
                f.write(data)
            saved.append(dest)
            print(f"Downloaded: {dest} ({len(data)} bytes)")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description="Krea 2 minimal generation runner")
    parser.add_argument("--server", default=DEFAULT_SERVER,
                        help="Base URL of ComfyUI instance")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="Positive prompt text (inline)")
    group.add_argument("--prompt-file", help="Path to UTF-8 text file with the prompt")
    parser.add_argument("--negative", default="",
                        help="Negative prompt (default: empty, per Krea2 workflow)")
    parser.add_argument("--seed", type=int, default=None, help="Fixed seed")
    parser.add_argument("--randomize-seed", action="store_true",
                        help="Random seed (overrides --seed)")
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--cfg", type=float, default=1.0)
    parser.add_argument("--sampler", default="euler")
    parser.add_argument("--scheduler", default="beta")
    parser.add_argument("--width", type=int, default=888)
    parser.add_argument("--height", type=int, default=1176)
    parser.add_argument("--prefix", default="krea2",
                        help="SaveImage filename prefix")
    parser.add_argument("--output-dir", default="./output")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    if args.prompt_file:
        with open(args.prompt_file, "r", encoding="utf-8") as f:
            positive = f.read().strip()
    else:
        positive = args.prompt.strip()
    if not positive:
        sys.exit("Empty positive prompt.")

    seed = random_seed() if (args.randomize_seed or args.seed is None) else args.seed
    print(f"Seed: {seed}")

    api_prompt = build_prompt(
        positive, args.negative, seed, args.steps, args.cfg,
        args.sampler, args.scheduler, args.width, args.height, args.prefix)

    print("Submitting Krea2 prompt...")
    prompt_id = queue_prompt(args.server, api_prompt)
    print(f"Queued: {prompt_id}")
    outputs = poll_outputs(args.server, prompt_id, max_wait=args.timeout)
    saved = download_images(args.server, outputs, args.output_dir)
    print(f"Done! {len(saved)} file(s) saved.")


if __name__ == "__main__":
    main()
