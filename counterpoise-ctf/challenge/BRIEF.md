# Counterpoise

An apothecary's back room: one wall of **1024 sealed tins**, numbered `0` to
`1023`. Every tin holds either exactly one brass slug or nothing at all. The
tins themselves weigh nothing, the slugs are identical, and nobody wrote down
which tins are which.

On the bench is a two-pan balance. Its knife-edge is nearly worn through: it
will give **255 more readings** and then lock for good.

Work out the contents of all 1024 tins.

The box is at `http://localhost:9300` (inside the puzzle network:
`http://app`). `GET /` is its instruction card, as JSON.

## The rules

- The wall is a hidden list of 1024 bits, `1` = slug, `0` = empty. It was
  fixed before you arrived and it does not change while you work on it.
- **One question = one weighing.** Put any tins you like on the left pan
  (`plus`) and any *other* tins on the right pan (`minus`). The balance
  answers with one integer:

  ```
  (number of slugs among plus)  -  (number of slugs among minus)
  ```

- A tin can be on at most one pan, and at most once. So in any one weighing
  each tin counts `+1`, `-1`, or not at all. Either pan may be empty.
- You get **255 answered weighings in total.** Not per attempt, not per
  connection: in total. The 256th is refused, and so is every one after it.
  A question you asked just to see what happens is still a question.
- A malformed question (a tin on both pans, a repeated index, an index outside
  `0..1023`, a missing field) is rejected and costs nothing.
- When you know the wall, submit it. A submission is free, but the answer is
  only yes or no. It never says how close you were.

## Talking to the box

```
GET  /         the instruction card: n, budget, questions used, the rule, the endpoints

POST /weigh    {"plus": [i, ...], "minus": [j, ...]}
               -> {"result": <integer>, "asked": <used so far>, "remaining": <left>}

POST /submit   {"bits": "<1024 characters, each 0 or 1; character i is tin i>"}
               -> {"solved": true, "token": "FLAG{...}"}     every character right
               -> {"solved": false}                            anything else
```

For example, this asks "slugs among tins 0, 1, 2 minus slugs among tins 10, 11"
and **spends one of the 255**:

```
curl -s localhost:9300/weigh -H 'Content-Type: application/json' \
     -d '{"plus":[0,1,2],"minus":[10,11]}'
```

The goal is the token: a string of the form `FLAG{...}`.

## Why this is a puzzle

Weighing the tins one at a time settles one tin per question and needs 1024
questions. You have 255. Guessing the rest is hopeless, and the balance will
not be talked into a 256th reading.

So the questions have to be worth more than one tin each, and with nothing to
spare you cannot afford to find out by trial and error on the real wall which
questions those are. Decide what you are going to ask before you ask it.

## A ladder

The wall is the top rung of a ladder. Every rung is the same game with a
smaller wall and a smaller budget, and every rung can be solved **with
certainty, whatever the tins hold,** in exactly the number of weighings shown.

| rung | tins | weighings |
|-----:|-----:|----------:|
|    1 |    1 |         1 |
|    2 |    4 |         3 |
|    3 |   12 |         7 |
|    4 |   32 |        15 |
|    5 |   80 |        31 |
|    6 |  192 |        63 |
|    7 |  448 |       127 |
|    8 | 1024 |       255 |

The box serves only rung 8. The lower rungs are for paper, or for a few lines
of your own code: the balance is easy to imitate (pick a secret list of 0s and
1s; a reading is a count minus a count), and an imitation never runs out.

Rung 1 is free. Rung 2 is the first real one: four tins, three weighings, no
luck allowed. Settle it by hand. Then look at how the ladder climbs.

## Ground rules

- This is a puzzle about asking good questions, not about breaking the
  service. There is no hidden endpoint and nothing to exploit; the three
  routes above are the whole interface.
- Standard tools only. Any language is fine; nothing beyond a JSON-over-HTTP
  client is needed.
- If the budget runs out before you have the wall, that wall is lost. Only the
  organizer can restart the box, and a restart draws a new wall and a new token.
