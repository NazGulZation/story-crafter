# Reference: Hugging Face Login via Edge CDP (verified 2026-09-10)

Proven flow for `https://huggingface.co/login` -> `https://huggingface.co/` + Space `https://huggingface.co/spaces/kulkas2pintu/QWEN_EDIT_IMAGE`.

Requires the debug Edge from the parent `browser-access` skill launched with `--remote-allow-origins=*` (websocket CDP), plus `C:\Python312\python.exe` + `websocket-client`.

## Form facts (plain POST, not React state)

- `form[action="/login"]`, `input[name=username]` (email or username), `input[name=password]`, `button[type=submit]` ("Login").

## Steps

```powershell
# 1. Open tabs (PUT required)
& curl.exe -s -X PUT "http://127.0.0.1:9333/json/new?https://huggingface.co/spaces/kulkas2pintu/QWEN_EDIT_IMAGE"
& curl.exe -s -X PUT "http://127.0.0.1:9333/json/new?https://huggingface.co/login"
```

```python
# 2. Fill + submit (creds ONLY via env HF_EMAIL / HF_PASS, never hardcoded or written to disk)
import json, os, urllib.request, websocket
email, pw = os.environ["HF_EMAIL"], os.environ["HF_PASS"]
with urllib.request.urlopen("http://127.0.0.1:9333/json/list", timeout=5) as r:
    tabs = json.load(r)
target = next(t for t in tabs if "huggingface.co/login" in t["url"])
ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=15)
fill = "(function(){ const email=%s; const pw=%s; const u=document.querySelector('input[name=username]'); const p=document.querySelector('input[name=password]'); const set=(el,v)=>{el.focus(); document.execCommand('selectAll',false,null); document.execCommand('insertText',false,v); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));}; set(u,email); set(p,pw); return 'filled:'+u.value.length+':'+p.value.length; })()" % (json.dumps(email), json.dumps(pw))
ws.send(json.dumps({"id": 20, "method": "Runtime.evaluate", "params": {"expression": fill, "returnByValue": True}}))
json.loads(ws.recv())  # expect filled:<n>:<m>
ws.send(json.dumps({"id": 21, "method": "Runtime.evaluate", "params": {"expression": "(() => { document.querySelector('form[action=\"/login\"] button[type=submit]').click(); return 'clicked'; })()", "returnByValue": True}}))
json.loads(ws.recv())
ws.close()
```

```powershell
# Run without persisting creds (single invocation, then clear):
$env:HF_EMAIL='user@example.com'; $env:HF_PASS='...'; C:\Python312\python.exe login.py; $env:HF_EMAIL=$null; $env:HF_PASS=$null
```

```python
# 3. Verify (after ~10-12s): login tab redirects /login -> https://huggingface.co/
# In-page check via async evaluate (awaitPromise: True):
expr = """(async () => {
  const r = await fetch('/api/whoami-v2', {credentials: 'include'});
  return JSON.stringify(await r.json()).slice(0, 800);
})()"""
# expect: {"type":"user","name":"...","email":"...","emailVerified":true,"auth":{"type":"cookie"}}
```

## Gotchas hit

- `Runtime.callFunctionOn` without `executionContextId` fails (`-32602`); use `Runtime.evaluate` with `json.dumps()`-escaped args instead.
- Fill succeeds when evaluate returns `filled:<n>:<m>` (input lengths), achieved via `execCommand('insertText')` + input/change events.
- Successful login proven by redirect to `/` plus `whoami-v2` returning the account email.

## Safety

Never echo creds, never write them to `*.py`/`*.md`/logs; pass via env for one process only; advise rotation if shared in chat; prefer HF access tokens for repeat use.
