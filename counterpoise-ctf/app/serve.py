#!/usr/bin/env python3
"""
Counterpoise -- a two-pan balance and a wall of 1024 sealed tins.

Each tin (index 0..1023) holds exactly one brass slug or nothing: a hidden bit
vector x in {0,1}^1024, drawn at startup.  The only instrument is the balance:

    POST /weigh  {"plus":[...], "minus":[...]}
        -> (# ones among plus) - (# ones among minus)

The pans must be disjoint and repeat-free, so every tin counts +1, -1 or 0.
The knife-edge survives 255 answered weighings; after that /weigh refuses.

    POST /submit {"bits":"<1024 chars of 0/1>"}
        -> {"solved":true,"token":"FLAG{...}"}  or  {"solved":false}

x is never sent anywhere and never logged; neither is the token until earned.
Standard library + Flask only.
"""
import hmac
import secrets
import threading

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

N = 1024        # tins on the wall = length of the hidden vector
BUDGET = 255    # answered weighings allowed per hidden vector

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024   # a full 1024-index question is ~5 kB
app.json.sort_keys = False

_lock = threading.Lock()
_token = "FLAG{" + secrets.token_hex(16) + "}"   # set once, at startup
_tins = []      # the hidden vector as a list of 0/1
_bits = ""      # the same vector as the 1024-character string /submit expects
_asked = 0      # questions answered about the current vector
_solves = 0     # correct submissions since startup


def _restock():
    """Draw a hidden vector uniformly from {0,1}^N and zero the question counter."""
    global _tins, _bits, _asked
    word = secrets.randbits(N)
    _tins = [(word >> i) & 1 for i in range(N)]
    _bits = "".join(map(str, _tins))
    _asked = 0


_restock()


class Rejected(Exception):
    """A malformed question: answered with 400 and never charged."""


def _pans(body):
    """Validate a /weigh body and return (plus, minus)."""
    if not isinstance(body, dict):
        raise Rejected('body must be a JSON object: {"plus":[...], "minus":[...]}')
    seen, pans = set(), []
    for name in ("plus", "minus"):
        if name not in body:
            raise Rejected(f'missing "{name}" (send an empty list for an empty pan)')
        pan = body[name]
        if not isinstance(pan, list):
            raise Rejected(f'"{name}" must be a list of indices')
        for i in pan:
            if type(i) is not int or not 0 <= i < N:      # no bools, floats, strings
                raise Rejected(f'"{name}" holds something that is not an integer in 0..{N - 1}')
            if i in seen:
                raise Rejected(f"index {i} appears more than once; plus and minus must be "
                               "disjoint and repeat-free")
            seen.add(i)
        pans.append(pan)
    return pans


def _body():
    """The request body as parsed JSON, or None if it is not JSON at all."""
    try:
        return request.get_json(force=True, silent=True)
    except RecursionError:      # absurdly nested brackets
        return None


@app.get("/")
def card():
    with _lock:
        asked, solves = _asked, _solves
    return jsonify({
        "name": "Counterpoise",
        "about": ("A wall of 1024 sealed tins, numbered 0..1023. Each tin holds exactly one "
                  "brass slug or nothing at all. Work out which is which. Your only instrument "
                  "is a two-pan balance whose knife-edge is good for 255 weighings."),
        "n": N,
        "budget": BUDGET,
        "asked": asked,
        "remaining": BUDGET - asked,
        "solves": solves,
        "rule": ("One question = one weighing. Put any tins on the left pan (plus) and any other "
                 "tins on the right pan (minus); the balance answers "
                 "(# slugs among plus) - (# slugs among minus). The pans must be disjoint and "
                 "no index may repeat, so each tin counts +1, -1 or not at all; either pan may "
                 "be empty. Every answered weighing costs one of the 255 questions. Once 255 "
                 "have been answered, /weigh refuses."),
        "endpoints": {
            "GET /": "this card (never the contents of the tins)",
            "POST /weigh": {
                "body": {"plus": ["<index>", "..."], "minus": ["<index>", "..."]},
                "indices": f"integers 0..{N - 1}, each at most once across both lists",
                "returns": {"result": "(# ones among plus) - (# ones among minus)",
                            "asked": "questions used so far", "remaining": "questions left"},
                "cost": "1 question per answered call; a malformed call gets 400 and costs nothing",
                "refused": f"429 once {BUDGET} questions have been answered",
            },
            "POST /submit": {
                "body": {"bits": f"<{N} characters of 0/1; character i is tin i>"},
                "returns": ('{"solved":true,"token":"FLAG{...}"} if every character is right, '
                            'otherwise {"solved":false}'),
                "cost": "free, and it tells you nothing about which characters are wrong",
            },
        },
        "notes": [
            "The contents were fixed before your first question and do not react to what you ask.",
            "A correct submission releases the token and retires that wall: a fresh hidden vector "
            "is drawn and the counter returns to 0. Nothing else gives questions back.",
        ],
    })


@app.post("/weigh")
def weigh():
    global _asked
    body = _body()
    with _lock:
        if _asked >= BUDGET:
            return jsonify(error=f"the knife-edge is worn out: all {BUDGET} questions are spent",
                           asked=_asked, remaining=0), 429
        try:
            plus, minus = _pans(body)
        except Rejected as why:
            return jsonify(error=str(why), charged=False,
                           asked=_asked, remaining=BUDGET - _asked), 400
        _asked += 1
        result = sum(_tins[i] for i in plus) - sum(_tins[i] for i in minus)
        return jsonify(result=result, asked=_asked, remaining=BUDGET - _asked)


@app.post("/submit")
def submit():
    global _solves
    body = _body()
    bits = body.get("bits") if isinstance(body, dict) else None
    if not isinstance(bits, str) or len(bits) != N or set(bits) - {"0", "1"}:
        return jsonify(solved=False,
                       error=f'send {{"bits": "<exactly {N} characters of 0/1>"}}'), 400
    with _lock:
        if hmac.compare_digest(bits, _bits):
            _solves += 1
            _restock()          # that wall is done; the next solver gets a new one
            return jsonify(solved=True, token=_token)
    return jsonify(solved=False)


@app.errorhandler(HTTPException)
def http_error(err):
    return jsonify(error=err.name.lower()), err.code


if __name__ == "__main__":
    print(f"[counterpoise] listening on :80  n={N} budget={BUDGET}", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
