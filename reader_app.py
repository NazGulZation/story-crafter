#!/usr/bin/env python3
"""
StoryCrafter Sleek Desktop Book Reader
A book-style desktop reader for StoryCrafter narratives.
Provides two-page book spread, continuous reading, customizable typography,
parchment/sepia/dark themes, and automatic reading progress tracking.
"""

import os
import sys
import json
import re
import html
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
from pathlib import Path

# Optional markdown library
try:
    import markdown
except ImportError:
    markdown = None

# Optional pywebview library
try:
    import webview
except ImportError:
    webview = None

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / ".reader_config.json"


def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
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
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def format_markdown_to_html(md_text, story_id=""):
    """Convert chapter markdown into clean, styled book HTML with drop caps and web-safe image paths."""
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

        if resolved_story:
            web_url = f"/api/assets/{resolved_story}/{filename}"
        else:
            web_url = f"/api/assets/{filename}"

        caption_html = f'<figcaption class="illustration-caption">{html.escape(alt)}</figcaption>' if alt else ''
        return f'\n\n<figure class="book-figure"><img src="{web_url}" alt="{html.escape(alt)}" loading="lazy">{caption_html}</figure>\n\n'

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
                        text = f.read_text(encoding="utf-8")
                        title, raw_html = format_markdown_to_html(text, story_id=item.name)
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

                    stories.append({
                        "id": item.name,
                        "title": display_title,
                        "chapters": chapter_list,
                        "total_chapters": len(chapter_list)
                    })

    # Sort so 'the_mockingbirds_ledger' is primary if present
    stories.sort(key=lambda s: 0 if s["id"] == "the_mockingbirds_ledger" else 1)
    return stories


def get_html_ui():
    """Generate the complete standalone reader HTML with pre-embedded library data."""
    config = load_config()
    library = scan_full_library()

    # Pre-embed complete library and config directly into JavaScript
    embedded_json = json.dumps({
        "stories": library,
        "config": config
    })

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StoryCrafter Book Reader</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 512 512'%3E%3Crect x='24' y='24' width='464' height='464' rx='108' ry='108' fill='%23141820' stroke='%23d4af37' stroke-width='16'/%3E%3Cpath d='M256 350C210 338 135 320 98 334C94 250 94 220 96 172C140 162 216 178 256 195Z' fill='%23fdfbf5'/%3E%3Cpath d='M256 350C302 338 377 320 414 334C418 250 418 220 416 172C372 162 296 178 256 195Z' fill='%23fdfbf5'/%3E%3Cpath d='M256 345Q296 230 354 100Q320 180 256 345Z' fill='%23d4af37'/%3E%3C/svg%3E">
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
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: background-color 0.3s ease, color 0.3s ease;
  }}

  /* TOP APP BAR */
  header.app-bar {{
    height: 52px;
    background-color: var(--bg-book);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    font-family: var(--font-sans);
    z-index: 50;
    user-select: none;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  }}

  .app-bar-left, .app-bar-right, .app-bar-center {{
    display: flex;
    align-items: center;
    gap: 10px;
  }}

  .btn {{
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: all 0.15s ease;
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
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    font-family: var(--font-sans);
    cursor: pointer;
    outline: none;
    min-width: 220px;
  }}

  .story-title-badge {{
    font-family: var(--font-serif);
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.5px;
    color: var(--accent);
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
    box-shadow: 4px 0 24px rgba(0,0,0,0.15);
  }}

  aside.toc-drawer.open {{
    transform: translateX(0);
  }}

  .toc-header {{
    padding: 16px;
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
    padding: 10px 0;
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
    padding: 12px 64px;
    overflow: hidden;
    position: relative;
    width: 100%;
    height: 100%;
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
    padding: 32px 56px 24px 56px;
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
    margin-bottom: 20px;
    user-select: none;
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
    max-width: min(920px, calc(100vw - 120px));
    height: 100%;
    max-height: 100%;
    background-color: var(--bg-page);
    border-radius: 8px;
    box-shadow: var(--shadow-page);
    border: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    padding: 44px 72px;
    overflow-y: auto;
  }}

  .book-single .page-content {{
    overflow-y: visible;
  }}

  /* CHAPTER TYPOGRAPHY */
  .chapter-title-block {{
    text-align: center;
    margin-bottom: 28px;
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
    margin-bottom: 10px;
    line-height: 1.3;
  }}

  .chapter-ornament {{
    font-size: 16px;
    color: var(--accent);
    opacity: 0.6;
    letter-spacing: 6px;
  }}

  /* Drop Cap */
  .has-drop-cap > p:first-of-type::first-letter,
  .page-content > p:first-of-type::first-letter {{
    float: left;
    font-size: 3.4em;
    line-height: 0.82;
    margin-top: 0.05em;
    margin-right: 0.12em;
    margin-bottom: -0.05em;
    color: var(--accent);
    font-weight: 700;
    font-family: 'Cinzel', 'Georgia', serif;
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
    width: 48px;
    height: 72px;
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
    z-index: 50;
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
    left: 10px;
  }}

  .nav-turn-btn.next {{
    right: 10px;
  }}

  /* PAPER SWISH ANIMATIONS */
  @keyframes swishRightToLeft {{
    0% {{
      transform: translateX(45px);
      opacity: 0.3;
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
      transform: translateX(-45px);
      opacity: 0.3;
      filter: blur(0.5px);
    }}
    100% {{
      transform: translateX(0);
      opacity: 1;
      filter: blur(0);
    }}
  }}

  .swish-next {{
    animation: swishRightToLeft 0.24s cubic-bezier(0.2, 0.8, 0.25, 1) both;
  }}

  .swish-prev {{
    animation: swishLeftToRight 0.24s cubic-bezier(0.2, 0.8, 0.25, 1) both;
  }}

  /* BOTTOM PROGRESS BAR */
  footer.app-footer {{
    height: 38px;
    background-color: var(--bg-book);
    border-top: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
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
    margin: 0 16px;
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
    background: rgba(0,0,0,0.5);
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
    padding: 24px;
    max-width: 420px;
    width: 90%;
    box-shadow: 0 16px 40px rgba(0,0,0,0.25);
    font-family: var(--font-sans);
  }}

  .modal-box h3 {{
    margin-bottom: 16px;
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
      <span class="story-title-badge" id="currentStoryTitle">StoryCrafter Reader</span>
    </div>

    <div class="app-bar-right">
      <button class="btn" id="btnFontDec" title="Decrease font size">A-</button>
      <button class="btn" id="btnFontInc" title="Increase font size">A+</button>

      <select class="select-input" id="selectTheme" style="min-width: 110px;" title="Select Reading Theme">
        <option value="parchment">Parchment</option>
        <option value="sepia">Sepia</option>
        <option value="midnight">Midnight</option>
        <option value="paper">Clean Paper</option>
      </select>

      <button class="btn" id="btnLayout" title="Toggle Layout (Spread / Single)">
        <span id="layoutIcon">📖 Spread</span>
      </button>

      <button class="btn" id="btnSound" title="Toggle Page Flip Sound">🔊 Sound</button>

      <button class="btn" id="btnHelp" title="Keyboard Shortcuts (?)">?</button>
    </div>
  </header>

  <!-- WORKSPACE -->
  <div class="workspace">
    <!-- TABLE OF CONTENTS DRAWER -->
    <aside class="toc-drawer" id="tocDrawer">
      <div class="toc-header">
        <h2>Chapters</h2>
        <button class="btn" id="btnCloseToc">✕</button>
      </div>
      <ul class="toc-list" id="tocList">
        <!-- populated dynamically -->
      </ul>
    </aside>

    <!-- BOOK VIEWPORT -->
    <main class="book-stage" id="bookStage">
      <!-- TURN BUTTONS -->
      <button class="nav-turn-btn prev" id="btnPrevPage" title="Previous Page / Chapter (Left Arrow / A)">‹</button>
      <button class="nav-turn-btn next" id="btnNextPage" title="Next Page / Chapter (Right Arrow / Space / D)">›</button>

      <!-- SPREAD MODE CONTAINER -->
      <div class="book-spread" id="bookSpread">
        <!-- Left Page -->
        <article class="page page-left" id="pageLeft">
          <div class="page-running-header" id="headerLeft">The Mockingbird's Ledger</div>
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
    <div id="footerChapterInfo">Chapter 1 of 15</div>
    <div class="progress-track">
      <div class="progress-fill" id="progressFill"></div>
    </div>
    <div id="footerProgressInfo">Page 1 of 6</div>
  </footer>

  <!-- KEYBOARD SHORTCUTS MODAL -->
  <div class="modal-backdrop" id="helpModal">
    <div class="modal-box">
      <h3>Keyboard Shortcuts</h3>
      <div class="shortcut-row"><span>Next Page / Chapter</span><span class="shortcut-key">Right / Space / D</span></div>
      <div class="shortcut-row"><span>Previous Page / Chapter</span><span class="shortcut-key">Left / A</span></div>
      <div class="shortcut-row"><span>Toggle Table of Contents</span><span class="shortcut-key">M</span></div>
      <div class="shortcut-row"><span>Cycle Theme</span><span class="shortcut-key">T</span></div>
      <div class="shortcut-row"><span>Toggle Sound Effect</span><span class="shortcut-key">S</span></div>
      <div class="shortcut-row"><span>Toggle Spread / Single</span><span class="shortcut-key">L</span></div>
      <div class="shortcut-row"><span>Font Size Up / Down</span><span class="shortcut-key">+ / -</span></div>
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
  const helpModal = document.getElementById('helpModal');
  const btnHelp = document.getElementById('btnHelp');
  const btnCloseModal = document.getElementById('btnCloseModal');

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

      // 160ms burst of fibrous paper friction noise
      const duration = 0.16;
      const bufferSize = Math.floor(ctx.sampleRate * duration);
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {{
        const t = i / bufferSize;
        const env = Math.sin(t * Math.PI) * Math.exp(-t * 3.8);
        data[i] = (Math.random() * 2 - 1) * env;
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

  // INITIALIZE SYNCHRONOUSLY
  function init() {{
    if (!stories.length) {{
      console.warn("No stories loaded.");
      return;
    }}

    // Resolve initial story
    if (currentConfig.active_story) {{
      const sIdx = stories.findIndex(s => s.id === currentConfig.active_story);
      if (sIdx !== -1) currentStoryIndex = sIdx;
    }}

    populateStorySelect();
    selectStory.value = currentStoryIndex;

    // Resolve initial chapter
    if (currentConfig.active_chapter) {{
      const cIdx = currentStory().chapters.findIndex(c => c.filename === currentConfig.active_chapter);
      if (cIdx !== -1) currentChapterIndex = cIdx;
    }}

    applyConfig();
    updateStoryView();
    loadChapter(currentChapterIndex, false, null);
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

  function loadChapter(idx, startAtEnd = false, direction = null) {{
    currentChapterIndex = idx;
    const ch = currentStory().chapters[idx];
    if (!ch) return;

    // Reset page pair to 0 on forward progress, or last page when returning
    currentPagePair = startAtEnd ? 999999 : 0;

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
    // Measure actual rendered size of the page content area
    const targetHeight = Math.max(320, (contentLeft.clientHeight > 50 ? contentLeft.clientHeight : (window.innerHeight - 200)));
    const targetWidth = Math.max(300, (contentLeft.clientWidth > 50 ? contentLeft.clientWidth : Math.floor((window.innerWidth - 200) / 2)));

    // Create an off-screen measurement sandbox with identical font and padding
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

    // Start Page 0 with Title Block
    tester.innerHTML = titleBlockHtml;
    currentPageNodes.push(titleBlockHtml);
    let isFirstPage = true;

    for (let i = 0; i < nodes.length; i++) {{
      const nodeHtml = nodes[i].outerHTML;
      tester.innerHTML += nodeHtml;

      // When added element causes page overflow
      if (tester.scrollHeight > targetHeight + 6) {{
        // If we already have content on this page, push current page and start a new one
        if (currentPageNodes.length > (isFirstPage ? 1 : 0)) {{
          splitPages.push(currentPageNodes.join(''));
          currentPageNodes = [nodeHtml];
          isFirstPage = false;
          tester.innerHTML = nodeHtml;

          // If a single massive paragraph overflows by itself, still push it to avoid losing text
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

    totalPagePairs = Math.max(1, Math.ceil(splitPages.length / 2));
    if (currentPagePair >= totalPagePairs) {{
      currentPagePair = totalPagePairs - 1;
    }}
    if (currentPagePair < 0) {{
      currentPagePair = 0;
    }}
    renderCurrentSpread(direction);
  }}

  function renderCurrentSpread(direction = null) {{
    const leftIndex = currentPagePair * 2;
    const rightIndex = leftIndex + 1;

    headerLeft.textContent = currentStory().title;
    headerRight.textContent = currentChapter().title;

    chapterTagLeft.textContent = `Chapter ${{currentChapterIndex + 1}}`;
    chapterTagRight.textContent = `Chapter ${{currentChapterIndex + 1}}`;

    contentLeft.innerHTML = splitPages[leftIndex] || '<p style="color:var(--text-muted); text-align:center; padding-top:40px;"><em>End of chapter.</em></p>';
    contentRight.innerHTML = splitPages[rightIndex] || '';

    // Scroll to top of content
    contentLeft.scrollTop = 0;
    contentRight.scrollTop = 0;

    pageLeftNum.textContent = `Page ${{leftIndex + 1}}`;
    pageRightNum.textContent = rightIndex < splitPages.length ? `Page ${{rightIndex + 1}}` : '';

    const totalPages = splitPages.length;
    footerProgressInfo.textContent = `Page ${{leftIndex + 1}}–${{Math.min(rightIndex + 1, totalPages)}} of ${{totalPages}}`;

    const progressPct = Math.round(((Math.min(rightIndex + 1, totalPages)) / totalPages) * 100);
    progressFill.style.width = `${{progressPct}}%`;

    // Apply swish animation & sound effect
    if (direction) {{
      pageLeft.classList.remove('swish-next', 'swish-prev');
      pageRight.classList.remove('swish-next', 'swish-prev');
      void pageLeft.offsetWidth; // Force reflow to restart animation
      const animClass = direction === 'next' ? 'swish-next' : 'swish-prev';
      pageLeft.classList.add(animClass);
      pageRight.classList.add(animClass);
      playPaperSound();
    }}
  }}

  function nextPage() {{
    if (currentConfig.layout === 'spread') {{
      if (currentPagePair < totalPagePairs - 1) {{
        currentPagePair++;
        renderCurrentSpread('next');
      }} else {{
        // Advance to Next Chapter starting at page 0
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
      }} else {{
        // Return to Previous Chapter starting at last page
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

  function saveState() {{
    const state = {{
      active_story: currentStory().id,
      active_chapter: currentChapter().filename,
      theme: currentConfig.theme,
      font_size: currentConfig.font_size,
      layout: currentConfig.layout
    }};

    // Save to LocalStorage
    try {{
      localStorage.setItem('storycrafter_reader_config', JSON.stringify(state));
    }} catch (e) {{}}

    // Save through pywebview API if available
    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_progress) {{
      window.pywebview.api.save_progress(state);
    }}
  }}

  // ATTACH EVENT LISTENERS IMMEDIATELY
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
    saveState();
  }};

  btnFontInc.onclick = () => {{
    if (currentConfig.font_size < 28) {{
      currentConfig.font_size += 2;
      applyConfig();
      if (currentChapter().html) {{
        splitPagesIntoSpreads(currentChapter().html, currentChapter().title);
      }}
      saveState();
    }}
  }};

  btnFontDec.onclick = () => {{
    if (currentConfig.font_size > 14) {{
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

  btnHelp.onclick = () => helpModal.classList.add('open');
  btnCloseModal.onclick = () => helpModal.classList.remove('open');
  helpModal.onclick = (e) => {{
    if (e.target === helpModal) helpModal.classList.remove('open');
  }};

  // KEYBOARD NAVIGATION
  window.addEventListener('keydown', (e) => {{
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'd' || e.key === 'D') {{
      nextPage();
    }} else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {{
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
    }} else if (e.key === '+' || e.key === '=') {{
      btnFontInc.click();
    }} else if (e.key === '-' || e.key === '_') {{
      btnFontDec.click();
    }} else if (e.key === 'Escape') {{
      tocDrawer.classList.remove('open');
      helpModal.classList.remove('open');
    }}
  }});

  // DYNAMIC RESIZE / MAXIMIZE LISTENER
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

  // Execute initialization immediately on DOM ready
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', init);
  }} else {{
    init();
  }}
</script>
</body>
</html>
"""


class ReaderApi:
    """Python-to-JavaScript bridge for pywebview."""

    def __init__(self):
        self.config = load_config()

    def save_progress(self, state):
        self.config.update(state)
        save_config(self.config)
        return True


def run_desktop():
    api = ReaderApi()

    if webview is not None:
        try:
            window = webview.create_window(
                title="StoryCrafter — The Mockingbird's Ledger",
                html=get_html_ui(),
                js_api=api,
                width=1280,
                height=860,
                min_size=(900, 600),
                background_color="#e8dec8"
            )
            webview.start(debug=False)
            return
        except Exception as e:
            print(f"pywebview GUI error: {e}. Falling back to local browser server...")

    # Fallback to local server + browser
    port = 8765
    server_html = get_html_ui()

    class ImmediateHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(server_html.encode("utf-8"))

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), ImmediateHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Opening StoryCrafter Reader at {url} ...")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    webbrowser.open(url)
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Reader closed.")


if __name__ == "__main__":
    if "--web" in sys.argv or "-w" in sys.argv:
        # Strip out --web and -w before passing to web_reader
        sys.argv = [arg for arg in sys.argv if arg not in ("--web", "-w")]
        import web_reader
        web_reader.main()
    else:
        run_desktop()
