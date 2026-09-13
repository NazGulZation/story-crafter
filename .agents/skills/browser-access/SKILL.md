---
name: browser-access
description: >-
  Control a real Microsoft Edge browser via Chrome DevTools Protocol (CDP) remote debugging on Windows.
  Use when websearch/webfetch is insufficient and a JS-rendered page, tab navigation, or visual verification is needed,
  including canonical research for story-writing Sections 7-8.
  Covers launching a separate debuggable Edge instance, verifying /json/version, tab control via HTTP-only CDP,
  websocket Runtime.evaluate via Python websocket-client, and Hugging Face login as reference form-fill flow.
---

# Browser Access via Edge Remote Debugging (CDP)

Control a real Edge instance from the agent when `websearch`/`webfetch` is insufficient (JS-heavy wikis, dynamic pages, visual verification).

Agent has no native browser tool. Control Edge via Chrome DevTools Protocol (CDP) over HTTP using PowerShell `bash` + `curl.exe` / `Invoke-RestMethod`.

## 1. Key Constraints (Windows, verified)

- Edge settings toggles do NOT enable remote debugging. Requires command-line `--remote-debugging-port`.
- Port `9222` is usually occupied by Edge background process (`msedge.exe --no-startup-window --win-session-start`) and returns `404 Not Found` on `/`, `/json/version`, `/json/list`. It may also show an `ESTABLISHED` connection from Antigravity `chrome-devtools-mcp`. Do NOT use `9222`.
- Never kill or retrofit the user's main Edge. Always launch a separate debuggable instance with a separate `--user-data-dir` and a free port (e.g. `9333`).
- Available runtimes in this workspace: `node v18`, `python 3.12`, `curl.exe`, PowerShell 5.1. Node 18 has no stable global `WebSocket`; prefer HTTP-only CDP endpoints unless a websocket lib is installed.
- Approved temp root: `$env:TEMP\opencode` (e.g. `C:\Users\<user>\AppData\Local\Temp\opencode`). Use subdir `edge-debug` for the debug profile.
- Edge binary: `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.

## 2. Launch (PowerShell via bash tool)

```powershell
$debugDir = "$env:TEMP\opencode\edge-debug"
New-Item -ItemType Directory -Path $debugDir -Force
Start-Process -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList "--remote-debugging-port=9333","--remote-allow-origins=*","--user-data-dir=$debugDir","--no-first-run","--no-default-browser-check","about:blank"
```
> `--remote-allow-origins=*` is required for websocket CDP (`Runtime.evaluate`, form fill, login verification). Without it, HTTP `/json/*` works but websocket handshake fails with `403 Forbidden ... Use --remote-allow-origins`.

## 3. Verify

```powershell
& curl.exe -s http://127.0.0.1:9333/json/version
# Expect: {"Browser":"Edg/...","Protocol-Version":"1.3","webSocketDebuggerUrl":"ws://127.0.0.1:9333/devtools/browser/..."}
# If 404/empty: wrong port or background-process listener — pick another free port, confirm with:
# netstat -ano | Select-String ":9333"
```

## 4. Control (HTTP-only, no websocket needed)

```powershell
# List tabs
Invoke-RestMethod -Uri "http://127.0.0.1:9333/json/list" | ForEach-Object { Write-Output "$($_.type) :: $($_.title) :: $($_.url)" }

# Open URL in new tab (MUST be PUT, GET returns "supports only PUT verb")
& curl.exe -s -X PUT "http://127.0.0.1:9333/json/new?https://www.google.com/search?q=opencode+edge+remote+debugging"

# Activate / close by id (from /json/list)
# & curl.exe -s "http://127.0.0.1:9333/json/activate/<id>"
# & curl.exe -s -X PUT "http://127.0.0.1:9333/json/close/<id>"
```

Successful navigation is proven when `/json/list` shows e.g. `page :: <query> - Google Search :: https://www.google.com/search?q=...`.

## 5. When to Use vs. websearch

- Default to `websearch`/`webfetch` for canonical lore, speech register, milestones.
- Escalate to Edge CDP only for pages that need JS rendering, interaction proof, or visual confirmation (e.g. character/world dossier research for story-writing). Record the verified URL + page title in the outline's research notes.

## 6. Websocket CDP via Python (Runtime.evaluate)

HTTP covers navigation, but form fill, login, and in-page verification need websocket. Verified stack: `python` + `websocket-client` (`import websocket`).

```powershell
python -c "import websocket; print(websocket.__version__)"
```

Pattern:

```python
import json, urllib.request, websocket
with urllib.request.urlopen("http://127.0.0.1:9333/json/list", timeout=5) as r:
    tabs = json.load(r)
target = next(t for t in tabs if "<url-substring>" in t.get("url", ""))
ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=15)
ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate",
  "params": {"expression": "document.title", "returnByValue": True}}))
print(json.dumps(json.loads(ws.recv()))[:1000])
ws.close()
```

For async page fetch, set `"awaitPromise": True` and use an `async` IIFE.

## 7. Reference: Form Fill & Login Automation

Proven login flow (form fill + submit + `whoami-v2` verification) is kept as a separate reference doc:

- See [references/huggingface-login.md](references/huggingface-login.md) — credentials passed only via environment variables (`HF_EMAIL`/`HF_PASS`), never written to disk or logs.
