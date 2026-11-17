#!/usr/bin/env python3
"""
Puppeteer / models — CVE-2026-115533 (LeRobot from_pretrained config-class RCE).

LeRobot's `from_pretrained` reads a model repo's config and instantiates the
Python class the config names (via importlib) with config-supplied arguments.
The flaw: an untrusted repo controls that class name and its arguments, so a
poisoned `config.json` makes the loader import and call an arbitrary callable —
remote code execution the moment the "model" is loaded.

The agent's model_load tool loads any repo URL it is told to. A poisoned repo
whose config names `subprocess.check_output` runs commands on the model host.

Isolated training range. Do not deploy.
"""
import importlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(ok=True, service="models")


def from_pretrained(repo: str):
    """Faithful minimal re-impl of the vulnerable loader."""
    cfg = requests.get(repo.rstrip("/") + "/config.json", timeout=8).json()
    class_path = cfg.get("class_path") or cfg.get("_target_")
    if not class_path or "." not in class_path:
        raise ValueError("config.json must name a class via 'class_path'")
    args = cfg.get("args", []) or []
    kwargs = cfg.get("init_args", {}) or {}

    module, _, name = class_path.rpartition(".")
    mod = importlib.import_module(module)      # import attacker-named module
    target = getattr(mod, name)                # resolve attacker-named attr
    # *** The vuln ***: instantiate/call it with attacker-supplied arguments.
    result = target(*args, **kwargs)
    if isinstance(result, (bytes, bytearray)):
        result = result.decode("utf-8", "replace")
    return cfg, result


@app.post("/load")
def load():
    body = request.get_json(silent=True) or {}
    repo = body.get("repo", "")
    if not repo:
        return jsonify(error="missing repo"), 400
    try:
        cfg, result = from_pretrained(repo)
        return jsonify(ok=True, repo=repo, loaded_class=cfg.get("class_path"),
                       result=str(result))
    except Exception as e:
        return jsonify(ok=False, repo=repo, error=f"{type(e).__name__}: {e}"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
