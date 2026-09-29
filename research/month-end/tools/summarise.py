#!/usr/bin/env python3
"""Aggregate the graded runs into results/summary.json and a markdown table."""
from __future__ import annotations
import json, pathlib, re, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = sorted((ROOT / "runs").glob("*[0-9]"))
ARMS = {"A": "prose", "P": "PACT-style prose", "L": "rogerwilco lines", "R": "lines, full readback"}


def sendbacks(run_dir: pathlib.Path) -> int:
    log = [json.loads(l) for l in (run_dir / "mail" / "log.jsonl").read_text().splitlines() if l.strip()]
    n = 0
    for r in log:
        if r.get("kind") == "msg" and r["from"] == "auditor" and r["to"] == "scheduler" and re.search(r"\bFAIL\b|ask=FIX", r["body"]):
            n += 1
    return n


def main() -> None:
    rows = []
    for rd in RUNS:
        g = json.loads((rd / "grade.json").read_text())
        leg = json.loads((rd / "legibility_score.json").read_text()) if (rd / "legibility_score.json").exists() else {}
        t, e, o = g["tokens"], g["escalation"], g["outcome"]
        rows.append({
            "run": rd.name, "arm": g["arm"],
            "outcome": f"{o['_core_passed']}/{o['_core_total']}", "audit_pass": o["P11_audit_pass"],
            "recall": e["recall"], "precision": e["precision"], "false_alarms": e["false_alarms"], "redundant": e["redundant"],
            "inter_agent_tokens": t["inter_agent_tokens"], "inter_agent_msgs": t["inter_agent_msgs"],
            "referenced_artifact_tokens": t["referenced_artifact_tokens"],
            "human_read": e["human_read_tokens"], "human_decisions": e["human_read_decision_tokens"],
            "human_final": e["human_read_final_tokens"], "human_info": e["human_read_info_tokens"], "human_msgs": e["human_messages"],
            "from_human": t["from_human_tokens"], "rejected_sends": t["rejected_sends"],
            "sendbacks": sendbacks(rd), "legibility": leg.get("score"),
            "prompt_tokens_extractor": (t.get("prompt_tokens_per_agent") or {}).get("extractor"),
        })
    by_arm = {}
    for arm in ARMS:
        rs = [r for r in rows if r["arm"] == arm]
        if not rs:
            continue
        def m(k): return round(st.mean(r[k] for r in rs), 0)
        def rng(k): return f"{min(r[k] for r in rs)}–{max(r[k] for r in rs)}"
        by_arm[arm] = {
            "name": ARMS[arm], "runs": len(rs),
            "outcome_all_pass": all(r["outcome"].split("/")[0] == r["outcome"].split("/")[1] and r["audit_pass"] for r in rs),
            "recall_mean": round(st.mean(r["recall"] for r in rs), 2), "precision_mean": round(st.mean(r["precision"] for r in rs), 2),
            "false_alarms_total": sum(r["false_alarms"] for r in rs), "redundant_total": sum(r["redundant"] for r in rs),
            "inter_agent_tokens_mean": m("inter_agent_tokens"), "inter_agent_tokens_range": rng("inter_agent_tokens"),
            "inter_agent_msgs_mean": round(st.mean(r["inter_agent_msgs"] for r in rs), 1),
            "referenced_artifact_tokens_mean": m("referenced_artifact_tokens"),
            "human_read_mean": m("human_read"), "human_read_range": rng("human_read"),
            "human_decisions_mean": m("human_decisions"), "human_final_mean": m("human_final"), "human_info_mean": m("human_info"),
            "human_msgs_mean": round(st.mean(r["human_msgs"] for r in rs), 1),
            "from_human_mean": m("from_human"), "rejected_sends_total": sum(r["rejected_sends"] for r in rs),
            "sendbacks_total": sum(r["sendbacks"] for r in rs),
            "legibility_mean": round(st.mean(r["legibility"] for r in rs if r["legibility"] is not None), 2),
            "prompt_tokens_per_agent": rs[0]["prompt_tokens_extractor"],
        }
    base = by_arm["A"]["inter_agent_tokens_mean"]; base_h = by_arm["A"]["human_read_mean"]
    for arm, v in by_arm.items():
        v["inter_agent_vs_prose_pct"] = round(100 * v["inter_agent_tokens_mean"] / base)
        v["human_read_vs_prose_pct"] = round(100 * v["human_read_mean"] / base_h)
    out = {"runs": rows, "by_arm": by_arm}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=1))
    # markdown table
    lines = ["| arm | runs | outcome | escalation recall / precision | false / redundant | inter-agent msg tokens (mean, range) | msgs | human read (mean, range) | decisions | final | readbacks etc | send-backs | legibility | prompt/agent |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, v in by_arm.items():
        lines.append(f"| {arm} {v['name']} | {v['runs']} | {'all 11/11, PASS' if v['outcome_all_pass'] else 'see runs'} | {v['recall_mean']} / {v['precision_mean']} | {v['false_alarms_total']} / {v['redundant_total']} | {int(v['inter_agent_tokens_mean'])} ({v['inter_agent_tokens_range']}) | {v['inter_agent_msgs_mean']} | {int(v['human_read_mean'])} ({v['human_read_range']}) | {int(v['human_decisions_mean'])} | {int(v['human_final_mean'])} | {int(v['human_info_mean'])} | {v['sendbacks_total']} | {v['legibility_mean']}/8 | {v['prompt_tokens_per_agent']} |")
    (ROOT / "results" / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print()
    for r in rows:
        print(f"{r['run']}: msgs {r['inter_agent_tokens']} ({r['inter_agent_msgs']}), human {r['human_read']} = {r['human_decisions']}+{r['human_final']}+{r['human_info']}, artifacts {r['referenced_artifact_tokens']}, sendbacks {r['sendbacks']}, rejected {r['rejected_sends']}, legibility {r['legibility']}")


if __name__ == "__main__":
    main()
