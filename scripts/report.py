#!/usr/bin/env python3
"""Summarize completed benchmark samples without copying private source/logs."""
import argparse
import collections
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]


def report(run_id):
    run = ROOT / ".work/runs" / run_id
    rows = []
    for path in sorted(run.glob("*/results.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text().splitlines())
    if not rows:
        raise RuntimeError("No completed samples")
    groups = collections.defaultdict(list)
    failures = []
    for row in rows:
        if row["status"] == "ok":
            groups[(row["project"], row["variant"], row["case"])].append(row)
        else:
            failures.append({key: row.get(key) for key in ["project", "variant", "case", "status", "error", "error_tail"]})
    summary = []
    lines = ["# Build experiment " + run_id, "", "Seconds; cold has one observation per variant. Warm entries are medians, with observed min–max. These are local development builds on a shared host, not production performance claims.", "", "| Project | Backend | Case | n | Build median | Min–max | Feedback median | Cache hits / misses |", "|---|---|---|---:|---:|---:|---:|---:|"]
    for (project, variant, case), samples in sorted(groups.items()):
        times = [s["build_seconds"] for s in samples]
        feedback = [s["feedback_seconds"] for s in samples]
        item = {"project": project, "variant": variant, "case": case, "n": len(times),
                "build_median_seconds": statistics.median(times), "build_min_seconds": min(times), "build_max_seconds": max(times),
                "feedback_median_seconds": statistics.median(feedback),
                "first_execution_median_seconds": statistics.median(s["probe_seconds"] for s in samples),
                "smoke_execution_median_seconds": statistics.median(s["runtime_seconds"] for s in samples),
                "cache_hits": sum(s["cache_hits"] for s in samples), "cache_misses": sum(s["cache_misses"] for s in samples)}
        summary.append(item)
        lines.append("| %s | %s | %s | %d | %.3f | %.3f–%.3f | %.3f | %d / %d |" % (
            project, variant, case, len(times), item["build_median_seconds"], min(times), max(times), item["feedback_median_seconds"], item["cache_hits"], item["cache_misses"]))
    if failures:
        lines += ["", "Failed configurations are excluded from timing comparisons:", ""]
        lines += ["- " + f["project"] + " / " + f["variant"] + ": " + f["status"] for f in failures]
    dest = ROOT / "results" / run_id
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "summary.md").write_text("\n".join(lines) + "\n")
    (dest / "summary.json").write_text(json.dumps({"run": run_id, "summary": summary, "failures": [{k:v for k,v in x.items() if k not in ["error_tail", "error"]} for x in failures]}, indent=2) + "\n")
    print(dest / "summary.md")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    report(parser.parse_args().run_id)
