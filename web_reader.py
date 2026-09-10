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


def format_markdown_to_html(md_text):
    """Convert chapter markdown into clean, styled book HTML with drop caps."""
    lines = md_text.splitlines()
    title = ""
    cleaned_lines = []

    for line in lines:
        if line.startswith("# ") and not title:
            title = line[2:].strip()
        else:
            cleaned_lines.append(line)

    body_md = "\n".join(cleaned_lines)

    if markdown:
        raw_html = markdown.markdown(body_md, extensions=['extra', 'smarty'])
    else:
        # Fallback converter
        paragraphs = [p.strip() for p in body_md.split("\n\n") if p.strip()]
        html_parts = []
        for p in paragraphs:
            if p.startswith("### "):
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

    return title, raw_html


def scan_full_library():
    """Scan workspace and pre-render all stories and chapters into complete JSON."""
    stories = []
    for item in BASE_DIR.iterdir():
        if item.is_dir() and not item.name.startswith((".", "_", "venv")):
            chapters_dir = item / "chapters"
            if chapters_dir.is_dir():
                files = sorted(chapters_dir.glob("*.md"))
                if files:
                    display_title = item.name.replace("_", " ").title()
                    chapter_list = []
                    for idx, f in enumerate(files, 1):
                        try:
                            text = f.read_text(encoding="utf-8")
                            title, raw_html = format_markdown_to_html(text)
                            word_count = len(re.findall(r"\b\w+\b", text))
                            reading_minutes = max(1, round(word_count / 220))

                            chapter_list.append({
                                "filename": f.name,
                                "title": title or f.stem.replace("_", " ").title(),
                                "index": idx,
                                "word_count": word_count,
                                "reading_time": f"{reading_minutes} min",
                                "html": raw_html
                            })
                        except Exception as e:
                            print(f"[WARN] Failed to parse chapter {f}: {e}")

                    stories.append({
                        "id": item.name,
                        "title": display_title,
                        "chapters": chapter_list,
                        "total_chapters": len(chapter_list)
                    })

    # Sort so 'the_mockingbirds_ledger' is primary if present
    stories.sort(key=lambda s: 0 if s["id"] == "the_mockingbirds_ledger" else 1)
    return stories


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
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    return start_port


def generate_web_ui(library, config):
    """Generate the complete web reader HTML with embedded library and client scripts."""
    embedded_json = json.dumps({
        "stories": library,
        "config": config
    })

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
  }}

  .app-bar-left, .app-bar-right, .app-bar-center {{
    display: flex;
    align-items: center;
    gap: 8px;
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

  /* SINGLE COLUMN MODE */
  .book-single {{
    width: 100%;
    max-width: min(920px, calc(100vw - 80px));
    height: 100%;
    max-height: 100%;
    background-color: var(--bg-page);
    border-radius: 8px;
    box-shadow: var(--shadow-page);
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    padding: 40px 60px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }}

  .book-single .page-content {{
    overflow-y: visible;
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
      padding: 20px 24px 16px 24px;
    }}
    .book-single {{
      padding: 24px 20px;
      max-width: 100%;
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

      <button class="btn" id="btnLayout" title="Toggle Layout Spread / Scroll (L)">
        <span id="layoutIcon">📖 Spread</span>
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
          <button class="btn" id="btnReloadLibrary" title="Rescan stories & chapters (R)" style="padding: 2px 8px; font-size: 11px;">
            ↻ Reload
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
      <div class="book-single" id="bookSingle" style="display: none;">
        <div class="page-running-header" id="headerSingle">Chapter Title</div>
        <div class="page-content" id="contentSingle"></div>
        <div class="page-running-footer">
          <span id="singleWordCount">Word count</span>
          <span id="singleReadTime">Reading time</span>
        </div>
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
      <div class="shortcut-row"><span>Next Page / Chapter</span><span class="shortcut-key">Right / Space / D / Swipe Left</span></div>
      <div class="shortcut-row"><span>Previous Page / Chapter</span><span class="shortcut-key">Left / A / Swipe Right</span></div>
      <div class="shortcut-row"><span>Table of Contents</span><span class="shortcut-key">M</span></div>
      <div class="shortcut-row"><span>Cycle Theme</span><span class="shortcut-key">T</span></div>
      <div class="shortcut-row"><span>Toggle Sound Effect</span><span class="shortcut-key">S</span></div>
      <div class="shortcut-row"><span>Toggle Spread / Scroll</span><span class="shortcut-key">L</span></div>
      <div class="shortcut-row"><span>Font Size Up / Down</span><span class="shortcut-key">+ / -</span></div>
      <div class="shortcut-row"><span>Toggle Fullscreen</span><span class="shortcut-key">F</span></div>
      <div class="shortcut-row"><span>Reload Library</span><span class="shortcut-key">R</span></div>
      <div class="shortcut-row"><span>Close Dialogs</span><span class="shortcut-key">Esc</span></div>
      <div style="text-align: right; margin-top: 16px;">
        <button class="btn active" id="btnCloseModal">Got it</button>
      </div>
    </div>
  </div>

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
      page: params.get('page') !== null ? parseInt(params.get('page'), 10) : null
    }};
  }}

  function syncUrlHash() {{
    const st = currentStory();
    const ch = currentChapter();
    if (!st || !ch) return;
    const hash = `#story=${{encodeURIComponent(st.id)}}&chapter=${{encodeURIComponent(ch.filename)}}&page=${{currentPagePair}}`;
    if (window.location.hash !== hash) {{
      history.replaceState(null, '', hash);
    }}
  }}

  // INITIALIZATION
  function init() {{
    if (!stories.length) {{
      console.warn("No stories loaded.");
      return;
    }}

    // Check URL Hash first, then config
    const hashParams = parseUrlHash();
    const activeStoryId = (hashParams && hashParams.story) || currentConfig.active_story;
    const activeChapterFile = (hashParams && hashParams.chapter) || currentConfig.active_chapter;
    const activePage = (hashParams && hashParams.page !== null) ? hashParams.page : currentConfig.page_index;

    if (activeStoryId) {{
      const sIdx = stories.findIndex(s => s.id === activeStoryId);
      if (sIdx !== -1) currentStoryIndex = sIdx;
    }}

    populateStorySelect();
    selectStory.value = currentStoryIndex;

    if (activeChapterFile) {{
      const cIdx = currentStory().chapters.findIndex(c => c.filename === activeChapterFile);
      if (cIdx !== -1) currentChapterIndex = cIdx;
    }}

    if (activePage !== undefined && activePage !== null) {{
      currentPagePair = Math.max(0, activePage);
    }}

    applyConfig();
    updateStoryView();
    loadChapter(currentChapterIndex, false, null, currentPagePair);

    // Check responsive layout mode
    checkViewport();

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
    document.querySelectorAll('.page-content').forEach(el => {{
      el.style.fontSize = currentConfig.font_size + 'px';
    }});
    updateLayoutDisplay();
  }}

  function updateLayoutDisplay() {{
    if (currentConfig.layout === 'spread') {{
      bookSpread.style.display = 'grid';
      bookSingle.style.display = 'none';
      layoutIcon.textContent = '📖 Spread';
    }} else {{
      bookSpread.style.display = 'none';
      bookSingle.style.display = 'flex';
      layoutIcon.textContent = '📜 Scroll';
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

  function updateStoryView() {{
    currentStoryTitle.textContent = currentStory().title;
    renderToc();
  }}

  function renderToc() {{
    tocList.innerHTML = '';
    const chs = currentStory().chapters;
    chs.forEach((ch, idx) => {{
      const li = document.createElement('li');
      li.className = 'toc-item' + (idx === currentChapterIndex ? ' active' : '');
      li.innerHTML = `
        <span class="ch-num">Chapter ${{ch.index}}</span>
        <span class="ch-name">${{ch.title}}</span>
        <span class="ch-meta">${{ch.word_count}} words · ${{ch.reading_time}}</span>
      `;
      li.onclick = () => {{
        loadChapter(idx, false, 'next');
        tocDrawer.classList.remove('open');
      }};
      tocList.appendChild(li);
    }});
  }}

  function loadChapter(idx, startAtEnd = false, direction = null, specificPage = null) {{
    currentChapterIndex = idx;
    const ch = currentStory().chapters[idx];
    if (!ch) return;

    if (specificPage !== null && specificPage !== undefined) {{
      currentPagePair = specificPage;
    }} else {{
      currentPagePair = startAtEnd ? 999999 : 0;
    }}

    renderToc();
    footerChapterInfo.textContent = `${{currentStory().title}} — Chapter ${{idx + 1}} of ${{currentStory().chapters.length}}`;

    renderChapterContent(ch, direction);
    saveState();
  }}

  function renderChapterContent(ch, direction = null) {{
    const rawHtml = ch.html;
    const title = ch.title;

    // Single Scroll View
    headerSingle.textContent = `${{currentStory().title}} — ${{title}}`;
    contentSingle.innerHTML = `
      <div class="chapter-title-block">
        <div class="chapter-eyebrow">Chapter ${{currentChapterIndex + 1}}</div>
        <h1 class="chapter-main-title">${{title}}</h1>
        <div class="chapter-ornament">❦  ❧</div>
      </div>
      <div class="has-drop-cap">${{rawHtml}}</div>
    `;
    document.getElementById('singleWordCount').textContent = `${{ch.word_count}} words`;
    document.getElementById('singleReadTime').textContent = `${{ch.reading_time}} read`;

    if (direction && currentConfig.layout === 'single') {{
      contentSingle.classList.remove('swish-next', 'swish-prev');
      void contentSingle.offsetWidth;
      contentSingle.classList.add(direction === 'next' ? 'swish-next' : 'swish-prev');
      playPaperSound();
    }}

    // Split into pages for Spread View
    splitPagesIntoSpreads(rawHtml, title, direction);
  }}

  function splitPagesIntoSpreads(rawHtml, title, direction = null) {{
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
        <div class="chapter-eyebrow">Chapter ${{currentChapterIndex + 1}}</div>
        <h1 class="chapter-main-title">${{title}}</h1>
        <div class="chapter-ornament">❦  ❧</div>
      </div>
    `;

    tester.innerHTML = titleBlockHtml;
    currentPageNodes.push(titleBlockHtml);
    let isFirstPage = true;

    for (let i = 0; i < nodes.length; i++) {{
      const nodeHtml = nodes[i].outerHTML;
      tester.innerHTML += nodeHtml;

      if (tester.scrollHeight > targetHeight + 6) {{
        if (currentPageNodes.length > (isFirstPage ? 1 : 0)) {{
          splitPages.push(currentPageNodes.join(''));
          currentPageNodes = [nodeHtml];
          isFirstPage = false;
          tester.innerHTML = nodeHtml;

          if (tester.scrollHeight > targetHeight + 6) {{
            splitPages.push(currentPageNodes.join(''));
            currentPageNodes = [];
            tester.innerHTML = '';
          }}
        }} else {{
          currentPageNodes.push(nodeHtml);
          splitPages.push(currentPageNodes.join(''));
          currentPageNodes = [];
          isFirstPage = false;
          tester.innerHTML = '';
        }}
      }} else {{
        currentPageNodes.push(nodeHtml);
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

    contentLeft.innerHTML = splitPages[leftIndex] || '<p style="color:var(--text-muted); text-align:center; padding-top:40px;"><em>End of chapter.</em></p>';
    contentRight.innerHTML = isSinglePageOnMobile ? '' : (splitPages[rightIndex] || '');

    if (currentPagePair === 0) {{
      pageLeft.classList.add('has-drop-cap');
    }} else {{
      pageLeft.classList.remove('has-drop-cap');
    }}
    pageRight.classList.remove('has-drop-cap');

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
        loadChapter(currentChapterIndex + 1, false, 'next');
        bookSingle.scrollTop = 0;
      }}
    }}
  }}

  function prevPage() {{
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
        loadChapter(currentChapterIndex - 1, true, 'prev');
        bookSingle.scrollTop = 0;
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
      page_index: currentPagePair
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
    currentChapterIndex = 0;
    updateStoryView();
    loadChapter(0);
  }};

  btnToggleToc.onclick = () => tocDrawer.classList.toggle('open');
  btnCloseToc.onclick = () => tocDrawer.classList.remove('open');

  selectTheme.onchange = (e) => {{
    currentConfig.theme = e.target.value;
    applyConfig();
    saveState();
  }};

  btnLayout.onclick = () => {{
    currentConfig.layout = currentConfig.layout === 'spread' ? 'single' : 'spread';
    updateLayoutDisplay();
    if (currentConfig.layout === 'spread') {{
      const ch = currentChapter();
      if (ch && ch.html) {{
        splitPagesIntoSpreads(ch.html, ch.title);
      }}
    }}
    saveState();
  }};

  btnFontInc.onclick = () => {{
    if (currentConfig.font_size < 32) {{
      currentConfig.font_size += 2;
      applyConfig();
      if (currentChapter().html) {{
        splitPagesIntoSpreads(currentChapter().html, currentChapter().title);
      }}
      saveState();
    }}
  }};

  btnFontDec.onclick = () => {{
    if (currentConfig.font_size > 12) {{
      currentConfig.font_size -= 2;
      applyConfig();
      if (currentChapter().html) {{
        splitPagesIntoSpreads(currentChapter().html, currentChapter().title);
      }}
      saveState();
    }}
  }};

  btnPrevPage.onclick = prevPage;
  btnNextPage.onclick = nextPage;

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

  // LIVE LIBRARY RELOAD
  async function reloadLibraryData() {{
    if (!btnReloadLibrary) return;
    btnReloadLibrary.disabled = true;
    btnReloadLibrary.textContent = '...';
    try {{
      const res = await fetch('/api/reload');
      const freshData = await res.json();
      if (freshData && freshData.stories) {{
        stories = freshData.stories;
        populateStorySelect();
        selectStory.value = currentStoryIndex;
        updateStoryView();
        loadChapter(currentChapterIndex);
      }}
    }} catch (err) {{
      console.error('Failed to reload library:', err);
    }} finally {{
      btnReloadLibrary.disabled = false;
      btnReloadLibrary.textContent = '↻ Reload';
    }}
  }}

  if (btnReloadLibrary) {{
    btnReloadLibrary.onclick = reloadLibraryData;
  }}

  // TOUCH & SWIPE NAVIGATION FOR MOBILE & TABLETS
  let touchStartX = 0;
  let touchStartY = 0;
  let touchStartTime = 0;

  const stage = document.getElementById('bookStage');
  stage.addEventListener('touchstart', (e) => {{
    if (e.touches.length === 1) {{
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
      touchStartTime = Date.now();
    }}
  }}, {{ passive: true }});

  stage.addEventListener('touchend', (e) => {{
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
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;

    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'd' || e.key === 'D') {{
      e.preventDefault();
      nextPage();
    }} else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {{
      e.preventDefault();
      prevPage();
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
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            library = self.server.get_library()
            config = load_config()
            html_content = generate_web_ui(library, config)
            self.wfile.write(html_content.encode("utf-8"))

        elif path == "/api/library":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            library = self.server.get_library()
            self.wfile.write(json.dumps({"stories": library}).encode("utf-8"))

        elif path == "/api/reload":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            library = self.server.reload_library()
            self.wfile.write(json.dumps({"status": "ok", "stories": library}).encode("utf-8"))

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
    """Threaded HTTP server managing library state and cache."""

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self._library = None
        self._lock = threading.Lock()

    def get_library(self):
        with self._lock:
            if self._library is None:
                self._library = scan_full_library()
            return self._library

    def reload_library(self):
        with self._lock:
            self._library = scan_full_library()
            return self._library


def run_server(host="127.0.0.1", port=8080, open_browser=True, lan_mode=False):
    """Run the StoryReader web server."""
    if lan_mode or host == "0.0.0.0":
        host = "0.0.0.0"

    actual_port = find_available_port(host, port)
    server = StoryReaderServer((host, actual_port), StoryReaderWebHandler)
    lan_ip = get_lan_ip()

    local_url = f"http://localhost:{actual_port}/"
    lan_url = f"http://{lan_ip}:{actual_port}/"

    print("=" * 62, flush=True)
    print("           StoryCrafter Sleek Python Web Reader           ", flush=True)
    print("=" * 62, flush=True)
    print(f"  Local Access:      {local_url}", flush=True)
    if host == "0.0.0.0" or lan_mode:
        print(f"  Network/LAN:       {lan_url}  (Mobile & Tablet)", flush=True)
    else:
        print(f"  Network access:    Run with --lan to enable mobile reading", flush=True)
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
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 to allow mobile/tablet access across LAN")
    parser.add_argument("--no-browser", action="store_true", help="Do not open web browser automatically")
    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        lan_mode=args.lan
    )


if __name__ == "__main__":
    main()
