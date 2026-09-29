"""Task 3: token cost and programmatic round-trip fidelity."""
import json, random, statistics as st
import tiktoken
from formcore.codec import Schema, encode, decode, validate, delta, FormError, encode_tight, decode_tight, tight_legend
from formcore.render import english, as_json, glyph, glyph_legend
from formcore import synth

S = Schema.load("schemas/pform.json")
ENCS = {"o200k": tiktoken.get_encoding("o200k_base"), "cl100k": tiktoken.get_encoding("cl100k_base")}
data = synth.make(240)
json.dump(data, open("data/handoffs.json", "w"), indent=1)

def clean(d): return {k: v for k, v in d.items() if not k.startswith("_")}

rows = []
for d in data:
    c = clean(d)
    r = {"id": d["_id"], "english": english(S, c, seed=d["_id"]), "json": as_json(S, c),
         "pform": encode(S, "HO", c), "tight": encode_tight(S, "HO", c), "glyph": glyph(S, c)}
    rows.append(r)
json.dump(rows, open("data/renderings.json", "w"), indent=1, ensure_ascii=False)

res = {"n": len(rows), "tokens": {}}
for en, enc in ENCS.items():
    t = {}
    for fmt in ["english", "json", "pform", "tight", "glyph"]:
        counts = [len(enc.encode(r[fmt])) for r in rows]
        t[fmt] = {"mean": round(st.mean(counts), 1), "median": st.median(counts), "total": sum(counts)}
    for fmt in ["json", "pform", "tight", "glyph"]:
        t[fmt]["vs_english_pct"] = round(100 * (1 - t[fmt]["total"] / t["english"]["total"]), 1)
    legend_pf = len(enc.encode(S.legend()))
    legend_gl = legend_pf + len(enc.encode(glyph_legend()))
    legend_ti = len(enc.encode(tight_legend(S)))
    t["legend_tokens"] = {"pform": legend_pf, "tight": legend_ti, "glyph": legend_gl}
    t["breakeven_msgs_tight"] = round(legend_ti / (t["english"]["mean"] - t["tight"]["mean"]), 1)
    saving = t["english"]["mean"] - t["pform"]["mean"]
    t["breakeven_msgs_pform"] = round(legend_pf / saving, 1)
    res["tokens"][en] = t

# round-trip
ok = 0; fails = []
for d in data:
    c = clean(d)
    code, back = decode(S, encode(S, "HO", c))
    if back == c: ok += 1
    else: fails.append((c, back))
res["roundtrip"] = {"exact": ok, "of": len(data)}
tok = 0
for d in data:
    c = clean(d)
    for chk in (False, True):
        _, back = decode_tight(S, encode_tight(S, "HO", c, check=chk))
        tok += (back == c)
res["roundtrip_tight"] = {"exact": tok, "of": 2 * len(data)}

# corruption rejection (sanity check, not a headline metric)
rng = random.Random(1)
mut_caught = 0; mut_total = 0; silent = []
def mutate(line):
    segs = line.split("|")
    kind = rng.choice(["drop", "badenum", "badint", "unknownkey", "truncate", "dupe"])
    i = rng.randrange(1, len(segs))
    if kind == "drop": segs.pop(i)
    elif kind == "badenum": segs = [s.replace("conf=", "conf=X") if s.startswith("conf=") else s for s in segs]
    elif kind == "badint": segs = [s.replace("imp=", "imp=1") if s.startswith("imp=") else s for s in segs]
    elif kind == "unknownkey": segs.insert(i, "zzz=1")
    elif kind == "truncate": return "|".join(segs)[: max(3, len("|".join(segs)) // 2)], kind
    elif kind == "dupe": segs.insert(i, segs[i])
    return "|".join(segs), kind
for d in data:
    line = encode(S, "HO", clean(d))
    for _ in range(3):
        m, kind = mutate(line)
        if m == line: continue
        mut_total += 1
        if validate(S, m): mut_caught += 1
        else:
            _, back = decode(S, m)
            silent.append({"kind": kind, "changed_fields": sorted(set(clean(d)) ^ set(back) | {k for k in back if back.get(k) != clean(d).get(k)})})
kinds = {}
for s_ in silent: kinds[s_["kind"]] = kinds.get(s_["kind"], 0) + 1
# tight-form corruption, with and without checksum
def tmut(line):
    body = line
    toks = body.split(" ")
    kind = rng.choice(["drop", "swapval", "digit", "insert"])
    i = rng.randrange(1, len(toks))
    if kind == "drop": toks.pop(i)
    elif kind == "insert": toks.insert(i, "-")
    elif kind == "swapval":
        j = rng.randrange(1, len(toks)); toks[i], toks[j] = toks[j], toks[i]
    elif kind == "digit":
        cand = [k for k, t in enumerate(toks) if any(ch.isdigit() for ch in t)]
        k = rng.choice(cand); t = toks[k]; pos = [q for q, ch in enumerate(t) if ch.isdigit()][0]
        toks[k] = t[:pos] + str((int(t[pos]) + 1) % 10) + t[pos+1:]
    return " ".join(toks), kind
tres = {}
for chk in (False, True):
    tot = caught = 0; silent_kinds = {}
    for d in data:
        c = {k: v for k, v in clean(d).items() if k != "note"}
        line = encode_tight(S, "HO", c, check=False)
        for _ in range(3):
            mm, kind = tmut(line)
            if mm == line: continue
            if chk: mm = mm + " #" + encode_tight(S, "HO", c, check=True)[-3:]
            tot += 1
            try:
                _, b = decode_tight(S, mm)
                if b == c: caught += 1  # accepted but unchanged counts as harmless
                else: silent_kinds[kind] = silent_kinds.get(kind, 0) + 1
            except FormError:
                caught += 1
    tres["checksum" if chk else "no_checksum"] = {"mutations": tot, "caught_or_harmless": caught, "silent_wrong": tot - caught, "silent_by_kind": silent_kinds}
res["tight_corruption"] = tres
res["corruption"] = {"mutations": mut_total, "rejected": mut_caught, "accepted_silently": len(silent), "silent_by_kind": kinds}

# delta encoding on a repeated state read
d0 = clean(data[0]); d1 = dict(d0); d1["stall_days"] = (d0.get("stall_days") or 0) + 1; d1["stage"] = "DEC"
enc = ENCS["o200k"]
res["delta_example"] = {"full": encode(S, "HO", d1), "delta": delta(S, "HO", d0, d1),
                        "full_tokens": len(enc.encode(encode(S, "HO", d1))), "delta_tokens": len(enc.encode(delta(S, "HO", d0, d1)))}
res["example"] = rows[3]
res["example_tight_check"] = encode_tight(S, "HO", clean(data[3]), check=True)
json.dump(res, open("results/measure.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(res, indent=1, ensure_ascii=False))
