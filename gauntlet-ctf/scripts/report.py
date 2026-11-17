#!/usr/bin/env python3
"""The Gauntlet — fetch each flag from the dispenser (verifies isSolved()
on-chain) and print the board. Exit 0 iff all seven are released."""
import json, sys, urllib.request
try:
    r = json.loads(urllib.request.urlopen("http://dispenser/result", timeout=12).read())
except Exception as e:
    print("ERROR contacting dispenser:", e); sys.exit(1)
print("== The Gauntlet — solver ==")
for c in r["challenges"]:
    print(f"  c{c['id']}  {c['name']:<13} {c['technique']:<44} {c.get('flag') or '<unsolved>'}")
ok = r.get("all_solved", False)
print("\nRESULT:", "ALL 7 FLAGS CAPTURED" if ok else "INCOMPLETE")
sys.exit(0 if ok else 1)
