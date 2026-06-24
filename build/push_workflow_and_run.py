#!/usr/bin/env python3
import base64
import json
import os
import urllib.parse
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
OWNER, REPO = "octopus87", "CWDZ"
WORKFLOW = ".github/workflows/build-windows.yml"


def api(method, url, body=None):
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw.strip() else {}


path = WORKFLOW
local = os.environ.get("WORKFLOW_FILE", path)
with open(local, "rb") as f:
    content = base64.b64encode(f.read()).decode()

quoted = urllib.parse.quote(path, safe="/")
url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{quoted}"
body = {"message": "fix: remove pip cache for setup-python", "content": content}
info = api("GET", url + "?ref=main")
body["sha"] = info["sha"]
api("PUT", url, body)
print("updated workflow")

api(
    "POST",
    f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/build-windows.yml/dispatches",
    {"ref": "main"},
)
print("triggered Build Windows")
