#!/usr/bin/env python3
"""Aggregate the graded runs into results/summary.json and results/summary.md."""
from __future__ import annotations
import json, pathlib, re, statistics as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUNS = sorted(p for p in (ROOT / "runs").iterdir() if (p / "grade.json").exists())
ARMS = {"A": "prose", "P": "PACT-style prose", "D": "disciplined prose", "L": "rogerwilco lines", "R": "lines, full readback",
        "D-haiku": "disciplined prose, Haiku agents", "L-haiku": "lines, Haiku agents", "A-s2": "prose, adversarial", "D-s2": "disciplined prose, adversarial", "L-s2": "lines, adversarial"}
USAGE = json.loads((ROOT / "results" / "agent_usage.json").read_text())["runs"] if (ROOT / "results" / "agent_usage.json").exists() else {}


def group_of(cfg: dict) -> str:
    g = cfg["arm"]
    if cfg.get("model") == "haiku":
        g += "-haiku"
    if cfg.get("scenario") == 2:
        g += "-s2"
    return g


def _log(run_dir: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in (run_dir / "mail" / "log.jsonl").read_text().splitlines() if l.strip()]


def sendbacks(run_dir: pathlib.Path) -> int:
    return sum(1 for r in _log(run_dir) if r.get("kind") == "msg" and r["from"] == "auditor" and r["to"] == "scheduler" and re.search(r"\bFAIL\b|ask=FIX", r["body"]))


def harness_bug_rejections(run_dir: pathlib.Path) -> int:
    return sum(1 for r in _log(run_dir) if r.get("kind") == "rejected" and any("could not parse" in e for e in r.get("errors", [])))


def main() -> None:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
    except Exception:  # noqa: BLE001
        enc = None
    rows = []
    for rd in RUNS:
        g = json.loads((rd / "grade.json").read_text())
        cfg = json.loads((rd / "run.json").read_text())
        leg = json.loads((rd / "legibility_score.json").read_text()) if (rd / "legibility_score.json").exists() else {}
        t, e, o = g["tokens"], g["escalation"], g["outcome"]
        pr = rd / "work" / "payment_run.json"
        final_artifact = len(enc.encode(pr.read_text())) if (enc and pr.exists()) else 0
        usage = USAGE.get(rd.name, {})
        rows.append({
            "run": rd.name, "arm": group_of(cfg), "base_arm": g["arm"], "scenario": cfg.get("scenario", 1), "model": cfg.get("model", "sonnet"),
            "outcome": f"{o['_core_passed']}/{o['_core_total']}", "outcome_ok": o["_core_passed"] == o["_core_total"] and o["P11_audit_pass"], "audit_pass": o["P11_audit_pass"],
            "recall": e["recall"], "precision": e["precision"], "false_alarms": e["false_alarms"], "redundant": e["redundant"],
            "inter_agent_tokens": t["inter_agent_tokens"], "inter_agent_msgs": t["inter_agent_msgs"],
            "referenced_artifact_tokens": t["referenced_artifact_tokens"],
            "human_read": e["human_read_tokens"], "human_decisions": e["human_read_decision_tokens"],
            "human_final": e["human_read_final_tokens"], "human_info": e["human_read_info_tokens"], "human_msgs": e["human_messages"],
            "final_artifact_tokens": final_artifact, "human_read_incl_artifact": e["human_read_tokens"] + final_artifact,
            "from_human": t["from_human_tokens"], "rejected_sends": t["rejected_sends"], "rejected_harness_bug": harness_bug_rejections(rd),
            "sendbacks": sendbacks(rd), "legibility": leg.get("score"), "legibility_of": leg.get("of"),
            "agent_first_turn_tokens": usage.get("total_first_turn"),
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
            "name": ARMS[arm], "runs": len(rs), "outcome_runs": [r["outcome"] for r in rs],
            "outcome_all_pass": all(r["outcome_ok"] for r in rs),
            "recall_mean": round(st.mean(r["recall"] for r in rs), 2), "precision_mean": round(st.mean(r["precision"] or 0 for r in rs), 2),
            "false_alarms_total": sum(r["false_alarms"] for r in rs), "redundant_total": sum(r["redundant"] for r in rs),
            "inter_agent_tokens_mean": m("inter_agent_tokens"), "inter_agent_tokens_range": rng("inter_agent_tokens"),
            "inter_agent_msgs_mean": round(st.mean(r["inter_agent_msgs"] for r in rs), 1),
            "referenced_artifact_tokens_mean": m("referenced_artifact_tokens"),
            "human_read_mean": m("human_read"), "human_read_range": rng("human_read"),
            "human_decisions_mean": m("human_decisions"), "human_final_mean": m("human_final"), "human_info_mean": m("human_info"),
            "human_msgs_mean": round(st.mean(r["human_msgs"] for r in rs), 1),
            "human_read_incl_artifact_mean": m("human_read_incl_artifact"),
            "from_human_mean": m("from_human"),
            "rejected_sends_total": sum(r["rejected_sends"] for r in rs),
            "rejected_agent_errors_total": sum(r["rejected_sends"] - r["rejected_harness_bug"] for r in rs),
            "sendbacks_total": sum(r["sendbacks"] for r in rs),
            "legibility_mean": round(st.mean(r["legibility"] / r["legibility_of"] for r in rs if r["legibility"] is not None), 2),
            "agent_first_turn_tokens_mean": round(st.mean(r["agent_first_turn_tokens"] for r in rs if r["agent_first_turn_tokens"]), 0) if any(r["agent_first_turn_tokens"] for r in rs) else None,
            "prompt_tokens_per_agent": rs[0]["prompt_tokens_extractor"],
        }
    base = by_arm["A"]
    for arm, v in by_arm.items():
        v["inter_agent_vs_prose_pct"] = round(100 * v["inter_agent_tokens_mean"] / base["inter_agent_tokens_mean"])
        v["human_read_vs_prose_pct"] = round(100 * v["human_read_mean"] / base["human_read_mean"])
        v["human_read_incl_artifact_vs_prose_pct"] = round(100 * v["human_read_incl_artifact_mean"] / base["human_read_incl_artifact_mean"])
    out = {"runs": rows, "by_arm": by_arm}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=1))
    lines = ["| arm | runs | outcome | recall / precision | false / redundant | msg tokens (mean, range) | msgs | human read (mean, range) | decisions | final | readbacks | incl. run file | agent first-turn tokens | send-backs | rejected (agent errors) | legibility | prompt/agent |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, v in by_arm.items():
        lines.append(f"| {arm} {v['name']} | {v['runs']} | {'all pass' if v['outcome_all_pass'] else ' / '.join(v['outcome_runs'])} | {v['recall_mean']} / {v['precision_mean']} | {v['false_alarms_total']} / {v['redundant_total']} | {int(v['inter_agent_tokens_mean'])} ({v['inter_agent_tokens_range']}) | {v['inter_agent_msgs_mean']} | {int(v['human_read_mean'])} ({v['human_read_range']}) | {int(v['human_decisions_mean'])} | {int(v['human_final_mean'])} | {int(v['human_info_mean'])} | {int(v['human_read_incl_artifact_mean'])} | {v['agent_first_turn_tokens_mean']} | {v['sendbacks_total']} | {v['rejected_agent_errors_total']} | {v['legibility_mean']} | {v['prompt_tokens_per_agent']} |")
    (ROOT / "results" / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print()
    for r in rows:
        print(f"{r['run']}: {r['outcome']} msgs {r['inter_agent_tokens']} ({r['inter_agent_msgs']}), human {r['human_read']} = {r['human_decisions']}+{r['human_final']}+{r['human_info']} (+{r['final_artifact_tokens']} run file), artifacts {r['referenced_artifact_tokens']}, first-turn {r['agent_first_turn_tokens']}, sendbacks {r['sendbacks']}, rejected {r['rejected_sends']} (bug {r['rejected_harness_bug']}), legibility {r['legibility']}/{r['legibility_of']}, recall {r['recall']} prec {r['precision']} false {r['false_alarms']} red {r['redundant']}")


if __name__ == "__main__":
    main()
