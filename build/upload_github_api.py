#!/usr/bin/env python3
"""Upload project to GitHub via Contents API (fallback when git push fails)."""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
OWNER = os.environ.get("GH_OWNER", "octopus87")
REPO = os.environ.get("GH_REPO", "CWDZ")
ROOT = os.environ.get("UPLOAD_ROOT", ".")
SKIP_DIRS = {".git", "__pycache__", ".venv", "dist", ".playwright"}
MAX_BYTES = 8 * 1024 * 1024


def api(method, url, body=None):
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "cwdz-upload",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                raw = r.read()
                return json.loads(raw.decode()) if raw else {}
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def should_upload(rel: str) -> bool:
    base = os.path.basename(rel)
    if base in (".DS_Store",) or base.startswith("._"):
        return False
    if rel.startswith("data/"):
        return False
    if rel.startswith("scripts/"):
        return False
    return True


def existing_paths():
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/git/trees/main?recursive=1"
    try:
        data = api("GET", url)
        return {t["path"] for t in data.get("tree", [])}
    except Exception:
        return set()


def main():
    have = existing_paths()
    files = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            if not should_upload(rel):
                continue
            if os.path.getsize(full) > MAX_BYTES:
                continue
            files.append(rel)
    files.sort(key=lambda x: (0 if x.startswith(".github") else 1, x))
    todo = [f for f in files if f not in have]
    print(f"upload {len(todo)} / {len(files)} (skip {len(files) - len(todo)} existing)")
    for i, rel in enumerate(todo):
        with open(os.path.join(ROOT, rel), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        quoted = urllib.parse.quote(rel, safe="/")
        url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{quoted}"
        body = {"message": f"ci: add {rel}", "content": b64}
        try:
            info = api("GET", url + "?ref=main")
            body["sha"] = info["sha"]
        except Exception:
            pass
        api("PUT", url, body)
        if (i + 1) % 10 == 0:
            print(f"{i + 1}/{len(todo)}")
        time.sleep(0.5)
    print("dispatch workflow")
    api(
        "POST",
        f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/build-windows.yml/dispatches",
        {"ref": "main"},
    )
    print("DONE")


if __name__ == "__main__":
    main()
