# talk_demo: the readback, live

A payment handed between agents, played as a radio exchange on a terminal. Each line is a real `RW1` message,
each check is the codec's own check with its own words, and every digest is computed as the scene runs. The script
checks its own expectations as it goes: a check that should pass and does not, or one that should refuse and does
not, stops with `DEMO FAULT`. If `--all --pace 0` exits 0 in the green room, the live run cannot go wrong.

Run everything from the repo root. Standard library only; the codec is imported by path, nothing is installed.

## Before the talk

```
python3 examples/talk_demo.py --all --pace 0 --no-color     # the green-room check; exits 0 and prints every scene
```

Set the terminal to a large font and at least 100 columns, dark background. Colour is used only on a tty and only
for the speaker tag (cyan), the check result (green or red) and the captions (dim). `--no-color` turns it off.

Pacing: `--pace 1.2` (the default) pauses 1.2 seconds between lines. `--step` waits for Enter instead, which is the
setting to use on stage: the speaker controls the beat, and a line never appears before the sentence that sets
it up. Both can be given; `--step` wins.

## The scenes

| Flag | What happens |
|---|---|
| `--clean` | The HO is built from the approved record and checked. The payment tool prepares and states the payment as an RB with `h=` and a token. The scheduler checks it, clears it with `AN val=Y`, the tool commits, the DN is checked against the plan. Roger. Wilco. |
| `--draft-fault` | The scheduler's draft carries a transposed account digit. `check-ho` refuses it before it is sent; nothing leaves the scheduler. |
| `--tool-fault` | The HO is right. The tool resolves a lookalike account at prepare; its statement differs from the plan; `check-rb` refuses; the tool abandons the token; nothing is paid. |
| `--relay` | The same handoff passed scheduler, coordinator, desk, payer. The coordinator adds `due=` and `pri=`, the desk adds `appr=OK`; each hop checks the line it sends against the line it heard. |
| `--relay --drop` | The desk drops `apref=` when it forwards. The check at that hop refuses, naming the slot. Nothing reaches the payer. |
| `--prose` | The same instruction as three paragraphs of prose, each hop rewording the last, with token counts side by side against the line. |
| `--all` | Every scene in order with a heading each: clean, draft-fault, tool-fault, relay, relay with drop, prose. |

The pay profile closes the set of agents that may speak (`scheduler`, `payer`, `coordinator`, `desk`, `auditor`,
`reconciler`, `extractor`, `human`). That closure is itself a point if a CTO asks: an agent the profile does not
name cannot speak on the frequency.

## Recommended order for a 15-minute slot

1. `--clean` (about 3 minutes). Establish the shape: one line, one readback, one clearance, one done report.
2. `--draft-fault` (1 minute). The first boundary: the line against the record, before it goes.
3. `--tool-fault` (2 minutes). The second boundary: the tool's statement against the plan, before it commits.
4. `--relay` then `--relay --drop` (3 minutes). The graph: every edge checked, and one edge refusing.
5. `--prose` (optional, 2 minutes). Contrast, if there is time. Skip it if the room is running long; the point has
   been made by then.

Run each scene as its own command so the terminal is clean between them. `--all` is for the green room and the
transcript, not for the stage.

## What to say over each scene

Radio voice: short, declarative, no hedging. The caption under each line does the explaining; the speaker does
the framing.

**Scene 1, clean.** "Cleared to land two seven left. I read it back because the error lives at the boundary and the
act is irreversible. Here is the same thing between three agents and a payment. Watch the line go out, come back
with a digest, and only then: cleared."

Over the tool's statement: "The tool sets the altitude in the window and says the number out loud. It has not
done anything yet."

Over `check-dn`: "After the act, the report says what the tool did, not what we meant. Checked against the plan.
Roger. Wilco."

**Scene 2, draft fault.** "Same job, typed by hand this time. Two digits swapped. The check at the boundary refuses
it before it leaves the scheduler. Nobody downstream ever hears it."

**Scene 3, tool fault.** "The line was right. The tool looked up the account and found a lookalike. It says so,
because it has to state what it will do before it does it. The other pilot checks the window. Not cleared. Nothing
is paid."

**Scene 4, relay.** "In practice the job passes through more hands. Each hop adds something and forwards. Each hop
checks the line it sends against the line it heard. The graph's edges, each one checked."

Over `--drop`: "Now the desk loses the approval reference on the way through. Its own check names the slot. The
error is caught on the edge where it happened, and only that edge."

**Scene 5, prose.** "This is how agents actually write to each other. Three paragraphs, three paraphrases. Hop
three quietly lost the approval reference and nothing can say so, because nothing has a slot. Four hundred tokens
against fifty, and the fifty can be checked."

## Fallback

If the live run cannot happen (no terminal, no projector, no power), show the transcript:

```
python3 examples/talk_demo.py --all --pace 0 --no-color > examples/talk_demo.txt
```

`examples/talk_demo.txt` is that file, generated from this version of the script. It is the whole `--all` run,
100 columns wide, plain text; open it in any viewer with a large font and scroll with the talk. The digests in it
are real, and the token in `x_tok=` is whatever the run drew.
