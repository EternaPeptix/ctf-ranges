# mintmark -- brief

## The setting

The Old Mint keeps a row of 128 coffers in its strongroom. Every coffer is
closed with a lead seal, and every seal was struck between two steel dies.
Nobody outside the die room has ever seen a die. What the strongroom register
shows for each coffer is its **mintmark**: one large number, the product of
the two secret primes cut into the dies that struck its seal.

One coffer is the vault. Something was sealed inside it, and the register
shows the sealed form.

Without the lead and the steel: the service publishes a **directory of large
composite integers** and one sealed value.

- `V_0, V_1, ..., V_{N-1}`, with `N = 128`. Each `V_i` is the product of two
  distinct primes of 512 bits each, so each `V_i` has 1024 bits. The primes
  are secret.
- One entry is the **vault**, `V = V_v`. Its index `v` is public.
- A public exponent `e = 65537`.
- A **sealed value** `c = m^e mod V`, for a secret integer `m` with `0 < m < V`.

Everything is drawn fresh when the service starts and stays fixed for as long
as it is up.

## The goal

**Open the vault: recover `m`** and submit it. The service answers with a
completion token of the form `FLAG{...}`.

## The service

Base URL: `http://app/` on the puzzle network (`http://localhost:9100/` from the host).
All requests and responses are JSON. Large integers travel as decimal strings.

### `GET /`

The register.

```
{
  "name": "mintmark",
  "about": "...",
  "N": 128,
  "bits": {"prime": 512, "composite": 1024},
  "e": 65537,
  "v": 17,
  "c": "8193...",
  "endpoints": {...},
  "directory": ["1042...", "1375...", ...]
}
```

`directory[i]` is `V_i`, `v` is the vault's index, `c` is the sealed value.
(The values above only illustrate the format.) The response is the same every
time you ask.

### `POST /open`

Submit `m`.

```
request   {"message": "<m as a decimal string, or as hex with a 0x prefix>"}
response  {"opened": true, "token": "FLAG{...}"}
     or   {"opened": false}
```

A JSON integer is accepted as well. The submitted integer must be `m` itself,
not merely congruent to it. Malformed requests get HTTP 400 and
`{"opened": false, "error": "..."}`.

## Rules

- Query access only. The puzzle is the numbers, not the container: do not
  inspect the service's process, image, or memory.
- There is no rate limit, and none is needed. `/open` says yes or no and
  nothing else; `m` has more than 500 random bits, so guessing it is hopeless.
- The vault's number is honest. It has no small prime factor, its two primes
  are not close to each other, and `e` is invertible for it. Taken on its
  own it is a 1024-bit number of the kind that general-purpose factoring does
  not reach on any hardware you have.
- Even so, the vault opens with nothing more than a laptop and the standard
  library of any language with big integers. A complete solution makes one
  `GET /` and one `POST /open`, and computes for well under a second.
- You are handed the whole register, not just the vault's line.
