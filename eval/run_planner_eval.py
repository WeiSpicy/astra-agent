#!/usr/bin/env python3
"""
Planner 结构校验 eval —— 调模型, 校验产出结构不校验具体步骤。

用法:
  python eval/run_planner_eval.py
  python eval/run_planner_eval.py --runs 3
  python eval/run_planner_eval.py --delay 1.0

校验规则:
  1. 可解析为 JSON 数组
  2. 非空（至少 1 步）
  3. 每步有 type 字段，值在 {tool, rag, llm}
  4. 末步是 llm
  5. tool 步骤：tool/name 字段存在，工具名在注册表中
  6. rag 步骤：query 字段存在且非空

输出: 通过率 + 每条 case 的违规明细。
每次运行结果存档 eval/results/planner/run-*.json。
"""

import asyncio
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.planner import plan_steps_async
from eval.dataset_planner import CASES

EVAL_NAME = "planner"
RESULTS_DIR = Path(__file__).resolve().parent / "results" / EVAL_NAME

STEP_TYPES = {"tool", "rag", "llm"}
TOOL_NAMES = {"calc", "now", "weather"}


def _checks(raw_output: str, steps: list | None, exc: str | None) -> list[str]:
    """对 planner 输出执行全部结构校验，返回违规列表。"""
    violations: list[str] = []

    # 1. 异常
    if exc is not None:
        violations.append(f"planner 抛出异常: {exc}")
        # planner 已抛异常 = 没有可解析的产物，后续结构校验无意义
        return violations

    # 2. 是 list
    if not isinstance(steps, list):
        violations.append(f"输出不是 JSON 数组，类型: {type(steps).__name__}")
        return violations

    # 3. 非空
    if len(steps) == 0:
        violations.append("空步骤列表")
        return violations

    # 4. 每步检查
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            violations.append(f"步骤[{i}] 不是 dict: {type(step).__name__}")
            continue

        stype = step.get("type")
        if not stype:
            violations.append(f"步骤[{i}] 缺少 type 字段")
            continue
        if stype not in STEP_TYPES:
            violations.append(f"步骤[{i}] type='{stype}' 不在白名单 {STEP_TYPES}")
            continue

        if stype == "tool":
            tool_name = step.get("tool") or step.get("name")
            if not tool_name:
                violations.append(f"步骤[{i}] tool 类型缺少 tool/name 字段")
            elif tool_name not in TOOL_NAMES:
                violations.append(f"步骤[{i}] 工具 '{tool_name}' 不在注册表 {TOOL_NAMES}")

        elif stype == "rag":
            query = step.get("query")
            if not query or not isinstance(query, str) or not query.strip():
                violations.append(f"步骤[{i}] rag 类型缺少有效的 query 字段")

    # 5. llm 不在中间位置
    llm_positions = [
        i for i, s in enumerate(steps)
        if isinstance(s, dict) and s.get("type") == "llm"
    ]
    if len(llm_positions) > 1:
        violations.append(f"llm 步骤出现 {len(llm_positions)} 次，应只有末尾一次")
    elif len(llm_positions) == 1 and llm_positions[0] != len(steps) - 1:
        violations.append(f"llm 在第 {llm_positions[0]} 位（共 {len(steps)} 步），应只在末尾")

    # 6. 末步是 llm
    last_type = steps[-1].get("type") if isinstance(steps[-1], dict) else None
    if last_type != "llm":
        violations.append(f"末步 type='{last_type}'，期望 llm")

    return violations


async def _run_once(inputs: list[str], delay: float) -> list[dict]:
    results: list[dict] = []
    for text in inputs:
        raw_output = ""
        steps = None
        exc = None
        try:
            raw_output = await plan_steps_async(text)  # 注意: 返回的是解析后的 list
            steps = raw_output
            raw_output = json.dumps(raw_output, ensure_ascii=False)
        except Exception as e:
            exc = str(e)
            raw_output = ""

        violations = _checks(raw_output, steps, exc)
        results.append({
            "input": text,
            "passed": len(violations) == 0,
            "violations": violations,
            "steps": steps,
        })
        if delay > 0:
            await asyncio.sleep(delay)
    return results


def _print_header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _print_results(results: list[dict], duration_s: float, n_runs: int) -> None:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    acc = passed / total if total > 0 else 0

    _print_header("结果")
    print(f"  数据集   : {total} 条  |  轮次 : {n_runs}  |  耗时 : {duration_s:.1f}s")
    print(f"  通过率   : {acc:.1%}  ({passed}/{total})")

    # 违规分布
    violation_counts: dict[str, int] = defaultdict(int)
    for r in results:
        for v in r["violations"]:
            # 取违规类型的前几个字作为分类
            key = v.split(":")[0] if ":" in v else v[:30]
            violation_counts[key] += 1

    if violation_counts:
        _print_header("违规分布")
        for k, c in sorted(violation_counts.items(), key=lambda x: -x[1]):
            print(f"  {c:>3} 次 : {k}")

    # 挂掉的 case
    failures = [r for r in results if not r["passed"]]
    if not failures:
        print("\n  ✅ 全部通过。")
    else:
        _print_header(f"未通过 ({len(failures)} 条)")
        for r in failures:
            display_text = r["input"] if len(r["input"]) <= 60 else r["input"][:57] + "..."
            print(f"  输入 : {display_text}")
            for v in r["violations"]:
                print(f"    ↳ {v}")
            # 也打印实际步骤
            if r["steps"]:
                steps_preview = json.dumps(r["steps"], ensure_ascii=False)
                if len(steps_preview) > 120:
                    steps_preview = steps_preview[:117] + "..."
                print(f"    实际步骤 : {steps_preview}")
            print()


async def _main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Planner 结构校验 eval")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    print(f"🧪 Planner 结构校验 eval  —  {len(CASES)} cases × {args.runs} run(s)")
    print(f"   模型: deepseek-v4-flash  |  延迟: {args.delay}s/req")
    print(f"   校验: JSON合法 / 非空 / type白名单 / 末步llm / tool名 / rag.query\n")

    t0 = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()

    if args.runs == 1:
        results = await _run_once(CASES, args.delay)
        elapsed = time.monotonic() - t0
        _print_results(results, elapsed, args.runs)
    else:
        all_results: list[list[dict]] = []
        all_accs: list[float] = []
        for run_idx in range(args.runs):
            print(f"  ▶ 第 {run_idx + 1}/{args.runs} 轮 ...", end=" ", flush=True)
            results = await _run_once(CASES, args.delay)
            passed = sum(1 for r in results if r["passed"])
            acc = passed / len(results)
            all_accs.append(acc)
            all_results.append(results)
            print(f"{acc:.1%}")

        elapsed = time.monotonic() - t0
        avg_acc = sum(all_accs) / len(all_accs)

        _print_header("多轮汇总")
        print(f"  各轮通过率 : {'  '.join(f'{a:.1%}' for a in all_accs)}")
        print(f"  平均通过率 : {avg_acc:.1%}")
        print(f"  总耗时     : {elapsed:.1f}s")

        _print_results(all_results[-1], elapsed, args.runs)

    # 存档
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    archive_path = RESULTS_DIR / f"run-{ts}.json"
    # 把 steps 转为可序列化的格式
    serializable = []
    for r in (all_results[-1] if args.runs > 1 else results):
        serializable.append({
            "input": r["input"],
            "passed": r["passed"],
            "violations": r["violations"],
            "steps": r["steps"],
        })
    payload = {
        "timestamp": timestamp,
        "n_cases": len(CASES),
        "n_runs": args.runs,
        "pass_rate": sum(1 for r in serializable if r["passed"]) / len(serializable),
        "duration_s": round(elapsed if args.runs > 1 else time.monotonic() - t0, 1),
        "results": serializable,
    }
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(_main())
