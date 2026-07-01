#!/usr/bin/env python3
"""
RAG 检索 hit@k eval —— case 级回归，确定性打分，不用 LLM Judge。

用法:
  python eval/run_rag_eval.py                           # case 级回归判定
  python eval/run_rag_eval.py --update-baseline         # 将当前结果写为基线（有 REGRESS 时拒写）
  python eval/run_rag_eval.py --update-baseline --force # 强制写基线（无视 REGRESS）
  python eval/run_rag_eval.py --top-k 3                  # 自定义 top-k（默认 5）
  python eval/run_rag_eval.py --delay 0.1                # 控制请求间隔

判定逻辑（逐条对比 expected_hit1 vs 实际 hit@1）：
  REGRESS  : expected=pass      → hit@1=false  ← 唯一报警，非零退出
  GRADUATE : expected=known_fail → hit@1=true  ← 可手动升为 pass
  PASS     : expected=pass      → hit@1=true
  KNOWN    : expected=known_fail → hit@1=false

expected_hit1 基线独立存储在 eval/baseline_rag.json，与 case 定义分离。
--update-baseline 直接写 JSON（无正则、不改源码），见 eval/dataset_rag.py。

输出: case 级四类分组 + 聚合 hit@1/3/5 作为参考。
每次运行结果存档 eval/results/rag-retrieval/run-*.json。
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.rag_pipeline import retrieve
from eval.dataset_rag import CASES

EVAL_NAME = "rag-retrieval"
RESULTS_DIR = Path(__file__).resolve().parent / "results" / EVAL_NAME
BASELINE_PATH = Path(__file__).resolve().parent / "baseline_rag.json"

# Fixed-width labels (all 10 chars, left-aligned for vertical scanning)
_LABEL = {
    "REGRESS":  "[REGRESS] ",   # 10
    "GRADUATE": "[GRADUATE]",   # 10 (exact fit)
    "PASS":     "[PASS]    ",   # 10 (6 + 4 pad)
    "KNOWN":    "[KNOWN]  ",    # 10 (8 + 2 pad)
}


# ---------------------------------------------------------------------------
# Baseline I/O
# ---------------------------------------------------------------------------

def _load_baseline() -> dict[str, str]:
    """Load expected_hit1 mapping from baseline JSON.

    Returns {case_id: "pass"|"known_fail"}.  Missing file or corrupt content
    yields an empty dict (all cases treated as 'pass' by the caller).
    """
    if not BASELINE_PATH.exists():
        print(f"  [WARN] baseline file not found: {BASELINE_PATH}  "
              f"(treating all as 'pass')", file=sys.stderr)
        return {}
    try:
        data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            print(f"  [WARN] baseline file is not a dict; treating all as "
                  f"'pass'", file=sys.stderr)
            return {}
        return data
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [WARN] baseline file corrupt ({exc}); treating all as "
              f"'pass'", file=sys.stderr)
        return {}


def _write_baseline(results: list[dict]) -> None:
    """Write current hit@1 results to baseline JSON."""
    mapping: dict[str, str] = {}
    for r in results:
        mapping[r["id"]] = "pass" if r["hit_at_1"] else "known_fail"
    payload = json.dumps(mapping, ensure_ascii=False, indent=2) + "\n"
    BASELINE_PATH.write_text(payload, encoding="utf-8")
    print(f"  [UPDATE] wrote {len(mapping)} entries to {BASELINE_PATH}")


def _enrich_cases(cases: list[dict],
                  baseline: dict[str, str]) -> list[dict]:
    """Merge baseline expected_hit1 into case dicts.

    Cases missing from the baseline default to 'pass'.
    """
    enriched: list[dict] = []
    for c in cases:
        ec = dict(c)
        ec["expected_hit1"] = baseline.get(c["id"], "pass")
        enriched.append(ec)
    return enriched


# ---------------------------------------------------------------------------
# Validation (audit fixes #2, #6)
# ---------------------------------------------------------------------------

def _validate_cases(cases: list[dict]) -> None:
    """Validate case definitions (from dataset_rag.py) before enrichment.

    Hard-fail on:
      - missing id / query / gold_sources
      - gold_sources empty  (audit #6)
    """
    errors: list[str] = []
    for c in cases:
        cid = c.get("id", "??")
        for field in ["id", "query", "gold_sources"]:
            if field not in c:
                errors.append(f"[{cid}] missing required field '{field}'")
        golds = c.get("gold_sources", [])
        if isinstance(golds, list) and len(golds) == 0:
            errors.append(f"[{cid}] gold_sources is empty -- data corruption")
    if errors:
        for e in errors:
            print(f"  [FATAL] {e}", file=sys.stderr)
        sys.exit(2)


def _validate_enriched(cases: list[dict]) -> None:
    """Validate expected_hit1 after baseline enrichment (audit #2).

    Hard-fail on:
      - expected_hit1 not in {pass, known_fail}
    """
    errors: list[str] = []
    for c in cases:
        cid = c.get("id", "??")
        exp = c.get("expected_hit1")
        if exp not in ("pass", "known_fail"):
            errors.append(
                f"[{cid}] invalid expected_hit1={exp!r} "
                f"(must be 'pass' or 'known_fail')")
    if errors:
        for e in errors:
            print(f"  [FATAL] {e}", file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# Case-ID cross-check (audit fix #3)
# ---------------------------------------------------------------------------

def _check_case_ids(current_ids: set[str]) -> None:
    """Compare current case IDs against the last archived run."""
    archives = sorted(RESULTS_DIR.glob("run-*.json"))
    if not archives:
        return
    last_archive = archives[-1]
    try:
        prev = json.loads(last_archive.read_text(encoding="utf-8"))
        prev_ids = {r["id"] for r in prev.get("results", [])}
    except Exception:
        return

    removed = prev_ids - current_ids
    added = current_ids - prev_ids

    if removed:
        print(f"  [REGRESS] cases REMOVED from dataset "
              f"(guard coverage shrunk): {sorted(removed)}")
    if added:
        print(f"  [WARN] new cases ADDED to dataset "
              f"(not yet in baseline): {sorted(added)}")


# ---------------------------------------------------------------------------
# Core eval logic
# ---------------------------------------------------------------------------

async def _run_once(cases: list[dict], top_k: int, delay: float) -> list[dict]:
    """Run retrieval for each case; attach hit flags + case metadata."""
    results: list[dict] = []
    for case in cases:
        query = case["query"]
        golds = case["gold_sources"]
        try:
            docs = await asyncio.to_thread(retrieve, query, top_k)
            retrieved_sources = [d.metadata["source"] for d in docs]
        except Exception as exc:
            print(f"  [ERROR] retrieve failed for [{case['id']}]: {exc}",
                  file=sys.stderr)
            retrieved_sources = ["__ERROR__"]

        hits = {}
        for k in [1, 3, 5]:
            top_k_sources = retrieved_sources[:k]
            hits[f"hit_at_{k}"] = any(gs in top_k_sources for gs in golds)

        results.append({
            "id": case["id"],
            "query": query,
            "gold_sources": golds,
            "expected_hit1": case["expected_hit1"],
            "retrieved": retrieved_sources,
            **hits,
        })
        if delay > 0:
            await asyncio.sleep(delay)
    return results


def _classify(results: list[dict]) -> dict[str, list[dict]]:
    """Bucket results by expected_hit1 vs actual hit@1."""
    buckets: dict[str, list[dict]] = {
        "REGRESS":  [],
        "GRADUATE": [],
        "PASS":     [],
        "KNOWN":    [],
    }
    for r in results:
        expected = r.get("expected_hit1", "pass")
        actual = r.get("hit_at_1", False)
        cat = (
            "REGRESS"  if expected == "pass"      and not actual else
            "GRADUATE" if expected == "known_fail" and actual     else
            "PASS"     if expected == "pass"      and actual     else
            "KNOWN"
        )
        r["category"] = cat
        buckets[cat].append(r)
    return buckets


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_aggregate(results: list[dict], n_cases: int) -> None:
    for k in [1, 3, 5]:
        n_hit = sum(1 for r in results if r.get(f"hit_at_{k}", False))
        rate = n_hit / n_cases if n_cases > 0 else 0
        marker = "  <-- primary" if k == 1 else ""
        print(f"  hit@{k}   : {rate:.1%}  ({n_hit}/{n_cases}){marker}")


def _print_category(title: str, items: list[dict], label_key: str,
                    top_n: int = 3) -> None:
    tag = _LABEL.get(label_key, f"[{label_key}]")
    if not items:
        print(f"\n  ({tag}{label_key}: none)")
        return
    _print_header(f"{title} ({len(items)})")
    for r in items:
        print(f"  {tag}[{r['id']}] {r['query']}")
        print(f"     gold: {r['gold_sources']}")
        print(f"     top-{min(top_n, len(r['retrieved']))}: "
              f"{r['retrieved'][:top_n]}")
        print()


def _print_case_results(results: list[dict], n_cases: int,
                        buckets: dict[str, list[dict]]) -> None:
    n_reg  = len(buckets["REGRESS"])
    n_grad = len(buckets["GRADUATE"])
    n_pass = len(buckets["PASS"])
    n_kn   = len(buckets["KNOWN"])

    _print_header("Results")
    print(f"  cases  : {n_cases}")
    print(f"  REGRESS={n_reg}  GRADUATE={n_grad}  PASS={n_pass}  KNOWN={n_kn}")
    print()
    print(f"  --- aggregate hit@k (reference) ---")
    _print_aggregate(results, n_cases)

    _print_category("REGRESS — previously-pass, now fail",
                    buckets["REGRESS"], "REGRESS")
    _print_category(
        "GRADUATE — previously-known_fail, now pass (candidate for promotion)",
        buckets["GRADUATE"], "GRADUATE")
    _print_category("PASS — still passing", buckets["PASS"], "PASS")
    _print_category("KNOWN — still known failure", buckets["KNOWN"], "KNOWN")


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------

def _archive(payload: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"run-{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="RAG retrieval hit@k eval (case-level regression)")
    parser.add_argument("--runs", type=int, default=1,
                        help="repeat N runs (retrieval is deterministic; "
                             "default 1)")
    parser.add_argument("--delay", type=float, default=0.1,
                        help="inter-request delay in seconds")
    parser.add_argument("--top-k", type=int, default=5,
                        help="retrieve top-k results (default 5)")
    parser.add_argument("--update-baseline", action="store_true",
                        help="bless current results as new baseline "
                             "(REFUSED if REGRESS exists)")
    parser.add_argument("--force", action="store_true",
                        help="with --update-baseline: force write even if "
                             "REGRESS exists")
    args = parser.parse_args()

    # --- validate raw case definitions ---
    _validate_cases(CASES)

    # --- load baseline and enrich cases ---
    baseline = _load_baseline()
    cases = _enrich_cases(CASES, baseline)
    _validate_enriched(cases)

    n_cases = len(cases)
    top_k = args.top_k

    # --- cross-check case ID set against last archive ---
    _check_case_ids({c["id"] for c in CASES})

    if args.update_baseline:
        mode = "FORCE" if args.force else "SAFE"
        print(f"[UPDATE] baseline mode ({mode}) -- will write current hit@1 "
              f"to {BASELINE_PATH}")

    print(f"\nRAG retrieval hit@k eval (case-level regression)  "
          f"-- {n_cases} cases x {args.runs} run(s)")
    print(f"  index  : vector_store/ (IndexFlatL2, 9 chunks)")
    print(f"  embed  : BAAI/bge-small-zh-v1.5  |  top-k: {top_k}")
    print(f"  verdict: per-case expected_hit1 vs actual hit@1\n")

    t0 = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()

    # --- run eval ---
    if args.runs == 1:
        results = await _run_once(cases, top_k, args.delay)
        elapsed = time.monotonic() - t0
    else:
        all_results: list[list[dict]] = []
        all_metrics: dict[int, list[float]] = {1: [], 3: [], 5: []}
        for run_idx in range(args.runs):
            label = f"[RUN {run_idx + 1}/{args.runs}]"
            print(f"  {label} ", end="", flush=True)
            results = await _run_once(cases, top_k, args.delay)
            all_results.append(results)
            for k in [1, 3, 5]:
                n_hit = sum(1 for r in results if r.get(f"hit_at_{k}"))
                all_metrics[k].append(n_hit / n_cases)
            print(f"hit@1={all_metrics[1][-1]:.1%}")

        elapsed = time.monotonic() - t0
        _print_header("Multi-run summary")
        for k in [1, 3, 5]:
            accs = all_metrics[k]
            avg = sum(accs) / len(accs)
            marker = "  <-- primary" if k == 1 else ""
            print(f"  hit@{k} mean : {avg:.1%}  "
                  f"({'  '.join(f'{a:.1%}' for a in accs)}){marker}")
        print(f"  wall time    : {elapsed:.1f}s")

    # --- classify BEFORE any baseline write (audit fix #1) ---
    buckets = _classify(results)
    n_reg = len(buckets["REGRESS"])

    # --- print results ---
    _print_case_results(results, n_cases, buckets)

    # --- baseline update (guarded by REGRESS check) ---
    if args.update_baseline:
        if n_reg > 0 and not args.force:
            _print_header("Update baseline -- BLOCKED")
            print(f"  [BLOCKED] {n_reg} REGRESS case(s) prevent baseline "
                  f"update:")
            for r in buckets["REGRESS"]:
                print(f"    {r['id']}: {r['query']}")
            print(f"\n  Baseline NOT written.  Review the regressions above, "
                  f"then either:")
            print(f"    - fix the root cause and re-run, or")
            print(f"    - use --update-baseline --force to accept them "
                  f"explicitly.")
            print(f"  Non-zero exit.")
            sys.exit(1)
        # safe path: no REGRESS, or --force active
        _print_header("Update baseline")
        _write_baseline(results)

    # --- archive ---
    _print_header("Archive")
    arc_path = _archive({
        "timestamp": timestamp,
        "eval": EVAL_NAME,
        "n_cases": n_cases,
        "n_runs": args.runs,
        "top_k": top_k,
        "duration_s": round(time.monotonic() - t0, 1),
        "hit_at_1": round(
            sum(1 for r in results if r.get("hit_at_1")) / n_cases, 4),
        "hit_at_3": round(
            sum(1 for r in results if r.get("hit_at_3")) / n_cases, 4),
        "hit_at_5": round(
            sum(1 for r in results if r.get("hit_at_5")) / n_cases, 4),
        "case_summary": {
            "REGRESS":  len(buckets["REGRESS"]),
            "GRADUATE": len(buckets["GRADUATE"]),
            "PASS":     len(buckets["PASS"]),
            "KNOWN":    len(buckets["KNOWN"]),
        },
        "results": results,
    })
    print(f"  {arc_path}")

    # --- exit code ---
    if n_reg > 0:
        print(f"\nREGRESS={n_reg} -- non-zero exit.")
        sys.exit(1)
    else:
        print(f"\nREGRESS=0 -- exit 0.")


if __name__ == "__main__":
    asyncio.run(_main())
