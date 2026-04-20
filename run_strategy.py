"""
HW1b Trader (L2) — Example strategy using full order book depth.

This week you extend your HW1a strategy to use the full L2 depth:
  - bid_px_00..09, ask_px_00..09  (prices at 10 levels)
  - bid_sz_00..09, ask_sz_00..09  (sizes at 10 levels)
  - bid_ct_00..09, ask_ct_00..09  (order counts at 10 levels)

You can reuse your L1 signals from HW1a and add L2 features on top.

Invoked as:
    python run_strategy.py --data <path> --output orders.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd


# ── Required output format (do not change) ────────────────────────────────
OUTPUT_COLUMNS = ["ts_event", "symbol", "side", "order_type", "qty", "limit_px"]

# ── Strategy parameters (tune these) ──────────────────────────────────────
SAMPLE_STEP = 5_000        # sample more frequently now (L2 signals are richer)
MAX_ORDERS_PER_FILE = 10000   # more orders allowed with better signals
IMBALANCE_THRESHOLD = 0.3  # order book imbalance threshold
ORDER_QTY = 10             # shares per order
MIN_EVENT_GAP_SECONDS = 300
SCORE_THRESHOLD = 0.5

# ── Symbol selection ──────────────────────────────────────────────────────
CHOSEN_SYMBOL: str | None = "TSLA"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--show-symbols", action="store_true")
    return parser.parse_args()


def find_parquet_files(data_root: Path) -> list[Path]:
    mbp10_dir = data_root / "mbp-10"
    if not mbp10_dir.exists():
        return []
    return sorted(mbp10_dir.glob("*/*.parquet"))


def discover_symbols(data_root: Path) -> list[str]:
    symbols: set[str] = set()
    for parquet_path in find_parquet_files(data_root):
        df = pd.read_parquet(parquet_path, columns=["symbol"])
        symbols.update(df["symbol"].unique().tolist())
    return sorted(symbols)


def pick_symbol(frame: pd.DataFrame) -> str:
    available = sorted(frame["symbol"].unique().tolist())
    if CHOSEN_SYMBOL is not None and CHOSEN_SYMBOL in available:
        return CHOSEN_SYMBOL
    if CHOSEN_SYMBOL is not None:
        print(f"Warning: CHOSEN_SYMBOL={CHOSEN_SYMBOL!r} not in {available}, using {available[0]!r}")
    return str(available[0])


# ── L2 Signal generation ─────────────────────────────────────────────────
#
# Now you can use the FULL order book depth (10 levels on each side).
#
# Key L2 features to consider:
#   - Order book imbalance: sum(bid_sz_00..04) vs sum(ask_sz_00..04)
#     Imbalance > 0 means more buying pressure -> price likely to rise
#   - Depth-weighted mid-price: weight prices by sizes across levels
#   - Spread + depth: thin book (low total size) means more volatility
#   - Order count: many small orders vs few large orders at a level

BID_PX = [f"bid_px_{i:02d}" for i in range(10)]
ASK_PX = [f"ask_px_{i:02d}" for i in range(10)]
BID_SZ = [f"bid_sz_{i:02d}" for i in range(10)]
ASK_SZ = [f"ask_sz_{i:02d}" for i in range(10)]
BID_CT = [f"bid_ct_{i:02d}" for i in range(10)]
ASK_CT = [f"ask_ct_{i:02d}" for i in range(10)]

L2_COLUMNS = ["ts_event", "symbol"] + BID_PX + ASK_PX + BID_SZ + ASK_SZ + BID_CT + ASK_CT



def build_orders(data_root: Path) -> pd.DataFrame:
    orders: list[dict[str, object]] = []

    for parquet_path in find_parquet_files(data_root):
        frame = pd.read_parquet(parquet_path, columns=L2_COLUMNS)
        symbol = pick_symbol(frame)
        frame = frame.loc[frame["symbol"] == symbol].copy()
        if frame.empty:
            continue

        frame["ts_event"] = pd.to_datetime(frame["ts_event"], utc=True, errors="coerce")

        numeric_cols = [c for c in frame.columns if c not in ["ts_event", "symbol"]]
        frame[numeric_cols] = frame[numeric_cols].astype(float)

        frame = (
            frame
            .dropna(subset=["ts_event", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"])
            .sort_values("ts_event")
            .reset_index(drop=True)
        )
        if frame.empty:
            continue

        # -------------------------------
        # Basic L1 state
        # -------------------------------
        frame["mid_px"] = (frame["bid_px_00"] + frame["ask_px_00"]) / 2.0
        frame["spread"] = frame["ask_px_00"] - frame["bid_px_00"]

        positive_spreads = np.sort(frame.loc[frame["spread"] > 0, "spread"].unique())
        tick = float(positive_spreads[0]) if len(positive_spreads) else 0.01

        bid1 = frame["bid_sz_00"]
        ask1 = frame["ask_sz_00"]
        tot1 = bid1 + ask1

        frame["imb_1"] = np.where(
            tot1 > 0,
            (bid1 - ask1) / tot1,
            0.0,
        )

        frame["microprice_1"] = np.where(
            tot1 > 0,
            (frame["ask_px_00"] * bid1 + frame["bid_px_00"] * ask1) / tot1,
            frame["mid_px"],
        )

        frame["micro_score"] = np.where(
            frame["spread"] > 0,
            (frame["microprice_1"] - frame["mid_px"]) / frame["spread"],
            0.0,
        )
        frame["micro_score"] = frame["micro_score"].clip(-1.0, 1.0)

        frame["mom_20"] = np.where(
            frame["spread"] > 0,
            (frame["mid_px"] - frame["mid_px"].shift(20)) / frame["spread"],
            0.0,
        )
        frame["mom_20"] = frame["mom_20"].fillna(0.0).clip(-2.0, 2.0) / 2.0

        # -------------------------------
        # L2 depth + count features
        # -------------------------------
        for k in [5, 10]:
            bid_sz_cols = [f"bid_sz_{i:02d}" for i in range(k)]
            ask_sz_cols = [f"ask_sz_{i:02d}" for i in range(k)]
            bid_ct_cols = [f"bid_ct_{i:02d}" for i in range(k)]
            ask_ct_cols = [f"ask_ct_{i:02d}" for i in range(k)]

            frame[f"bid_depth_{k}"] = frame[bid_sz_cols].sum(axis=1)
            frame[f"ask_depth_{k}"] = frame[ask_sz_cols].sum(axis=1)
            depth_total = frame[f"bid_depth_{k}"] + frame[f"ask_depth_{k}"]

            frame[f"imb_{k}"] = np.where(
                depth_total > 0,
                (frame[f"bid_depth_{k}"] - frame[f"ask_depth_{k}"]) / depth_total,
                0.0,
            )

            bid_ct_total = frame[bid_ct_cols].sum(axis=1)
            ask_ct_total = frame[ask_ct_cols].sum(axis=1)
            ct_total = bid_ct_total + ask_ct_total

            frame[f"ct_imb_{k}"] = np.where(
                ct_total > 0,
                (bid_ct_total - ask_ct_total) / ct_total,
                0.0,
            )

        weights = np.array([1.0 / (i + 1) for i in range(10)], dtype=float)
        bid_mat = frame[BID_SZ].to_numpy(dtype=float)
        ask_mat = frame[ASK_SZ].to_numpy(dtype=float)

        weighted_bid = bid_mat @ weights
        weighted_ask = ask_mat @ weights
        weighted_total = weighted_bid + weighted_ask

        frame["w_imb_10"] = np.where(
            weighted_total > 0,
            (weighted_bid - weighted_ask) / weighted_total,
            0.0,
        )

        frame["top_share_bid"] = np.where(
            frame["bid_depth_10"] > 0,
            frame["bid_sz_00"] / frame["bid_depth_10"],
            0.0,
        )
        frame["top_share_ask"] = np.where(
            frame["ask_depth_10"] > 0,
            frame["ask_sz_00"] / frame["ask_depth_10"],
            0.0,
        )
        frame["fragility"] = (frame["top_share_bid"] - frame["top_share_ask"]).clip(-1.0, 1.0)

        # -------------------------------
        # Combined signal
        # -------------------------------
        frame["score"] = (
            0.40 * frame["imb_1"] +
            0.30 * frame["imb_5"] +
            0.05 * frame["w_imb_10"] +
            0.20 * frame["micro_score"] +
            0.05 * frame["ct_imb_5"] +
            0.03 * frame["mom_20"] +
            0.02 * frame["fragility"]
        )

        signal_cols = ["imb_1", "imb_5", "imb_10", "w_imb_10", "micro_score"]
        frame["vote"] = np.sign(frame[signal_cols]).sum(axis=1)

        # -------------------------------
        # Trade filters
        # -------------------------------
        spread_cap = max(4.0 * tick, float(frame["spread"].quantile(0.85)))
        bid_depth_floor = float(frame["bid_depth_10"].quantile(0.15))
        ask_depth_floor = float(frame["ask_depth_10"].quantile(0.15))

        candidates = frame.loc[
            (frame["spread"] >= tick) &
            (frame["spread"] <= spread_cap) &
            (frame["bid_depth_10"] >= bid_depth_floor) &
            (frame["ask_depth_10"] >= ask_depth_floor)
        ].copy()

        candidates["abs_score"] = candidates["score"].abs()

        candidates = candidates.loc[
            ((candidates["score"] >= SCORE_THRESHOLD) & (candidates["vote"] >= 3)) |
            ((candidates["score"] <= -SCORE_THRESHOLD) & (candidates["vote"] <= -3))
        ].copy()

        # Spread trades through time instead of only taking the biggest scores of the whole day
        candidates["time_bucket"] = candidates["ts_event"].dt.floor("15s")
        candidates = (
            candidates
            .sort_values(["time_bucket", "abs_score"], ascending=[True, False])
            .groupby("time_bucket", as_index=False)
            .head(2)
            .sort_values("ts_event")
        )

        selected: list[dict[str, object]] = []

        for _, row in candidates.iterrows():
            if len(selected) >= MAX_ORDERS_PER_FILE:
                break

            ts = row["ts_event"]
            too_close = any(
                abs(ts - existing["_ts"]) < pd.Timedelta(seconds=MIN_EVENT_GAP_SECONDS)
                for existing in selected
            )
            if too_close:
                continue

            selected.append(
                {
                    "_ts": ts,
                    "ts_event": ts.isoformat(),
                    "symbol": symbol,
                    "side": "buy" if row["score"] > 0 else "sell",
                    "order_type": "market",
                    "qty": ORDER_QTY,
                    "limit_px": "",
                }
            )

        selected.sort(key=lambda x: x["_ts"])
        for row in selected:
            row.pop("_ts", None)
            orders.append(row)

    return pd.DataFrame(orders, columns=OUTPUT_COLUMNS)


if __name__ == "__main__":
    args = parse_args()
    data_root = Path(args.data)

    if args.show_symbols:
        print(f"Available symbols in {data_root}: {discover_symbols(data_root)}")
        raise SystemExit(0)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build_orders(data_root).to_csv(output_path, index=False)
