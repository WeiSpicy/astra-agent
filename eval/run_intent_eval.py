#!/usr/bin/env python3
"""
意图路由准确率 eval —— 真调 DeepSeek，预测 vs 期望。

用法:
  python eval/run_intent_eval.py                 # 全量
  python eval/run_intent_eval.py --new-only      # 仅跑边界增量
  python eval/run_intent_eval.py --runs 3        # 多跑看稳定性
  python eval/run_intent_eval.py --delay 1.0     # 控制请求间隔

输出: 准确率 / 混淆矩阵 / 挂掉的 case 列表。
每次运行结果存档 eval/results/intent-routing/run-*.json。
"""

import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.intent import detect_intent
from eval.dataset_intent import CASES, BOUNDARY_CASES

BUCKETS = ["chat", "rag", "tool", "dynamic"]
EVAL_NAME = "intent-routing"
RESULTS_DIR = Path(__file__).resolve().parent / "results" / EVAL_NAME


def _normalize(raw: str) -> str:
    cleaned = raw.strip().lower()
    for b in BUCKETS:
        if b in cleaned:
            return b
    return "???"


async def _run_once(cases: list[tuple[str, str]], delay: float) -> tuple[list, float]:
    # 每条结果: (输入, 期望, 归一化输出, 模型原始输出)
    results: list[tuple[str, str, str, str]] = []
    correct = 0
    for text, expected in cases:
        raw = "ERR"
        try:
            raw = await detect_intent(text)
            normalized = _normalize(raw)
        except Exception as exc:
            raw = str(exc)
            normalized = f"ERR:{exc}"
        results.append((text, expected, normalized, raw))
        if normalized == expected:
            correct += 1
        if delay > 0:
            await asyncio.sleep(delay)
    return results, correct / len(cases)


def _confusion_matrix(results: list[tuple[str, str, str, str]]) -> dict:
    m: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, expected, normalized, _ in results:
        m[expected][normalized] += 1
    return m


def _print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_results(results: list[tuple[str, str, str, str]], accuracy: float,
                   n_runs: int, duration_s: float, n_cases: int) -> list[dict]:
    m = _confusion_matrix(results)

    _print_header("结果")
    print(f"  数据集 : {n_cases} 条  |  轮次 : {n_runs}  |  耗时 : {duration_s:.1f}s")
    print(f"  准确率 : {accuracy:.1%}  ({int(accuracy * n_cases)}/{n_cases})")

    _print_header("混淆矩阵 (行=期望, 列=预测)")
    header = f"{'':>10}" + "".join(f"{b:>10}" for b in BUCKETS)
    print(header)
    for row_bucket in BUCKETS:
        cells = "".join(f"{m[row_bucket].get(col_bucket, 0):>10}" for col_bucket in BUCKETS)
        print(f"{row_bucket:>10}{cells}")

    failures = [(text, exp, norm, raw) for text, exp, norm, raw in results if exp != norm]
    if not failures:
        print("\n  ✅ 全部通过。")
    else:
        _print_header(f"未通过 ({len(failures)} 条)")
        for text, exp, norm, raw in failures:
            display_text = text if len(text) <= 60 else text[:57] + "..."
            print(f"  输入     : {display_text}")
            print(f"  期望     : {exp}")
            print(f"  模型输出 : {raw!r}  →  归一化: {norm}")
            print()

    return [
        {"input": text, "expected": exp, "predicted": norm, "raw_output": raw}
        for text, exp, norm, raw in results
    ]


def _archive(payload: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = RESULTS_DIR / f"run-{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


async def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="意图路由准确率 eval")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--new-only", action="store_true")
    args = parser.parse_args()

    cases = BOUNDARY_CASES if args.new_only else CASES
    tag = "边界增量" if args.new_only else "全量"

    print(f"🧪 意图路由 eval [{tag}]  —  {len(cases)} cases × {args.runs} run(s)")
    print(f"   模型: deepseek-v4-flash  |  延迟: {args.delay}s/req\n")

    t0 = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()

    if args.runs == 1:
        results, acc = await _run_once(cases, args.delay)
        result_dicts = _print_results(results, acc, args.runs, time.monotonic() - t0, len(cases))
        payload = {
            "timestamp": timestamp,
            "tag": tag,
            "n_cases": len(cases),
            "n_runs": args.runs,
            "accuracy": acc,
            "duration_s": round(time.monotonic() - t0, 1),
            "results": result_dicts,
        }
    else:
        all_accs: list[float] = []
        all_results_list: list[list] = []
        for run_idx in range(args.runs):
            print(f"  ▶ 第 {run_idx + 1}/{args.runs} 轮 ...", end=" ", flush=True)
            results, acc = await _run_once(cases, args.delay)
            all_accs.append(acc)
            all_results_list.append(results)
            print(f"{acc:.1%}")

        elapsed = time.monotonic() - t0
        avg_acc = sum(all_accs) / len(all_accs)

        _print_header("多轮汇总")
        print(f"  各轮准确率 : {'  '.join(f'{a:.1%}' for a in all_accs)}")
        print(f"  平均准确率 : {avg_acc:.1%}")
        print(f"  标准差     : {(sum((a - avg_acc)**2 for a in all_accs) / len(all_accs))**0.5:.3f}")
        print(f"  总耗时     : {elapsed:.1f}s")

        result_dicts = _print_results(
            all_results_list[-1], all_accs[-1], args.runs, elapsed, len(cases))

        payload = {
            "timestamp": timestamp,
            "tag": tag,
            "n_cases": len(cases),
            "n_runs": args.runs,
            "average_accuracy": avg_acc,
            "std": round((sum((a - avg_acc)**2 for a in all_accs) / len(all_accs))**0.5, 4),
            "per_run_accuracy": [round(a, 4) for a in all_accs],
            "duration_s": round(elapsed, 1),
            "results": result_dicts,
        }

    _archive(payload)


if __name__ == "__main__":
    asyncio.run(_main())
