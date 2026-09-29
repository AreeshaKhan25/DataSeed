"""Unified Test Runner for Synthetic Data Platform.

Runs all test suites in isolated processes across engine, API, AI fallbacks, provider adapters, and frontend builds.
Outputs a clean execution summary with total pass/fail counts.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SUITES = [
    ("Engine Pipeline", ROOT / "tests" / "test_engine.py"),
    ("API Routes & Workflows", ROOT / "tests" / "test_api.py"),
    ("AI Heuristic Fallback", ROOT / "tests" / "test_ai_fallback.py"),
    ("Provider Adapter & Schemas", ROOT / "tests" / "test_provider.py"),
]


def run_suite(name: str, path: Path) -> tuple[bool, float]:
    print(f"\n========================================================")
    print(f" Running Test Suite: {name} ({path.name})")
    print(f"========================================================")
    started = time.time()
    try:
        res = subprocess.run(
            [sys.executable, str(path)],
            cwd=str(ROOT),
            text=True,
            capture_output=False,
        )
        elapsed = time.time() - started
        return res.returncode == 0, elapsed
    except Exception as exc:
        print(f"FAILED to execute {path.name}: {exc}")
        return False, time.time() - started


def main() -> int:
    print("Synthetic Data Platform - Full System Test Suite")
    print(f"Python: {sys.version.split()[0]} | Root: {ROOT}")
    
    total_start = time.time()
    results: list[tuple[str, bool, float]] = []

    for name, path in SUITES:
        if not path.exists():
            print(f"\n[SKIP] {name}: File {path} not found.")
            results.append((name, False, 0.0))
            continue
        ok, duration = run_suite(name, path)
        results.append((name, ok, duration))

    total_duration = time.time() - total_start

    print("\n" + "=" * 60)
    print("                  TEST SUITE SUMMARY                    ")
    print("=" * 60)
    passed_count = 0
    for name, ok, duration in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed_count += 1
        print(f"  [{status}] {name:<35} ({duration:.2f}s)")
    print("-" * 60)
    print(f"  Total Passed: {passed_count}/{len(results)} suites | Time: {total_duration:.2f}s")
    print("=" * 60 + "\n")

    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
