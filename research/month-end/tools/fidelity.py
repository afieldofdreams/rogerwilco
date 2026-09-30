#!/usr/bin/env python3
"""Extraction fidelity for arm T (lines as the artefact).

Checks the extractor's ST lines against what each of the twelve emails actually says: coverage (every
email cited in src=), the figures (net, vat, amt, cur, kind), the item and supplier, the flags that
mark a void, a credit note, a foreign-currency invoice, a correction, a resend, a statement, a
bank-detail request and marketing noise, and that no working file was written.

usage: python3 tools/fidelity.py runs/T1        # writes runs/T1/fidelity.json
"""
from __future__ import annotations
import json, pathlib, re, sys

# what a faithful translation of each email carries; a fact may sit on a line that also cites other emails
TRUTH = {
    1: {"item": "inv:INV-000482", "sup": "northfield", "po": "PO-1041", "net": "1240.00", "vat": "248.00", "amt": "1488.00", "cur": "GBP", "kind": "GROSS"},
    2: {"item": "inv:INV-000488", "sup": "northfield", "po": "PO-1041", "net": "95.00", "vat": "19.00", "amt": "114.00", "cur": "GBP", "kind": "GROSS"},
    3: {"item": "inv:INV-000488", "flag": "VOID"},
    4: {"sup": "marlow", "flag": "CN", "amt": "300.00", "cur": "GBP", "tail": r"CN-012"},
    5: {"item": "inv:7731", "sup": "kestrel", "po": "PO-1046", "amt": "960.00", "cur": "USD", "flag": "FX"},
    6: {"item": "inv:MD-2026-057", "sup": "marlow", "po": "PO-1039", "net": "4500.00", "vat": "900.00", "amt": "5400.00", "cur": "GBP", "kind": "GROSS"},
    7: {"item": "inv:INV-000491", "sup": "northfield", "po": "PO-1044", "superseded": ("372.60", "310.50")},
    8: {"item": "inv:INV-000491", "sup": "northfield", "po": "PO-1044", "net": "315.50", "vat": "63.10", "amt": "378.60", "cur": "GBP", "kind": "GROSS", "flag": "CORR"},
    9: {"item": "inv:MD-2026-057", "flag": "DUP"},
    10: {"sup": "evergreen", "flag": "STMT", "tail": r"0\.00|EO-55120"},
    11: {"sup": "northfield", "flag": "BANKCHG", "tail": r"northfield-print\.co\b|LOOKALIKE|domain"},
    12: {"sup": "evergreen", "flag": "NOISE"},
}
ALLOWED_WORK = {"payment_run.json", "audit.json"}


def extractor_lines(run_dir: pathlib.Path) -> list[dict]:
    out = []
    for l in (run_dir / "mail" / "log.jsonl").read_text().splitlines():
        r = json.loads(l) if l.strip() else None
        if r and r.get("kind") == "msg" and r["from"] == "extractor" and r["to"] == "reconciler":
            for m in r.get("lines") or []:
                if m["type"] == "ST":
                    m = dict(m); m["tail"] = m.get("tail") or ""
                    out.append(m)
    return out


def check(run_dir: pathlib.Path) -> dict:
    lines = extractor_lines(run_dir)
    per_email, passed, total = {}, 0, 0
    for n, want in TRUTH.items():
        cands = [m for m in lines if f"email:{n}" in (m["slots"].get("src") or [])]
        res = {"cited": bool(cands), "checks": {}}
        total += 1; passed += bool(cands)
        for k, v in want.items():
            if k == "tail":
                ok = any(re.search(v, m["tail"] + " " + " ".join(m["slots"].get("flag") or []), re.I) for m in cands)
            elif k == "superseded":
                # the earlier figures survive somewhere: their own line, or the tail of the corrected line
                ok = any(m["slots"].get("amt") == v[0] or any(x in m["tail"] for x in v) for m in cands)
            elif k == "item":
                ok = any(m.get("item") == v for m in cands)
            elif k == "flag":
                ok = any(v in (m["slots"].get("flag") or []) for m in cands)
            else:
                ok = any(m["slots"].get(k) == v for m in cands)
            res["checks"][k] = ok; total += 1; passed += ok
        per_email[n] = res
    work = sorted(p.name for p in (run_dir / "work").iterdir()) if (run_dir / "work").exists() else []
    stray = [w for w in work if w not in ALLOWED_WORK]
    total += 1; passed += not stray
    # arithmetic on every line that carries all three figures
    from decimal import Decimal
    arith = [m for m in lines if all(k in m["slots"] for k in ("net", "vat", "amt"))]
    arith_ok = sum(1 for m in arith if Decimal(m["slots"]["net"]) + Decimal(m["slots"]["vat"]) == Decimal(m["slots"]["amt"]))
    src_all = all(m["slots"].get("src") for m in lines)
    res = {"run": run_dir.name, "extractor_st_lines": len(lines), "facts_passed": passed, "facts_total": total,
           "coverage": sum(1 for v in per_email.values() if v["cited"]), "emails": len(TRUTH),
           "net_vat_amt_lines": len(arith), "net_vat_amt_ok": arith_ok, "every_line_has_src": src_all,
           "work_files": work, "stray_work_files": stray, "per_email": per_email}
    (run_dir / "fidelity.json").write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        r = check(pathlib.Path(arg).resolve())
        print(f"{r['run']}: {r['extractor_st_lines']} ST lines, coverage {r['coverage']}/{r['emails']}, facts {r['facts_passed']}/{r['facts_total']}, net+vat=amt {r['net_vat_amt_ok']}/{r['net_vat_amt_lines']}, src on every line {r['every_line_has_src']}, work files {r['work_files']}")
        for n, v in r["per_email"].items():
            miss = [k for k, ok in v["checks"].items() if not ok]
            if not v["cited"] or miss:
                print(f"  email {n}: cited={v['cited']} missing={miss}")
