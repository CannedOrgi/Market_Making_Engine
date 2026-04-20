from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from pathlib import Path


REQUIRED_OUTPUT_COLUMNS = ("ts_event", "symbol", "side", "order_type", "qty", "limit_px")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="run_strategy.py")
    parser.add_argument("--split", default="test_sample")
    parser.add_argument("--orders", default="orders.csv")
    parser.add_argument("--report-dir", default="local_public_report")
    parser.add_argument(
        "--date",
        default=None,
        help="Run only one date, e.g. 2024-04-08. Use --list-dates to see choices.",
    )
    parser.add_argument(
        "--list-dates",
        action="store_true",
        help="Print available dates in the data and exit.",
    )
    return parser.parse_args()


def resolve_split_root(package_root: Path, split_name: str) -> tuple[str, Path]:
    aliases = {
        "train": "full_sample",
        "full_sample": "test_sample",
        "public_sample": "test_sample",
        "test_sample": "test_sample",
    }
    canonical = aliases.get(split_name, split_name)
    split_root = package_root / canonical
    if split_root.exists():
        return canonical, split_root
    legacy_root = package_root / split_name
    return split_name, legacy_root


def validate_orders_csv(csv_path: Path) -> tuple[bool, str]:
    if not csv_path.exists():
        return False, "run_strategy.py did not create orders.csv."

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return False, "orders.csv is empty."
        if tuple(reader.fieldnames) != REQUIRED_OUTPUT_COLUMNS:
            return False, f"orders.csv columns must be exactly: {', '.join(REQUIRED_OUTPUT_COLUMNS)}"

        for idx, row in enumerate(reader, start=2):
            side = (row["side"] or "").lower()
            order_type = (row["order_type"] or "").lower()
            if side not in {"buy", "sell"}:
                return False, f"Invalid side on line {idx}: {row['side']!r}"
            if order_type not in {"market", "limit"}:
                return False, f"Invalid order_type on line {idx}: {row['order_type']!r}"
            try:
                qty = int(row["qty"])
            except ValueError:
                return False, f"qty must be an integer on line {idx}"
            if qty <= 0:
                return False, f"qty must be positive on line {idx}"
            if order_type == "limit" and row["limit_px"] in {"", None}:
                return False, f"limit orders require limit_px on line {idx}"
    return True, "orders.csv is valid."


def available_dates(data_root: Path) -> list[str]:
    schema_dir = data_root / "mbp-10"
    if not schema_dir.exists():
        return []
    return sorted(
        d.name for d in schema_dir.iterdir()
        if d.is_dir() and any(d.glob("*.parquet"))
    )


def filter_orders_to_date(orders_path: Path, date: str) -> None:
    import pandas as pd

    df = pd.read_csv(orders_path)
    if df.empty:
        return
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True, format="mixed")
    mask = df["ts_event"].dt.strftime("%Y-%m-%d") == date
    df.loc[mask].to_csv(orders_path, index=False)
    kept = int(mask.sum())
    total = len(df)
    print(f"Filtered orders to {date}: {kept}/{total} orders kept.")


def fast_assignment():
    support_root = Path(__file__).resolve().parent / "_local_eval_support"
    sys.path.insert(0, str(support_root))
    from microstructure_autograder.grading.fast_simulator import FastAssignment

    return FastAssignment(kind="trader")


def main() -> int:
    args = parse_args()
    package_root = Path.cwd()
    split_name, split_root = resolve_split_root(package_root, args.split)
    if not split_root.exists():
        print(f"Missing split directory: {split_root}", file=sys.stderr)
        return 1

    if args.list_dates:
        dates = available_dates(split_root)
        print(f"Available dates in {split_name}: {dates}")
        return 0

    chosen_date = args.date
    if chosen_date is not None:
        dates = available_dates(split_root)
        if chosen_date not in dates:
            print(f"Date {chosen_date!r} not found. Available: {dates}", file=sys.stderr)
            return 1

    orders_path = package_root / args.orders
    report_dir = package_root / args.report_dir
    if report_dir.exists():
        shutil.rmtree(report_dir)
    if orders_path.exists():
        orders_path.unlink()

    print(f"Running strategy on {split_root}...")
    command = [
        sys.executable,
        str((package_root / args.strategy).resolve()),
        "--data",
        str(split_root),
        "--output",
        str(orders_path),
    ]
    completed = subprocess.run(command, cwd=package_root, capture_output=True, text=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.returncode != 0:
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")
        print("Strategy execution failed.", file=sys.stderr)
        return completed.returncode

    ok, message = validate_orders_csv(orders_path)
    if not ok:
        print(message, file=sys.stderr)
        return 1

    if chosen_date is not None:
        filter_orders_to_date(orders_path, chosen_date)

    date_label = chosen_date or "all dates"
    print(f"Scoring fast replay for trader on {date_label}...")

    assignment = fast_assignment()
    from microstructure_autograder.grading.fast_simulator import fast_simulate

    detailed = fast_simulate(
        orders_path,
        split_root,
        assignment=assignment,
        report_dir=report_dir,
        date_filter=chosen_date,
    )

    metrics = detailed.metrics

    print(f"Local evaluation complete for trader ({date_label}).")
    print(f"Score: {metrics.get('score', '0.00')}")
    print(f"Net PnL: {metrics.get('net_pnl', '0.00')}")
    print(f"Max drawdown: {metrics.get('max_drawdown', '0.00')}")
    print(f"Turnover: {metrics.get('turnover', '0.00')}")
    print(f"Violations: {metrics.get('violations', '0')}")
    print(f"Orders file: {orders_path}")
    print(f"Report directory: {report_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
