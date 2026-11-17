# Flags (organizer)

One flag, **earned** (not hardcoded): the service mints a fresh
`FLAG{synapse_reconstruct_relu_net_<random>}` at startup and reveals it from
`POST /verify` only to a submission that is *exactly* functionally equal to the
hidden network. Verified live via `scripts/solve.py` — `make check` reconstructs
`f` from `/eval` queries alone and recovers the token (exit 0), repeatably.

| Widget | Port | Technique required | Flag |
|--------|------|--------------------|------|
| synapse | 8800 | cryptanalytic reconstruction of a hidden ReLU network from exact query access (recover its kink hyperplanes, then fit the output by exact rational linear algebra) | `FLAG{synapse_reconstruct_relu_net_<random per boot>}` |

## The technique (why it's the whole point)
The hidden `f(x) = Σ aⱼ·max(0, wⱼ·x + bⱼ) + c` is piecewise-linear on `Q⁶`.
Dense sampling is hopeless in 6 dimensions, so you must recover *structure*:
1. exact local gradients via central differences on a verified-linear stencil;
2. exact kink locations of `F(t)=f(p+t·d)` along random lines;
3. one hyperplane `(U, β)` per kink from the gradient jump across it (`U = aⱼwⱼ`),
   each confirmed by independent probes elsewhere on that hyperplane;
4. an exact (3× overdetermined) rational linear solve for the output coefficients
   in `f(x)=Σ λⱼ·max(0,Uⱼ·x+βⱼ) + L·x + e`.

Submit `{relus, lin, const}` to `/verify`; a near-miss hyperplane (even off by
1/10⁹) fails, because the verifier samples points hugging every kink surface.

## Reference solver stats
- Recovers all 10 hyperplanes and the exact output, typically within 1–4 lines
  and ~1000–1500 `/eval` queries; a full `make check` run is ~1.5 s.
- Pure stdlib, `fractions.Fraction` throughout — no floating point, no tolerance,
  only exact equality. Deterministic solver RNG (`SYN_SEED`); the service's secret
  network + token are OS-random per boot, so `make reset && make check` stays green.

## Notes
- No scoreboard: this is a single-service range; the flag is the `/verify` token.
- The host's default Docker address pools are exhausted by sibling ranges, so the
  compose pins `synapse_net` to an explicit `10.85.0.0/24`.
- Built by Fable 5.2 to spec; the organizer self-check and strict verifier were
  reviewed and re-run here (token format aligned to `FLAG{...}` for the collection).
