#!/usr/bin/env python3
"""
treadle -- reference solver.

Reconstructs the hidden Mealy machine from /run and /conjecture alone, using
Angluin's L* in its Mealy form with Rivest-Schapire counterexample analysis.

  observation table   rows are input prefixes, columns are input suffixes;
                      the cell (u, e) holds the last |e| output symbols of
                      out(u.e), i.e. what the machine emits on e after u.
  S                   prefixes whose rows are pairwise different: one access
                      word per state discovered so far.
  E                   suffixes (experiments) that tell those states apart.
                      E starts as Sigma, so a row also fixes the outputs.
  closed              every one-step extension s.a has the row of some s' in S
  consistent          equal rows in S stay equal after any one more symbol
  hypothesis          states = S, delta(s, a) = the s' whose row is row(s.a),
                      lambda(s, a) = cell(s, a)
  counterexample      binary search for the one position where swapping a
                      prefix for its hypothesis access word changes the true
                      final output; the rest of the word from there on is a
                      new experiment that splits a state.

Standard library only. No randomness: a run is a pure function of the box.
Override the target with TREADLE_URL (e.g. http://localhost:8900 from the host).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("TREADLE_URL", "http://app").rstrip("/")


def say(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
#  The teacher: the two queries, over HTTP
# --------------------------------------------------------------------------
class Box:
    """Output queries (cached) and equivalence queries against the service."""

    def __init__(self, base=BASE):
        self.base = base
        # A Mealy machine answers every prefix of a word while answering the
        # word, so the cache is prefix-closed: non-empty input word -> the
        # single output symbol emitted on its last input symbol.
        self.last = {}
        self.runs = 0           # /run requests actually sent
        self.conjectures = 0    # /conjecture requests sent

    def call(self, path, body=None, tries=6, pause=0.2):
        """One JSON request. Both queries are pure, so retrying is safe."""
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"} if data else {}
        for attempt in range(1, tries + 1):
            req = urllib.request.Request(self.base + path, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace").strip()
                if e.code < 500:                      # our mistake: do not retry
                    raise RuntimeError(f"{path} -> HTTP {e.code}: {detail}") from None
                problem = f"HTTP {e.code}: {detail}"
            except (urllib.error.URLError, OSError, ValueError) as e:
                problem = repr(e)                     # not up yet / transient
            if attempt == tries:
                raise RuntimeError(f"{path} failed after {tries} tries: {problem}")
            time.sleep(pause)

    def describe(self):
        """GET /, waiting up to a minute for the service to come up."""
        return self.call("/", tries=120, pause=0.5)

    def out(self, word):
        """out(word): the output string for `word` from the start state."""
        known = [self.last.get(word[:i]) for i in range(1, len(word) + 1)]
        if None not in known:
            return "".join(known)
        reply = self.call("/run", {"input": word})["output"]
        if not isinstance(reply, str) or len(reply) != len(word):
            raise RuntimeError(f"/run returned a malformed output for {word!r}")
        self.runs += 1
        for i, o in enumerate(reply, 1):
            self.last[word[:i]] = o
        return reply

    def conjecture(self, machine):
        self.conjectures += 1
        return self.call("/conjecture", {"machine": machine})


# --------------------------------------------------------------------------
#  A hypothesis machine
# --------------------------------------------------------------------------
class Hypothesis:
    """Mealy machine read off a closed, consistent table. State i is reached
    by the access word access[i]; state 0 is the start (access word "")."""

    def __init__(self, access, step, emit):
        self.access = access    # access[i]  -> input word
        self.step = step        # step[i][a] -> state
        self.emit = emit        # emit[i][a] -> output symbol

    def run(self, word):
        """(output string, state reached) for `word` from the start."""
        q, cloth = 0, []
        for a in word:
            cloth.append(self.emit[q][a])
            q = self.step[q][a]
        return "".join(cloth), q

    def machine(self):
        """The JSON shape /conjecture expects."""
        name = [f"q{i}" for i in range(len(self.access))]
        return {
            "start": name[0],
            "states": name,
            "delta": {name[i]: {a: name[j] for a, j in row.items()}
                      for i, row in enumerate(self.step)},
            "lambda": {name[i]: dict(row) for i, row in enumerate(self.emit)},
        }


# --------------------------------------------------------------------------
#  L* for Mealy machines
# --------------------------------------------------------------------------
class Learner:
    def __init__(self, sigma, teacher):
        self.sigma = sigma
        self.teacher = teacher
        self.S = [""]               # access words; prefix-closed
        self.E = list(sigma)        # experiments; the first |Sigma| are the symbols
        self.T = {}                 # (prefix, suffix) -> output on the suffix

    # -- the table ---------------------------------------------------------
    def cell(self, u, e):
        key = (u, e)
        value = self.T.get(key)
        if value is None:
            value = self.T[key] = self.teacher.out(u + e)[len(u):]
        return value

    def row(self, u):
        # Fill the missing cells longest experiment first: the answer for u.e
        # also answers u.e' for every prefix e' of e, so shorter ones come free.
        missing = [e for e in self.E if (u, e) not in self.T]
        for e in sorted(missing, key=len, reverse=True):
            self.cell(u, e)
        return tuple(self.T[u, e] for e in self.E)

    # -- closedness --------------------------------------------------------
    def close(self):
        """Promote every extension s.a whose row matches no row of S.
        Returns True if S grew."""
        seen = {self.row(s) for s in self.S}
        grew = False
        for s in self.S:                         # S grows while we walk it
            for a in self.sigma:
                r = self.row(s + a)
                if r not in seen:
                    seen.add(r)
                    self.S.append(s + a)
                    grew = True
        return grew

    # -- consistency -------------------------------------------------------
    def make_consistent(self):
        """If s1, s2 in S have equal rows but s1.a and s2.a do not, the
        experiment a.e that exposes it separates s1 from s2: add it.
        Returns True if E grew.

        With Rivest-Schapire refinement S only ever receives words whose row
        is new, so its rows stay pairwise different and this never fires; it
        is kept as the guard that makes the hypothesis well defined whatever
        ends up in S."""
        alike = {}
        for s in self.S:
            alike.setdefault(self.row(s), []).append(s)
        for group in alike.values():
            for i, s1 in enumerate(group):
                for s2 in group[i + 1:]:
                    for a in self.sigma:
                        for e in self.E:
                            if self.cell(s1 + a, e) != self.cell(s2 + a, e):
                                self.E.append(a + e)
                                return True
        return False

    def stabilise(self):
        while self.close() or self.make_consistent():
            pass

    # -- hypothesis --------------------------------------------------------
    def hypothesis(self):
        state_of = {self.row(s): i for i, s in enumerate(self.S)}
        step = [{a: state_of[self.row(s + a)] for a in self.sigma} for s in self.S]
        emit = [{a: self.cell(s, a) for a in self.sigma} for s in self.S]
        return Hypothesis(list(self.S), step, emit)

    # -- counterexamples (Rivest-Schapire) ---------------------------------
    def refine(self, cex, hyp):
        """Turn a counterexample into one new experiment.

        Cut the word to w, ending at the first position where the hypothesis
        output is wrong. For 0 <= i < |w| let s_i be the access word of the
        hypothesis state after w[:i], and

            alpha(i) = last output symbol of out(s_i . w[i:])     (real machine)

        alpha(0) is the true last output (s_0 is the empty word). alpha(|w|-1)
        is the hypothesis' last output, because lambda(s, a) is a table cell.
        Those differ, so somewhere alpha(i) != alpha(i+1); binary search finds
        such an i with about log2|w| output queries. There s_i.w[i] and s_{i+1}
        have the same row yet behave differently on w[i+1:], so adding w[i+1:]
        to E opens the table and a new state appears.
        """
        truth = self.teacher.out(cex)
        guess, _ = hyp.run(cex)
        if truth == guess:
            raise RuntimeError(f"{cex!r} is not a counterexample")
        n = next(i for i in range(len(cex)) if truth[i] != guess[i]) + 1
        w, target = cex[:n], truth[n - 1]

        def alpha(i):
            _, q = hyp.run(w[:i])
            return self.teacher.out(hyp.access[q] + w[i:])[-1]

        lo, hi = 0, n - 1           # alpha(lo) == target, alpha(hi) != target
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if alpha(mid) == target:
                lo = mid
            else:
                hi = mid
        suffix = w[hi:]
        if not suffix or suffix in self.E:
            raise RuntimeError(f"no new experiment in counterexample {cex!r}")
        self.E.append(suffix)
        return suffix


def learn(teacher, sigma, max_states=None, log=say):
    """Run L* to completion. Returns (token, final hypothesis)."""
    learner = Learner(sigma, teacher)
    while True:
        learner.stabilise()
        if max_states is not None and len(learner.S) > max_states:
            raise RuntimeError(f"{len(learner.S)} states exceeds the advertised "
                               f"maximum of {max_states}; did the box restart?")
        hyp = learner.hypothesis()
        verdict = teacher.conjecture(hyp.machine())
        line = (f"[solve] conjecture {teacher.conjectures:2d}: {len(learner.S):2d} states, "
                f"{len(learner.E):2d} experiments, {teacher.runs:4d} runs")
        if verdict.get("solved") is True:
            log(line + " -> equivalent")
            return verdict["token"], hyp
        cex = verdict["counterexample"]
        suffix = learner.refine(cex, hyp)
        log(line + f" -> differs on {cex!r} (len {len(cex)}), new experiment {suffix!r}")


def main():
    box = Box()
    info = box.describe()
    sigma = "".join(info["sigma"])
    lo, hi = info["states"]["min"], info["states"]["max"]
    say(f"[solve] box at {box.base}: sigma={list(sigma)} gamma={info['gamma']} "
        f"states in [{lo}, {hi}]")
    t0 = time.time()
    token, hyp = learn(box, sigma, max_states=hi)
    say(f"[solve] recovered a {len(hyp.access)}-state machine with {box.runs} runs and "
        f"{box.conjectures} conjectures in {time.time() - t0:.1f}s")
    say(f"TOKEN: {token}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as e:
        say(f"[solve] FAILED: {e}")
        sys.exit(1)
