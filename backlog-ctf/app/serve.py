#!/usr/bin/env python3
"""Dispatcher: serve the challenge named by $CHALLENGE (e.g. c01)."""
import os, importlib

name = os.environ.get("CHALLENGE", "c01")
mod = importlib.import_module(f"challenges.{name}")

# challenges that read a flag file expect it at /flag
flag = getattr(mod, "FLAG", None)
if flag:
    try:
        with open("/flag", "w") as f:
            f.write(flag + "\n")
    except OSError:
        pass

if hasattr(mod, "run"):
    mod.run()                                  # custom server (e.g. raw TCP)
else:
    mod.app.run(host="0.0.0.0", port=80, threaded=True)
