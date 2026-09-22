#!/usr/bin/env python3
"""
StoryCrafter Sleek Python Web Reader
A responsive, book-style web application for StoryCrafter narratives.
Provides two-page book spread with spine crease effect, continuous reading mode,
customizable typography, parchment/sepia/midnight/clean paper themes,
synthesized Web Audio paper turning sounds, touch swipe gestures on mobile/tablet,
URL deep linking, live library reloading, and reading progress synchronization.
"""

import os
import sys
import json
import re
import html
import socket
import argparse
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Optional markdown library
try:
    import markdown
except ImportError:
    markdown = None

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / ".reader_config.json"
ICON_SVG_FILE = BASE_DIR / "app_icon.svg"
ICON_ICO_FILE = BASE_DIR / "app_icon.ico"


def load_config():
    """Load user configuration and reading progress from .reader_config.json."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read config: {e}")
    return {
        "active_story": "the_mockingbirds_ledger",
        "active_chapter": "ch01_the_gutter_and_the_mockingbird.md",
        "theme": "parchment",
        "font_size": 18,
        "font_family": "georgia",
        "layout": "spread",  # 'spread' or 'single'
        "line_height": 1.75,
        "page_index": 0
    }


def save_config(config):
    """Save user configuration and reading progress to .reader_config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] Error saving config: {e}")
        return False


def format_markdown_to_html(md_text, story_id=""):
    """Convert chapter markdown into clean, styled book HTML with drop caps, choices parsing, and web-safe image paths."""
    # Check frontmatter if present
    is_ending = False
    ending_title = None
    if md_text.startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            fm_str = parts[1]
            md_text = parts[2]
            for fline in fm_str.splitlines():
                if fline.strip().lower().startswith("ending:"):
                    val = fline.split(":", 1)[1].strip().lower()
                    if val in ("true", "yes", "1"):
                        is_ending = True
                elif fline.strip().lower().startswith("ending_title:"):
                    ending_title = fline.split(":", 1)[1].strip().strip('"\'')

    # Check for ### Ending: [Title] heading anywhere in md_text
    m_ending = re.search(r'^\s*#{2,3}\s+Ending:\s*(.+)$', md_text, re.MULTILINE | re.IGNORECASE)
    if m_ending:
        is_ending = True
        if not ending_title:
            ending_title = m_ending.group(1).strip()

    # Parse ### Choices block
    choices = []
    choices_pattern = r'(?:\r?\n|^)\s*#{2,3}\s+Choices\s*\r?\n([\s\S]*?)$'
    m_choices = re.search(choices_pattern, md_text, re.IGNORECASE)
    if m_choices:
        choices_block = m_choices.group(1)
        # Strip choices block from md_text so it does not render as raw markdown bullets
        md_text = md_text[:m_choices.start()].rstrip()
        for bline in choices_block.splitlines():
            m_link = re.search(r'[-*]\s*\[(.*?)\]\((.*?)\)', bline)
            if m_link:
                c_text = m_link.group(1).strip()
                c_target = m_link.group(2).strip().replace("\\", "/").split("/")[-1]
                if c_text and c_target:
                    choices.append({
                        "text": c_text,
                        "target": c_target
                    })

    lines = md_text.splitlines()
    title = ""
    cleaned_lines = []

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        else:
            cleaned_lines.append(line)

    body_md = "\n".join(cleaned_lines)

    # Pre-process markdown image tags into web-safe HTML figures
    def _replace_image_tag(match):
        alt = match.group(1).strip()
        src = match.group(2).strip()
        src_norm = src.replace("\\", "/")

        # Extract filename
        filename = src_norm.split("/")[-1]

        # Detect story from path if present (e.g. c:/StoryCrafter/bakushin_after_training/assets/...)
        m_story = re.search(r'StoryCrafter/([^/]+)/assets/', src_norm, re.IGNORECASE)
        resolved_story = m_story.group(1) if m_story else story_id

        # Attempt to detect natural dimensions for smooth layout reservation
        aspect_style = ""
        asset_file = None
        if resolved_story:
            cand = BASE_DIR / resolved_story / "assets" / filename
            if cand.exists():
                asset_file = cand
        if not asset_file:
            cand = BASE_DIR / "assets" / filename
            if cand.exists():
                asset_file = cand

        v_param = ""
        if asset_file:
            try:
                v_param = f"?v={int(asset_file.stat().st_mtime)}"
            except Exception:
                pass
            try:
                from PIL import Image as PILImage
                with PILImage.open(asset_file) as img_obj:
                    w, h = img_obj.size
                    if w > 0 and h > 0:
                        aspect_style = f' style="aspect-ratio: {w} / {h};"'
            except Exception:
                pass

        if resolved_story:
            web_url = f"/api/assets/{resolved_story}/{filename}{v_param}"
        else:
            web_url = f"/api/assets/{filename}{v_param}"

        caption_html = f'<figcaption class="illustration-caption">{html.escape(alt)}</figcaption>' if alt else ''
        return f'\n\n<figure class="book-figure"><img src="{web_url}" alt="{html.escape(alt)}" loading="lazy"{aspect_style}>{caption_html}</figure>\n\n'

    body_md = re.sub(r'!\[(.*?)\]\((.*?)\)', _replace_image_tag, body_md)

    if markdown:
        raw_html = markdown.markdown(body_md, extensions=['extra', 'smarty'])
    else:
        # Fallback converter
        paragraphs = [p.strip() for p in body_md.split("\n\n") if p.strip()]
        html_parts = []
        for p in paragraphs:
            if p.startswith("<figure") and p.endswith("</figure>"):
                html_parts.append(p)
            elif p.startswith("### "):
                html_parts.append(f"<h3>{html.escape(p[4:])}</h3>")
            elif p.startswith("## "):
                html_parts.append(f"<h2>{html.escape(p[3:])}</h2>")
            elif p.startswith("> "):
                html_parts.append(f"<blockquote>{html.escape(p[2:])}</blockquote>")
            elif p.startswith("---") or p.startswith("***"):
                html_parts.append("<div class='ornament'>❦  ❦  ❦</div>")
            else:
                formatted = html.escape(p)
                formatted = re.sub(r"\*(.*?)\*", r"<em>\1</em>", formatted)
                formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", formatted)
                html_parts.append(f"<p>{formatted}</p>")
        raw_html = "\n".join(html_parts)

    return title, raw_html, choices, is_ending, ending_title


def scan_full_library():
    """Scan workspace and pre-render all stories and chapters into complete JSON."""
    stories = []
    for item in sorted(BASE_DIR.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir() and not item.name.startswith((".", "_", "venv")):
            chapters_dir = item / "chapters"
            if chapters_dir.is_dir():
                # Natural sort for chapters: ch01, ch02, ..., ch10, etc.
                files = sorted(chapters_dir.glob("*.md"), key=lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', f.name)])
                if files:
                    display_title = item.name.replace("_", " ").title()
                    chapter_list = []
                    for idx, f in enumerate(files, 1):
                        try:
                            text = f.read_text(encoding="utf-8")
                            title, raw_html, choices, is_ending, ending_title = format_markdown_to_html(text, story_id=item.name)
                            word_count = len(re.findall(r"\b\w+\b", text))
                            reading_minutes = max(1, round(word_count / 220))

                            chapter_list.append({
                                "filename": f.name,
                                "title": title or f.stem.replace("_", " ").title(),
                                "index": idx,
                                "word_count": word_count,
                                "reading_time": f"{reading_minutes} min",
                                "html": raw_html,
                                "choices": choices,
                                "is_ending": is_ending,
                                "ending_title": ending_title or (title if is_ending else None)
                            })
                        except Exception as e:
                            print(f"[WARN] Failed to parse chapter {f}: {e}")

                    is_interactive = any(bool(ch.get("choices") or ch.get("is_ending")) for ch in chapter_list)
                    endings = [
                        {
                            "filename": ch["filename"],
                            "title": ch.get("ending_title") or ch["title"],
                            "index": ch["index"]
                        }
                        for ch in chapter_list if ch.get("is_ending")
                    ]

                    stories.append({
                        "id": item.name,
                        "title": display_title,
                        "chapters": chapter_list,
                        "total_chapters": len(chapter_list),
                        "is_interactive": is_interactive,
                        "endings": endings,
                        "total_endings": len(endings)
                    })

    # Sort so 'the_mockingbirds_ledger' is primary if present, then alphabetical
    stories.sort(key=lambda s: (0 if s["id"] == "the_mockingbirds_ledger" else 1, s["title"].lower()))
    return stories


def scan_assets_gallery():
    """Scan the root \\assets directory (ignoring story chapter assets) and return standalone assets."""
    assets_dir = BASE_DIR / "assets"
    if not assets_dir.is_dir():
        return {"total": 0, "folders": ["All"], "assets": []}

    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp", ".avif"}
    all_assets = []
    folder_set = set()

    for item in sorted(assets_dir.rglob("*")):
        if item.is_file() and item.suffix.lower() in valid_exts:
            try:
                rel_to_assets = item.relative_to(assets_dir)
                rel_path_str = str(rel_to_assets).replace("\\", "/")
                parent_folder = rel_to_assets.parent.as_posix()
                if parent_folder == ".":
                    parent_folder = "root"
                else:
                    folder_set.add(parent_folder)

                st = item.stat()
                size_bytes = st.st_size
                if size_bytes >= 1024 * 1024:
                    size_formatted = f"{size_bytes / (1024 * 1024):.2f} MB"
                elif size_bytes >= 1024:
                    size_formatted = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_formatted = f"{size_bytes} B"

                # Check dimensions with PIL
                w, h = None, None
                try:
                    from PIL import Image as PILImage
                    with PILImage.open(item) as img_obj:
                        w, h = img_obj.size
                except Exception:
                    pass

                all_assets.append({
                    "filename": item.name,
                    "rel_path": rel_path_str,
                    "folder": parent_folder,
                    "url": f"/api/gallery/asset/{rel_path_str}?v={int(st.st_mtime)}",
                    "size_bytes": size_bytes,
                    "size_formatted": size_formatted,
                    "modified": int(st.st_mtime),
                    "width": w,
                    "height": h,
                    "aspect_ratio": f"{w} / {h}" if (w and h) else "auto"
                })
            except Exception as e:
                print(f"[WARN] Failed to read asset {item}: {e}")

    # Discover any subdirectories (including empty directories)
    for sub in sorted(assets_dir.iterdir()):
        if sub.is_dir() and not sub.name.startswith((".", "_")):
            folder_set.add(sub.name)

    folders = ["All"] + sorted(list(folder_set))
    return {
        "total": len(all_assets),
        "folders": folders,
        "assets": all_assets
    }


def get_lan_ip():
    """Attempt to discover the host's local IPv4 address on the LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def find_available_port(host, start_port=8080, max_attempts=25):
    """Find an available TCP port starting from start_port."""
    is_ipv6 = ":" in str(host)
    family = socket.AF_INET6 if is_ipv6 else socket.AF_INET
    for p in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                if is_ipv6:
                    try:
                        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except (AttributeError, OSError):
                        pass
                s.bind((host, p))
                return p
        except OSError:
            continue
    return start_port


def generate_web_ui(library, config, gallery=None, lan_url=None):
    """Generate the complete web reader HTML with embedded library and client scripts."""
    if gallery is None:
        gallery = scan_assets_gallery()
    embedded_json = json.dumps({
        "stories": library,
        "config": config,
        "gallery": gallery,
        "lan_url": lan_url
    })

    if lan_url:
        lan_section = f"""
      <div style="margin-top: 14px; padding: 10px 12px; background: rgba(0,0,0,0.04); border-radius: 6px; border: 1px solid var(--border-color); font-size: 13px;">
        <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
          <span>📱</span> LAN Mode Active (Mobile &amp; Tablet)
        </div>
        <div style="color: var(--text-secondary); font-size: 12px; line-height: 1.4;">
          Connect any mobile phone or tablet on your Wi-Fi network:
        </div>
        <div style="margin-top: 6px; font-family: monospace; font-size: 13px; font-weight: bold; color: var(--accent); user-select: all; word-break: break-all;">
          {html.escape(lan_url)}
        </div>
      </div>"""
    else:
        lan_section = """
      <div style="margin-top: 14px; padding: 10px 12px; background: rgba(0,0,0,0.04); border-radius: 6px; border: 1px solid var(--border-color); font-size: 13px;">
        <div style="font-weight: 600; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
          <span>🔒</span> Local Only Mode
        </div>
        <div style="color: var(--text-secondary); font-size: 12px; line-height: 1.4;">
          Server is bound to localhost (127.0.0.1). Run without --local to enable LAN mode.
        </div>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>StoryCrafter Web Reader</title>
<meta name="description" content="A sleek, book-style web reader for StoryCrafter narratives.">
<meta name="theme-color" content="#8b3a2b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json">
<link rel="icon" type="image/svg+xml" href="/app_icon.svg">
<link rel="alternate icon" href="/favicon.ico">
<style>
  :root {{
    --bg-app: #e8dec8;
    --bg-book: #f7f1e3;
    --bg-page: #fbf8f1;
    --text-primary: #2b2318;
    --text-secondary: #736452;
    --text-muted: #9e8e7a;
    --border-color: #dfd3bc;
    --accent: #8b3a2b;
    --accent-hover: #b24d3b;
    --shadow-page: 0 10px 30px rgba(43, 35, 24, 0.15);
    --spine-shadow: linear-gradient(to right, rgba(0,0,0,0.14) 0%, rgba(0,0,0,0.02) 8%, rgba(0,0,0,0) 20%, rgba(0,0,0,0) 80%, rgba(0,0,0,0.02) 92%, rgba(0,0,0,0.14) 100%);
    --font-serif: 'Georgia', 'Baskerville', 'Palatino Linotype', 'Times New Roman', serif;
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  }}

  [data-theme="sepia"] {{
    --bg-app: #dfd0b5;
    --bg-book: #ebe0cb;
    --bg-page: #f3ebd9;
    --text-primary: #34281d;
    --text-secondary: #7a6652;
    --text-muted: #a38f7a;
    --border-color: #d1c1a5;
    --accent: #78351f;
    --accent-hover: #9c4529;
    --shadow-page: 0 10px 30px rgba(52, 40, 29, 0.2);
  }}

  [data-theme="midnight"] {{
    --bg-app: #121417;
    --bg-book: #181b20;
    --bg-page: #1e2227;
    --text-primary: #ddd6c8;
    --text-secondary: #9aa1a9;
    --text-muted: #6b727d;
    --border-color: #2b3038;
    --accent: #d4836a;
    --accent-hover: #e89980;
    --shadow-page: 0 10px 35px rgba(0,0,0,0.6);
    --spine-shadow: linear-gradient(to right, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.1) 8%, transparent 20%, transparent 80%, rgba(0,0,0,0.1) 92%, rgba(0,0,0,0.5) 100%);
  }}

  [data-theme="paper"] {{
    --bg-app: #e9eaec;
    --bg-book: #f4f5f7;
    --bg-page: #ffffff;
    --text-primary: #1e2022;
    --text-secondary: #5a6068;
    --text-muted: #8b929d;
    --border-color: #d8dbe0;
    --accent: #2c5282;
    --accent-hover: #3b6ba5;
    --shadow-page: 0 10px 30px rgba(0,0,0,0.08);
    --spine-shadow: linear-gradient(to right, rgba(0,0,0,0.08) 0%, rgba(0,0,0,0.01) 8%, transparent 20%, transparent 80%, rgba(0,0,0,0.01) 92%, rgba(0,0,0,0.08) 100%);
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    background-color: var(--bg-app);
    color: var(--text-primary);
    font-family: var(--font-serif);
    height: 100vh;
    height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: background-color 0.3s ease, color 0.3s ease;
    touch-action: pan-y;
  }}

  /* TOP APP BAR */
  header.app-bar {{
    height: 52px;
    background-color: var(--bg-book);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 12px;
    font-family: var(--font-sans);
    z-index: 50;
    user-select: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    overflow-x: auto;
    scrollbar-width: none;
  }}

  header.app-bar::-webkit-scrollbar {{
    display: none;
  }}

  .app-bar-left, .app-bar-right, .app-bar-center {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }}

  .btn {{
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
    white-space: nowrap;
  }}

  .btn:hover {{
    background: var(--bg-page);
    border-color: var(--text-muted);
    color: var(--accent);
  }}

  .btn.active {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }}

  select.select-input {{
    background: var(--bg-page);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    font-family: var(--font-sans);
    cursor: pointer;
    outline: none;
    max-width: 220px;
  }}

  .story-title-badge {{
    font-family: var(--font-serif);
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: var(--accent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 320px;
  }}

  /* MAIN WORKSPACE */
  .workspace {{
    flex: 1;
    display: flex;
    position: relative;
    overflow: hidden;
  }}

  /* TABLE OF CONTENTS DRAWER */
  aside.toc-drawer {{
    width: 340px;
    max-width: 85vw;
    background-color: var(--bg-book);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 60;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    transform: translateX(-100%);
    box-shadow: 4px 0 24px rgba(0,0,0,0.18);
  }}

  aside.toc-drawer.open {{
    transform: translateX(0);
  }}

  .toc-header {{
    padding: 14px 16px;
    border-bottom: 1px solid var(--border-color);
    font-family: var(--font-sans);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .toc-header h2 {{
    font-size: 16px;
    font-weight: 600;
  }}

  .toc-list {{
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
    list-style: none;
    font-family: var(--font-sans);
  }}

  .toc-item {{
    padding: 12px 18px;
    cursor: pointer;
    border-left: 4px solid transparent;
    display: flex;
    flex-direction: column;
    gap: 3px;
    transition: background 0.15s ease;
  }}

  .toc-item:hover {{
    background-color: var(--bg-page);
  }}

  .toc-item.active {{
    background-color: var(--bg-page);
    border-left-color: var(--accent);
  }}

  .toc-item .ch-num {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
  }}

  .toc-item .ch-name {{
    font-size: 14px;
    font-weight: 500;
    color: var(--text-primary);
  }}

  .toc-item.active .ch-name {{
    color: var(--accent);
    font-weight: 600;
  }}

  .toc-item .ch-meta {{
    font-size: 11px;
    color: var(--text-muted);
  }}

  /* BOOK CONTAINER */
  main.book-stage {{
    flex: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 12px 54px;
    overflow: hidden;
    position: relative;
    width: 100%;
    height: 100%;
    user-select: text;
  }}

  /* SPREAD MODE */
  .book-spread {{
    width: 100%;
    max-width: 100%;
    height: 100%;
    max-height: 100%;
    background-color: var(--bg-page);
    border-radius: 8px;
    box-shadow: var(--shadow-page);
    display: grid;
    grid-template-columns: 1fr 1fr;
    position: relative;
    border: 1px solid var(--border-color);
    overflow: hidden;
  }}

  /* Center Spine Effect */
  .book-spread::after {{
    content: '';
    position: absolute;
    top: 0;
    bottom: 0;
    left: 50%;
    width: 80px;
    transform: translateX(-50%);
    background: var(--spine-shadow);
    pointer-events: none;
    z-index: 10;
  }}

  .page {{
    padding: 30px 48px 20px 48px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    position: relative;
    height: 100%;
    min-height: 0;
  }}

  .page-left {{
    border-right: 1px solid var(--border-color);
  }}

  /* Header & Footer on Pages */
  .page-running-header {{
    height: 26px;
    font-family: var(--font-sans);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 18px;
    user-select: none;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .page-running-footer {{
    height: 26px;
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: auto;
    border-top: 1px solid var(--border-color);
    padding-top: 8px;
    user-select: none;
  }}

  .page-content {{
    flex: 1;
    overflow: hidden;
    font-size: 18px;
    line-height: 1.75;
    text-align: justify;
    hyphens: auto;
    min-height: 0;
  }}

  /* BOOK ILLUSTRATIONS & FIGURES */
  .book-figure {{
    margin: 0 auto 10px auto;
    text-align: center;
    max-width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    page-break-inside: avoid;
    break-inside: avoid;
    box-sizing: border-box;
  }}

  .book-figure img,
  .page-content img,
  #contentSingle img {{
    max-width: 100%;
    max-height: min(440px, calc(100vh - 220px), calc(100dvh - 220px));
    height: auto;
    object-fit: contain;
    border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
    display: block;
    margin: 0 auto;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }}

  .book-figure img:hover,
  .page-content img:hover,
  #contentSingle img:hover {{
    transform: scale(1.01);
    box-shadow: 0 6px 22px rgba(0,0,0,0.25);
  }}

  .book-figure figcaption,
  .illustration-caption {{
    font-family: var(--font-serif);
    font-size: 0.82em;
    font-style: italic;
    color: var(--text-secondary);
    margin-top: 6px;
    text-align: center;
    line-height: 1.35;
    max-width: 95%;
  }}

  /* FULL ILLUSTRATION DEDICATED PAGE */
  .has-illustration .page-content,
  .page-content:has(.book-figure) {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    height: 100%;
    overflow: hidden;
  }}

  .has-illustration .book-figure,
  .page-content:has(.book-figure) > .book-figure {{
    margin: 0 auto;
    width: 100%;
    height: 100%;
    flex: 1 1 auto;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
  }}

  .has-illustration .book-figure img,
  .page-content:has(.book-figure) .book-figure img {{
    max-width: 100%;
    max-height: calc(100% - 32px);
    width: auto;
    height: auto;
    object-fit: contain;
    flex: 1 1 auto;
    min-height: 0;
  }}

  .has-illustration .book-figure figcaption,
  .page-content:has(.book-figure) .book-figure figcaption {{
    flex-shrink: 0;
    margin-top: 6px;
    margin-bottom: 2px;
  }}

  /* STANDALONE CHAPTER TITLE CARD PAGE */
  .is-title-page .page-content,
  .page-content:has(.chapter-title-block:only-child) {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    height: 100%;
    text-align: center;
  }}
  .is-title-page .chapter-title-block,
  .page-content:has(.chapter-title-block:only-child) .chapter-title-block {{
    margin: auto 0;
    padding: 24px 12px;
  }}
  .is-title-page .chapter-main-title {{
    font-size: 28px;
    letter-spacing: 0.8px;
    margin-bottom: 12px;
  }}

  /* INFINITE SCROLL DOWN MODE */
  .book-single {{
    width: 100%;
    max-width: min(900px, calc(100vw - 40px));
    height: 100%;
    max-height: 100%;
    background-color: var(--bg-page);
    border-radius: 8px;
    box-shadow: var(--shadow-page);
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    padding: 0 48px 40px 48px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    scroll-behavior: smooth;
    box-sizing: border-box;
    position: relative;
  }}

  .book-single .page-running-header {{
    position: sticky;
    top: 0;
    background-color: var(--bg-page);
    z-index: 20;
    padding: 14px 0 10px 0;
    margin: 0;
    border-bottom: 1px solid var(--border-color);
    text-align: center;
    font-size: 11px;
    font-family: var(--font-sans);
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--text-muted);
    user-select: none;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  }}

  .book-single .page-content {{
    overflow-y: visible;
    width: 100%;
  }}

  .chapter-scroll-section {{
    padding: 40px 0 32px 0;
    border-bottom: 1px dashed var(--border-color);
  }}

  .chapter-scroll-section:last-of-type {{
    border-bottom: none;
  }}

  .chapter-scroll-footer {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    margin-top: 36px;
    padding-top: 16px;
    color: var(--text-muted);
    font-size: 12px;
    font-family: var(--font-sans);
    user-select: none;
  }}

  .chapter-scroll-divider {{
    font-size: 14px;
    letter-spacing: 8px;
    color: var(--accent);
    opacity: 0.6;
  }}

  .chapter-scroll-section .book-figure {{
    margin: 28px auto;
    text-align: center;
    max-width: 100%;
  }}

  .chapter-scroll-section .book-figure img {{
    max-width: 100%;
    max-height: 80vh;
    height: auto;
    border-radius: 6px;
    box-shadow: var(--shadow-page);
    object-fit: contain;
  }}

  .story-end-block {{
    text-align: center;
    padding: 50px 0 70px 0;
    user-select: none;
  }}

  .story-end-ornament {{
    font-size: 20px;
    color: var(--accent);
    margin-bottom: 10px;
    letter-spacing: 6px;
  }}

  .story-end-title {{
    font-size: 17px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 16px;
  }}

  .btn-back-to-top {{
    margin: 0 auto;
    padding: 6px 16px;
    font-size: 13px;
    cursor: pointer;
  }}

  .book-single .page-running-footer {{
    display: none;
  }}

  /* CHAPTER TYPOGRAPHY */
  .chapter-title-block {{
    text-align: center;
    margin-bottom: 24px;
    user-select: none;
  }}

  .chapter-eyebrow {{
    font-family: var(--font-sans);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text-muted);
    margin-bottom: 6px;
  }}

  .chapter-main-title {{
    font-size: 24px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 0.5px;
    margin-bottom: 8px;
    line-height: 1.3;
  }}

  .chapter-ornament {{
    font-size: 16px;
    color: var(--accent);
    opacity: 0.6;
    letter-spacing: 6px;
  }}

  /* Drop Cap - Chapter beginning only */
  .has-drop-cap > p:first-of-type::first-letter,
  .page-left.has-drop-cap .page-content > p:first-of-type::first-letter {{
    float: left;
    font-size: 3.4em;
    line-height: 0.82;
    margin-top: 0.05em;
    margin-right: 0.12em;
    margin-bottom: -0.05em;
    color: var(--accent);
    font-weight: 700;
    font-family: 'Georgia', serif;
  }}

  .page-content p {{
    margin-bottom: 1em;
    text-indent: 1.8em;
  }}

  .page-content p:first-of-type {{
    text-indent: 0;
  }}

  .page-content p.paragraph-continuation,
  .page-content blockquote.paragraph-continuation {{
    text-indent: 0 !important;
    margin-top: 0 !important;
  }}

  .page-content blockquote {{
    border-left: 3px solid var(--accent);
    padding-left: 18px;
    margin: 1.2em 0;
    font-style: italic;
    color: var(--text-secondary);
  }}

  .page-content .ornament {{
    text-align: center;
    margin: 1.8em 0;
    color: var(--accent);
    letter-spacing: 8px;
    opacity: 0.7;
  }}

  .page-content em {{
    font-style: italic;
  }}

  .page-content strong {{
    font-weight: 600;
    color: var(--text-primary);
  }}

  /* TURN BUTTONS OVERLAY */
  .nav-turn-btn {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    width: 44px;
    height: 68px;
    background: var(--bg-book);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    transition: all 0.2s ease;
    z-index: 40;
    font-size: 26px;
    font-weight: bold;
    user-select: none;
    opacity: 0.85;
  }}

  .nav-turn-btn:hover {{
    opacity: 1;
    background: var(--bg-page);
    color: var(--accent);
    border-color: var(--accent);
    transform: translateY(-50%) scale(1.05);
  }}

  .nav-turn-btn.prev {{
    left: 8px;
  }}

  .nav-turn-btn.next {{
    right: 8px;
  }}

  /* PAPER SWISH ANIMATIONS */
  @keyframes swishRightToLeft {{
    0% {{
      transform: translateX(36px);
      opacity: 0.35;
      filter: blur(0.5px);
    }}
    100% {{
      transform: translateX(0);
      opacity: 1;
      filter: blur(0);
    }}
  }}

  @keyframes swishLeftToRight {{
    0% {{
      transform: translateX(-36px);
      opacity: 0.35;
      filter: blur(0.5px);
    }}
    100% {{
      transform: translateX(0);
      opacity: 1;
      filter: blur(0);
    }}
  }}

  .swish-next {{
    animation: swishRightToLeft 0.22s cubic-bezier(0.2, 0.8, 0.25, 1) both;
  }}

  .swish-prev {{
    animation: swishLeftToRight 0.22s cubic-bezier(0.2, 0.8, 0.25, 1) both;
  }}

  /* BOTTOM PROGRESS BAR */
  footer.app-footer {{
    height: 38px;
    background-color: var(--bg-book);
    border-top: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--text-secondary);
    user-select: none;
  }}

  .progress-track {{
    flex: 1;
    max-width: 400px;
    height: 4px;
    background: var(--border-color);
    border-radius: 2px;
    margin: 0 14px;
    overflow: hidden;
    position: relative;
  }}

  .progress-fill {{
    height: 100%;
    background: var(--accent);
    width: 0%;
    transition: width 0.25s ease;
  }}

  /* SHORTCUT MODAL */
  .modal-backdrop {{
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.55);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 100;
  }}

  .modal-backdrop.open {{
    display: flex;
  }}

  .modal-box {{
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 22px;
    max-width: 440px;
    width: 90%;
    box-shadow: 0 16px 40px rgba(0,0,0,0.25);
    font-family: var(--font-sans);
  }}

  .modal-box h3 {{
    margin-bottom: 14px;
    color: var(--accent);
  }}

  .shortcut-row {{
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-color);
    font-size: 13px;
  }}

  .shortcut-key {{
    background: var(--bg-book);
    border: 1px solid var(--border-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
  }}

  /* RESPONSIVE DESIGN FOR MOBILE & TABLET */
  @media (max-width: 820px) {{
    header.app-bar {{
      padding: 0 8px;
    }}
    .app-bar-center {{
      display: none;
    }}
    select.select-input {{
      max-width: 140px;
      font-size: 12px;
      padding: 4px 6px;
    }}
    .btn {{
      padding: 4px 8px;
      font-size: 12px;
    }}
    main.book-stage {{
      padding: 6px 36px;
    }}
    .book-spread {{
      grid-template-columns: 1fr;
    }}
    .book-spread::after {{
      display: none;
    }}
    .page-right {{
      display: none;
    }}
    .page-left {{
      border-right: none;
      padding: 16px 20px 14px 20px;
    }}
    .page-running-header {{
      margin-bottom: 8px;
    }}
    .page-running-footer {{
      padding-top: 4px;
    }}
    .book-figure {{
      margin: 0 auto 6px auto;
    }}
    .book-figure img,
    .page-content img,
    .has-illustration .book-figure img {{
      max-width: 100%;
      max-height: min(420px, calc(100vh - 180px), calc(100dvh - 180px), calc(100% - 26px));
      height: auto;
      object-fit: contain;
    }}
    .book-figure figcaption,
    .illustration-caption {{
      font-size: 0.78em;
      margin-top: 4px;
      line-height: 1.25;
    }}
    .book-single {{
      padding: 0 20px 30px 20px;
      max-width: 100%;
    }}
    body[data-layout="scroll"] main.book-stage {{
      padding: 0 !important;
    }}
    body[data-layout="scroll"] .book-single {{
      border: none;
      border-radius: 0;
      box-shadow: none;
      padding: 0 16px 40px 16px;
      max-width: 100%;
    }}
    body[data-layout="scroll"] .nav-turn-btn {{
      display: none !important;
    }}
    body[data-layout="scroll"] .chapter-scroll-section {{
      padding: 24px 0 20px 0;
    }}
    .nav-turn-btn {{
      width: 32px;
      height: 54px;
      font-size: 20px;
    }}
    .nav-turn-btn.prev {{ left: 2px; }}
    .nav-turn-btn.next {{ right: 2px; }}
    footer.app-footer {{
      font-size: 11px;
      padding: 0 10px;
    }}
  }}

  @media (max-width: 540px) {{
    .btn .btn-text {{
      display: none;
    }}
  }}

  /* ==========================================================================
     GLOBAL ASSET GALLERY MODAL & LIGHTBOX
     ========================================================================== */
  .gallery-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(14, 16, 20, 0.78);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    z-index: 95;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 16px;
    animation: fadeIn 0.18s ease-out;
  }}

  .gallery-overlay.open {{
    display: flex;
  }}

  @keyframes fadeIn {{
    from {{ opacity: 0; transform: scale(0.985); }}
    to {{ opacity: 1; transform: scale(1); }}
  }}

  .gallery-container {{
    width: 100%;
    max-width: 1360px;
    height: 92vh;
    height: 92dvh;
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45);
    overflow: hidden;
    font-family: var(--font-sans);
  }}

  .gallery-header {{
    padding: 14px 20px;
    background: var(--bg-book);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
    user-select: none;
  }}

  .gallery-title-area {{
    display: flex;
    flex-direction: column;
    gap: 2px;
  }}

  .gallery-title {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .gallery-title h2 {{
    font-size: 17px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0;
  }}

  .gallery-badge-dir {{
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    padding: 2px 7px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 11px;
    color: var(--accent);
    font-weight: 700;
  }}

  .gallery-count-badge {{
    background: var(--accent);
    color: #fff;
    padding: 2px 9px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
  }}

  .gallery-subtitle {{
    font-size: 12px;
    color: var(--text-secondary);
    margin: 0;
  }}

  .gallery-subtitle code {{
    background: rgba(0,0,0,0.05);
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 11px;
    font-family: monospace;
  }}

  .gallery-actions {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .btn-close-gallery {{
    font-size: 15px;
    font-weight: bold;
    padding: 5px 12px;
  }}

  .gallery-toolbar {{
    padding: 10px 20px;
    background: var(--bg-book);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }}

  .gallery-search-box {{
    display: flex;
    align-items: center;
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 5px 10px;
    gap: 8px;
    flex: 1;
    max-width: 380px;
    min-width: 220px;
  }}

  .gallery-search-input {{
    background: transparent;
    border: none;
    outline: none;
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 13px;
    width: 100%;
  }}

  .btn-clear-search {{
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--text-muted);
    font-size: 12px;
    padding: 0 2px;
  }}

  .btn-clear-search:hover {{
    color: var(--accent);
  }}

  .gallery-folder-tabs {{
    display: flex;
    align-items: center;
    gap: 6px;
    overflow-x: auto;
    max-width: 100%;
    padding-bottom: 2px;
  }}

  .folder-tab-btn {{
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 5px 13px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }}

  .folder-tab-btn:hover {{
    border-color: var(--accent);
    color: var(--accent);
  }}

  .folder-tab-btn.active {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    font-weight: 600;
  }}

  .gallery-body {{
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    -webkit-overflow-scrolling: touch;
  }}

  .gallery-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 16px;
  }}

  .asset-card {{
    background: var(--bg-book);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    display: flex;
    flex-direction: column;
    user-select: none;
  }}

  .asset-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    border-color: var(--accent);
  }}

  .asset-thumb-wrap {{
    width: 100%;
    height: 190px;
    background: rgba(0,0,0,0.06);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    position: relative;
  }}

  .asset-thumb-img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.28s ease;
  }}

  .asset-card:hover .asset-thumb-img {{
    transform: scale(1.05);
  }}

  .asset-folder-tag {{
    position: absolute;
    top: 6px;
    left: 6px;
    background: rgba(0, 0, 0, 0.68);
    color: #fff;
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.4px;
    backdrop-filter: blur(2px);
  }}

  .asset-info {{
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-top: 1px solid var(--border-color);
  }}

  .asset-filename {{
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .asset-meta {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-muted);
  }}

  .gallery-empty {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    text-align: center;
    color: var(--text-muted);
  }}

  .gallery-empty-icon {{
    font-size: 48px;
    margin-bottom: 12px;
    opacity: 0.6;
  }}

  .gallery-empty-text {{
    font-size: 15px;
    font-weight: 500;
  }}

  /* LIGHTBOX OVERLAY */
  .lightbox-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(8, 10, 14, 0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    z-index: 120;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 12px;
  }}

  .lightbox-overlay.open {{
    display: flex;
  }}

  .lightbox-dialog {{
    width: 100%;
    height: 100%;
    max-width: 1300px;
    max-height: 98vh;
    display: flex;
    flex-direction: column;
    user-select: none;
  }}

  .lightbox-header {{
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 8px;
    color: #f7f1e3;
    font-family: var(--font-sans);
  }}

  .lightbox-title-info {{
    display: flex;
    align-items: center;
    gap: 10px;
    overflow: hidden;
  }}

  .lightbox-filename {{
    font-size: 14px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .lightbox-folder-badge {{
    background: rgba(255,255,255,0.15);
    padding: 2px 7px;
    border-radius: 4px;
    font-size: 11px;
    color: #e2d9c8;
  }}

  .lightbox-counter {{
    font-size: 12px;
    color: #a89f8d;
    white-space: nowrap;
  }}

  .lightbox-top-actions {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .lightbox-top-actions .btn {{
    color: #f7f1e3;
    border-color: rgba(255,255,255,0.22);
    background: rgba(255,255,255,0.08);
  }}

  .lightbox-top-actions .btn:hover {{
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }}

  .lightbox-stage {{
    flex: 1;
    min-height: 0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: relative;
    padding: 4px 0;
  }}

  .lightbox-nav-btn {{
    width: 46px;
    height: 72px;
    background: rgba(30, 34, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: #fff;
    font-size: 32px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    z-index: 10;
    user-select: none;
  }}

  .lightbox-nav-btn:hover {{
    background: var(--accent);
    border-color: var(--accent);
    transform: scale(1.06);
  }}

  .lightbox-image-wrap {{
    flex: 1;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    padding: 6px 12px;
  }}

  #lightboxImage {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    border-radius: 6px;
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.7);
  }}

  .lightbox-footer {{
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 12px;
    font-family: var(--font-sans);
    font-size: 12px;
    color: rgba(255, 255, 255, 0.75);
  }}

  .lightbox-metadata {{
    display: flex;
    align-items: center;
    gap: 16px;
  }}

  .lightbox-hint {{
    color: rgba(255, 255, 255, 0.45);
    font-size: 11px;
  }}

  /* TOAST NOTIFICATION */
  .gallery-toast {{
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #181b20;
    color: #fff;
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    border: 1px solid var(--accent);
    opacity: 0;
    pointer-events: none;
    transition: all 0.22s cubic-bezier(0.2, 0.8, 0.25, 1);
    z-index: 200;
    font-family: var(--font-sans);
  }}

  .gallery-toast.show {{
    transform: translateX(-50%) translateY(0);
    opacity: 1;
  }}

  @media (max-width: 820px) {{
    .gallery-overlay {{
      padding: 0;
    }}
    .gallery-container {{
      width: 100%;
      height: 100dvh;
      border-radius: 0;
      border: none;
    }}
    .gallery-header {{
      padding: 10px 14px;
    }}
    .gallery-toolbar {{
      padding: 8px 14px;
    }}
    .gallery-search-box {{
      max-width: 100%;
    }}
    .gallery-grid {{
      grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: 10px;
    }}
    .asset-thumb-wrap {{
      height: 135px;
    }}
    .lightbox-dialog {{
      max-height: 100dvh;
    }}
    .lightbox-nav-btn {{
      width: 36px;
      height: 56px;
      font-size: 24px;
    }}
    .lightbox-footer {{
      flex-direction: column;
      height: auto;
      gap: 4px;
      padding: 6px 8px;
    }}
    .lightbox-hint {{
      display: none;
    }}
  }}

  /* INTERACTIVE STORY MODE STYLES */
  .story-mode-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(139, 58, 43, 0.12);
    color: var(--accent);
    border: 1px solid var(--accent);
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-family: var(--font-sans);
    margin-left: 8px;
    vertical-align: middle;
  }}

  .interactive-block {{
    margin: 28px auto 14px auto;
    width: 100%;
    max-width: 600px;
    box-sizing: border-box;
    text-align: center;
  }}

  .choice-container {{
    background: rgba(0, 0, 0, 0.02);
    border: 1px dashed var(--border-color);
    border-radius: 10px;
    padding: 20px 18px;
    margin-top: 10px;
  }}

  .interactive-choice-header {{
    font-family: var(--font-serif);
    font-size: 16px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 16px;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}

  .choice-options-grid {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }}

  .choice-card {{
    background: var(--bg-book);
    border: 1.5px solid var(--border-color);
    border-radius: 8px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    gap: 14px;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    text-align: left;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    width: 100%;
    box-sizing: border-box;
    font-family: var(--font-serif);
  }}

  .choice-card:hover {{
    background: var(--bg-page);
    border-color: var(--accent);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
  }}

  .choice-card .choice-icon {{
    font-size: 14px;
    color: var(--accent);
    background: rgba(139, 58, 43, 0.1);
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    transition: transform 0.2s ease;
  }}

  .choice-card:hover .choice-icon {{
    transform: translateX(3px);
    background: var(--accent);
    color: #fff;
  }}

  .choice-card .choice-text {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1.45;
    flex: 1;
  }}

  /* ENDING CARD */
  .ending-card {{
    background: var(--bg-book);
    border: 2px solid var(--accent);
    border-radius: 10px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 8px 26px rgba(0, 0, 0, 0.12);
  }}

  .ending-ribbon {{
    font-family: var(--font-sans);
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--accent);
    margin-bottom: 8px;
  }}

  .ending-heading {{
    font-family: var(--font-serif);
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 10px;
  }}

  .ending-meta-badge {{
    display: inline-block;
    padding: 4px 12px;
    background: rgba(139, 58, 43, 0.1);
    border-radius: 14px;
    font-size: 12px;
    font-weight: 700;
    color: var(--accent);
    margin-bottom: 18px;
    font-family: var(--font-sans);
  }}

  .ending-actions {{
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: 14px;
  }}

  .btn-interactive {{
    padding: 9px 18px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
  }}

  /* INTERACTIVE TOC & STORY MAP */
  .toc-interactive-panel {{
    padding: 12px 16px;
    border-bottom: 1px solid var(--border-color);
    background: rgba(0, 0, 0, 0.02);
  }}

  .toc-tracker-card {{
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 12px;
  }}

  .toc-tracker-title-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    font-weight: 700;
    font-family: var(--font-sans);
    margin-bottom: 6px;
  }}

  .toc-tracker-stat {{
    color: var(--accent);
  }}

  .toc-progress-track {{
    height: 6px;
    background: var(--border-color);
    border-radius: 3px;
    overflow: hidden;
  }}

  .toc-progress-fill {{
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.3s ease;
  }}

  .toc-path-header {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    color: var(--text-muted);
    margin-bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .btn-toc-action {{
    background: transparent;
    border: none;
    color: var(--accent);
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
  }}

  .btn-toc-action:hover {{
    background: rgba(139, 58, 43, 0.1);
  }}

  .toc-path-trail {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    margin-bottom: 10px;
    font-size: 12px;
  }}

  .toc-path-chip {{
    background: var(--bg-page);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 11px;
    cursor: pointer;
    max-width: 140px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: all 0.15s ease;
  }}

  .toc-path-chip:hover {{
    border-color: var(--accent);
    color: var(--accent);
  }}

  .toc-path-chip.active {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
    font-weight: 600;
  }}

  .toc-path-arrow {{
    color: var(--text-muted);
    font-weight: bold;
    font-size: 12px;
  }}

  .toc-section-header {{
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-weight: 700;
    color: var(--text-muted);
    margin-top: 8px;
    margin-bottom: 4px;
  }}

  .interactive-toc-item.visited {{
    border-left-color: var(--accent);
  }}

  .interactive-toc-item.locked {{
    opacity: 0.6;
    cursor: not-allowed;
    background: transparent !important;
  }}

  .ch-badge {{
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 1px 6px;
    border-radius: 4px;
  }}

  .ch-badge.root-node {{
    background: rgba(44, 82, 130, 0.15);
    color: #2c5282;
  }}

  .ch-badge.branch-node {{
    background: rgba(139, 58, 43, 0.12);
    color: var(--accent);
  }}

  .ch-badge.ending-discovered {{
    background: rgba(40, 167, 69, 0.15);
    color: #28a745;
  }}

  .ch-badge.ending-revealed {{
    background: rgba(255, 193, 7, 0.2);
    color: #b78103;
  }}

  /* SCROLLBAR */
  ::-webkit-scrollbar {{
    width: 6px;
  }}
  ::-webkit-scrollbar-track {{
    background: transparent;
  }}
  ::-webkit-scrollbar-thumb {{
    background: var(--border-color);
    border-radius: 3px;
  }}
</style>
</head>
<body data-theme="{config.get('theme', 'parchment')}">

  <!-- TOP BAR -->
  <header class="app-bar">
    <div class="app-bar-left">
      <button class="btn" id="btnToggleToc" title="Table of Contents (M)">
        <span>☰</span> Contents
      </button>

      <select class="select-input" id="selectStory" title="Select Story">
        <!-- populated dynamically -->
      </select>

      <button class="btn" id="btnReloadLibrary" title="Rescan & reload all stories and chapters (R)">
        <span>↻</span> <span class="btn-text">Reload</span>
      </button>

      <button class="btn" id="btnGallery" title="Asset Gallery (\assets) (G)">
        <span>🖼️</span> Gallery
      </button>
    </div>

    <div class="app-bar-center">
      <svg width="24" height="24" viewBox="0 0 512 512" style="border-radius: 6px; vertical-align: middle; box-shadow: 0 2px 6px rgba(0,0,0,0.15);">
        <rect x="24" y="24" width="464" height="464" rx="108" ry="108" fill="#141820" stroke="#d4af37" stroke-width="16"/>
        <path d="M256 350C210 338 135 320 98 334C94 250 94 220 96 172C140 162 216 178 256 195Z" fill="#fdfbf5"/>
        <path d="M256 350C302 338 377 320 414 334C418 250 418 220 416 172C372 162 296 178 256 195Z" fill="#fdfbf5"/>
        <path d="M256 345Q296 230 354 100Q320 180 256 345Z" fill="#d4af37"/>
        <circle cx="256" cy="370" r="8" fill="#d4af37"/>
      </svg>
      <span class="story-title-badge" id="currentStoryTitle">StoryCrafter Web Reader</span>
      <span class="story-mode-badge" id="storyModeBadge" style="display: none;"></span>
    </div>

    <div class="app-bar-right">
      <button class="btn" id="btnFontDec" title="Decrease font size (-)">A-</button>
      <button class="btn" id="btnFontInc" title="Increase font size (+)">A+</button>

      <select class="select-input" id="selectTheme" style="min-width: 100px;" title="Select Reading Theme (T)">
        <option value="parchment">Parchment</option>
        <option value="sepia">Sepia</option>
        <option value="midnight">Midnight</option>
        <option value="paper">Clean Paper</option>
      </select>

      <button class="btn" id="btnLayout" title="Toggle Reading Mode: Book Spread / Infinite Scroll (L)">
        <span id="layoutIcon">📖 <span class="btn-text">Spread</span></span>
      </button>

      <button class="btn" id="btnSound" title="Toggle Page Flip Sound (S)">🔊 Sound</button>

      <button class="btn" id="btnFullscreen" title="Toggle Fullscreen (F)"><span>⛶</span> Full</button>

      <button class="btn" id="btnHelp" title="Shortcuts & Help (?)">?</button>
    </div>
  </header>

  <!-- WORKSPACE -->
  <div class="workspace">
    <!-- TABLE OF CONTENTS DRAWER -->
    <aside class="toc-drawer" id="tocDrawer">
      <div class="toc-header">
        <div style="display: flex; align-items: center; gap: 8px;">
          <h2>Chapters</h2>
          <button class="btn" id="btnReloadLibraryDrawer" title="Rescan stories & chapters (R)" style="padding: 2px 8px; font-size: 11px;">
            ↻ Reload
          </button>
          <button class="btn" id="btnLayoutDrawer" title="Switch Reading Mode (Spread / Infinite Scroll)" style="padding: 2px 8px; font-size: 11px;">
            <span id="layoutDrawerIcon">📜 Scroll</span>
          </button>
        </div>
        <button class="btn" id="btnCloseToc">✕</button>
      </div>
      <ul class="toc-list" id="tocList">
        <!-- populated dynamically -->
      </ul>
    </aside>

    <!-- BOOK VIEWPORT -->
    <main class="book-stage" id="bookStage">
      <!-- TURN BUTTONS -->
      <button class="nav-turn-btn prev" id="btnPrevPage" title="Previous Page (Left Arrow / A / Swipe Right)">‹</button>
      <button class="nav-turn-btn next" id="btnNextPage" title="Next Page (Right Arrow / Space / D / Swipe Left)">›</button>

      <!-- SPREAD MODE CONTAINER -->
      <div class="book-spread" id="bookSpread">
        <!-- Left Page -->
        <article class="page page-left" id="pageLeft">
          <div class="page-running-header" id="headerLeft">Story Title</div>
          <div class="page-content" id="contentLeft"></div>
          <div class="page-running-footer">
            <span id="pageLeftNum">Page 1</span>
            <span id="chapterTagLeft">Chapter 1</span>
          </div>
        </article>

        <!-- Right Page -->
        <article class="page page-right" id="pageRight">
          <div class="page-running-header" id="headerRight">Chapter Title</div>
          <div class="page-content" id="contentRight"></div>
          <div class="page-running-footer">
            <span id="chapterTagRight">Chapter 1</span>
            <span id="pageRightNum">Page 2</span>
          </div>
        </article>
      </div>

      <!-- SINGLE COLUMN CONTAINER -->
      <!-- SINGLE COLUMN / INFINITE SCROLL CONTAINER -->
      <div class="book-single" id="bookSingle" style="display: none;">
        <div class="page-running-header" id="headerSingle">Chapter Title</div>
        <div class="page-content" id="contentSingle"></div>
      </div>
    </main>
  </div>

  <!-- BOTTOM STATUS & PROGRESS -->
  <footer class="app-footer">
    <div id="footerChapterInfo">Chapter 1</div>
    <div class="progress-track">
      <div class="progress-fill" id="progressFill"></div>
    </div>
    <div id="footerProgressInfo">Page 1 of 1</div>
  </footer>

  <!-- KEYBOARD SHORTCUTS & HELP MODAL -->
  <div class="modal-backdrop" id="helpModal">
    <div class="modal-box">
      <h3>StoryCrafter Web Reader</h3>
      <div class="shortcut-row"><span>Next Page / Chapter</span><span class="shortcut-key">Right / D / Swipe Left</span></div>
      <div class="shortcut-row"><span>Previous Page / Chapter</span><span class="shortcut-key">Left / A / Swipe Right</span></div>
      <div class="shortcut-row"><span>Scroll Down (Scroll Mode)</span><span class="shortcut-key">Space / PageDown</span></div>
      <div class="shortcut-row"><span>Table of Contents</span><span class="shortcut-key">M</span></div>
      <div class="shortcut-row"><span>Asset Gallery (\assets)</span><span class="shortcut-key">G</span></div>
      <div class="shortcut-row"><span>Cycle Theme</span><span class="shortcut-key">T</span></div>
      <div class="shortcut-row"><span>Toggle Sound Effect</span><span class="shortcut-key">S</span></div>
      <div class="shortcut-row"><span>Toggle Spread / Infinite Scroll</span><span class="shortcut-key">L</span></div>
      <div class="shortcut-row"><span>Font Size Up / Down</span><span class="shortcut-key">+ / -</span></div>
      <div class="shortcut-row"><span>Toggle Fullscreen</span><span class="shortcut-key">F</span></div>
      <div class="shortcut-row"><span>Reload Library</span><span class="shortcut-key">R</span></div>
      <div class="shortcut-row"><span>Close Dialogs</span><span class="shortcut-key">Esc</span></div>
      {lan_section}
      <div style="text-align: right; margin-top: 16px;">
        <button class="btn active" id="btnCloseModal">Got it</button>
      </div>
    </div>
  </div>

  <!-- ASSET GALLERY MODAL -->
  <div class="gallery-overlay" id="galleryModal">
    <div class="gallery-container">
      <div class="gallery-header">
        <div class="gallery-title-area">
          <div class="gallery-title">
            <span style="font-size: 20px;">🖼️</span>
            <h2>Root Asset Gallery</h2>
            <span class="gallery-badge-dir">(\\assets)</span>
            <span class="gallery-count-badge" id="galleryCountBadge">0 assets</span>
          </div>
          <p class="gallery-subtitle">Browsing standalone media assets in <code>\\assets</code> (independent of story chapters)</p>
        </div>
        <div class="gallery-actions">
          <button class="btn" id="btnReloadGallery" title="Rescan \\assets directory">
            ↻ Rescan
          </button>
          <button class="btn btn-close-gallery" id="btnCloseGallery" title="Close Gallery (Esc)">✕</button>
        </div>
      </div>

      <!-- FILTER & SEARCH BAR -->
      <div class="gallery-toolbar">
        <div class="gallery-search-box">
          <span style="font-size: 13px; opacity: 0.7;">🔍</span>
          <input type="text" id="gallerySearchInput" class="gallery-search-input" placeholder="Search assets by filename or folder...">
          <button class="btn-clear-search" id="btnClearSearch" style="display:none;" title="Clear search">✕</button>
        </div>
        <div class="gallery-folder-tabs" id="galleryFolderTabs">
          <!-- Populated dynamically with pills: All, rezero_nsfw, etc. -->
        </div>
      </div>

      <!-- GALLERY BODY -->
      <div class="gallery-body" id="galleryBody">
        <div class="gallery-grid" id="galleryGrid">
          <!-- Populated dynamically -->
        </div>
        <div class="gallery-empty" id="galleryEmpty" style="display:none;">
          <div class="gallery-empty-icon">📁</div>
          <div class="gallery-empty-text" id="galleryEmptyText">No assets found in \\assets</div>
        </div>
      </div>
    </div>
  </div>

  <!-- LIGHTBOX MODAL -->
  <div class="lightbox-overlay" id="lightboxModal">
    <div class="lightbox-dialog">
      <div class="lightbox-header">
        <div class="lightbox-title-info">
          <span class="lightbox-filename" id="lightboxFilename">filename.png</span>
          <span class="lightbox-folder-badge" id="lightboxFolderBadge">folder</span>
          <span class="lightbox-counter" id="lightboxCounter">1 / 18</span>
        </div>
        <div class="lightbox-top-actions">
          <button class="btn" id="btnCopyMdTag" title="Copy Markdown Tag">📋 Copy Markdown</button>
          <a class="btn" id="btnOpenOriginal" target="_blank" rel="noopener" title="Open Full Resolution">↗ Open Full</a>
          <button class="btn btn-close-lightbox" id="btnCloseLightbox" title="Close (Esc)">✕</button>
        </div>
      </div>

      <div class="lightbox-stage">
        <button class="lightbox-nav-btn prev" id="btnLightboxPrev" title="Previous Image (Left Arrow)">‹</button>
        <div class="lightbox-image-wrap">
          <img id="lightboxImage" src="" alt="Asset preview">
        </div>
        <button class="lightbox-nav-btn next" id="btnLightboxNext" title="Next Image (Right Arrow)">›</button>
      </div>

      <div class="lightbox-footer">
        <div class="lightbox-metadata" id="lightboxMeta">
          <span>📐 Dimensions</span>
          <span>💾 Size</span>
          <span>📁 Path</span>
        </div>
        <div class="lightbox-hint">Use ‹ / › or Left / Right arrow keys to browse · Esc to exit</div>
      </div>
    </div>
  </div>

  <!-- TOAST NOTIFICATION -->
  <div class="gallery-toast" id="galleryToast">Copied to clipboard!</div>

<!-- PRE-LOADED DATA FROM BACKEND -->
<script>
  window.APP_DATA = {embedded_json};
</script>

<script>
  // STATE MANAGEMENT
  const data = window.APP_DATA || {{ stories: [], config: {{}} }};
  let stories = data.stories || [];
  let currentConfig = Object.assign({{
    theme: 'parchment',
    font_size: 18,
    layout: 'spread',
    active_story: 'the_mockingbirds_ledger',
    active_chapter: 'ch01_the_gutter_and_the_mockingbird.md'
  }}, data.config || {{}});

  // INTERACTIVE STORY PROGRESS STATE
  let interactiveProgress = currentConfig.interactive_progress || {{}};
  try {{
    const localInteractive = localStorage.getItem('storycrafter_interactive_progress');
    if (localInteractive) {{
      interactiveProgress = Object.assign(JSON.parse(localInteractive), interactiveProgress);
    }}
  }} catch (e) {{}}

  function getStoryProgress(storyId) {{
    if (!interactiveProgress[storyId]) {{
      interactiveProgress[storyId] = {{
        current_chapter: null,
        history: [],
        discovered_endings: [],
        revealed_nodes: []
      }};
    }}
    return interactiveProgress[storyId];
  }}

  function saveInteractiveProgress() {{
    try {{
      localStorage.setItem('storycrafter_interactive_progress', JSON.stringify(interactiveProgress));
    }} catch (e) {{}}
    currentConfig.interactive_progress = interactiveProgress;
    saveState();
  }}

  let currentStoryIndex = 0;
  let currentChapterIndex = 0;
  let currentPagePair = 0;
  let totalPagePairs = 1;
  let splitPages = [];
  let isSinglePageOnMobile = false;

  // DOM Elements
  const body = document.body;
  const selectStory = document.getElementById('selectStory');
  const currentStoryTitle = document.getElementById('currentStoryTitle');
  const btnToggleToc = document.getElementById('btnToggleToc');
  const btnCloseToc = document.getElementById('btnCloseToc');
  const tocDrawer = document.getElementById('tocDrawer');
  const tocList = document.getElementById('tocList');
  const selectTheme = document.getElementById('selectTheme');
  const btnLayout = document.getElementById('btnLayout');
  const layoutIcon = document.getElementById('layoutIcon');
  const btnLayoutDrawer = document.getElementById('btnLayoutDrawer');
  const layoutDrawerIcon = document.getElementById('layoutDrawerIcon');
  const btnFontInc = document.getElementById('btnFontInc');
  const btnFontDec = document.getElementById('btnFontDec');
  const btnPrevPage = document.getElementById('btnPrevPage');
  const btnNextPage = document.getElementById('btnNextPage');
  const bookSpread = document.getElementById('bookSpread');
  const bookSingle = document.getElementById('bookSingle');
  const headerLeft = document.getElementById('headerLeft');
  const headerRight = document.getElementById('headerRight');
  const headerSingle = document.getElementById('headerSingle');
  const contentLeft = document.getElementById('contentLeft');
  const contentRight = document.getElementById('contentRight');
  const contentSingle = document.getElementById('contentSingle');
  const pageLeftNum = document.getElementById('pageLeftNum');
  const pageRightNum = document.getElementById('pageRightNum');
  const chapterTagLeft = document.getElementById('chapterTagLeft');
  const chapterTagRight = document.getElementById('chapterTagRight');
  const footerChapterInfo = document.getElementById('footerChapterInfo');
  const footerProgressInfo = document.getElementById('footerProgressInfo');
  const progressFill = document.getElementById('progressFill');
  const pageLeft = document.getElementById('pageLeft');
  const pageRight = document.getElementById('pageRight');
  const btnSound = document.getElementById('btnSound');
  const btnFullscreen = document.getElementById('btnFullscreen');
  const helpModal = document.getElementById('helpModal');
  const btnHelp = document.getElementById('btnHelp');
  const btnCloseModal = document.getElementById('btnCloseModal');
  const btnReloadLibrary = document.getElementById('btnReloadLibrary');
  const btnReloadLibraryDrawer = document.getElementById('btnReloadLibraryDrawer');

  // GLOBAL ASSET GALLERY STATE
  let galleryData = data.gallery || {{ total: 0, folders: ['All'], assets: [] }};
  let currentFolderFilter = 'All';
  let currentSearchQuery = '';
  let filteredAssets = [];
  let currentLightboxIndex = 0;

  // DOM Elements for Gallery
  const btnGallery = document.getElementById('btnGallery');
  const galleryModal = document.getElementById('galleryModal');
  const btnCloseGallery = document.getElementById('btnCloseGallery');
  const btnReloadGallery = document.getElementById('btnReloadGallery');
  const gallerySearchInput = document.getElementById('gallerySearchInput');
  const btnClearSearch = document.getElementById('btnClearSearch');
  const galleryFolderTabs = document.getElementById('galleryFolderTabs');
  const galleryGrid = document.getElementById('galleryGrid');
  const galleryEmpty = document.getElementById('galleryEmpty');
  const galleryEmptyText = document.getElementById('galleryEmptyText');
  const galleryCountBadge = document.getElementById('galleryCountBadge');

  // DOM Elements for Lightbox
  const lightboxModal = document.getElementById('lightboxModal');
  const btnCloseLightbox = document.getElementById('btnCloseLightbox');
  const lightboxImage = document.getElementById('lightboxImage');
  const lightboxFilename = document.getElementById('lightboxFilename');
  const lightboxFolderBadge = document.getElementById('lightboxFolderBadge');
  const lightboxCounter = document.getElementById('lightboxCounter');
  const lightboxMeta = document.getElementById('lightboxMeta');
  const btnLightboxPrev = document.getElementById('btnLightboxPrev');
  const btnLightboxNext = document.getElementById('btnLightboxNext');
  const btnOpenOriginal = document.getElementById('btnOpenOriginal');
  const btnCopyMdTag = document.getElementById('btnCopyMdTag');
  const galleryToast = document.getElementById('galleryToast');

  // ASSET GALLERY & LIGHTBOX LOGIC
  function showToast(msg) {{
    if (!galleryToast) return;
    galleryToast.textContent = msg;
    galleryToast.classList.add('show');
    clearTimeout(galleryToast._timer);
    galleryToast._timer = setTimeout(() => {{
      galleryToast.classList.remove('show');
    }}, 2400);
  }}

  function escapeHtml(str) {{
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }}

  function openGallery() {{
    galleryModal.classList.add('open');
    renderGallery();
  }}

  function closeGallery() {{
    galleryModal.classList.remove('open');
    closeLightbox();
  }}

  function renderFolderTabs() {{
    galleryFolderTabs.innerHTML = '';
    const folders = galleryData.folders || ['All'];
    folders.forEach(folder => {{
      const btn = document.createElement('button');
      btn.className = 'folder-tab-btn' + (folder === currentFolderFilter ? ' active' : '');
      let count = 0;
      if (folder === 'All') {{
        count = (galleryData.assets || []).length;
      }} else {{
        count = (galleryData.assets || []).filter(a => a.folder === folder).length;
      }}
      btn.textContent = `${{folder}} (${{count}})`;
      btn.onclick = () => {{
        currentFolderFilter = folder;
        renderFolderTabs();
        filterAndRenderAssets();
      }};
      galleryFolderTabs.appendChild(btn);
    }});
  }}

  function filterAndRenderAssets() {{
    const q = currentSearchQuery.trim().toLowerCase();
    const assets = galleryData.assets || [];
    filteredAssets = assets.filter(a => {{
      const matchFolder = (currentFolderFilter === 'All') || (a.folder === currentFolderFilter);
      const matchSearch = !q || (a.filename.toLowerCase().includes(q) || a.folder.toLowerCase().includes(q));
      return matchFolder && matchSearch;
    }});

    galleryCountBadge.textContent = `${{filteredAssets.length}} of ${{assets.length}} assets`;
    galleryGrid.innerHTML = '';

    if (filteredAssets.length === 0) {{
      galleryEmpty.style.display = 'flex';
      if (q) {{
        galleryEmptyText.textContent = `No assets match "${{currentSearchQuery}}" in folder "${{currentFolderFilter}}"`;
      }} else if (currentFolderFilter !== 'All') {{
        galleryEmptyText.textContent = `No assets found in folder "${{currentFolderFilter}}"`;
      }} else {{
        galleryEmptyText.textContent = 'No media assets found in root \\assets';
      }}
    }} else {{
      galleryEmpty.style.display = 'none';
      filteredAssets.forEach((asset, idx) => {{
        const card = document.createElement('div');
        card.className = 'asset-card';
        card.title = `${{asset.filename}} (${{asset.size_formatted}})`;

        const dimText = (asset.width && asset.height) ? `${{asset.width}}×${{asset.height}}` : 'Image';
        card.innerHTML = `
          <div class="asset-thumb-wrap">
            <span class="asset-folder-tag">${{escapeHtml(asset.folder)}}</span>
            <img class="asset-thumb-img" src="${{asset.url}}" alt="${{escapeHtml(asset.filename)}}" loading="lazy">
          </div>
          <div class="asset-info">
            <div class="asset-filename">${{escapeHtml(asset.filename)}}</div>
            <div class="asset-meta">
              <span>${{dimText}}</span>
              <span>${{asset.size_formatted}}</span>
            </div>
          </div>
        `;
        card.onclick = () => openLightbox(idx);
        galleryGrid.appendChild(card);
      }});
    }}
  }}

  function renderGallery() {{
    renderFolderTabs();
    filterAndRenderAssets();
  }}

  function openLightbox(idx) {{
    if (!filteredAssets.length) return;
    currentLightboxIndex = Math.max(0, Math.min(idx, filteredAssets.length - 1));
    const asset = filteredAssets[currentLightboxIndex];
    if (!asset) return;

    lightboxImage.src = asset.url;
    lightboxFilename.textContent = asset.filename;
    lightboxFolderBadge.textContent = asset.folder;
    lightboxCounter.textContent = `${{currentLightboxIndex + 1}} / ${{filteredAssets.length}}`;
    const dimText = (asset.width && asset.height) ? `${{asset.width}} × ${{asset.height}} px` : '';
    lightboxMeta.innerHTML = `
      ${{dimText ? `<span>📐 ${{dimText}}</span>` : ''}}
      <span>💾 ${{asset.size_formatted}}</span>
      <span>📁 \\assets\\${{escapeHtml(asset.rel_path)}}</span>
    `;
    btnOpenOriginal.href = asset.url;

    btnLightboxPrev.style.visibility = currentLightboxIndex > 0 ? 'visible' : 'hidden';
    btnLightboxNext.style.visibility = currentLightboxIndex < filteredAssets.length - 1 ? 'visible' : 'hidden';

    lightboxModal.classList.add('open');
  }}

  function closeLightbox() {{
    lightboxModal.classList.remove('open');
    lightboxImage.src = '';
  }}

  function nextLightbox() {{
    if (currentLightboxIndex < filteredAssets.length - 1) {{
      openLightbox(currentLightboxIndex + 1);
    }}
  }}

  function prevLightbox() {{
    if (currentLightboxIndex > 0) {{
      openLightbox(currentLightboxIndex - 1);
    }}
  }}

  async function reloadGalleryData() {{
    if (!btnReloadGallery) return;
    btnReloadGallery.disabled = true;
    btnReloadGallery.textContent = '...';
    try {{
      const res = await fetch('/api/gallery?t=' + Date.now());
      const fresh = await res.json();
      if (fresh && fresh.assets) {{
        galleryData = fresh;
        renderGallery();
        showToast(`Rescanned: ${{fresh.total}} assets found`);
      }}
    }} catch (e) {{
      console.error('Failed to reload gallery:', e);
      showToast('Error reloading gallery');
    }} finally {{
      btnReloadGallery.disabled = false;
      btnReloadGallery.textContent = '↻ Rescan';
    }}
  }}

  // AUDIO SYNTHESIZER FOR CRISP PAPER SWIPE
  let audioCtx = null;
  let soundEnabled = true;

  function getAudioContext() {{
    if (!audioCtx) {{
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) {{
        audioCtx = new AudioContextClass();
      }}
    }}
    if (audioCtx && audioCtx.state === 'suspended') {{
      audioCtx.resume();
    }}
    return audioCtx;
  }}

  function playPaperSound() {{
    if (!soundEnabled) return;
    try {{
      const ctx = getAudioContext();
      if (!ctx) return;
      const now = ctx.currentTime;

      // 160ms fibrous paper friction noise
      const duration = 0.16;
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const channelData = buffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {{
        const t = i / bufferSize;
        const env = Math.sin(t * Math.PI) * Math.exp(-t * 3.8);
        channelData[i] = (Math.random() * 2 - 1) * env;
      }}

      const noiseSource = ctx.createBufferSource();
      noiseSource.buffer = buffer;

      // Dynamic Bandpass Filter capturing crisp rustle
      const filter = ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(2800, now);
      filter.frequency.exponentialRampToValueAtTime(950, now + duration);
      filter.Q.setValueAtTime(2.0, now);

      // Highpass to eliminate muddy rumble
      const highpass = ctx.createBiquadFilter();
      highpass.type = 'highpass';
      highpass.frequency.setValueAtTime(700, now);

      // Fast attack, crisp decay envelope
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.01, now);
      gain.gain.linearRampToValueAtTime(0.38, now + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);

      noiseSource.connect(filter);
      filter.connect(highpass);
      highpass.connect(gain);
      gain.connect(ctx.destination);

      noiseSource.start(now);
    }} catch (e) {{}}
  }}

  function currentStory() {{
    return stories[currentStoryIndex] || {{ title: '', chapters: [] }};
  }}

  function currentChapter() {{
    return currentStory().chapters[currentChapterIndex] || {{ title: '', filename: '', html: '' }};
  }}

  // URL HASH ROUTING & DEEP LINKING
  function parseUrlHash() {{
    if (!window.location.hash) return null;
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    return {{
      story: params.get('story'),
      chapter: params.get('chapter'),
      page: params.get('page') !== null ? parseInt(params.get('page'), 10) : null,
      layout: params.get('layout')
    }};
  }}

  function syncUrlHash() {{
    const st = currentStory();
    const ch = currentChapter();
    if (!st || !ch) return;
    let hash = `#story=${{encodeURIComponent(st.id)}}&chapter=${{encodeURIComponent(ch.filename)}}`;
    if (currentConfig.layout === 'spread') {{
      hash += `&page=${{currentPagePair}}`;
    }} else {{
      hash += `&layout=scroll`;
    }}
    if (window.location.hash !== hash) {{
      history.replaceState(null, '', hash);
    }}
  }}

  function isMobileClient() {{
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
           (window.innerWidth <= 820 && window.matchMedia && window.matchMedia('(pointer: coarse)').matches) ||
           window.innerWidth <= 820;
  }}

  // INITIALIZATION
  function init() {{
    if (!stories.length) {{
      console.warn("No stories loaded.");
      return;
    }}

    // Check responsive viewport
    checkViewport();

    // Check URL Hash first, then config
    const hashParams = parseUrlHash();
    const activeStoryId = (hashParams && hashParams.story) || currentConfig.active_story;
    const activeChapterFile = (hashParams && hashParams.chapter) || currentConfig.active_chapter;
    const activePage = (hashParams && hashParams.page !== null) ? hashParams.page : currentConfig.page_index;

    // Mobile detection & Layout preference: default to infinite scroll on mobile
    const isMobile = isMobileClient();
    let savedLayout = null;
    try {{
      savedLayout = localStorage.getItem('storycrafter_layout_override');
    }} catch (e) {{}}

    if (hashParams && hashParams.layout) {{
      currentConfig.layout = (hashParams.layout === 'scroll' || hashParams.layout === 'single') ? 'scroll' : 'spread';
    }} else if (savedLayout) {{
      currentConfig.layout = (savedLayout === 'scroll' || savedLayout === 'single') ? 'scroll' : 'spread';
    }} else if (isMobile) {{
      currentConfig.layout = 'scroll';
    }} else if (currentConfig.layout === 'single') {{
      currentConfig.layout = 'scroll';
    }}

    if (activeStoryId) {{
      const sIdx = stories.findIndex(s => s.id === activeStoryId);
      if (sIdx !== -1) currentStoryIndex = sIdx;
    }}

    populateStorySelect();
    selectStory.value = currentStoryIndex;

    if (activeChapterFile) {{
      const cIdx = currentStory().chapters.findIndex(c => c.filename === activeChapterFile);
      if (cIdx !== -1) currentChapterIndex = cIdx;
    }} else {{
      const st = currentStory();
      if (st && st.is_interactive) {{
        const prog = getStoryProgress(st.id);
        if (prog && prog.current_chapter) {{
          const cIdx = st.chapters.findIndex(c => c.filename === prog.current_chapter);
          if (cIdx !== -1) currentChapterIndex = cIdx;
        }}
      }}
    }}

    if (activePage !== undefined && activePage !== null) {{
      currentPagePair = Math.max(0, activePage);
    }}

    applyConfig();
    updateStoryView();
    renderGallery();

    if (currentConfig.layout === 'scroll') {{
      renderInfiniteScroll(currentChapterIndex);
    }} else {{
      loadChapter(currentChapterIndex, false, null, currentPagePair);
    }}

    requestAnimationFrame(() => {{
      const ch = currentChapter();
      if (ch && ch.html && currentConfig.layout === 'spread') {{
        splitPagesIntoSpreads(ch.html, ch.title);
      }}
    }});

    if (document.fonts && document.fonts.ready) {{
      document.fonts.ready.then(() => {{
        const ch = currentChapter();
        if (ch && ch.html && currentConfig.layout === 'spread') {{
          splitPagesIntoSpreads(ch.html, ch.title);
        }}
      }});
    }}
  }}

  function checkViewport() {{
    isSinglePageOnMobile = window.innerWidth <= 820;
  }}

  function applyConfig() {{
    body.setAttribute('data-theme', currentConfig.theme);
    selectTheme.value = currentConfig.theme;
    document.querySelectorAll('.page-content, .chapter-body-html').forEach(el => {{
      el.style.fontSize = currentConfig.font_size + 'px';
    }});
    updateLayoutDisplay();
  }}

  function updateLayoutDisplay() {{
    const isSpread = currentConfig.layout === 'spread';
    body.setAttribute('data-layout', isSpread ? 'spread' : 'scroll');

    const btnPrevPage = document.getElementById('btnPrevPage');
    const btnNextPage = document.getElementById('btnNextPage');

    if (isSpread) {{
      bookSpread.style.display = 'grid';
      bookSingle.style.display = 'none';
      layoutIcon.innerHTML = '<span>📖</span> <span class="btn-text">Spread</span>';
      btnLayout.title = 'Current Mode: Book Spread (Click or press L for Infinite Scroll)';
      if (layoutDrawerIcon) layoutDrawerIcon.textContent = '📜 Scroll Mode';
      if (btnPrevPage) btnPrevPage.style.display = '';
      if (btnNextPage) btnNextPage.style.display = '';
    }} else {{
      bookSpread.style.display = 'none';
      bookSingle.style.display = 'flex';
      layoutIcon.innerHTML = '<span>📜</span> <span class="btn-text">Scroll</span>';
      btnLayout.title = 'Current Mode: Infinite Scroll (Click or press L for Book Spread)';
      if (layoutDrawerIcon) layoutDrawerIcon.textContent = '📖 Spread Mode';
      if (btnPrevPage) btnPrevPage.style.display = 'none';
      if (btnNextPage) btnNextPage.style.display = 'none';
    }}
  }}

  function populateStorySelect() {{
    selectStory.innerHTML = '';
    stories.forEach((st, idx) => {{
      const opt = document.createElement('option');
      opt.value = idx;
      opt.textContent = st.title;
      selectStory.appendChild(opt);
    }});
  }}

  function buildInteractiveBlockHtml(ch) {{
    if (!ch) return '';
    const st = currentStory();
    if (!st || !st.is_interactive) return '';

    if (ch.is_ending) {{
      const prog = getStoryProgress(st.id);
      if (!prog.discovered_endings.includes(ch.filename)) {{
        prog.discovered_endings.push(ch.filename);
        saveInteractiveProgress();
      }}
      const endingIndex = (st.endings ? st.endings.findIndex(e => e.filename === ch.filename) : -1) + 1;
      const totalEndings = st.total_endings || (st.endings ? st.endings.length : 1);
      return `
        <div class="ending-card">
          <div class="ending-ribbon">✦ Ending Reached ✦</div>
          <h2 class="ending-heading">${{escapeHtml(ch.ending_title || ch.title)}}</h2>
          <div class="ending-meta-badge">Discovered: Ending ${{endingIndex || 1}} of ${{totalEndings}}</div>
          <div class="ending-actions">
            <button class="btn btn-interactive active" onclick="handleRestartStory()">↻ Restart Story</button>
            <button class="btn btn-interactive" onclick="handleBacktrack()">⮌ Backtrack to Previous Choice</button>
          </div>
        </div>
      `;
    }}

    if (ch.choices && ch.choices.length > 0) {{
      let optionsHtml = '';
      ch.choices.forEach(opt => {{
        optionsHtml += `
          <button class="choice-card" onclick="handleChoiceClick('${{escapeHtml(opt.target)}}')">
            <span class="choice-icon">➤</span>
            <span class="choice-text">${{escapeHtml(opt.text)}}</span>
          </button>
        `;
      }});
      return `
        <div class="choice-container">
          <div class="interactive-choice-header">❦ Decide Your Course ❦</div>
          <div class="choice-options-grid">
            ${{optionsHtml}}
          </div>
          <div style="margin-top: 12px;">
            <button class="btn" style="font-size: 11px; opacity: 0.8;" onclick="handleBacktrack()">⮌ Backtrack to Previous Choice</button>
          </div>
        </div>
      `;
    }}

    return '';
  }}

  function handleChoiceClick(targetFilename) {{
    const st = currentStory();
    if (!st || !st.chapters) return;
    const targetIdx = st.chapters.findIndex(c => c.filename === targetFilename);
    if (targetIdx === -1) {{
      showToast('Destination chapter not found: ' + targetFilename);
      return;
    }}
    const currentCh = st.chapters[currentChapterIndex];
    const prog = getStoryProgress(st.id);
    if (currentCh && !prog.history.includes(currentCh.filename)) {{
      prog.history.push(currentCh.filename);
    }}
    if (!prog.revealed_nodes.includes(targetFilename)) {{
      prog.revealed_nodes.push(targetFilename);
    }}
    prog.current_chapter = targetFilename;
    saveInteractiveProgress();

    playPaperSound();
    if (currentConfig.layout === 'scroll') {{
      scrollToChapter(targetIdx, true);
    }} else {{
      loadChapter(targetIdx, false, 'next', 0);
    }}
    renderToc();
  }}

  function handleBacktrack() {{
    const st = currentStory();
    if (!st || !st.is_interactive) return;
    const prog = getStoryProgress(st.id);
    if (!prog.history || prog.history.length === 0) {{
      showToast('Already at the opening chapter.');
      return;
    }}
    const prevFilename = prog.history.pop();
    const prevIdx = st.chapters.findIndex(c => c.filename === prevFilename);
    prog.current_chapter = prevFilename;
    saveInteractiveProgress();

    playPaperSound();
    if (prevIdx !== -1) {{
      if (currentConfig.layout === 'scroll') {{
        scrollToChapter(prevIdx, true);
      }} else {{
        loadChapter(prevIdx, false, 'prev', 0);
      }}
      showToast('Backtracked to previous chapter.');
    }}
    renderToc();
  }}

  function handleRestartStory() {{
    const st = currentStory();
    if (!st || !st.is_interactive) return;
    const prog = getStoryProgress(st.id);
    prog.history = [];
    const rootChapter = st.chapters[0];
    prog.current_chapter = rootChapter ? rootChapter.filename : null;
    if (rootChapter && !prog.revealed_nodes.includes(rootChapter.filename)) {{
      prog.revealed_nodes.push(rootChapter.filename);
    }}
    saveInteractiveProgress();

    playPaperSound();
    if (currentConfig.layout === 'scroll') {{
      scrollToChapter(0, true);
    }} else {{
      loadChapter(0, false, 'prev', 0);
    }}
    showToast('Story restarted from Chapter 1.');
    renderToc();
  }}

  function updateStoryView() {{
    const st = currentStory();
    currentStoryTitle.textContent = st.title;
    const badge = document.getElementById('storyModeBadge');
    if (badge) {{
      if (st.is_interactive) {{
        badge.style.display = 'inline-flex';
        badge.textContent = `🎲 Interactive (${{st.total_endings || (st.endings ? st.endings.length : 5)}} Endings)`;
      }} else {{
        badge.style.display = 'none';
      }}
    }}
    renderToc();
  }}

  function renderToc() {{
    tocList.innerHTML = '';
    const st = currentStory();
    if (!st) return;

    if (!st.is_interactive) {{
      const chs = st.chapters;
      chs.forEach((ch, idx) => {{
        const li = document.createElement('li');
        li.className = 'toc-item' + (idx === currentChapterIndex ? ' active' : '');
        li.innerHTML = `
          <span class="ch-num">Chapter ${{ch.index}}</span>
          <span class="ch-name">${{ch.title}}</span>
          <span class="ch-meta">${{ch.word_count}} words · ${{ch.reading_time}}</span>
        `;
        li.onclick = () => {{
          if (currentConfig.layout === 'scroll') {{
            scrollToChapter(idx, true);
          }} else {{
            loadChapter(idx, false, 'next');
          }}
          tocDrawer.classList.remove('open');
        }};
        tocList.appendChild(li);
      }});
      return;
    }}

    // INTERACTIVE STORY MAP TOC
    const prog = getStoryProgress(st.id);
    const discoveredCount = (prog.discovered_endings || []).length;
    const totalEndings = st.total_endings || (st.endings ? st.endings.length : 5);
    const progressPct = Math.round((discoveredCount / Math.max(1, totalEndings)) * 100);

    const trackerContainer = document.createElement('div');
    trackerContainer.className = 'toc-interactive-panel';
    trackerContainer.innerHTML = `
      <div class="toc-tracker-card">
        <div class="toc-tracker-title-row">
          <span class="toc-tracker-label">🏆 Endings Discovered</span>
          <span class="toc-tracker-stat">${{discoveredCount}} / ${{totalEndings}}</span>
        </div>
        <div class="toc-progress-track">
          <div class="toc-progress-fill" style="width: ${{progressPct}}%"></div>
        </div>
      </div>

      <div class="toc-path-header">
        <span>🧭 Active Playthrough Path</span>
        <button class="btn-toc-action" onclick="handleRestartStory()" title="Restart from Chapter 1">↻ Restart</button>
      </div>
      <div class="toc-path-trail" id="tocPathTrail"></div>

      <div class="toc-section-header">📜 Story Map (Fog-of-War)</div>
    `;
    tocList.appendChild(trackerContainer);

    const pathTrailEl = trackerContainer.querySelector('#tocPathTrail');
    const pathList = [...(prog.history || [])];
    const currentCh = st.chapters[currentChapterIndex];
    if (currentCh && !pathList.includes(currentCh.filename)) {{
      pathList.push(currentCh.filename);
    }}
    if (pathList.length === 0 && currentCh) pathList.push(currentCh.filename);

    pathList.forEach((fname, stepIdx) => {{
      const chObj = st.chapters.find(c => c.filename === fname);
      if (!chObj) return;
      const chip = document.createElement('span');
      chip.className = 'toc-path-chip' + (fname === currentCh.filename ? ' active' : '');
      chip.textContent = chObj.title;
      chip.title = `Step ${{stepIdx + 1}}: ${{chObj.title}} (Click to navigate)`;
      chip.onclick = () => {{
        const cIdx = st.chapters.findIndex(c => c.filename === fname);
        if (cIdx !== -1) {{
          if (currentConfig.layout === 'scroll') scrollToChapter(cIdx, true);
          else loadChapter(cIdx, false, null, 0);
          tocDrawer.classList.remove('open');
        }}
      }};
      pathTrailEl.appendChild(chip);
      if (stepIdx < pathList.length - 1) {{
        const arrow = document.createElement('span');
        arrow.className = 'toc-path-arrow';
        arrow.textContent = '›';
        pathTrailEl.appendChild(arrow);
      }}
    }});

    st.chapters.forEach((ch, idx) => {{
      const isCurrent = idx === currentChapterIndex;
      const isVisited = (prog.history || []).includes(ch.filename) || isCurrent;
      const isRevealed = isVisited || (prog.revealed_nodes || []).includes(ch.filename) || idx === 0;

      const li = document.createElement('li');
      li.className = 'toc-item interactive-toc-item' + (isCurrent ? ' active' : '') + (isVisited ? ' visited' : '') + (!isRevealed ? ' locked' : '');

      if (isRevealed) {{
        let tagBadge = '';
        if (ch.is_ending) {{
          const isEndingDiscovered = (prog.discovered_endings || []).includes(ch.filename);
          tagBadge = isEndingDiscovered 
            ? '<span class="ch-badge ending-discovered">✓ Discovered Ending</span>' 
            : '<span class="ch-badge ending-revealed">★ Ending Node</span>';
        }} else if (idx === 0) {{
          tagBadge = '<span class="ch-badge root-node">◆ Opening Chapter</span>';
        }} else {{
          tagBadge = '<span class="ch-badge branch-node">⑂ Decision Node</span>';
        }}

        li.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span class="ch-num">${{isVisited ? '● Visited' : '○ Unlocked Branch'}}</span>
            ${{tagBadge}}
          </div>
          <span class="ch-name">${{ch.title}}</span>
          <span class="ch-meta">${{ch.word_count}} words · ${{ch.reading_time}}</span>
        `;
        li.onclick = () => {{
          if (currentConfig.layout === 'scroll') {{
            scrollToChapter(idx, true);
          }} else {{
            loadChapter(idx, false, 'next', 0);
          }}
          tocDrawer.classList.remove('open');
        }};
      }} else {{
        li.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: space-between;">
            <span class="ch-num" style="opacity: 0.6;">🔒 Locked Branch</span>
          </div>
          <span class="ch-name" style="opacity: 0.5; font-style: italic;">??? (Unexplored Choice)</span>
          <span class="ch-meta" style="opacity: 0.5;">Make decisions in story to reveal</span>
        `;
      }}
      tocList.appendChild(li);
    }});
  }}

  function renderInfiniteScroll(targetChapterIndex = null) {{
    const st = currentStory();
    if (!st || !st.chapters || !st.chapters.length) {{
      contentSingle.innerHTML = '<p class="empty-notice" style="text-align: center; padding: 40px; color: var(--text-muted);">No chapters found in this story.</p>';
      return;
    }}

    let html = '';
    st.chapters.forEach((ch, idx) => {{
      let interactiveHtml = '';
      if (st.is_interactive) {{
        interactiveHtml = `<div class="interactive-block">${{buildInteractiveBlockHtml(ch)}}</div>`;
      }}
      html += `
        <article class="chapter-scroll-section" id="chapter-scroll-${{idx}}" data-chapter-index="${{idx}}">
          <div class="chapter-title-block">
            <div class="chapter-eyebrow">${{ch.is_ending ? 'Ending' : 'Chapter ' + (idx + 1)}}</div>
            <h1 class="chapter-main-title">${{escapeHtml(ch.title)}}</h1>
            <div class="chapter-ornament">❦  ❧</div>
          </div>
          <div class="has-drop-cap chapter-body-html">${{ch.html}}</div>
          ${{interactiveHtml}}
          <div class="chapter-scroll-footer">
            <div class="chapter-scroll-divider">✦ ✦ ✦</div>
            <div class="chapter-meta-tag">${{ch.word_count}} words · ${{ch.reading_time}} read</div>
          </div>
        </article>
      `;
    }});

    html += `
      <div class="story-end-block">
        <div class="story-end-ornament">❦  ❦  ❦</div>
        <div class="story-end-title">End of ${{escapeHtml(st.title)}}</div>
        <button class="btn btn-back-to-top" id="btnBackToTop">↑ Return to Top</button>
      </div>
    `;

    contentSingle.innerHTML = html;

    const btnBackToTop = document.getElementById('btnBackToTop');
    if (btnBackToTop) {{
      btnBackToTop.onclick = () => {{
        scrollToChapter(0, true);
      }};
    }}

    // Apply font size
    document.querySelectorAll('.page-content, .chapter-body-html').forEach(el => {{
      el.style.fontSize = currentConfig.font_size + 'px';
    }});

    const targetIdx = (targetChapterIndex !== null && targetChapterIndex !== undefined) ? targetChapterIndex : currentChapterIndex;
    if (targetIdx > 0 && targetIdx < st.chapters.length) {{
      requestAnimationFrame(() => {{
        scrollToChapter(targetIdx, false);
      }});
    }} else {{
      const ch = st.chapters[0];
      if (ch) {{
        headerSingle.textContent = `${{st.title}} — ${{ch.title}}`;
        footerChapterInfo.textContent = `${{st.title}} — Chapter 1 of ${{st.chapters.length}}`;
      }}
      updateScrollHeaderAndFooter();
    }}
  }}

  function scrollToChapter(idx, smooth = true) {{
    const st = currentStory();
    if (!st || !st.chapters || idx < 0 || idx >= st.chapters.length) return;
    currentChapterIndex = idx;
    const target = document.getElementById(`chapter-scroll-${{idx}}`);
    if (target && bookSingle) {{
      const targetTop = target.offsetTop - 10;
      bookSingle.scrollTo({{ top: Math.max(0, targetTop), behavior: smooth ? 'smooth' : 'auto' }});
    }}
    const ch = st.chapters[idx];
    if (ch) {{
      headerSingle.textContent = `${{st.title}} — ${{ch.title}}`;
      footerChapterInfo.textContent = `${{st.title}} — Chapter ${{idx + 1}} of ${{st.chapters.length}}`;
    }}
    renderToc();
    syncUrlHash();
    saveState();
  }}

  function updateScrollHeaderAndFooter() {{
    if (currentConfig.layout !== 'scroll') return;
    const sections = bookSingle.querySelectorAll('.chapter-scroll-section');
    if (!sections.length) return;

    const containerTop = bookSingle.getBoundingClientRect().top;
    let activeIdx = currentChapterIndex;

    sections.forEach((sec, idx) => {{
      const rect = sec.getBoundingClientRect();
      if (rect.top - containerTop <= 160 && rect.bottom - containerTop > 40) {{
        activeIdx = idx;
      }}
    }});

    if (activeIdx !== currentChapterIndex) {{
      currentChapterIndex = activeIdx;
      const ch = currentStory().chapters[currentChapterIndex];
      if (ch) {{
        headerSingle.textContent = `${{currentStory().title}} — ${{ch.title}}`;
        footerChapterInfo.textContent = `${{currentStory().title}} — Chapter ${{currentChapterIndex + 1}} of ${{currentStory().chapters.length}}`;
        renderToc();
        syncUrlHash();
        saveState();
      }}
    }}

    const scrollRange = bookSingle.scrollHeight - bookSingle.clientHeight;
    if (scrollRange > 0) {{
      const pct = Math.min(100, Math.max(0, Math.round((bookSingle.scrollTop / scrollRange) * 100)));
      progressFill.style.width = pct + '%';
      footerProgressInfo.textContent = pct + '% Read';
    }}
  }}

  function loadChapter(idx, startAtEnd = false, direction = null, specificPage = null) {{
    currentChapterIndex = idx;
    const ch = currentStory().chapters[idx];
    if (!ch) return;

    if (currentConfig.layout === 'scroll') {{
      scrollToChapter(idx, false);
      return;
    }}

    if (specificPage !== null && specificPage !== undefined) {{
      currentPagePair = specificPage;
    }} else {{
      currentPagePair = startAtEnd ? 999999 : 0;
    }}

    renderToc();
    const st = currentStory();
    if (st.is_interactive) {{
      footerChapterInfo.textContent = ch.is_ending
        ? `${{st.title}} — Ending: ${{ch.title}}`
        : `${{st.title}} — ${{ch.title}}`;
    }} else {{
      footerChapterInfo.textContent = `${{st.title}} — Chapter ${{idx + 1}} of ${{st.chapters.length}}`;
    }}

    renderChapterContent(ch, direction);
    saveState();
  }}

  function renderChapterContent(ch, direction = null) {{
    const st = currentStory();
    const rawHtml = ch.html;
    const title = ch.title;
    const isEnding = Boolean(ch.is_ending);
    let interactiveHtml = '';
    if (st.is_interactive) {{
      interactiveHtml = `<div class="interactive-block">${{buildInteractiveBlockHtml(ch)}}</div>`;
    }}

    // Single Scroll View
    headerSingle.textContent = `${{st.title}} — ${{title}}`;
    contentSingle.innerHTML = `
      <div class="chapter-title-block">
        <div class="chapter-eyebrow">${{isEnding ? 'Ending' : 'Chapter ' + (currentChapterIndex + 1)}}</div>
        <h1 class="chapter-main-title">${{title}}</h1>
        <div class="chapter-ornament">❦  ❧</div>
      </div>
      <div class="has-drop-cap">${{rawHtml}}</div>
      ${{interactiveHtml}}
    `;
    const singleWc = document.getElementById('singleWordCount');
    if (singleWc) singleWc.textContent = `${{ch.word_count}} words`;
    const singleRt = document.getElementById('singleReadTime');
    if (singleRt) singleRt.textContent = `${{ch.reading_time}} read`;

    if (direction && currentConfig.layout === 'single') {{
      contentSingle.classList.remove('swish-next', 'swish-prev');
      void contentSingle.offsetWidth;
      contentSingle.classList.add(direction === 'next' ? 'swish-next' : 'swish-prev');
      playPaperSound();
    }}

    // Split into pages for Spread View
    const fullHtml = rawHtml + (interactiveHtml ? '\n' + interactiveHtml : '');
    splitPagesIntoSpreads(fullHtml, title, direction, isEnding);
  }}

  function splitHtmlIntoTokens(inner) {{
    return inner.split(/(\\s+|<[^>]+>)/).filter(t => t.length > 0);
  }}

  function buildSubParagraph(tokens, start, end, isContinuation, tagName = 'p') {{
    if (start >= end) return '';
    let openTags = [];
    for (let i = 0; i < start; i++) {{
      const t = tokens[i];
      if (t.startsWith('</')) {{
        openTags.pop();
      }} else if (t.startsWith('<') && !t.endsWith('/>')) {{
        const m = t.match(/<([a-zA-Z0-9]+)/);
        if (m) openTags.push(m[1]);
      }}
    }}

    let result = '';
    for (const tag of openTags) {{
      result += '<' + tag + '>';
    }}

    let activeTags = [...openTags];
    for (let i = start; i < end; i++) {{
      const t = tokens[i];
      result += t;
      if (t.startsWith('</')) {{
        activeTags.pop();
      }} else if (t.startsWith('<') && !t.endsWith('/>')) {{
        const m = t.match(/<([a-zA-Z0-9]+)/);
        if (m) activeTags.push(m[1]);
      }}
    }}

    for (let i = activeTags.length - 1; i >= 0; i--) {{
      result += '</' + activeTags[i] + '>';
    }}

    const trimmed = result.trim();
    if (!trimmed) return '';
    const cls = isContinuation ? ' class="paragraph-continuation"' : '';
    return `<${{tagName}}${{cls}}>${{trimmed}}</${{tagName}}>`;
  }}

  function splitPagesIntoSpreads(rawHtml, title, direction = null, isEnding = false) {{
    checkViewport();
    const targetHeight = Math.max(320, (contentLeft.clientHeight > 50 ? contentLeft.clientHeight : (window.innerHeight - 190)));
    const targetWidth = Math.max(280, (contentLeft.clientWidth > 50 ? contentLeft.clientWidth : (isSinglePageOnMobile ? window.innerWidth - 60 : Math.floor((window.innerWidth - 160) / 2))));

    const tester = document.createElement('div');
    tester.className = 'page-content';
    tester.style.cssText = `
      position: absolute;
      visibility: hidden;
      left: -9999px;
      top: 0;
      width: ${{targetWidth}}px;
      height: ${{targetHeight}}px;
      max-height: ${{targetHeight}}px;
      font-size: ${{currentConfig.font_size}}px;
      line-height: 1.75;
      text-align: justify;
      hyphens: auto;
      box-sizing: border-box;
      overflow: hidden;
      padding: 0;
      margin: 0;
    `;
    document.body.appendChild(tester);

    const temp = document.createElement('div');
    temp.innerHTML = rawHtml;
    const nodes = Array.from(temp.children);

    splitPages = [];
    let currentPageNodes = [];

    const titleBlockHtml = `
      <div class="chapter-title-block">
        <div class="chapter-eyebrow">${{isEnding ? 'Ending' : 'Chapter ' + (currentChapterIndex + 1)}}</div>
        <h1 class="chapter-main-title">${{title}}</h1>
        <div class="chapter-ornament">❦  ❧</div>
      </div>
    `;

    tester.innerHTML = titleBlockHtml;
    currentPageNodes.push(titleBlockHtml);
    let isFirstPage = true;

    for (let i = 0; i < nodes.length; i++) {{
      const node = nodes[i];
      const nodeHtml = node.outerHTML;
      const isImage = node.matches('figure, .book-figure, img') || Boolean(node.querySelector('img, figure, .book-figure'));
      const isInteractiveBlock = node.matches('.interactive-block') || Boolean(node.querySelector('.interactive-block'));

      if (isImage) {{
        // If there is preceding content accumulated on the current page, close and push that page
        if (currentPageNodes.length > 0) {{
          splitPages.push(currentPageNodes.join(''));
          currentPageNodes = [];
          tester.innerHTML = '';
          isFirstPage = false;
        }}
        // The picture ALWAYS starts on its own new page at the very top
        splitPages.push(nodeHtml);
        tester.innerHTML = '';
        isFirstPage = false;
        continue;
      }}

      if (isInteractiveBlock) {{
        // Test if interactive block fits on current page
        const testCurrent = currentPageNodes.join('') + nodeHtml;
        tester.innerHTML = testCurrent;
        if (tester.scrollHeight <= targetHeight + 6) {{
          currentPageNodes.push(nodeHtml);
        }} else {{
          if (currentPageNodes.length > 0) {{
            splitPages.push(currentPageNodes.join(''));
            currentPageNodes = [];
            tester.innerHTML = '';
            isFirstPage = false;
          }}
          splitPages.push(nodeHtml);
        }}
        continue;
      }}

      // Check if nodeHtml fits entirely on the current page
      const testCurrent = currentPageNodes.join('') + nodeHtml;
      tester.innerHTML = testCurrent;

      if (tester.scrollHeight <= targetHeight + 6) {{
        currentPageNodes.push(nodeHtml);
        continue;
      }}

      // Node does not fit on current page.
      // Check if it fits whole on a fresh empty page:
      const canPushCurrent = currentPageNodes.length > (isFirstPage ? 1 : 0);
      tester.innerHTML = nodeHtml;
      if (canPushCurrent && tester.scrollHeight <= targetHeight + 6) {{
        splitPages.push(currentPageNodes.join(''));
        currentPageNodes = [nodeHtml];
        tester.innerHTML = nodeHtml;
        isFirstPage = false;
        continue;
      }}

      // Node is a long paragraph that cannot fit on a single page,
      // or current page already has prior content: push current page if possible so paragraph begins cleanly
      if (canPushCurrent) {{
        splitPages.push(currentPageNodes.join(''));
        currentPageNodes = [];
        tester.innerHTML = '';
        isFirstPage = false;
      }}

      // Binary-search splitting for long paragraphs/blockquotes across pages
      const tagName = (node.tagName && node.tagName.toLowerCase() === 'blockquote') ? 'blockquote' : 'p';
      const tagRegex = new RegExp(`^<${{tagName}}[^>]*>([\\\\s\\\\S]*)<\\\\/${{tagName}}>$`, 'i');
      const m = nodeHtml.match(tagRegex);
      const inner = m ? m[1] : nodeHtml;
      const tokens = splitHtmlIntoTokens(inner);

      let remainingTokens = tokens;
      let isContinuation = false;

      while (remainingTokens.length > 0) {{
        const baseHtml = currentPageNodes.join('');
        let low = 1;
        let high = remainingTokens.length;
        let bestFit = 0;

        while (low <= high) {{
          const mid = Math.floor((low + high) / 2);
          const cand = buildSubParagraph(remainingTokens, 0, mid, isContinuation, tagName);
          tester.innerHTML = baseHtml + cand;
          if (tester.scrollHeight <= targetHeight + 6) {{
            bestFit = mid;
            low = mid + 1;
          }} else {{
            high = mid - 1;
          }}
        }}

        if (bestFit === 0) {{
          if (currentPageNodes.length > 0) {{
            splitPages.push(currentPageNodes.join(''));
            currentPageNodes = [];
            tester.innerHTML = '';
            isFirstPage = false;
            continue;
          }} else {{
            bestFit = Math.min(remainingTokens.length, 1);
          }}
        }}

        const chunkHtml = buildSubParagraph(remainingTokens, 0, bestFit, isContinuation, tagName);
        remainingTokens = remainingTokens.slice(bestFit);
        isContinuation = true;

        if (remainingTokens.length > 0) {{
          currentPageNodes.push(chunkHtml);
          splitPages.push(currentPageNodes.join(''));
          currentPageNodes = [];
          tester.innerHTML = '';
          isFirstPage = false;
        }} else {{
          currentPageNodes.push(chunkHtml);
          tester.innerHTML = currentPageNodes.join('');
        }}
      }}
    }}

    if (currentPageNodes.length > 0) {{
      splitPages.push(currentPageNodes.join(''));
    }}

    document.body.removeChild(tester);

    // On narrow screens (mobile), 1 page per spread step; on wide desktop, 2 pages per spread
    const pagesPerStep = isSinglePageOnMobile ? 1 : 2;
    totalPagePairs = Math.max(1, Math.ceil(splitPages.length / pagesPerStep));

    if (currentPagePair >= totalPagePairs) {{
      currentPagePair = totalPagePairs - 1;
    }}
    if (currentPagePair < 0) {{
      currentPagePair = 0;
    }}
    renderCurrentSpread(direction);
  }}

  function renderCurrentSpread(direction = null) {{
    checkViewport();
    const pagesPerStep = isSinglePageOnMobile ? 1 : 2;
    const leftIndex = currentPagePair * pagesPerStep;
    const rightIndex = leftIndex + 1;

    headerLeft.textContent = currentStory().title;
    headerRight.textContent = currentChapter().title;

    chapterTagLeft.textContent = `Chapter ${{currentChapterIndex + 1}}`;
    chapterTagRight.textContent = `Chapter ${{currentChapterIndex + 1}}`;

    const leftHtml = splitPages[leftIndex] || '<p style="color:var(--text-muted); text-align:center; padding-top:40px;"><em>End of chapter.</em></p>';
    const rightHtml = isSinglePageOnMobile ? '' : (splitPages[rightIndex] || '');

    contentLeft.innerHTML = leftHtml;
    contentRight.innerHTML = rightHtml;

    // Drop cap on first narrative paragraph of chapter
    const firstParaIndex = splitPages.findIndex(p => p.includes('<p'));
    pageLeft.classList.toggle('has-drop-cap', leftIndex === firstParaIndex);
    pageRight.classList.toggle('has-drop-cap', !isSinglePageOnMobile && rightIndex === firstParaIndex);

    // Track illustration page to apply dedicated top-aligned full layout
    pageLeft.classList.toggle('has-illustration', leftHtml.includes('book-figure'));
    pageRight.classList.toggle('has-illustration', !isSinglePageOnMobile && rightHtml.includes('book-figure'));

    // Track standalone title-card page
    const isTitleOnly = (h) => h && h.includes('chapter-title-block') && !h.includes('<p') && !h.includes('book-figure');
    pageLeft.classList.toggle('is-title-page', isTitleOnly(leftHtml));
    pageRight.classList.toggle('is-title-page', !isSinglePageOnMobile && isTitleOnly(rightHtml));

    contentLeft.scrollTop = 0;
    contentRight.scrollTop = 0;

    pageLeftNum.textContent = `Page ${{leftIndex + 1}}`;
    pageRightNum.textContent = (!isSinglePageOnMobile && rightIndex < splitPages.length) ? `Page ${{rightIndex + 1}}` : '';

    const totalPages = splitPages.length;
    if (isSinglePageOnMobile) {{
      footerProgressInfo.textContent = `Page ${{leftIndex + 1}} of ${{totalPages}}`;
    }} else {{
      footerProgressInfo.textContent = `Page ${{leftIndex + 1}}–${{Math.min(rightIndex + 1, totalPages)}} of ${{totalPages}}`;
    }}

    const viewedPage = isSinglePageOnMobile ? (leftIndex + 1) : Math.min(rightIndex + 1, totalPages);
    const progressPct = Math.round((viewedPage / Math.max(1, totalPages)) * 100);
    progressFill.style.width = `${{progressPct}}%`;

    syncUrlHash();

    // Swish animation & sound effect
    if (direction) {{
      pageLeft.classList.remove('swish-next', 'swish-prev');
      pageRight.classList.remove('swish-next', 'swish-prev');
      void pageLeft.offsetWidth;
      const animClass = direction === 'next' ? 'swish-next' : 'swish-prev';
      pageLeft.classList.add(animClass);
      if (!isSinglePageOnMobile) pageRight.classList.add(animClass);
      playPaperSound();
    }}
  }}

  function nextPage() {{
    const st = currentStory();
    const ch = currentChapter();
    if (st && st.is_interactive) {{
      if (currentConfig.layout === 'spread') {{
        if (currentPagePair < totalPagePairs - 1) {{
          currentPagePair++;
          renderCurrentSpread('next');
          saveState();
        }} else {{
          if (ch && ch.choices && ch.choices.length > 0) {{
            showToast('Please make a choice below to proceed.');
          }} else if (ch && ch.is_ending) {{
            showToast('Ending reached. Select Restart or Backtrack.');
          }}
        }}
      }} else {{
        if (ch && ch.choices && ch.choices.length > 0) {{
          showToast('Please make a choice below to proceed.');
        }}
      }}
      return;
    }}

    if (currentConfig.layout === 'spread') {{
      if (currentPagePair < totalPagePairs - 1) {{
        currentPagePair++;
        renderCurrentSpread('next');
        saveState();
      }} else {{
        if (currentChapterIndex < currentStory().chapters.length - 1) {{
          loadChapter(currentChapterIndex + 1, false, 'next');
        }}
      }}
    }} else {{
      if (currentChapterIndex < currentStory().chapters.length - 1) {{
        scrollToChapter(currentChapterIndex + 1, true);
      }}
    }}
  }}

  function prevPage() {{
    const st = currentStory();
    if (st && st.is_interactive) {{
      if (currentConfig.layout === 'spread') {{
        if (currentPagePair > 0) {{
          currentPagePair--;
          renderCurrentSpread('prev');
          saveState();
        }} else {{
          handleBacktrack();
        }}
      }} else {{
        handleBacktrack();
      }}
      return;
    }}

    if (currentConfig.layout === 'spread') {{
      if (currentPagePair > 0) {{
        currentPagePair--;
        renderCurrentSpread('prev');
        saveState();
      }} else {{
        if (currentChapterIndex > 0) {{
          loadChapter(currentChapterIndex - 1, true, 'prev');
        }}
      }}
    }} else {{
      if (currentChapterIndex > 0) {{
        scrollToChapter(currentChapterIndex - 1, true);
      }}
    }}
  }}

  // SAVE PROGRESS & CONFIG TO SERVER & LOCAL STORAGE
  let saveTimer = null;
  function saveState() {{
    const state = {{
      active_story: currentStory().id,
      active_chapter: currentChapter().filename,
      theme: currentConfig.theme,
      font_size: currentConfig.font_size,
      layout: currentConfig.layout,
      page_index: currentPagePair,
      interactive_progress: interactiveProgress
    }};

    try {{
      localStorage.setItem('storycrafter_reader_config', JSON.stringify(state));
    }} catch (e) {{}}

    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {{
      fetch('/api/config', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(state)
      }}).catch(() => {{}});
    }}, 400);

    syncUrlHash();
  }}

  // ATTACH EVENT LISTENERS
  selectStory.onchange = (e) => {{
    currentStoryIndex = parseInt(e.target.value, 10);
    const st = currentStory();
    let initialChapterIdx = 0;
    if (st && st.is_interactive) {{
      const prog = getStoryProgress(st.id);
      if (prog && prog.current_chapter) {{
        const found = st.chapters.findIndex(c => c.filename === prog.current_chapter);
        if (found !== -1) initialChapterIdx = found;
      }}
    }}
    currentChapterIndex = initialChapterIdx;
    updateStoryView();
    if (currentConfig.layout === 'scroll') {{
      renderInfiniteScroll(initialChapterIdx);
      if (bookSingle) bookSingle.scrollTop = 0;
    }} else {{
      loadChapter(initialChapterIdx);
    }}
  }};

  btnToggleToc.onclick = () => tocDrawer.classList.toggle('open');
  btnCloseToc.onclick = () => tocDrawer.classList.remove('open');

  selectTheme.onchange = (e) => {{
    currentConfig.theme = e.target.value;
    applyConfig();
    saveState();
  }};

  btnLayout.onclick = () => {{
    currentConfig.layout = (currentConfig.layout === 'spread') ? 'scroll' : 'spread';
    try {{
      localStorage.setItem('storycrafter_layout_override', currentConfig.layout);
    }} catch (e) {{}}
    updateLayoutDisplay();
    if (currentConfig.layout === 'spread') {{
      loadChapter(currentChapterIndex, false, null, 0);
    }} else {{
      renderInfiniteScroll(currentChapterIndex);
    }}
    saveState();
  }};

  if (btnLayoutDrawer) {{
    btnLayoutDrawer.onclick = () => btnLayout.click();
  }}

  btnFontInc.onclick = () => {{
    if (currentConfig.font_size < 32) {{
      currentConfig.font_size += 2;
      applyConfig();
      if (currentConfig.layout === 'spread') {{
        const ch = currentChapter();
        if (ch && ch.html) splitPagesIntoSpreads(ch.html, ch.title);
      }}
      saveState();
    }}
  }};

  btnFontDec.onclick = () => {{
    if (currentConfig.font_size > 12) {{
      currentConfig.font_size -= 2;
      applyConfig();
      if (currentConfig.layout === 'spread') {{
        const ch = currentChapter();
        if (ch && ch.html) splitPagesIntoSpreads(ch.html, ch.title);
      }}
      saveState();
    }}
  }};

  btnPrevPage.onclick = prevPage;
  btnNextPage.onclick = nextPage;

  let scrollThrottleTimer = null;
  bookSingle.addEventListener('scroll', () => {{
    if (currentConfig.layout !== 'scroll') return;
    if (scrollThrottleTimer) return;
    scrollThrottleTimer = requestAnimationFrame(() => {{
      scrollThrottleTimer = null;
      updateScrollHeaderAndFooter();
    }});
  }}, {{ passive: true }});

  btnSound.onclick = () => {{
    soundEnabled = !soundEnabled;
    btnSound.textContent = soundEnabled ? '🔊 Sound' : '🔇 Mute';
  }};

  // FULLSCREEN TOGGLE
  function toggleFullscreen() {{
    if (!document.fullscreenElement) {{
      document.documentElement.requestFullscreen().catch(() => {{}});
    }} else {{
      if (document.exitFullscreen) {{
        document.exitFullscreen().catch(() => {{}});
      }}
    }}
  }}

  btnFullscreen.onclick = toggleFullscreen;
  document.addEventListener('fullscreenchange', () => {{
    btnFullscreen.innerHTML = document.fullscreenElement ? '<span>⛶</span> Exit' : '<span>⛶</span> Full';
  }});

  btnHelp.onclick = () => helpModal.classList.add('open');
  btnCloseModal.onclick = () => helpModal.classList.remove('open');
  helpModal.onclick = (e) => {{
    if (e.target === helpModal) helpModal.classList.remove('open');
  }};

  // ATTACH GALLERY & LIGHTBOX LISTENERS
  if (btnGallery) {{
    btnGallery.onclick = () => {{
      if (galleryModal.classList.contains('open')) {{
        closeGallery();
      }} else {{
        openGallery();
      }}
    }};
  }}
  if (btnCloseGallery) btnCloseGallery.onclick = closeGallery;
  if (galleryModal) {{
    galleryModal.onclick = (e) => {{
      if (e.target === galleryModal) closeGallery();
    }};
  }}

  if (gallerySearchInput) {{
    gallerySearchInput.oninput = () => {{
      currentSearchQuery = gallerySearchInput.value;
      btnClearSearch.style.display = currentSearchQuery ? 'block' : 'none';
      filterAndRenderAssets();
    }};
  }}
  if (btnClearSearch) {{
    btnClearSearch.onclick = () => {{
      gallerySearchInput.value = '';
      currentSearchQuery = '';
      btnClearSearch.style.display = 'none';
      filterAndRenderAssets();
      gallerySearchInput.focus();
    }};
  }}

  if (btnCloseLightbox) btnCloseLightbox.onclick = closeLightbox;
  if (btnLightboxPrev) btnLightboxPrev.onclick = (e) => {{ e.stopPropagation(); prevLightbox(); }};
  if (btnLightboxNext) btnLightboxNext.onclick = (e) => {{ e.stopPropagation(); nextLightbox(); }};
  if (lightboxModal) {{
    lightboxModal.onclick = (e) => {{
      if (e.target === lightboxModal || e.target.classList.contains('lightbox-stage') || e.target.classList.contains('lightbox-image-wrap')) {{
        closeLightbox();
      }}
    }};
  }}

  if (btnCopyMdTag) {{
    btnCopyMdTag.onclick = () => {{
      const asset = filteredAssets[currentLightboxIndex];
      if (!asset) return;
      const md = `![${{asset.filename}}](/api/gallery/asset/${{asset.rel_path}})`;
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(md).then(() => {{
          showToast('Copied markdown tag to clipboard!');
        }}).catch(() => {{
          prompt('Copy markdown tag:', md);
        }});
      }} else {{
        prompt('Copy markdown tag:', md);
      }}
    }};
  }}

  if (btnReloadGallery) {{
    btnReloadGallery.onclick = reloadGalleryData;
  }}

  // LIVE LIBRARY RELOAD
  async function reloadLibraryData() {{
    const reloadBtns = [btnReloadLibrary, btnReloadLibraryDrawer].filter(Boolean);
    reloadBtns.forEach(btn => {{
      btn.disabled = true;
      btn._origHtml = btn.innerHTML;
      btn.textContent = '...';
    }});
    try {{
      const res = await fetch('/api/reload?t=' + Date.now());
      if (!res.ok) {{
        throw new Error(`HTTP ${{res.status}}`);
      }}
      const freshData = await res.json();
      if (freshData && freshData.stories) {{
        const prevStoryId = currentStory() ? currentStory().id : null;
        const prevChapterFilename = currentChapter() ? currentChapter().filename : null;
        const prevPage = currentPagePair;

        stories = freshData.stories;
        if (freshData.gallery) {{
          galleryData = freshData.gallery;
          if (galleryModal && galleryModal.classList.contains('open')) {{
            renderGallery();
          }}
        }}
        populateStorySelect();

        // Restore active story by ID
        if (prevStoryId) {{
          const sIdx = stories.findIndex(s => s.id === prevStoryId);
          if (sIdx !== -1) {{
            currentStoryIndex = sIdx;
          }} else {{
            currentStoryIndex = Math.min(currentStoryIndex, Math.max(0, stories.length - 1));
          }}
        }}
        selectStory.value = currentStoryIndex;
        updateStoryView();

        // Restore active chapter by filename
        let targetChapterIndex = currentChapterIndex;
        if (prevChapterFilename && currentStory() && currentStory().chapters) {{
          const cIdx = currentStory().chapters.findIndex(c => c.filename === prevChapterFilename);
          if (cIdx !== -1) {{
            targetChapterIndex = cIdx;
          }} else {{
            targetChapterIndex = Math.min(currentChapterIndex, Math.max(0, currentStory().chapters.length - 1));
          }}
        }}

        if (currentConfig.layout === 'scroll') {{
          const prevScroll = bookSingle ? bookSingle.scrollTop : 0;
          renderInfiniteScroll(targetChapterIndex);
          if (bookSingle && prevScroll > 0) {{
            bookSingle.scrollTop = prevScroll;
          }}
          updateScrollHeaderAndFooter();
        }} else {{
          loadChapter(targetChapterIndex, false, null, prevPage);
        }}

        let totalChapters = 0;
        stories.forEach(s => {{ totalChapters += (s.chapters ? s.chapters.length : 0); }});
        showToast(`Reloaded: ${{stories.length}} stories, ${{totalChapters}} chapters`);
      }} else {{
        showToast('No stories found');
      }}
    }} catch (err) {{
      console.error('Failed to reload library:', err);
      showToast('Error reloading stories');
    }} finally {{
      reloadBtns.forEach(btn => {{
        btn.disabled = false;
        if (btn._origHtml) {{
          btn.innerHTML = btn._origHtml;
        }} else {{
          btn.innerHTML = '<span>↻</span> <span class="btn-text">Reload</span>';
        }}
      }});
    }}
  }}

  if (btnReloadLibrary) {{
    btnReloadLibrary.onclick = reloadLibraryData;
  }}
  if (btnReloadLibraryDrawer) {{
    btnReloadLibraryDrawer.onclick = reloadLibraryData;
  }}

  // TOUCH & SWIPE NAVIGATION FOR MOBILE & TABLETS
  let touchStartX = 0;
  let touchStartY = 0;
  let touchStartTime = 0;

  const stage = document.getElementById('bookStage');
  stage.addEventListener('touchstart', (e) => {{
    if (currentConfig.layout !== 'spread') return;
    if (e.touches.length === 1) {{
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      touchStartTime = Date.now();
    }}
  }}, {{ passive: true }});

  stage.addEventListener('touchend', (e) => {{
    if (currentConfig.layout !== 'spread') return;
    if (e.changedTouches.length === 1) {{
      const deltaX = e.changedTouches[0].clientX - touchStartX;
      const deltaY = e.changedTouches[0].clientY - touchStartY;
      const elapsedTime = Date.now() - touchStartTime;

      if (Math.abs(deltaX) > 45 && Math.abs(deltaX) > Math.abs(deltaY) * 1.4 && elapsedTime < 600) {{
        if (deltaX < 0) {{
          nextPage();
        }} else {{
          prevPage();
        }}
      }}
    }}
  }}, {{ passive: true }});

  // KEYBOARD NAVIGATION
  window.addEventListener('keydown', (e) => {{
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {{
      if (e.key === 'Escape') {{
        if (e.target === gallerySearchInput) {{
          gallerySearchInput.blur();
        }}
      }}
      return;
    }}

    // Lightbox navigation takes precedence if open
    if (lightboxModal && lightboxModal.classList.contains('open')) {{
      if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D' || e.key === ' ') {{
        e.preventDefault();
        nextLightbox();
        return;
      }} else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {{
        e.preventDefault();
        prevLightbox();
        return;
      }} else if (e.key === 'Escape') {{
        e.preventDefault();
        closeLightbox();
        return;
      }}
    }}

    // Gallery close takes precedence if open
    if (galleryModal && galleryModal.classList.contains('open')) {{
      if (e.key === 'Escape') {{
        e.preventDefault();
        closeGallery();
        return;
      }} else if (e.key === 'g' || e.key === 'G') {{
        e.preventDefault();
        closeGallery();
        return;
      }}
    }}

    if (e.key === 'g' || e.key === 'G') {{
      e.preventDefault();
      openGallery();
      return;
    }}

    if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {{
      e.preventDefault();
      if (currentConfig.layout === 'scroll') {{
        if (currentChapterIndex < currentStory().chapters.length - 1) {{
          scrollToChapter(currentChapterIndex + 1, true);
        }}
      }} else {{
        nextPage();
      }}
    }} else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {{
      e.preventDefault();
      if (currentConfig.layout === 'scroll') {{
        if (currentChapterIndex > 0) {{
          scrollToChapter(currentChapterIndex - 1, true);
        }}
      }} else {{
        prevPage();
      }}
    }} else if (e.key === ' ') {{
      e.preventDefault();
      if (currentConfig.layout === 'scroll') {{
        bookSingle.scrollBy({{ top: Math.round(bookSingle.clientHeight * 0.8), behavior: 'smooth' }});
      }} else {{
        nextPage();
      }}
    }} else if (e.key === 'm' || e.key === 'M') {{
      tocDrawer.classList.toggle('open');
    }} else if (e.key === 's' || e.key === 'S') {{
      btnSound.click();
    }} else if (e.key === 't' || e.key === 'T') {{
      const themes = ['parchment', 'sepia', 'midnight', 'paper'];
      const nextIdx = (themes.indexOf(currentConfig.theme) + 1) % themes.length;
      currentConfig.theme = themes[nextIdx];
      applyConfig();
      saveState();
    }} else if (e.key === 'l' || e.key === 'L') {{
      btnLayout.click();
    }} else if (e.key === 'f' || e.key === 'F') {{
      toggleFullscreen();
    }} else if (e.key === 'r' || e.key === 'R') {{
      reloadLibraryData();
    }} else if (e.key === '+' || e.key === '=') {{
      btnFontInc.click();
    }} else if (e.key === '-' || e.key === '_') {{
      btnFontDec.click();
    }} else if (e.key === '?' || (e.shiftKey && e.key === '/')) {{
      btnHelp.click();
    }} else if (e.key === 'Escape') {{
      tocDrawer.classList.remove('open');
      helpModal.classList.remove('open');
      if (galleryModal) galleryModal.classList.remove('open');
      closeLightbox();
    }}
  }});

  // POPSTATE & HASHCHANGE LISTENER
  window.addEventListener('hashchange', () => {{
    const hashParams = parseUrlHash();
    if (!hashParams) return;
    if (hashParams.story) {{
      const sIdx = stories.findIndex(s => s.id === hashParams.story);
      if (sIdx !== -1 && sIdx !== currentStoryIndex) {{
        currentStoryIndex = sIdx;
        selectStory.value = sIdx;
        updateStoryView();
      }}
    }}
    if (hashParams.chapter) {{
      const cIdx = currentStory().chapters.findIndex(c => c.filename === hashParams.chapter);
      if (cIdx !== -1 && (cIdx !== currentChapterIndex || hashParams.page !== currentPagePair)) {{
        loadChapter(cIdx, false, null, hashParams.page);
      }}
    }}
  }});

  // DYNAMIC RESIZE LISTENER
  let resizeTimer = null;
  window.addEventListener('resize', () => {{
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {{
      const ch = currentChapter();
      if (ch && ch.html && currentConfig.layout === 'spread') {{
        const prevRatio = currentPagePair / Math.max(1, totalPagePairs);
        splitPagesIntoSpreads(ch.html, ch.title);
        currentPagePair = Math.min(totalPagePairs - 1, Math.round(prevRatio * totalPagePairs));
        renderCurrentSpread();
      }}
    }}, 100);
  }});

  // INITIALIZE ON DOM READY
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', init);
  }} else {{
    init();
  }}
</script>
</body>
</html>
"""


class StoryReaderWebHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler providing REST API and serving Web Reader assets."""

    server_version = "StoryReader/2.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            library = self.server.reload_library()
            gallery = self.server.get_gallery()
            config = load_config()
            lan_url = getattr(self.server, "lan_url", None)
            html_content = generate_web_ui(library, config, gallery=gallery, lan_url=lan_url)
            self.wfile.write(html_content.encode("utf-8"))

        elif path == "/api/library":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            library = self.server.get_library()
            self.wfile.write(json.dumps({"stories": library}).encode("utf-8"))

        elif path == "/api/reload":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            library = self.server.reload_library()
            gallery = self.server.get_gallery()
            self.wfile.write(json.dumps({"status": "ok", "stories": library, "gallery": gallery}).encode("utf-8"))

        elif path == "/api/gallery":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            self.end_headers()
            gallery = self.server.reload_gallery()
            self.wfile.write(json.dumps(gallery).encode("utf-8"))

        elif path.startswith("/api/gallery/asset/"):
            import mimetypes
            import shutil
            import urllib.parse
            rel_req = urllib.parse.unquote(path[len("/api/gallery/asset/"):])
            assets_dir = (BASE_DIR / "assets").resolve()
            target_file = (assets_dir / rel_req).resolve()
            if target_file.is_file() and (assets_dir == target_file.parent or assets_dir in target_file.parents):
                mime_type, _ = mimetypes.guess_type(str(target_file))
                if not mime_type:
                    mime_type = "image/png" if target_file.suffix.lower() == ".png" else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(target_file.stat().st_size))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(target_file, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_error(404, f"Gallery Asset Not Found: {path}")

        elif path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            config = load_config()
            self.wfile.write(json.dumps(config).encode("utf-8"))

        elif path == "/manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json; charset=utf-8")
            self.end_headers()
            manifest = {
                "name": "StoryCrafter Web Reader",
                "short_name": "StoryReader",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#e8dec8",
                "theme_color": "#8b3a2b",
                "icons": [
                    {
                        "src": "/app_icon.svg",
                        "sizes": "any",
                        "type": "image/svg+xml"
                    },
                    {
                        "src": "/app_icon.ico",
                        "sizes": "64x64 32x32 24x24 16x16",
                        "type": "image/x-icon"
                    }
                ]
            }
            self.wfile.write(json.dumps(manifest, indent=2).encode("utf-8"))

        elif path == "/app_icon.svg":
            if ICON_SVG_FILE.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.end_headers()
                self.wfile.write(ICON_SVG_FILE.read_bytes())
            else:
                self.send_error(404, "Icon not found")

        elif path in ("/app_icon.ico", "/favicon.ico"):
            if ICON_ICO_FILE.exists():
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.end_headers()
                self.wfile.write(ICON_ICO_FILE.read_bytes())
            else:
                self.send_error(404, "Icon not found")

        elif path.startswith("/api/assets/") or "/assets/" in path:
            import mimetypes
            import shutil
            import urllib.parse
            clean_path = urllib.parse.unquote(path)
            if clean_path.startswith("/api/assets/"):
                sub_path = clean_path[len("/api/assets/"):]
            elif clean_path.startswith("/assets/"):
                sub_path = clean_path[len("/assets/"):]
            else:
                sub_path = clean_path.lstrip("/")

            parts = [p for p in sub_path.split("/") if p and p != "assets"]
            target_file = None
            assets_dir = (BASE_DIR / "assets").resolve()

            # First, check if sub_path resolves inside root \assets
            cand_global = (assets_dir / "/".join(parts)).resolve()
            if cand_global.exists() and cand_global.is_file() and (assets_dir == cand_global.parent or assets_dir in cand_global.parents):
                target_file = cand_global

            # Next, if 2 or more parts: check story-level assets
            if not target_file and len(parts) >= 2:
                story_name = parts[0]
                filename = parts[-1]
                cand = (BASE_DIR / story_name / "assets" / filename).resolve()
                if cand.exists() and cand.is_file():
                    target_file = cand

            # Next, if 1 part: search root \assets first, then all story assets
            if not target_file and len(parts) == 1:
                filename = parts[0]
                cand_root = (assets_dir / filename).resolve()
                if cand_root.exists() and cand_root.is_file():
                    target_file = cand_root
                else:
                    for s_dir in BASE_DIR.iterdir():
                        if s_dir.is_dir():
                            cand = (s_dir / "assets" / filename).resolve()
                            if cand.exists() and cand.is_file():
                                target_file = cand
                                break

            if target_file and BASE_DIR in target_file.parents and target_file.is_file():
                mime_type, _ = mimetypes.guess_type(str(target_file))
                if not mime_type:
                    mime_type = "image/png" if target_file.suffix.lower() == ".png" else "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(target_file.stat().st_size))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                with open(target_file, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            else:
                self.send_error(404, f"Asset Not Found: {path}")

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                post_body = self.rfile.read(content_len).decode("utf-8")
                updates = json.loads(post_body)
                current = load_config()
                current.update(updates)
                save_config(current)

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "config": current}).encode("utf-8"))
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        # Suppress routine request logging to keep console clean, but print errors
        if args and str(args[1]) in ("400", "404", "500"):
            print(f"[HTTP {args[1]}] {args[0]}")


class StoryReaderServer(ThreadingHTTPServer):
    """Threaded HTTP server managing library state and cache, supporting dual-stack IPv4/IPv6."""

    def __init__(self, server_address, RequestHandlerClass):
        host = server_address[0]
        if ":" in str(host):
            self.address_family = socket.AF_INET6
        else:
            self.address_family = socket.AF_INET
        try:
            super().__init__(server_address, RequestHandlerClass)
        except OSError as e:
            # If IPv6 (::) binding fails (e.g. disabled on machine), fallback to IPv4 (0.0.0.0)
            if self.address_family == socket.AF_INET6 and host == "::":
                print(f"[WARN] IPv6 (::) binding failed ({e}), falling back to IPv4 (0.0.0.0)...")
                self.address_family = socket.AF_INET
                super().__init__(("0.0.0.0", server_address[1]), RequestHandlerClass)
            else:
                raise
        self._library = None
        self._gallery = None
        self._lock = threading.Lock()

    def server_bind(self):
        if self.address_family == socket.AF_INET6:
            try:
                # Enable dual-stack IPv4/IPv6 on supported systems
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            except (AttributeError, OSError):
                pass
        super().server_bind()

    def get_library(self):
        with self._lock:
            if self._library is None:
                self._library = scan_full_library()
            return self._library

    def reload_library(self):
        with self._lock:
            self._library = scan_full_library()
            self._gallery = scan_assets_gallery()
            return self._library

    def get_gallery(self):
        with self._lock:
            if self._gallery is None:
                self._gallery = scan_assets_gallery()
            return self._gallery

    def reload_gallery(self):
        with self._lock:
            self._gallery = scan_assets_gallery()
            return self._gallery


def run_server(host="0.0.0.0", port=8080, open_browser=True, lan_mode=True):
    """Run the StoryReader web server in LAN mode by default."""
    if not lan_mode and host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    elif lan_mode and host in ("127.0.0.1", "localhost"):
        host = "0.0.0.0"

    actual_port = find_available_port(host, port)
    server = StoryReaderServer((host, actual_port), StoryReaderWebHandler)
    lan_ip = get_lan_ip()

    local_url = f"http://127.0.0.1:{actual_port}/"
    lan_url = f"http://{lan_ip}:{actual_port}/"
    ipv6_url = f"http://[::1]:{actual_port}/"

    is_all_interfaces = host in ("::", "0.0.0.0") or lan_mode
    server.lan_url = lan_url if is_all_interfaces else None
    server.local_url = local_url
    server.is_lan_mode = is_all_interfaces

    mode_label = "LAN Mode (All Interfaces)" if is_all_interfaces else "Local Only"
    print("=" * 62, flush=True)
    print(f"       StoryCrafter Sleek Python Web Reader [{mode_label}]", flush=True)
    print("=" * 62, flush=True)
    print(f"  Local Access:      {local_url}", flush=True)
    if is_all_interfaces:
        print(f"  Network/LAN:       {lan_url}  (Mobile & Tablet)", flush=True)
        if ":" in host:
            print(f"  IPv6 Loopback:     {ipv6_url}", flush=True)
    else:
        print(f"  Network access:    Disabled (run without --local to enable LAN mode)", flush=True)
    print("-" * 62, flush=True)
    print("  Controls & Hotkeys:", flush=True)
    print("    [Arrow Keys / Space / A / D] Turn Pages", flush=True)
    print("    [M] Table of Contents    [T] Cycle Themes", flush=True)
    print("    [S] Sound Toggle         [L] Spread / Scroll Layout", flush=True)
    print("    [F] Fullscreen           [R] Live Reload Library", flush=True)
    print("=" * 62, flush=True)
    print("  Press Ctrl+C to stop server.\n", flush=True)

    if open_browser:
        def _open():
            import time
            time.sleep(0.4)
            webbrowser.open(local_url)
        threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down StoryCrafter Web Reader server...")
        server.shutdown()
        server.server_close()
        print("[OK] Server stopped.")


def main():
    parser = argparse.ArgumentParser(description="StoryCrafter Sleek Python Web Reader")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to run server on (default: 8080)")
    parser.add_argument("--host", type=str, default=None, help="Host address to bind to (default: 0.0.0.0 [LAN mode])")
    parser.add_argument("--lan", dest="lan", action="store_true", default=True, help="Enable LAN mode (default: enabled)")
    parser.add_argument("--local", "--no-lan", dest="lan", action="store_false", help="Disable LAN mode and bind only to localhost (127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically")
    args = parser.parse_args()

    if args.host is not None:
        host = args.host
        lan_mode = args.lan if host not in ("127.0.0.1", "localhost") else False
    elif not args.lan:
        host = "127.0.0.1"
        lan_mode = False
    else:
        host = "0.0.0.0"
        lan_mode = True

    run_server(
        host=host,
        port=args.port,
        open_browser=not args.no_browser,
        lan_mode=lan_mode
    )


if __name__ == "__main__":
    main()
