#!/usr/bin/env python3
"""Dispatcher: serve the VitaChain challenge named by $CHALLENGE (e.g. c1_settle)."""
import os, importlib

name = os.environ.get("CHALLENGE", "c1_settle")
mod = importlib.import_module(f"challenges.{name}")

flag = getattr(mod, "FLAG", None)
if flag:
    try:
        with open("/flag", "w") as f:
            f.write(flag + "\n")
    except OSError:
        pass

mod.app.run(host="0.0.0.0", port=80, threaded=True)
