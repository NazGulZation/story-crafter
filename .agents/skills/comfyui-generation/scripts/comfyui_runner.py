#!/usr/bin/env python3
"""
ComfyUI Runner Utility
Handles:
  1. Inspecting server system stats (/system_stats)
  2. Converting ComfyUI frontend workflow JSON to API prompt format
  3. Overriding parameters (positive prompt, negative prompt, seed, steps, cfg, dimensions)
  4. Submitting jobs via POST /prompt
  5. Polling job execution via GET /history/{prompt_id}
  6. Downloading generated output images via GET /view
  7. Randomized seed support (--randomize-seed flag / randomize_seed=True)
  8. Character tag research workflow: always verify Danbooru tags for anime/game characters
     before constructing a prompt (see Section 8 of SKILL.md)
  9. No underscores needed: Anima was trained without underscores, so convert Danbooru tags
     to use natural spaces (e.g., 'reimu hakurei', 'brown hair', 'detached sleeves')
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
from typing import Any, Dict, List, Optional, Tuple


def random_seed() -> int:
    """Return a random integer in ComfyUI's valid seed range (0 to 2^32-1)."""
    return random.randint(0, 2**32 - 1)


def get_system_stats(server_url: str, timeout: int = 15) -> Dict[str, Any]:
    """Retrieve system information and GPU status from ComfyUI."""
    url = f"{server_url.rstrip('/')}/system_stats"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to connect to ComfyUI server at {server_url}: {e}")


def load_workflow(workflow_path: str) -> Dict[str, Any]:
    """Load workflow JSON from file."""
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(f"Workflow file not found: {workflow_path}")
    with open(workflow_path, "r", encoding="utf-8") as f:
        return json.load(f)


def convert_frontend_to_api(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert frontend graph workflow JSON (nodes, links, widgets) into
    ComfyUI API prompt dictionary format.
    """
    # If the workflow is already in API format (keys are node IDs, values contain class_type & inputs)
    if "nodes" not in workflow and all(
        isinstance(v, dict) and "class_type" in v and "inputs" in v
        for v in workflow.values()
    ):
        return workflow

    api_prompt: Dict[str, Any] = {}
    nodes = workflow.get("nodes", [])
    links = workflow.get("links", [])

    # Map link_id -> (source_node_id, source_slot_index)
    link_map: Dict[int, Tuple[str, int]] = {}
    for link in links:
        # link format: [link_id, source_node_id, source_slot, target_node_id, target_slot, type]
        link_id = link[0]
        source_node_id = str(link[1])
        source_slot = link[2]
        link_map[link_id] = (source_node_id, source_slot)

    # Pass 1: Build base nodes
    for node in nodes:
        node_id = str(node["id"])
        class_type = node.get("type", "")

        # Skip UI-only documentation nodes
        if class_type in ("Note", "MarkdownNote"):
            continue

        api_node: Dict[str, Any] = {
            "class_type": class_type,
            "inputs": {}
        }
        if "title" in node and node["title"]:
            api_node["_meta"] = {"title": node["title"]}

        # Extract widget inputs (prefer named widgets)
        if "widgets_values_named" in node and node["widgets_values_named"]:
            for key, value in node["widgets_values_named"].items():
                # Skip UI frontend control fields
                if key in ("control_after_generate",):
                    continue
                api_node["inputs"][key] = value

        # Process input connections
        node_inputs = node.get("inputs", [])
        for inp in node_inputs:
            input_name = inp["name"]
            link_id = inp.get("link")
            if link_id is not None and link_id in link_map:
                src_id, src_slot = link_map[link_id]
                api_node["inputs"][input_name] = [src_id, src_slot]

        api_prompt[node_id] = api_node

    return api_prompt


def apply_overrides(
    api_prompt: Dict[str, Any],
    positive_prompt: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    seed: Optional[int] = None,
    randomize_seed: bool = False,
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Dict[str, Any]:
    """Apply common parameter overrides to the API prompt dictionary.

    Args:
        randomize_seed: If True, generate a fresh random seed for every
                        KSampler/KSamplerAdvanced node, overriding any
                        fixed seed supplied via the `seed` argument.
    """
    # Resolve effective seed once so both KSampler nodes get the same value
    effective_seed: Optional[int] = seed
    if randomize_seed:
        effective_seed = random_seed()
        print(f"  [randomize_seed] Using seed: {effective_seed}")

    for node_id, node_data in api_prompt.items():
        ctype = node_data.get("class_type", "")
        inputs = node_data.get("inputs", {})

        # Override prompt text
        if ctype == "CLIPTextEncode":
            title = node_data.get("_meta", {}).get("title", "").lower()
            if "negative" in title:
                if negative_prompt is not None:
                    inputs["text"] = negative_prompt
            elif "positive" in title:
                if positive_prompt is not None:
                    inputs["text"] = positive_prompt
            else:
                existing_text = str(inputs.get("text", "")).lower()
                if "worst quality" in existing_text or "low quality" in existing_text:
                    if negative_prompt is not None:
                        inputs["text"] = negative_prompt
                else:
                    if positive_prompt is not None:
                        inputs["text"] = positive_prompt

        # Override latent size
        if ctype == "EmptyLatentImage":
            if width is not None:
                inputs["width"] = width
            if height is not None:
                inputs["height"] = height

        # Override sampler settings
        if ctype in ("KSampler", "KSamplerAdvanced"):
            if effective_seed is not None:
                if "seed" in inputs:
                    inputs["seed"] = effective_seed
                if "noise_seed" in inputs:
                    inputs["noise_seed"] = effective_seed
            if steps is not None:
                inputs["steps"] = steps
            if cfg is not None:
                inputs["cfg"] = cfg

    return api_prompt


def queue_prompt(server_url: str, api_prompt: Dict[str, Any], client_id: Optional[str] = None) -> str:
    """Queue workflow prompt and return prompt_id."""
    url = f"{server_url.rstrip('/')}/prompt"
    payload: Dict[str, Any] = {"prompt": api_prompt}
    if client_id:
        payload["client_id"] = client_id

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "node_errors" in data and data["node_errors"]:
                raise RuntimeError(f"ComfyUI returned node validation errors: {json.dumps(data['node_errors'], indent=2)}")
            return data["prompt_id"]
    except urllib.error.HTTPError as e:
        error_content = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code} while queueing prompt: {error_content}")


def poll_completion(
    server_url: str,
    prompt_id: str,
    poll_interval: int = 5,
    max_wait: int = 600,
    verbose: bool = True
) -> Dict[str, Any]:
    """Poll /history/{prompt_id} until completion, returning outputs data."""
    url = f"{server_url.rstrip('/')}/history/{prompt_id}"
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
            prompt_data = history[prompt_id]
            status = prompt_data.get("status", {})
            status_str = status.get("status_str", "unknown")

            if status_str == "error":
                messages = status.get("messages", [])
                raise RuntimeError(f"Generation error: {messages}")

            if status_str == "success":
                if verbose:
                    print(f"Generation completed successfully in ~{elapsed}s!")
                return prompt_data.get("outputs", {})

        if verbose:
            print(f"Waiting for generation... ({elapsed}s elapsed)", end="\r", flush=True)

    raise TimeoutError(f"Job {prompt_id} did not finish within {max_wait}s")


def download_images(
    server_url: str,
    outputs: Dict[str, Any],
    output_dir: str,
    skip_temp: bool = True
) -> List[str]:
    """Download output images from outputs dict to local directory."""
    os.makedirs(output_dir, exist_ok=True)
    saved_paths: List[str] = []

    for node_id, node_data in outputs.items():
        images = node_data.get("images", [])
        for img in images:
            filename = img.get("filename")
            subfolder = img.get("subfolder", "")
            img_type = img.get("type", "output")

            if skip_temp and img_type == "temp":
                continue

            params = urllib.parse.urlencode({
                "filename": filename,
                "subfolder": subfolder,
                "type": img_type
            })
            url = f"{server_url.rstrip('/')}/view?{params}"
            target_path = os.path.join(output_dir, filename)

            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                with open(target_path, "wb") as f:
                    f.write(data)

            saved_paths.append(target_path)
            print(f"Downloaded: {target_path} ({len(data)} bytes)")

    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="ComfyUI Image Generation Runner")
    parser.add_argument("--server", required=True, help="Base URL of ComfyUI instance (e.g. https://shrimp-taco-teniyo1vd6ugnz31.salad.cloud)")
    parser.add_argument("--workflow", required=True, help="Path to workflow JSON file")
    parser.add_argument("--output-dir", default="./output", help="Directory to save generated images")
    parser.add_argument("--prompt", help="Override positive prompt text")
    parser.add_argument("--negative", help="Override negative prompt text")
    parser.add_argument("--seed", type=int, help="Override generation seed (fixed integer)")
    parser.add_argument("--randomize-seed", action="store_true", help="Generate a random seed for each run (overrides --seed)")
    parser.add_argument("--steps", type=int, help="Override sampling steps")
    parser.add_argument("--cfg", type=float, help="Override CFG scale")
    parser.add_argument("--width", type=int, help="Override width")
    parser.add_argument("--height", type=int, help="Override height")
    parser.add_argument("--timeout", type=int, default=600, help="Max wait time in seconds")
    parser.add_argument("--stats-only", action="store_true", help="Only check server status and exit")

    args = parser.parse_args()

    # Step 1: Health check
    print(f"[1] Checking server status at {args.server}...")
    stats = get_system_stats(args.server)
    sys_info = stats.get("system", {})
    devices = stats.get("devices", [])
    gpu_name = devices[0].get("name", "Unknown GPU") if devices else "CPU only"
    print(f"    ComfyUI v{sys_info.get('comfyui_version')} | Python {sys_info.get('python_version', '').split()[0]}")
    print(f"    Compute device: {gpu_name}")

    if args.stats_only:
        return

    # Step 2: Load & convert workflow
    print(f"[2] Loading workflow from {args.workflow}...")
    wf = load_workflow(args.workflow)
    api_prompt = convert_frontend_to_api(wf)
    print(f"    Parsed {len(api_prompt)} active nodes")

    # Step 3: Apply overrides
    api_prompt = apply_overrides(
        api_prompt,
        positive_prompt=args.prompt,
        negative_prompt=args.negative,
        seed=args.seed,
        randomize_seed=args.randomize_seed,
        steps=args.steps,
        cfg=args.cfg,
        width=args.width,
        height=args.height
    )

    # Step 4: Queue prompt
    print("[3] Submitting prompt to ComfyUI...")
    prompt_id = queue_prompt(args.server, api_prompt)
    print(f"    Prompt queued successfully! ID: {prompt_id}")

    # Step 5: Poll completion
    print("[4] Monitoring execution...")
    outputs = poll_completion(args.server, prompt_id, max_wait=args.timeout)

    # Step 6: Download outputs
    print(f"[5] Downloading outputs to {args.output_dir}...")
    saved_files = download_images(args.server, outputs, args.output_dir)
    print(f"Done! {len(saved_files)} file(s) saved successfully.")


if __name__ == "__main__":
    main()
