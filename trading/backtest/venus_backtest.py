"""Venus model v1 backtester (spec: trading/strategy/venus_model_v1.md).

Bar-by-bar, no lookahead: signal judged on bar i close, entry at bar i+1 open.
Prices in the CSV are bid; ask = bid + spread(points) * POINT.

Usage:
  python trading/backtest/venus_backtest.py --data trading/data/EURUSD_M15_icmarkets.csv --model A
  python trading/backtest/venus_backtest.py --data ... --model A --flow 5 --rr 2.0 --start 2024-01-01
  python trading/backtest/venus_backtest.py --data ... --model A --grid

Resolved ambiguities (see report / comments marked [AMB]):
  - Entry window uses the signal bar's CLOSE time (= bar open time + 15 min).
  - SL distance (clamp 6 pip / skip >25|30 pip, RR, lot sizing) is measured from
    the actual fill price (buy: ask = open+spread, sell: bid = open).
  - Buy SL/TP trigger on bid (bar low/high); sell SL/TP trigger on ask
    (bar high/low + that bar's spread). Gaps through SL fill at the bar open.
  - Forced exit: at the open of the first bar whose server time >= 19:00 on the
    entry date (or the first bar of a later date).
  - Daily lock: per bar, equity at the adverse extreme (realised today + floating
    incl. commission). If <= -3% of day-start balance, the position is closed at
    the price where equity equals the -3% level (or the bar open if already beyond).
  - Max 2 entries per server date counts filled entries (skipped signals don't count).
  - Model B: a setup stays live for the whole C3 bar (re-entry allowed after a
    trade closes, subject to 1 position / 2 per day). If long and short setups
    both fire on the same bar, no trade.
  - R per trade = net P&L (after commission) / (lots * SL pips * $10).
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PIP = 0.0001
POINT = 0.00001
PIP_VALUE = 10.0  # USD per lot per pip
EPS = 1e-9

LONDON = (10 * 60, 13 * 60)
NEWYORK = (15 * 60, 17 * 60 + 30)
FORCE_EXIT_MIN = 19 * 60

IS_START, IS_END = "2019-01-01", "2023-12-31"
OOS_START = "2024-01-01"

RESULTS = Path(__file__).resolve().parent / "results"


@dataclass
class Config:
    balance: float = 10_000.0
    risk_pct: float = 0.005
    commission_per_lot: float = 7.0
    daily_lock_pct: float = 0.03
    max_entries_per_day: int = 2
    lot_step: float = 0.01
    lot_min: float = 0.01
    min_sl_pips: float = 6.0
    start: pd.Timestamp | None = None  # signal-time filter (inclusive)
    end: pd.Timestamp | None = None    # signal-time filter (inclusive, whole day)


# --------------------------------------------------------------------------- data
def load_csv(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "server_time" in df.columns:
        df["server_time"] = pd.to_datetime(df["server_time"])
    else:
        df["server_time"] = pd.to_datetime(df["time"], unit="s")
    if "spread" not in df.columns:
        df["spread"] = 0
    df = df.drop_duplicates("server_time").sort_values("server_time").reset_index(drop=True)
    return df


def _close_minutes(df: pd.DataFrame) -> np.ndarray:
    ct = df["server_time"] + pd.Timedelta(minutes=15)
    return (ct.dt.hour * 60 + ct.dt.minute).to_numpy()


def in_window(df: pd.DataFrame) -> np.ndarray:
    m = _close_minutes(df)
    return ((m >= LONDON[0]) & (m < LONDON[1])) | ((m >= NEWYORK[0]) & (m < NEWYORK[1]))


# ---------------------------------------------------------------- signal building
def _last_true_index(mask: np.ndarray) -> np.ndarray:
    """For each i, the largest k <= i with mask[k], else -1."""
    idx = np.where(mask, np.arange(len(mask)), -1)
    return np.maximum.accumulate(idx) if len(idx) else idx


def bos_arrays(df: pd.DataFrame):
    """Model A rule 2. Returns (bos_up, bos_dn, swing_high_price, swing_low_price)."""
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    is_sh = np.zeros(n, bool)
    is_sl = np.zeros(n, bool)
    if n >= 3:
        is_sh[1:-1] = (h[1:-1] > h[:-2]) & (h[1:-1] >= h[2:])
        is_sl[1:-1] = (l[1:-1] < l[:-2]) & (l[1:-1] <= l[2:])
    # most recent k <= i-1 (so k+1 <= i), within i-16..i-1
    last_sh = np.full(n, -1)
    last_sl = np.full(n, -1)
    if n > 1:
        last_sh[1:] = _last_true_index(is_sh)[:-1]
        last_sl[1:] = _last_true_index(is_sl)[:-1]
    i = np.arange(n)
    ok_h = (last_sh >= 0) & (last_sh >= i - 16)
    ok_l = (last_sl >= 0) & (last_sl >= i - 16)
    sh_px = np.where(ok_h, h[np.maximum(last_sh, 0)], np.nan)
    sl_px = np.where(ok_l, l[np.maximum(last_sl, 0)], np.nan)
    with np.errstate(invalid="ignore"):
        bos_up = ok_h & (c > sh_px)
        bos_dn = ok_l & (c < sl_px)
    return bos_up, bos_dn, sh_px, sl_px


def _empty_signals(n):
    return {
        "dir": np.zeros(n, np.int8),
        "sl": np.full(n, np.nan),
        "tp": np.full(n, np.nan),     # fixed TP price (model B)
        "rr": np.full(n, np.nan),     # TP = entry +/- rr*dist (model A)
        "max_sl": np.full(n, np.nan),
        "min_rr": np.full(n, np.nan),
    }


def signals_model_a(df: pd.DataFrame, flow_min: float = 5.0, rr: float = 2.0) -> dict:
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(df)
    s = _empty_signals(n)
    c4 = pd.Series(c).shift(4).to_numpy()
    with np.errstate(invalid="ignore"):
        flow_up = (c - c4) / PIP >= flow_min - EPS
        flow_dn = (c4 - c) / PIP >= flow_min - EPS
    bos_up, bos_dn, _, _ = bos_arrays(df)
    rh = pd.Series(h).rolling(16).max().to_numpy()
    rl = pd.Series(l).rolling(16).min().to_numpy()
    rng = rh - rl
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = np.where(rng > 0, (c - rl) / rng, np.nan)
        pos_up = pos >= 0.5
        pos_dn = (1 - pos) >= 0.5
    low4 = pd.Series(l).rolling(4).min().to_numpy()
    high4 = pd.Series(h).rolling(4).max().to_numpy()
    long_ = flow_up & bos_up & pos_up
    short = flow_dn & bos_dn & pos_dn
    both = long_ & short
    long_ &= ~both
    short &= ~both
    s["dir"][long_] = 1
    s["dir"][short] = -1
    s["sl"] = np.where(long_, low4 - PIP, np.where(short, high4 + PIP, np.nan))
    s["rr"][long_ | short] = rr
    s["max_sl"][long_ | short] = 25.0
    return s


def h4_bars(df: pd.DataFrame) -> pd.DataFrame:
    b = df["server_time"].dt.floor("4h")
    g = df.groupby(b, sort=True)
    return pd.DataFrame({"high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})


def crt_setups(h4: pd.DataFrame):
    """Per H4 bar n (as C2, with C1 = n-1): long/short CRT setup flags."""
    hi, lo, cl = (h4[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(h4)
    long_ = np.zeros(n, bool)
    short = np.zeros(n, bool)
    if n >= 2:
        c1h, c1l = hi[:-1], lo[:-1]
        c2h, c2l, c2c = hi[1:], lo[1:], cl[1:]
        inside = (c2c > c1l) & (c2c < c1h)
        long_[1:] = (c2l < c1l) & inside
        short[1:] = (c2h > c1h) & inside
    return long_, short


def signals_model_b(df: pd.DataFrame) -> dict:
    n = len(df)
    s = _empty_signals(n)
    h4 = h4_bars(df)
    lset, sset = crt_setups(h4)
    hi4, lo4 = h4["high"].to_numpy(float), h4["low"].to_numpy(float)
    bucket = df["server_time"].dt.floor("4h")
    b_idx = h4.index.get_indexer(bucket)          # H4 index of each M15 bar (this is C3)
    c2 = b_idx - 1
    c1 = b_idx - 2
    valid = c1 >= 0
    c2s, c1s = np.maximum(c2, 0), np.maximum(c1, 0)
    has_long = valid & lset[c2s]
    has_short = valid & sset[c2s]
    bos_up, bos_dn, _, _ = bos_arrays(df)
    long_ = has_long & bos_up
    short = has_short & bos_dn
    both = long_ & short
    long_ &= ~both
    short &= ~both
    s["dir"][long_] = 1
    s["dir"][short] = -1
    s["sl"] = np.where(long_, lo4[c2s] - PIP, np.where(short, hi4[c2s] + PIP, np.nan))
    s["tp"] = np.where(long_, hi4[c1s], np.where(short, lo4[c1s], np.nan))
    s["max_sl"][long_ | short] = 30.0
    s["min_rr"][long_ | short] = 1.5
    return s


# ------------------------------------------------------------------ simulation
@dataclass
class Position:
    dir: int
    entry: float
    sl: float
    tp: float
    lots: float
    sl_pips: float
    entry_time: pd.Timestamp
    entry_date: object
    signal_time: pd.Timestamp


def _pnl(pos: Position, exit_px: float) -> float:
    gross = (exit_px - pos.entry) * pos.dir / PIP * PIP_VALUE * pos.lots
    return gross


def size_lots(balance, sl_pips, cfg: Config) -> float:
    raw = balance * cfg.risk_pct / (sl_pips * PIP_VALUE)
    lots = math.floor(raw / cfg.lot_step + EPS) * cfg.lot_step
    return round(max(lots, cfg.lot_min), 2)


def prepare_entry(sig: dict, i: int, d: int, open_bid: float, spread_px: float, cfg: Config):
    """Returns (entry, sl, tp, sl_pips) or a str reason for skip."""
    entry = open_bid + spread_px if d == 1 else open_bid
    sl = sig["sl"][i]
    dist = (entry - sl) * d / PIP
    if dist > sig["max_sl"][i] + EPS:
        return "sl_too_wide"
    if dist < cfg.min_sl_pips - EPS:
        dist = cfg.min_sl_pips
        sl = entry - d * dist * PIP
    if not np.isnan(sig["rr"][i]):
        tp = entry + d * sig["rr"][i] * dist * PIP
    else:
        tp = sig["tp"][i]
        tp_dist = (tp - entry) * d / PIP
        if tp_dist / dist < sig["min_rr"][i] - EPS:
            return "rr_too_low"
    return entry, sl, tp, dist


def simulate(df: pd.DataFrame, sig: dict, cfg: Config | None = None):
    cfg = cfg or Config()
    t = df["server_time"].to_numpy()
    ts = pd.DatetimeIndex(df["server_time"])
    dates = ts.normalize().to_numpy()
    mins = (ts.hour * 60 + ts.minute).to_numpy()
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    spr = df["spread"].to_numpy(float) * POINT
    win = in_window(df)
    sig_ok = np.ones(len(df), bool)
    if cfg.start is not None:
        sig_ok &= t >= np.datetime64(cfg.start)
    if cfg.end is not None:
        sig_ok &= t < np.datetime64(cfg.end + pd.Timedelta(days=1))

    balance = cfg.balance
    day = None
    day_start = balance
    entries_today = 0
    locked = False
    pos: Position | None = None
    pending = -1
    trades = []
    skips = {"sl_too_wide": 0, "rr_too_low": 0}

    def close(j, px, reason):
        nonlocal balance, pos, locked
        comm = cfg.commission_per_lot * pos.lots
        net = _pnl(pos, px) - comm
        risk = pos.lots * pos.sl_pips * PIP_VALUE
        balance += net
        trades.append({
            "signal_time": pos.signal_time, "entry_time": pos.entry_time, "exit_time": ts[j],
            "dir": "long" if pos.dir == 1 else "short", "entry": pos.entry, "sl": pos.sl,
            "tp": pos.tp, "exit": px, "sl_pips": round(pos.sl_pips, 2), "lots": pos.lots,
            "commission": comm, "pnl": net, "R": net / risk, "reason": reason, "balance": balance,
        })
        pos = None
        if balance - day_start <= -cfg.daily_lock_pct * day_start + EPS:
            locked = True

    for j in range(len(df)):
        if dates[j] != day:
            day = dates[j]
            day_start = balance
            entries_today = 0
            locked = False

        # 1. forced exit at 19:00 (or a later date)
        if pos is not None and (dates[j] != pos.entry_date or mins[j] >= FORCE_EXIT_MIN):
            close(j, o[j] if pos.dir == 1 else o[j] + spr[j], "time_exit")

        # 2. pending entry at this bar's open
        if pending >= 0:
            i = pending
            pending = -1
            if (pos is None and not locked and entries_today < cfg.max_entries_per_day
                    and dates[j] == dates[i] and mins[j] < FORCE_EXIT_MIN):
                d = int(sig["dir"][i])
                r = prepare_entry(sig, i, d, o[j], spr[j], cfg)
                if isinstance(r, str):
                    skips[r] += 1
                else:
                    entry, sl, tp, dist = r
                    pos = Position(d, entry, sl, tp, size_lots(balance, dist, cfg), dist,
                                   ts[j], dates[j], ts[i])
                    entries_today += 1

        # 3. intrabar SL / TP (SL first if both)
        if pos is not None:
            if pos.dir == 1:
                if l[j] <= pos.sl + EPS:
                    close(j, min(pos.sl, o[j]), "sl")
                elif h[j] >= pos.tp - EPS:
                    close(j, max(pos.tp, o[j]), "tp")
            else:
                ask_o, ask_h, ask_l = o[j] + spr[j], h[j] + spr[j], l[j] + spr[j]
                if ask_h >= pos.sl - EPS:
                    close(j, max(pos.sl, ask_o), "sl")
                elif ask_l <= pos.tp + EPS:
                    close(j, min(pos.tp, ask_o), "tp")

        # 4. daily loss lock on worst intrabar equity
        if pos is not None:
            worst = l[j] if pos.dir == 1 else h[j] + spr[j]
            comm = cfg.commission_per_lot * pos.lots
            limit = day_start * (1 - cfg.daily_lock_pct)
            if balance + _pnl(pos, worst) - comm <= limit + EPS:
                # price where equity == limit
                need = (limit - balance + comm) / (PIP_VALUE * pos.lots) * PIP  # signed price move
                px = pos.entry + pos.dir * need
                bar_open = o[j] if pos.dir == 1 else o[j] + spr[j]
                px = min(px, bar_open) if pos.dir == 1 else max(px, bar_open)
                close(j, px, "daily_lock")
                locked = True

        # 5. signal on this bar's close
        d = sig["dir"][j]
        if (d != 0 and pos is None and not locked and entries_today < cfg.max_entries_per_day
                and win[j] and sig_ok[j] and j + 1 < len(df)):
            pending = j

    if pos is not None:  # data ended with an open position
        j = len(df) - 1
        close(j, c[j] if pos.dir == 1 else c[j] + spr[j], "end_of_data")

    cols = ["signal_time", "entry_time", "exit_time", "dir", "entry", "sl", "tp", "exit", "sl_pips",
            "lots", "commission", "pnl", "R", "reason", "balance"]
    return pd.DataFrame(trades, columns=cols), skips


# --------------------------------------------------------------------- metrics
def summarize(tr: pd.DataFrame, start_balance: float = 10_000.0) -> dict:
    if tr.empty:
        return {"trades": 0}
    R = tr["R"].to_numpy()
    wins, losses = R[R > 0], R[R <= 0]
    cumR = np.concatenate([[0], np.cumsum(R)])
    ddR = float(np.max(np.maximum.accumulate(cumR) - cumR))
    bal = np.concatenate([[start_balance], tr["balance"].to_numpy()])
    peak = np.maximum.accumulate(bal)
    ddP = float(np.max((peak - bal) / peak) * 100)
    streak = best = 0
    for r in R:
        streak = streak + 1 if r <= 0 else 0
        best = max(best, streak)
    gp, gl = tr.loc[tr.pnl > 0, "pnl"].sum(), -tr.loc[tr.pnl <= 0, "pnl"].sum()
    et = pd.DatetimeIndex(tr["exit_time"])
    half = et.year.astype(str) + np.where(et.month <= 6, "H1", "H2")
    per_half = tr.groupby(half)["R"].sum().round(2).to_dict()
    return {
        "trades": len(tr),
        "win_rate": round(len(wins) / len(R) * 100, 1),
        "total_R": round(float(R.sum()), 2),
        "PF": round(gp / gl, 3) if gl > 0 else float("inf"),
        "max_dd_R": round(ddR, 2),
        "max_dd_pct": round(ddP, 2),
        "avg_R": round(float(R.mean()), 3),
        "longest_losing_streak": best,
        "net_pnl": round(float(tr["pnl"].sum()), 2),
        "end_balance": round(float(bal[-1]), 2),
        "losing_halves": f"{sum(v < 0 for v in per_half.values())}/{len(per_half)}",
        "per_half_year_R": per_half,
    }


def print_summary(title: str, s: dict, skips: dict | None = None):
    print(f"\n=== {title} ===")
    for k, v in s.items():
        if k == "per_half_year_R":
            print("  per_half_year_R:")
            for hk, hv in v.items():
                print(f"    {hk}: {hv:+.2f}")
        else:
            print(f"  {k}: {v}")
    if skips:
        print(f"  skipped_signals: {skips}")


def save_outputs(tr: pd.DataFrame, tag: str, start_balance: float, title: str):
    RESULTS.mkdir(parents=True, exist_ok=True)
    csv = RESULTS / f"trades_{tag}.csv"
    tr.to_csv(csv, index=False)
    png = RESULTS / f"equity_{tag}.png"
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    x = [tr["entry_time"].iloc[0]] + list(tr["exit_time"]) if len(tr) else []
    bal = [start_balance] + list(tr["balance"])
    cumR = [0] + list(tr["R"].cumsum())
    for ax, y, lab in ((a1, bal, "Balance (USD)"), (a2, cumR, "Cumulative R")):
        if x:
            ax.plot(x, y, color="#2a78d6", lw=1.5)
        ax.set_ylabel(lab, color="#555")
        ax.grid(True, color="#e5e5e5", lw=0.6)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    a1.set_title(title, loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(png, dpi=110)
    plt.close(fig)
    return csv, png


# ------------------------------------------------------------------------- CLI
def build_signals(df, model, flow, rr):
    return signals_model_a(df, flow, rr) if model == "A" else signals_model_b(df)


def run_once(df, model, flow, rr, start, end, cfg_base: Config):
    cfg = Config(**{**cfg_base.__dict__, "start": start, "end": end})
    tr, skips = simulate(df, build_signals(df, model, flow, rr), cfg)
    return tr, skips, summarize(tr, cfg.balance)


def _ts(x):
    return pd.Timestamp(x) if x else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", required=True)
    ap.add_argument("--model", choices=["A", "B"], required=True)
    ap.add_argument("--flow", type=float, default=5.0)
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--grid", action="store_true", help="IS grid -> pick best PF (>=60 trades) -> single OOS run")
    ap.add_argument("--tag", default="", help="suffix for output files")
    a = ap.parse_args(argv)

    df = load_csv(a.data)
    base = Config()
    print(f"data: {a.data}  bars={len(df):,}  {df.server_time.iloc[0]} ~ {df.server_time.iloc[-1]}")
    sfx = f"_{a.tag}" if a.tag else ""

    if not a.grid:
        tr, skips, s = run_once(df, a.model, a.flow, a.rr, _ts(a.start), _ts(a.end), base)
        label = f"model{a.model}" + (f"_flow{a.flow:g}_rr{a.rr:g}" if a.model == "A" else "")
        rng = f"{a.start or 'begin'}..{a.end or 'end'}"
        print_summary(f"{label} {rng}", s, skips)
        if len(tr):
            csv, png = save_outputs(tr, f"{label}{sfx}", base.balance, f"Venus {label} {rng}")
            print(f"  -> {csv}\n  -> {png}")
        return 0

    is_s, is_e = _ts(a.start or IS_START), _ts(a.end or IS_END)
    oos_s = _ts(OOS_START)
    if a.model == "A":
        rows = []
        for fm in (3, 5, 8):
            for rr in (1.5, 2.0, 2.5):
                _, _, s = run_once(df, "A", fm, rr, is_s, is_e, base)
                rows.append({"flow": fm, "rr": rr, "trades": s.get("trades", 0), "PF": s.get("PF", 0),
                             "total_R": s.get("total_R", 0), "max_dd_R": s.get("max_dd_R", 0)})
        grid = pd.DataFrame(rows)
        print("\nIS grid (model A):")
        print(grid.to_string(index=False))
        elig = grid[grid.trades >= 60]
        if elig.empty:
            print("WARNING: no IS combo has >= 60 trades; picking best PF among all combos.")
            elig = grid
        best = elig.sort_values(["PF", "total_R"], ascending=False).iloc[0]
        flow, rr = float(best.flow), float(best.rr)
        print(f"selected on IS: FlowMin={flow:g} RR={rr:g}")
    else:
        flow, rr = a.flow, a.rr
    label = f"model{a.model}" + (f"_flow{flow:g}_rr{rr:g}" if a.model == "A" else "")
    for name, s0, e0 in (("IS", is_s, is_e), ("OOS", oos_s, None)):
        tr, skips, s = run_once(df, a.model, flow, rr, s0, e0, base)
        print_summary(f"{name} {label} {s0.date()}..{e0.date() if e0 is not None else 'end'}", s, skips)
        if len(tr):
            csv, png = save_outputs(tr, f"{label}_{name}{sfx}", base.balance, f"Venus {label} {name}")
            print(f"  -> {csv}\n  -> {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
