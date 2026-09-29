# rogerwilco protocol, version RW1 (v0.1)

A one-line, typed, closed-vocabulary message format for handing work between agents and asking them bounded questions. Any agent that can read a line of text can use it. Facts go in slots. Reasoning goes in the tail.

Status: draft v0.1, 28 September 2026. Author: Adam Field, Croxio Ltd. Licence: MIT.

## 1. Design goals

1. One line of text, so a message travels over any channel: a chat turn, an MCP tool result, an A2A message part, an HTTP body, a Slack post, a log file, a comment on a record.
2. Readable by a model from a short legend alone, with no library on the receiving side.
3. Validatable in code where code exists.
4. Closed vocabulary. Unknown codes are refused, never guessed.
5. Domain-agnostic core; domain vocabulary lives in profiles.

## 2. Wire format

```
RW1 <TYPE> <id> [re=<id>] from=<agent> to=<agent> [item=<ref>] [<key>=<value> ...] [// <tail>]
```

Tokens are separated by single spaces. The first three are positional; everything after is keyed. Order of keyed slots is free; the recommended order is `re from to item` then type slots.

| Element | Rule |
|---|---|
| `RW1` | Protocol version token. Required, always first. |
| `TYPE` | One of the eight message types in section 3. Uppercase. |
| `id` | Message id: `<from>-<n>`, the sending agent's name, a hyphen and a number, e.g. `writer-07`, unique within the conversation. The validator refuses any other shape, so a receiver can tell who a message came from and which of theirs it is from the id alone. |
| `key=value` | Keys are lowercase `[a-z][a-z0-9_]*`. Values contain no spaces. Lists join with `+`. Dates are `YYYYMMDD`. Booleans are `Y` or `N`. |
| `// tail` | Free text after ` // `. At most 300 characters. Anything longer becomes an artifact and is referenced with `art=`. |

Extension keys begin with `x_` and may carry anything a profile has not defined. A receiver ignores keys it does not know unless the key is required by the type; it must refuse unknown enum values (section 5, rule 2).

### 2.1 References

`item`, `art` and `ctx` carry references. A reference is any token without whitespace. The recommended shape is `<namespace>:<id>`:

- `gh:owner/repo#42`, `jira:ABC-12`, `pensive:4102`, `notion:<id>`
- `url:https://example.com/x`
- `file:path/to/thing.md`
- `sha256:<hex>` for a content-addressed artifact
- `msg:<id>` for another rogerwilco message

### 2.2 Agents

`from` and `to` are agent names: tokens matching `[A-Za-z0-9._-]+`. The name `human` is reserved for the human principal. A message to `human` is how an agent escalates.

## 3. Message types

| Type | Meaning | Required slots | Optional slots |
|---|---|---|---|
| `HO` | Handoff: here is work, do this with it | `from to item ask` | `re due pri conf keep art ctx rb acc` |
| `RB` | Readback: I received the handoff, here is what I understood, and I will act on it | `re from to item ask` (+ `due` if the HO had one, + anything the HO's `rb=` names, + `acc` when the HO asked `rb=acc` or `rb=plan`, + `do` for `rb=plan`) | `h eta not asm` |
| `AQ` | Ask: a bounded question | `from to need` (+ `opts` when `need=ENUM`) | `re item by` |
| `AN` | Answer to an AQ | `re from to val` | `item` |
| `ST` | Status: state changed on an item, no handover | `from to item` | `re pct eta blk` (+ profile state slots) |
| `DN` | Done: the handed-off work is complete | `re from to item out` | `art next` |
| `UN` | Unable: I will not or cannot take this | `re from to why` | `item alt need` |
| `FL` | Fail: I took it and it failed | `re from to item why` | `art retry` |

### 3.1 Slot definitions

| Slot | Type | Meaning |
|---|---|---|
| `re` | msg id | The message this replies to. Threads are rebuilt from `re`, never from position. |
| `item` | ref | The thing under discussion. |
| `ask` | enum `ask` | What the receiver should do. Core set in section 4; profiles extend it. |
| `due` | date | When the work is needed. |
| `by` | date | When an answer is needed. |
| `pri` | int 1–5 | Priority, 1 highest. |
| `conf` | `L` `M` `H` | Sender's confidence in the brief and the state it describes. |
| `keep` | list of agents | Agents that stay involved after the handoff. |
| `art` | list of refs | Artifacts: context on a HO, output on a DN, logs on a FL. |
| `ctx` | list of msg ids | Earlier messages the receiver should read first. |
| `eta` | date | Expected completion. |
| `pct` | int 0–100 | Progress. |
| `blk` | list of refs | Items or messages blocking this one. |
| `need` | enum `need` | Answer shape for an AQ: `ENUM` `TEXT` `NUM` `DATE` `YESNO`. |
| `opts` | list | Allowed values when `need=ENUM`. |
| `val` | value | The answer. For `need=TEXT`, `val=tail` and the answer is the tail. |
| `out` | enum `out` | Outcome of a DN: `OK` `PARTIAL` `NOOP`. |
| `next` | enum `ask` | Suggested next ask. |
| `why` | enum `why` | Reason code on UN or FL. |
| `alt` | agent | Suggested alternative receiver on UN. |
| `retry` | `Y` `N` | Whether a retry is sensible on FL. |
| `keys` | list of constraint keys | On an HO with `rb=acc` or `rb=plan`: the dimensions the sender will check (`keys=len+lang+must+no`). Never carries values. |
| `rb` | list | On an HO: the readback level and any extra slots to echo. Levels: `echo` (default: `item ask due`), `all` (every slot), `acc` (derived acceptance criteria, section 5.2), `plan` (`acc` plus `do`). Slot names add to the echo set: `rb=acc+pri`. |
| `h` | 12 hex chars | On an RB: SHA-256 digest of the HO's canonical JSON form (section 5.1). Produced only by code. |
| `acc` | list of constraints | Acceptance criteria as `key:value` tokens (section 5.2). On an HO: criteria the sender chooses to send. On an RB: criteria the receiver derived from the brief. |
| `do` | token | On an RB: what the receiver will produce (`copy`, `spec`, `dataset`, `pr`). Required when the HO asked `rb=plan`. |
| `not` | list of tokens | On an RB: what the receiver understands to be out of scope. |
| `asm` | list of tokens | On an RB: assumptions the receiver is making that the brief did not settle. |

## 4. Core vocabulary

Profiles may extend any of these lists. They may not redefine a core code.

**ask**: `REVIEW` review against stated criteria · `DRAFT` produce a first version · `DECIDE` choose among options · `RESEARCH` find out · `BUILD` implement · `FIX` repair a named defect · `SUMM` summarise · `PLAN` produce a plan · `TEST` verify · `EXTRACT` pull structured data out

**why**: `NOCAP` no capability · `NOCTX` missing context · `PERM` not permitted · `BUSY` at capacity · `CONFLICT` item owned by another agent · `DUP` duplicate of an open handoff · `VER` unsupported protocol version · `UNK` unknown code in the message · `SCOPE` out of scope · `ERR` runtime error · `TIMEOUT` ran out of time

**out**: `OK` · `PARTIAL` · `NOOP`

**need**: `ENUM` · `TEXT` · `NUM` · `DATE` · `YESNO`

**conf**: `L` · `M` · `H`

## 5. Rules

1. **No handover without readback.** An HO transfers ownership only when the receiver sends an RB that passes the sender's check (section 5.1). Until then the sender owns the item. The sender sets the level per handoff with `rb=`: the default envelope echo (`item`, `ask`, `due`) where a misread is cheap to catch later; `rb=all` where the receiver's next act is irreversible (a payment release, a payee change, anything external), and in that regime every `ST` or `AN` the receiver will act on is echoed back before it acts; `rb=acc` where the instruction lives in a brief. The month-end study measured full readback at 1.6x the traffic of envelope echo with nothing caught in twelve clean runs, which is why the level belongs to the handoff and not to the team. An RB that does not pass is void; the sender re-issues the HO with `re=` pointing at the void RB. The owner of an item is the `to` of the most recent HO that received a passing RB. No RB within the sender's deadline: the sender re-issues the same HO with `re=` pointing at the original; a receiver that already read it back replies `UN why=DUP`, so a retry cannot create two owners.
2. **Never guess.** A receiver that meets an unknown version token, type, or enum value replies `UN why=UNK` (or `why=VER`) naming the offending code in the tail. It does not infer a meaning, and it does not substitute a nearby reason such as `NOCAP` or `SCOPE`: those describe the receiver, `UNK` describes the message. An AQ is answered with an AN or refused with UN; it is never left unanswered because the receiver is busy.
3. **Every reply carries `re=`.** RB, AN, DN, UN and FL always do. Threads are reconstructed from ids.
4. **Facts in slots, reasoning in the tail.** A fact that has a slot goes in the slot, never only in the tail. The tail is at most 300 characters; longer content is an artifact referenced by `art=`.
5. **Two forms, one message.** Every line has a canonical JSON form (section 6). An implementation is conformant when it round-trips the conformance suite in both directions and produces the expected replies.

### 5.1 What a readback proves, and how the sender checks it

"Did you get it" means three different things, and the RB carries all three. In radio terms, tiers 1 and 2 are *roger* (received, intact) and tiers 3 and 4 are *wilco* (understood, will comply); a handoff whose readback passes every tier the sender asked for is wilco, and only then does ownership transfer. The sender verifies them in code (`scripts/rogerwilco.py check-rb`); a model-only sender applies the same checks by reading.

| Tier | Proves | Carried by | Who can produce it |
|---|---|---|---|
| 1 Receipt | A message with this id arrived, and the reply is from the right agent | `re=`, `from`, `to` | anyone |
| 2 Integrity | The receiver holds exactly the message that was sent | `h=` digest of the HO's canonical form | code only |
| 3 Echo | The receiver decoded the envelope the same way the sender encoded it | echo of the readback set, as decoded values | anyone, including model-only receivers |
| 4 Comprehension | The receiver's working picture of the task matches the sender's | `acc=` derived by the receiver from the brief, compared by key with the sender's own criteria | anyone; the check is code on the sender's side |

Tier 3 catches a misread of the envelope: a receiver can hold the right bytes and still read the wrong column. Tier 2 is optional and only meaningful where the receiver runs code, since a model cannot compute a hash.

Tier 3 alone is recall, not comprehension. In ATC the numbers are the instruction, so echoing them verifies the instruction. Between agents the envelope is the address and the instruction lives in the tail and the artifacts, so an echo verifies the wrong thing. Tier 4 is teach-back: the receiver states what it understood in typed form, and the sender checks it against what it meant.

The readback level is set by the sender with `rb=` on the HO: `echo` (default) echoes `item ask due`; `all` echoes every slot, an equality of two decoded messages; `acc` requires the receiver to derive the acceptance criteria and send them as `acc=`; `plan` requires `acc` plus `do`. Slot names add to the echo set (`rb=acc+pri`). Use `all` when the envelope carries the stakes, `acc` or `plan` whenever the instruction lives in prose.

### 5.2 The comprehension check

Before sending an HO with `rb=acc` or `rb=plan`, the sender writes its acceptance criteria as typed constraints and keeps them. That is the challenge. The receiver reads the brief and the artifacts, derives its own criteria, and sends them as `acc=`. The sender compares the two sets by key (`scripts/rogerwilco.py check-rb --expect-acc`):

| Finding | Meaning | Result |
|---|---|---|
| same key, different value (`len:150w` vs `len:120w`) | contradiction: the receiver understood a constraint wrongly | readback fails |
| key in the sender's set, absent from the receiver's | gap: the receiver did not extract a constraint the sender holds | readback fails |
| key only in the receiver's set | assumption: the receiver filled in something the brief left open | noted for the sender to confirm or correct |
| a `not=` token matching a sender `must:` | the receiver excluded something required | readback fails |

The sender may also send `acc=` on the HO. Then the receiver's `acc=` is an echo of typed criteria, which verifies less but is still stronger than an envelope echo, because the receiver has to map each criterion onto the brief to know it is complete. Withholding is the stronger form and costs nothing.

Constraint grammar: `key:value`, no spaces, joined with `+`, compared case-insensitively. Keys are a closed set, because two agents reading the same brief will otherwise name the same fact differently (`lang:uk`, `spelling:uk`, `lang:en-gb` were all produced in testing) and the comparison turns naming variance into false gaps. The core set: `len` (unit suffix: `120w` words, `800c` characters, `2p` pages, `10s` slides), `fmt`, `lang`, `tone`, `voice`, `aud`, `out`, `by`, `src`, `scope`, `must`, `no`. `must`, `no`, `scope` and `src` are set-valued and may repeat; the others are single-valued. A key outside the set is noted and not compared. Profiles may extend the set.

The sender names the dimensions it will check with `keys=` on the HO (`keys=len+lang+must+no`). Dimensions only, never values, so nothing leaks; the receiver then knows which keys to report and a key the sender asked for that the receiver omits is a gap.

Values are compared after normalisation, not as strings: lowercase, punctuation stripped, an alias table (`uk` = `en-gb` = `british`, `md` = `markdown`, `we` = `first-person-plural`). Two values name the same fact when they are equal, one is a prefix of the other, or one's word set contains the other's. Set-valued keys additionally accept a loose match on a shared distinctive word (`regulated-proof` and `regulated-ai`) and report it as a note; single-valued keys never do, so `len:120w` and `len:150w` always contradict. For `must` and `no`, the receiver should use the brief's own words, which is what makes the match reliable.

A receiver's `not=` list is compared as `no:` values.

The check is lossless to the resolution of the criteria the sender typed, and no further. That is the intended limit: it verifies that the two agents hold the same structured picture of the task before work starts, which is the failure that matters between agents. The paraphrase in the RB tail is for a human or model hearback and is not checked by code.

Translation between profiles is the same check in a different vocabulary. A receiver on another profile reads back in its own codes; the sender maps them through a crosswalk and diffs. Where a mapping exists the check is exact; where none exists the diff names what the translation lost, so loss is visible rather than silent.

Comparison is by decoded value, never by string: `pri=2` and `pri=02` are the same fact; `keep=a+b` and `keep=b+a` are not, because list order is significant. A receiver's own additions (`h=`, `eta=`, `asm=`) are not compared except as section 5.2 describes.

Canonical form for the digest: the JSON form of section 6 serialised with keys sorted, no whitespace, UTF-8, lists in written order. `h=` is the first 12 hexadecimal characters of SHA-256 over that string.

No third leg is needed. A passing RB transfers ownership; a failing one is answered by a re-issued HO; a ledger records which happened. That is the controller's silence after a correct readback, made explicit and checked by code rather than by attention.

## 6. JSON form

```json
{"v":"RW1","type":"HO","id":"research-01","re":null,
 "from":"research","to":"writer","item":"gh:crox/site#42",
 "slots":{"ask":"DRAFT","due":"20261002","pri":2,"conf":"M","keep":["research"]},
 "tail":"hero copy, 120 words, no em dashes"}
```

Encoding rules: integers are JSON numbers; lists are JSON arrays; `Y`/`N` are JSON booleans; everything else is a string. `re` and `tail` are `null` when absent. Slot order in the line is not significant.

## 7. Profiles

A profile is a JSON file that extends the core for a domain. It may add enum values to `ask` and `why`, add new enums, add slots (with the types they apply to and whether required), and name agents. It may not remove or redefine anything in the core.

```json
{"profile":"pform","version":"0.1","extends":"RW1",
 "enums":{"stage":{"DIA":"diagnose","REV":"review","OPT":"options","DEC":"decide","ACT":"action","DONE":"done"}},
 "asks":{"SCORE4":"run 4-axis scoring","ENRICH":"fill missing fields","PRUNE":"retire or merge"},
 "slots":[{"key":"stg","type":"enum:stage","on":["HO","ST"],"required":false}],
 "agents":["TRI","STR","ARC","BLD","QAR","CPY","GRD","DAT","MKT","SCT","IDE"]}
```

A message using a profile carries `p=<profile>` as a keyed slot, e.g. `p=pform`. Without `p=`, only core vocabulary is valid.

A profile may also close the answer vocabulary. If it defines an enum `ans`, every `AQ need=ENUM` must draw its `opts` from `ans` and every `AN val` (other than `tail`, `Y`, `N`, a number or a date) must be one of them. Without it, agents invent option words (`OFFRUN`, `KEEPFILE`, `PAY-USD`) and the human, or a policy engine, has to decode each one; the month-end study saw seven different spellings of the same three answers in twelve runs. The pay profile's vocabulary is `APPROVE DECLINE HOLD REJECT CALLBACK`. A profile may list `asks_used`, the core asks its domain needs, so the lean legend omits the rest.

Slots a profile adds may carry `desc`, which the legend prints.

The legend a model needs is generated from the core plus the profile (`scripts/rogerwilco.py legend --profile pay`). `--lean` drops the comprehension-readback keys and the unused core asks for teams that use envelope echo only: about 1,000 tokens with the pay profile against 1,360 for the full legend.

## 8. Exchanges

Handoff, question, completion:

```
RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 pri=2 conf=M keep=research // hero copy, 120 words, no em dashes
RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 h=c40bba4360dc
RW1 AQ writer-02 re=research-01 from=writer to=research item=gh:crox/site#42 need=ENUM opts=formal+plain+punchy // tone?
RW1 AN research-02 re=writer-02 from=research to=writer val=plain
RW1 DN writer-03 re=research-01 from=writer to=research item=gh:crox/site#42 out=OK art=sha256:9f3e1c // v1, 118 words
```

Handoff with a comprehension readback (the sender kept `len:120w+tone:plain+no:em-dash+must:monday-problem` to itself):

```
RW1 HO research-01 from=research to=writer item=gh:crox/site#42 ask=DRAFT due=20261002 rb=acc keys=len+tone+must+no art=url:https://example.com/brief // hero copy for the landing page, 120 words, plain tone, no em dashes, must name the reader's Monday problem
RW1 RB writer-01 re=research-01 from=writer to=research item=gh:crox/site#42 ask=DRAFT due=20261002 acc=len:120w+tone:plain+must:monday-problem+no:em-dash+fmt:md do=copy // landing hero, 120 words, plain, no em dashes, lead with the Monday problem
```

`check-rb --expect-acc` passes and notes `fmt:md` as an assumption to confirm. Had the receiver sent `len:150w`, the readback would fail on a contradiction before any copy was written.

Refusal with an alternative:

```
RW1 UN writer-04 re=research-01 from=writer to=research item=gh:crox/site#42 why=NOCTX alt=copywriter // no style guide on file
```

Escalation to the human principal with an option set:

```
RW1 AQ triage-09 from=triage to=human item=pensive:4664 need=ENUM opts=RETIRE+ACTIVATE+PARK by=20261005 // stale 15d, no owner active; default PARK
```

Void readback and re-issue:

```
RW1 HO ops-03 from=ops to=builder item=jira:OPS-77 ask=FIX due=20261001
RW1 RB builder-05 re=ops-03 from=builder to=ops item=jira:OPS-77 ask=BUILD due=20261001
RW1 HO ops-04 re=builder-05 from=ops to=builder item=jira:OPS-77 ask=FIX due=20261001 // readback mismatch on ask
RW1 RB builder-06 re=ops-04 from=builder to=ops item=jira:OPS-77 ask=FIX due=20261001
```

## 9. Where it sits

rogerwilco is content, not transport. It rides inside an A2A message part, an MCP tool result, a chat turn or a queue message. It does not do discovery, authentication or task lifecycle; the transport or runtime does. It replaces the free text those carry with a line that can be validated, read back and audited.

## 10. Evidence

The format choices come from a 240-message study (September 2026). Keyed form rather than positional because a small model miscounted positional columns in one run of two while reading keyed form at 90–100%. Three-letter codes rather than glyphs because glyph savings were tokenizer-dependent and the legend cost 1.7x more. Readback because the errors observed were misreads of a neighbouring field, which an echo catches at the boundary. The comprehension tier because an envelope echo is recall, and between agents the instruction lives in prose the envelope does not carry. The closed constraint key set and `keys=` because the first end-to-end test (two sender agents, four receiver agents, one brief) showed every receiver understanding the brief while the comparator reported four to ten false gaps from key naming alone; with the closed set and `keys=`, three of four pairs passed clean and the fourth reported one real omission (the receiver had dropped "without naming clients"). In the same test, receivers given a tail that said "short paragraph" and an artifact that said 150 words reported `len:150w`, so a sender who believed 120 words was caught by a contradiction before any work was done. Free text confined to a bounded tail because real agent logs were 50% process narration and 26% narrated field changes.
