#!/usr/bin/env python3
"""Dispatcher: serve the Obscura widget named by $CHALLENGE (e.g. c1_reverb)."""
import os, importlib

name = os.environ.get("CHALLENGE", "c1_reverb")
mod = importlib.import_module(f"challenges.{name}")

flag = getattr(mod, "FLAG", None)
if flag:
    try:
        with open("/flag", "w") as f:
            f.write(flag + "\n")
    except OSError:
        pass

mod.app.run(host="0.0.0.0", port=80, threaded=True)
