---
name: rogerwilco
description: Typed one-line messages for handing work between agents, reading a handoff back, asking bounded questions, and reporting done, unable or failed. Use whenever you hand work to another agent or subagent, receive a message starting with RW1, or need a receipt for what was agreed between agents.
---

# rogerwilco

Roger: received. Wilco: understood and will comply. Agents hand work to each other in one typed line instead of a paragraph, and the receiver proves both before it owns the work. Facts go in slots, reasoning goes in the tail, and the receiver reads the line back before it owns the work. Full spec: `references/SPEC.md`.

## The discipline comes first

Seven rules carry most of the value, and a team can adopt them in plain English before it adopts the syntax. In a 23-run study, prose written under these rules cut inter-agent traffic to a third of free prose and the principal's reading to 40%; the line syntax matched that and added verification.

1. **Facts once, in a fixed shape.** Each item on its own line with its identifiers, amounts and your decision.
2. **Reasoning by reference.** Anything longer than a short paragraph goes in a file; the message carries the path, not a paraphrase.
3. **State by delta.** Once an item has been reported, mention it again only when something about it changed.
4. **Acknowledge a handoff before you start.** Say what you received and the deadline.
5. **Escalate as a question with a closed list of options.** The item, the amounts, the decision needed, and the answers the human may give. Do not escalate what the policy leaves to you.
6. **Ask, answer, finish.** Bounded questions, direct answers, an explicit done.
7. **No preamble, no recap.**

The lines below are those rules made checkable by code: a validator refuses a malformed message, a closed vocabulary refuses an invented option, a digest proves a handoff arrived intact. Use them wherever a smaller or mixed set of models is doing the work, before an irreversible step, and wherever the log will be read by someone who has to trust it.

## When to use

- You are delegating work to another agent, subagent or role.
- You receive a line that starts with `RW1`.
- You need to ask another agent a question with a bounded answer.
- You are reporting that delegated work is done, that you cannot take it, or that it failed.
- You are escalating a decision to a human with a fixed set of options.

Do not use it for the work itself. Drafts, specs and analysis stay as normal content; the line points at them.

## The line

```
RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] [key=value ...] [// tail]
```

- First three tokens are positional: version `RW1`, the type, your message id: `<yourname>-<n>`, unique in the conversation (`from=writer` sends `writer-1`, `writer-2`, ...; the validator refuses any other shape).
- Everything else is `key=value`, any order. No spaces inside values. Lists join with `+`. Dates are `YYYYMMDD`.
- ` // ` starts the tail: free text, 300 characters max. Longer content becomes an artifact you reference with `art=`.
- `item` is a reference to the thing under discussion: `gh:owner/repo#42`, `pensive:4102`, `url:...`, `file:...`, `sha256:...`.
- `to=human` escalates to the human principal.

## Eight types

| Type | Use | Required |
|---|---|---|
| `HO` | hand work over | `from to item ask` |
| `RB` | read a handoff back: what you received and what you understood | `re from to item ask`, `due` if the HO had one, every slot the HO names in `rb=`, and `acc` when the HO says `rb=acc` or `rb=plan` (`do` too for `plan`) |
| `AQ` | ask a bounded question | `from to need` and `opts` when `need=ENUM` |
| `AN` | answer | `re from to val` |
| `ST` | report a state change, no handover | `from to item` |
| `DN` | done | `re from to item out` |
| `UN` | unable, will not take it | `re from to why` |
| `FL` | took it and it failed | `re from to item why` |

Optional slots: `rb` readback level on an HO: `echo` (default), `all`, `acc`, `plan`, plus slot names to echo (`rb=acc+pri`) · `keys` on an HO: the constraint keys the sender will check (`keys=len+lang+must+no`), so the receiver reports those dimensions · `acc` acceptance criteria as `key:value` tokens (`len:120w+lang:uk+must:monday-problem+no:em-dash`) · `do` what you will produce · `not` what you exclude · `asm` assumptions you are making · `h` digest of the HO, code-side receivers only · `due` `by` (dates) · `pri` 1–5, 1 highest · `conf` L/M/H · `keep` agents staying involved · `art` artifact refs · `ctx` earlier message ids · `eta` · `pct` 0–100 · `blk` blockers · `alt` alternative agent · `next` suggested next ask · `retry` Y/N.

## Codes

- `ask`: `REVIEW` `DRAFT` `DECIDE` `RESEARCH` `BUILD` `FIX` `SUMM` `PLAN` `TEST` `EXTRACT`
- `why`: `NOCAP` no capability · `NOCTX` missing context · `PERM` not permitted · `BUSY` · `CONFLICT` owned elsewhere · `DUP` · `VER` bad version · `UNK` unknown code · `SCOPE` · `ERR` · `TIMEOUT`
- `out`: `OK` `PARTIAL` `NOOP`
- `need`: `ENUM` `TEXT` `NUM` `DATE` `YESNO`. For `TEXT`, reply `val=tail` and put the answer in the tail.

- `acc` keys, a closed set: `len` (unit suffix: `120w` words, `800c` chars, `2p` pages, `10s` slides) · `fmt` (`md` `docx` `json` `csv` `html`) · `lang` (`uk` `us` `fr`) · `tone` (`plain` `formal` `casual` `technical`) · `voice` (`we` `i` `you` `third`) · `aud` · `out` (`copy` `spec` `dataset` `pr` `report`) · `by` (date) · `src` · `scope` · `must` · `no`. `must`, `no`, `scope` and `src` may repeat. For `must` and `no` values, use the brief's own words, hyphenated, no spaces (`must:monday-problem`, `no:em-dash`). Do not invent keys; a key outside the set is not compared.

A profile adds domain codes and slots; a message using one carries `p=<profile>`. Profiles live in `profiles/`. Without `p=`, only the codes above are valid. A profile may close the answer vocabulary with an `ans` enum (the pay profile has `APPROVE DECLINE HOLD REJECT CALLBACK`): then every `AQ need=ENUM` takes its `opts` from it and every `AN val` is one of them, so a human or a policy engine can answer without decoding invented words.

## Five rules

1. **No handover without readback.** Set the level per handoff, not per team: `rb=all` (every slot echoed) before an irreversible act such as releasing a payment, changing a payee or sending anything external; the default envelope echo (`item`, `ask`, `due`) for everything else; `rb=acc` when the instruction lives in a brief. After you send an HO, you still own the item until the receiver's RB passes your check: it echoes `item`, `ask`, `due` and anything you named in `rb=`, with the same decoded values, and if you asked `rb=acc` its `acc=` matches the criteria you wrote down before sending. If it does not pass, re-send the HO with `re=` pointing at the bad RB. No RB by your deadline: re-send with `re=` pointing at the original; a receiver that already read it back replies `UN why=DUP`. When you receive an HO, send the RB before doing anything else, echoing the values exactly as you read them; if you have code, add `h=` from `make-rb`.
   **Readback is comprehension, not recall.** Echoing slots proves you saw them. When the HO says `rb=acc` or `rb=plan`, read the brief and any `art=` it points at, derive the acceptance criteria yourself, and send them as `acc=` (`len:120w+tone:plain+no:em-dash+must:monday-problem`); add `do=` for `plan`; put anything you are excluding in `not=` and anything the brief left open in `asm=`; paraphrase the task in the tail. The sender compares your `acc=` by key with criteria it kept to itself: a different value is a contradiction and a missing key is a gap, both fail the readback; an extra key is an assumption the sender will confirm. When you send an HO whose instruction lives in the tail or an artifact, ask for `rb=acc`, name the keys you will check with `keys=` (dimensions only, never the values), and write your criteria down first using the closed key set.
2. **Never guess.** Unknown version, type or code: reply `UN why=UNK` (or `why=VER`) and name the code in the tail. `UNK` describes the message; do not substitute `NOCAP` or `SCOPE`, which describe you. An AQ always gets an AN (or a UN); never leave a question unanswered because you are busy.
3. **Every reply carries `re=`.** RB, AN, DN, UN, FL always. Reconstruct threads from ids, not from position.
4. **Facts in slots, reasoning in the tail.** If a fact has a slot, it goes in the slot. Tail is 300 characters max.
5. **One message, two forms.** The line and its JSON twin are equivalent (see SPEC §6). Use whichever your side handles better; the codec maps between them.

## Worked exchange

```
RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 conf=M keep=research // hero copy, 120 words, no em dashes
RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 h=c40bba4360dc
RW1 AQ writer-02 re=research-01 from=writer to=research item=gh:crox/site#42 need=ENUM opts=formal+plain+punchy // tone?
RW1 AN research-02 re=writer-02 from=research to=writer val=plain
RW1 DN writer-03 re=research-01 from=writer to=research item=gh:crox/site#42 out=OK art=sha256:9f3e1c // v1, 118 words
```

Comprehension readback (sender asked `rb=acc` and kept `len:120w+tone:plain+no:em-dash+must:monday-problem`):

```
RW1 HO research-03 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 rb=acc keys=len+tone+must+no art=url:https://example.com/brief // hero copy, 120 words, plain tone, no em dashes, must name the reader's Monday problem
RW1 RB writer-05 re=research-03 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 acc=len:120w+tone:plain+must:monday-problem+no:em-dash do=copy // landing hero, 120 words, plain, lead with the Monday problem
```

Refusing: `RW1 UN writer-04 re=research-01 from=writer to=research item=gh:crox/site#42 why=NOCTX alt=copywriter // no style guide on file`

Escalating: `RW1 AQ triage-09 from=triage to=human item=pensive:4664 need=ENUM opts=RETIRE+ACTIVATE+PARK by=20261005 // stale 15d; default PARK`

## Validate when you can

If you have a shell, check every line you send or receive:

```
python3 scripts/rogerwilco.py validate "RW1 HO a-1 from=a to=b item=x:1 ask=DRAFT"
python3 scripts/rogerwilco.py make-rb "<HO line>" <your-id> [--acc "k:v+k:v" --do copy]   # readback with h= digest
python3 scripts/rogerwilco.py check-rb "<HO line>" "<RB line>" [--expect-acc "k:v+k:v"]    # sender side: receipt, integrity, echo, comprehension
python3 scripts/rogerwilco.py to-json "<line>"  |  from-json '<json>'
python3 scripts/rogerwilco.py legend [--profile pay] [--lean]      # legend for another agent's prompt; --lean drops the comprehension-readback keys (about 1,000 tokens with the pay profile)
```

If you have no shell, read the line against the table above and apply rule 2.

## Giving it to another agent

Put the output of `legend` (or this file) in the other agent's system prompt. That is all the other side needs; it does not have to install anything.
