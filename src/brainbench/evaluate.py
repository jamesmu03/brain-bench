"""Run a submission against the benchmark and write a result record.

    brainbench-evaluate my_model.py --train data/partitions/public --test data/partitions/private \\
        --task media_vs_rest --out results/my_model.json

A submission is a Python file (or an importable module) that defines

    def build() -> Model

returning an object implementing brainbench.submission.Model. It is fitted on
the train partition's train+val splits and scored on the test partition's
test and test_xdevice splits. The record names the submission, its sha256 and
the release it was scored on, so a leaderboard row is always traceable.

Submissions run in-process; run untrusted ones in a sandbox (a container or a
throwaway VM) with no network and no access to anything but the partitions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from brainbench.loader import BrainBench
from brainbench.submission import TASKS, Model, evaluate, iter_windows


def load_submission(spec: str) -> tuple[Model, dict]:
    """spec is a path to a .py file or a dotted module name; it must define build()."""
    path = Path(spec)
    if path.suffix == ".py":
        module_spec = importlib.util.spec_from_file_location(f"submission_{path.stem}", path)
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_spec.name] = module
        module_spec.loader.exec_module(module)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        meta = {"submission": path.name, "sha256": digest}
    else:
        module = importlib.import_module(spec)
        meta = {"submission": spec, "sha256": None}
    if not hasattr(module, "build"):
        raise ValueError(f"{spec} does not define build()")
    model = module.build()
    if not isinstance(model, Model):
        raise TypeError(f"{spec}: build() must return an object with fit() and predict_proba()")
    return model, meta


def run_submission(
    spec: str,
    train: Path,
    test: Path,
    task_name: str,
    train_splits=("train", "val"),
    test_splits=("test", "test_xdevice"),
    max_per_recording: int | None = None,
) -> dict:
    model, meta = load_submission(spec)
    task = TASKS[task_name]
    train_bb, test_bb = BrainBench(train), BrainBench(test)
    if train_bb.manifest["version"] != test_bb.manifest["version"]:
        raise ValueError(f"train and test partitions come from different releases: {train_bb.manifest['version']} vs {test_bb.manifest['version']}")

    def training():
        for split in train_splits:
            for window, _ in iter_windows(train_bb, task, split, max_per_recording):
                yield window

    model.fit(training())
    return {
        **meta,
        "model": type(model).__name__,
        "task": task_name,
        "dataset": test_bb.manifest.get("name"),
        "release": test_bb.manifest["version"],
        "schema_version": test_bb.manifest["schema_version"],
        "holdout_source": test_bb.splits["holdout_source"],
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "results": {split: evaluate(model, test_bb, task, split, max_per_recording) for split in test_splits},
    }


def leaderboard(records: list[dict], split: str = "test_xdevice", metric: str = "auroc") -> str:
    """Markdown table of result records, best first."""
    rows = [r for r in records if metric in r["results"].get(split, {})]
    rows.sort(key=lambda r: r["results"][split][metric], reverse=True)
    lines = [
        f"| # | Submission | Model | Task | Release | {split} {metric} | test {metric} | Evaluated |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(rows, 1):
        test = r["results"].get("test", {}).get(metric)
        lines.append(
            f"| {i} | {r.get('submission', '?')} | {r.get('model', '?')} | {r['task']} | {r['release']} | "
            f"{r['results'][split][metric]:.3f} | {'' if test is None else f'{test:.3f}'} | {r.get('evaluated_at', '')[:10]} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="brainbench-evaluate")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="fit a submission on the train partition and score it on the test partition")
    r.add_argument("submission", help="path to a .py file defining build(), or a module name")
    r.add_argument("--train", type=Path, required=True)
    r.add_argument("--test", type=Path, required=True)
    r.add_argument("--task", default="media_vs_rest", choices=sorted(TASKS))
    r.add_argument("--out", type=Path)
    r.add_argument("--max-per-recording", type=int, help="cap windows per recording (for quick runs)")

    b = sub.add_parser("board", help="print a leaderboard from result records")
    b.add_argument("records", nargs="+", type=Path)
    b.add_argument("--split", default="test_xdevice")
    b.add_argument("--metric", default="auroc")

    args = p.parse_args(argv)
    if args.command == "run":
        result = run_submission(args.submission, args.train, args.test, args.task, max_per_recording=args.max_per_recording)
        text = json.dumps(result, indent=2)
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text)
    else:
        print(leaderboard([json.loads(path.read_text()) for path in args.records], args.split, args.metric))


if __name__ == "__main__":
    main()
