#!/usr/bin/env python3
"""
treadle -- a hidden-machine reconstruction puzzle.

The box is a loom. Behind the cloth beam runs a closed chain of pattern cards
that nobody gets to look at. Press a treadle and the loom throws exactly one
pick of weft; which dye comes off the shuttle depends on the card currently
under the needles, and the chain then advances to some other card.

Stripped of the wood and wool, the loom is a deterministic Mealy machine:

    treadles  = input alphabet  Sigma   (2 or 3 symbols)
    threads   = output alphabet Gamma   (2 or 3 symbols)
    cards     = states                  (between 24 and 40, minimal, reachable)

    GET  /            what the box is (alphabets, state-count range, endpoints)
    POST /run         weave a treadling from the start card, get the cloth
    POST /conjecture  submit a draft (a Mealy machine); the loom checks exact
                      equivalence and answers with the completion token or
                      with a shortest treadling on which the two cloths differ

The machine and the token are drawn fresh at every start and live in memory
only. Nothing secret is written to disk, the environment, or the logs.
"""
import logging
import random
import secrets
import threading
from collections import deque

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

STATE_MIN, STATE_MAX = 24, 40      # reachable + minimal state count, inclusive
TREADLES = "123"                   # Sigma is a prefix of this, length 2 or 3
THREADS = "imw"                    # Gamma is a prefix of this, length 2 or 3
THREAD_NAMES = {"i": "indigo", "m": "madder", "w": "weld"}
TREADLE_NAMES = {"1": "first treadle", "2": "second treadle", "3": "third treadle"}

MAX_INPUT = 8192                   # longest treadling /run will weave
MAX_DRAFT_STATES = 2048            # largest draft /conjecture will read
MAX_BODY = 4 * 1024 * 1024


# --------------------------------------------------------------------------
#  The machine
# --------------------------------------------------------------------------
class Loom:
    """A Mealy machine over single-character symbols. States are 0..n-1."""

    def __init__(self, sigma, gamma, start, delta, lam):
        self.sigma = sigma          # str, input symbols in canonical order
        self.gamma = gamma          # str, output symbols
        self.start = start          # int
        self.delta = delta          # delta[q][a] -> next state
        self.lam = lam              # lam[q][a]   -> output symbol
        self.n = len(delta)

    def out(self, word):
        """The output string emitted while reading `word` from the start."""
        q, cloth = self.start, []
        for a in word:
            cloth.append(self.lam[q][a])
            q = self.delta[q][a]
        return "".join(cloth)


def reachable(start, delta, sigma):
    """States reachable from `start`, in BFS order."""
    order, seen = [start], {start}
    for q in order:                 # `order` grows while we walk it
        for a in sigma:
            t = delta[q][a]
            if t not in seen:
                seen.add(t)
                order.append(t)
    return order


def refine(states, delta, lam, sigma):
    """Partition refinement (Moore's algorithm, Mealy flavour).

    Start from "same output on every input symbol", then repeatedly split
    blocks whose members step into different blocks. Refinement only ever
    splits, so it has converged as soon as the block count stops growing.
    Returns {state: block id}; two states share a block iff they are
    behaviourally equivalent.
    """
    def number(signature):
        ids = {}
        return {q: ids.setdefault(signature[q], len(ids)) for q in states}

    block = number({q: tuple(lam[q][a] for a in sigma) for q in states})
    while True:
        finer = number({q: (block[q],) + tuple(block[delta[q][a]] for a in sigma)
                        for q in states})
        if len(set(finer.values())) == len(set(block.values())):
            return block
        block = finer


def draw(rng):
    """One attempt at a machine. Returns a Loom, or None if the attempt does
    not land in the required state range after trimming and minimising."""
    sigma = TREADLES[:rng.choice((2, 3))]
    gamma = THREADS[:rng.choice((2, 3))]
    raw = rng.randint(STATE_MIN, STATE_MAX + 12)
    delta = [{a: rng.randrange(raw) for a in sigma} for _ in range(raw)]
    lam = [{a: rng.choice(gamma) for a in sigma} for _ in range(raw)]
    start = rng.randrange(raw)

    live = reachable(start, delta, sigma)               # drop unreachable
    block = refine(live, delta, lam, sigma)             # merge equivalent
    n = len(set(block.values()))
    if not STATE_MIN <= n <= STATE_MAX:
        return None
    if {lam[q][a] for q in live for a in sigma} != set(gamma):
        return None                                     # advertised Gamma must be used

    # Quotient machine, with the block ids shuffled so that no internal
    # numbering carries any structure (e.g. "the start state is state 0").
    perm = list(range(n))
    rng.shuffle(perm)
    name = {q: perm[block[q]] for q in live}
    q_delta, q_lam = [None] * n, [None] * n
    for q in live:
        q_delta[name[q]] = {a: name[delta[q][a]] for a in sigma}
        q_lam[name[q]] = {a: lam[q][a] for a in sigma}
    return Loom(sigma, gamma, name[start], q_delta, q_lam)


def make_loom(rng):
    """Regenerate until the reachable, minimal machine has 24..40 states."""
    while True:
        loom = draw(rng)
        if loom is None:
            continue
        everyone = list(range(loom.n))
        assert sorted(reachable(loom.start, loom.delta, loom.sigma)) == everyone
        assert len(set(refine(everyone, loom.delta, loom.lam, loom.sigma).values())) == loom.n
        assert STATE_MIN <= loom.n <= STATE_MAX
        return loom


# --------------------------------------------------------------------------
#  The equivalence teacher
# --------------------------------------------------------------------------
class BadDraft(ValueError):
    pass


def _ident(x, what):
    """State identifiers may be JSON strings or integers; compare as strings."""
    if isinstance(x, bool) or not isinstance(x, (str, int)):
        raise BadDraft(f"{what} must be a string or an integer")
    return str(x)


def parse_draft(machine, sigma, gamma):
    """Validate a submitted machine. Returns (start, step, emit) with states
    renumbered 0..n-1, step[q][a] -> state and emit[q][a] -> output symbol."""
    if not isinstance(machine, dict):
        raise BadDraft('"machine" must be an object')
    states = machine.get("states")
    if not isinstance(states, list) or not states:
        raise BadDraft('"states" must be a non-empty list')
    if len(states) > MAX_DRAFT_STATES:
        raise BadDraft(f"at most {MAX_DRAFT_STATES} states")
    names = [_ident(s, "a state") for s in states]
    index = {s: i for i, s in enumerate(names)}
    if len(index) != len(names):
        raise BadDraft('"states" contains duplicates')
    if "start" not in machine:
        raise BadDraft('"start" is missing')
    start = _ident(machine["start"], '"start"')
    if start not in index:
        raise BadDraft('"start" is not one of "states"')
    delta, lam = machine.get("delta"), machine.get("lambda")
    if not isinstance(delta, dict) or not isinstance(lam, dict):
        raise BadDraft('"delta" and "lambda" must be objects keyed by state')

    step, emit = [], []
    for s in names:
        d_row, l_row = delta.get(s), lam.get(s)
        if not isinstance(d_row, dict) or not isinstance(l_row, dict):
            raise BadDraft(f"state {s!r} needs a row in both delta and lambda")
        s_step, s_emit = {}, {}
        for a in sigma:
            if a not in d_row or a not in l_row:
                raise BadDraft(f"state {s!r} has no entry for input {a!r}")
            nxt = _ident(d_row[a], f"delta[{s!r}][{a!r}]")
            if nxt not in index:
                raise BadDraft(f"delta[{s!r}][{a!r}] is not one of \"states\"")
            o = l_row[a]
            if not isinstance(o, str) or len(o) != 1 or o not in gamma:
                raise BadDraft(f"lambda[{s!r}][{a!r}] must be one of {list(gamma)}")
            s_step[a], s_emit[a] = index[nxt], o
        step.append(s_step)
        emit.append(s_emit)
    return index[start], step, emit


def shortest_difference(loom, start, step, emit):
    """Exact equivalence check.

    Breadth-first search over the product of the hidden machine and the
    draft, starting from the pair of start states. A pair is expanded only
    after every pair closer to the root, so the first input symbol on which
    the two machines emit different outputs closes a shortest distinguishing
    word. If the whole reachable product is exhausted without a difference,
    the two machines agree on every input string: return None.
    """
    root = (loom.start, start)
    came = {root: None}             # pair -> (previous pair, symbol)
    queue = deque([root])
    while queue:
        pair = queue.popleft()
        hq, dq = pair
        for a in loom.sigma:
            if loom.lam[hq][a] != emit[dq][a]:
                word = [a]
                while came[pair] is not None:
                    pair, sym = came[pair]
                    word.append(sym)
                return "".join(reversed(word))
            nxt = (loom.delta[hq][a], step[dq][a])
            if nxt not in came:
                came[nxt] = (pair, a)
                queue.append(nxt)
    return None


# --------------------------------------------------------------------------
#  Secrets: drawn once per process, kept in memory only
# --------------------------------------------------------------------------
LOOM = make_loom(random.SystemRandom())
TOKEN = "FLAG{treadle_learn_hidden_mealy_machine_" + secrets.token_hex(12) + "}"

_ledger = {"runs": 0, "conjectures": 0}
_ledger_lock = threading.Lock()


def _tally(key):
    with _ledger_lock:
        _ledger[key] += 1


# --------------------------------------------------------------------------
#  HTTP
# --------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_BODY
app.json.sort_keys = False


def _fail(msg, code=400):
    return jsonify({"error": msg}), code


@app.errorhandler(HTTPException)
def _http_error(e):
    return _fail(e.description or e.name, e.code or 500)


@app.get("/")
def index():
    sigma, gamma = list(LOOM.sigma), list(LOOM.gamma)
    with _ledger_lock:
        ledger = dict(_ledger)
    return jsonify({
        "box": "treadle",
        "kind": "mealy",
        "about": ("A loom with a hidden chain of pattern cards. Each treadle press "
                  "throws one pick of weft; its dye depends on the card under the "
                  "needles, and the chain then moves on. Work out the whole chain "
                  "and hand in a draft that weaves the same cloth for every "
                  "treadling."),
        "sigma": sigma,
        "gamma": gamma,
        "legend": {
            "sigma": {a: TREADLE_NAMES[a] for a in sigma},
            "gamma": {o: THREAD_NAMES[o] + " weft" for o in gamma},
        },
        "states": {"min": STATE_MIN, "max": STATE_MAX,
                   "note": "minimal and fully reachable; the exact count is not disclosed"},
        "endpoints": {
            "GET /": "this description",
            "POST /run": {
                "request": {"input": "<string over sigma>"},
                "response": {"output": "<string over gamma, same length>"},
                "meaning": "weave the treadling from the start card; one thread per press",
            },
            "POST /conjecture": {
                "request": {"machine": {
                    "start": "<state id>",
                    "states": ["<state id>", "..."],
                    "delta": {"<state id>": {"<input symbol>": "<next state id>"}},
                    "lambda": {"<state id>": {"<input symbol>": "<output symbol>"}},
                }},
                "response": [
                    {"solved": True, "token": "FLAG{...}"},
                    {"solved": False,
                     "counterexample": "<a shortest input on which the outputs differ>"},
                ],
                "meaning": "exact equivalence check against the hidden machine",
            },
        },
        "limits": {"max_input_length": MAX_INPUT,
                   "max_conjecture_states": MAX_DRAFT_STATES},
        "ledger": ledger,
    })


@app.post("/run")
def run():
    body = request.get_json(silent=True, force=True)
    if not isinstance(body, dict) or not isinstance(body.get("input"), str):
        return _fail('send JSON {"input": "<string over sigma>"}')
    word = body["input"]
    if len(word) > MAX_INPUT:
        return _fail(f"input longer than {MAX_INPUT} symbols")
    stray = sorted(set(word) - set(LOOM.sigma))
    if stray:
        return _fail(f"symbols outside sigma {list(LOOM.sigma)}: {stray[:8]}")
    _tally("runs")
    return jsonify({"output": LOOM.out(word)})


@app.post("/conjecture")
def conjecture():
    body = request.get_json(silent=True, force=True)
    if not isinstance(body, dict) or "machine" not in body:
        return _fail('send JSON {"machine": {"start": ..., "states": [...], '
                     '"delta": {...}, "lambda": {...}}}')
    try:
        start, step, emit = parse_draft(body["machine"], LOOM.sigma, LOOM.gamma)
    except BadDraft as e:
        return _fail(f"malformed machine: {e}")
    _tally("conjectures")
    word = shortest_difference(LOOM, start, step, emit)
    if word is None:
        return jsonify({
            "solved": True,
            "token": TOKEN,
            "message": "Thread for thread, your draft weaves the loom's cloth. The chain is yours.",
        })
    return jsonify({
        "solved": False,
        "counterexample": word,
        "message": "Your draft and the loom part ways on the last pick of this treadling.",
    })


if __name__ == "__main__":
    logging.getLogger("werkzeug").setLevel(logging.WARNING)   # no per-request lines
    print("[treadle] loom threaded; listening on :80", flush=True)
    app.run(host="0.0.0.0", port=80, threaded=True)
