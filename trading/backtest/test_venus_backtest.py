"""Unit tests for venus_backtest on tiny hand-built bar sequences.  Run: pytest trading/backtest"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import venus_backtest as vb  # noqa: E402

PIP = vb.PIP


def make_bars(start, rows, spread=0):
    """rows: list of (o, h, l, c); consecutive M15 bars from `start` (server time)."""
    t = pd.date_range(start, periods=len(rows), freq="15min")
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "server_time", t)
    df["spread"] = spread
    return df


def flat(n, px=1.1000):
    return [(px, px + PIP, px - PIP, px)] * n


# ---------------------------------------------------------------- model A pattern
def model_a_rows():
    """20 bars; bar 19 is a model A long (flow 12p, BOS over swing high @14, pos 0.93)."""
    rows = [(1.1000, 1.1002, 1.0998, 1.1000)] * 14
    rows.append((1.1000, 1.1010, 1.0998, 1.1000))   # 14: swing high 1.1010
    rows.append((1.1000, 1.1005, 1.0998, 1.1000))   # 15
    rows.append((1.1000, 1.1003, 1.0999, 1.1002))   # 16
    rows.append((1.1002, 1.1005, 1.1001, 1.1004))   # 17
    rows.append((1.1004, 1.1007, 1.1003, 1.1006))   # 18
    rows.append((1.1006, 1.1013, 1.1004, 1.1012))   # 19: signal
    return rows


START = "2024-01-03 06:00"  # bar 19 opens 10:45, closes 11:00 (London window)


def test_model_a_long_fires_only_when_all_three_hold():
    df = make_bars(START, model_a_rows())
    s = vb.signals_model_a(df, flow_min=5, rr=2.0)
    assert list(np.nonzero(s["dir"])[0]) == [19]
    assert s["dir"][19] == 1
    assert s["sl"][19] == pytest.approx(1.0999 - PIP)  # min low of 16..19 - 1 pip


def test_model_a_no_signal_when_flow_fails():
    df = make_bars(START, model_a_rows())
    assert vb.signals_model_a(df, flow_min=13)["dir"].sum() == 0  # flow is 12 pips


def test_model_a_no_signal_when_bos_fails():
    rows = model_a_rows()
    rows[19] = (1.1006, 1.1010, 1.1004, 1.1009)  # close below swing high 1.1010, flow still 9p
    s = vb.signals_model_a(make_bars(START, rows))
    assert s["dir"].sum() == 0


def test_model_a_no_signal_when_position_fails():
    rows = model_a_rows()
    rows[10] = (1.1000, 1.1060, 1.0998, 1.1000)  # range high 1.1060 -> position 0.23
    s = vb.signals_model_a(make_bars(START, rows))
    assert s["dir"].sum() == 0


def test_model_a_short_symmetric():
    rows = [(2.2 - o, 2.2 - l, 2.2 - h, 2.2 - c) for o, h, l, c in model_a_rows()]
    s = vb.signals_model_a(make_bars(START, rows))
    assert list(np.nonzero(s["dir"])[0]) == [19] and s["dir"][19] == -1
    assert s["sl"][19] == pytest.approx(2.2 - 1.0999 + PIP)


def test_swing_high_must_be_within_16_bars():
    rows = model_a_rows()
    # move the only swing high to bar 2 (older than i-16=3) -> no BOS
    rows[14] = (1.1000, 1.1002, 1.0998, 1.1000)
    rows[15] = (1.1000, 1.1002, 1.0998, 1.1000)
    rows[2] = (1.1000, 1.1010, 1.0998, 1.1000)
    up, _, _, _ = vb.bos_arrays(make_bars(START, rows))
    assert not up[19]


# ------------------------------------------------------------ SL clamp / skip rules
def _sig(n, i, d, sl, rr=2.0, tp=np.nan, max_sl=25.0, min_rr=np.nan):
    s = vb._empty_signals(n)
    s["dir"][i], s["sl"][i], s["rr"][i], s["tp"][i] = d, sl, rr, tp
    s["max_sl"][i], s["min_rr"][i] = max_sl, min_rr
    return s


def test_sl_clamped_to_6_pips():
    s = _sig(1, 0, 1, 1.1000 - 3 * PIP)
    entry, sl, tp, dist = vb.prepare_entry(s, 0, 1, 1.1000, 0.0, vb.Config())
    assert dist == pytest.approx(6) and sl == pytest.approx(1.0994) and tp == pytest.approx(1.1012)


def test_sl_too_wide_skipped_model_a_and_b():
    s = _sig(1, 0, 1, 1.1000 - 26 * PIP)
    assert vb.prepare_entry(s, 0, 1, 1.1000, 0.0, vb.Config()) == "sl_too_wide"
    s = _sig(1, 0, 1, 1.1000 - 26 * PIP, rr=np.nan, tp=1.1100, max_sl=30, min_rr=1.5)
    assert vb.prepare_entry(s, 0, 1, 1.1000, 0.0, vb.Config()) != "sl_too_wide"
    s = _sig(1, 0, 1, 1.1000 - 31 * PIP, rr=np.nan, tp=1.1100, max_sl=30, min_rr=1.5)
    assert vb.prepare_entry(s, 0, 1, 1.1000, 0.0, vb.Config()) == "sl_too_wide"


def test_buy_fills_at_ask_and_spread_counts_in_sl_distance():
    s = _sig(1, 0, 1, 1.0990)
    entry, sl, tp, dist = vb.prepare_entry(s, 0, 1, 1.1000, 12 * vb.POINT, vb.Config())
    assert entry == pytest.approx(1.10012) and dist == pytest.approx(11.2)


# ---------------------------------------------------------------- simulation
def model_a_df(after):
    return make_bars(START, model_a_rows() + after)


def test_sl_first_when_both_touched():
    # entry at bar 20 open 1.1012; SL 1.0998 (14p), TP 1.1040
    after = [(1.1012, 1.1060, 1.0990, 1.1010)] + flat(40, 1.1010)
    df = model_a_df(after)
    tr, _ = vb.simulate(df, vb.signals_model_a(df))
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t.reason == "sl" and t.exit == pytest.approx(1.0998)


def test_lot_sizing_and_R():
    after = [(1.1012, 1.1060, 1.0990, 1.1010)] + flat(40, 1.1010)
    df = model_a_df(after)
    tr, _ = vb.simulate(df, vb.signals_model_a(df))
    t = tr.iloc[0]
    # risk $50, 14 pip -> 0.357 lots -> 0.35
    assert t.lots == pytest.approx(0.35)
    assert t.pnl == pytest.approx(-14 * 10 * 0.35 - 7 * 0.35)
    assert t.R == pytest.approx(t.pnl / (0.35 * 14 * 10))


def test_tp_hit():
    after = [(1.1012, 1.1041, 1.1005, 1.1030)] + flat(4, 1.1030)
    df = model_a_df(after)
    tr, _ = vb.simulate(df, vb.signals_model_a(df))
    assert tr.iloc[0].reason == "tp" and tr.iloc[0].exit == pytest.approx(1.1040)


def test_forced_exit_at_1900():
    # bar 20 opens 11:00; flat until well past 19:00 without touching SL/TP
    after = flat(50, 1.1012)
    df = model_a_df(after)
    tr, _ = vb.simulate(df, vb.signals_model_a(df))
    assert len(tr) == 1
    t = tr.iloc[0]
    assert t.reason == "time_exit"
    assert t.exit_time == pd.Timestamp("2024-01-03 19:00")


def _day_df(day, signal_bars, crash_after=2, px=1.1000):
    """Flat day from 00:00; long signals (SL -10p) at given bar indices, each stopped out."""
    rows = flat(96, px)
    for i in signal_bars:
        rows[i + crash_after] = (px, px + PIP, px - 30 * PIP, px)
    return rows


def test_daily_two_entry_cap():
    sig_bars = [40, 44, 48]              # signal bars close 10:15, 11:15, 12:15
    rows = _day_df("d1", sig_bars) + _day_df("d2", [40])
    df = make_bars("2024-01-03 00:00", rows)
    s = vb._empty_signals(len(df))
    for i in sig_bars + [96 + 40]:
        s["dir"][i], s["sl"][i], s["rr"][i], s["max_sl"][i] = 1, 1.1000 - 10 * PIP, 2.0, 25
    tr, _ = vb.simulate(df, s)
    days = pd.DatetimeIndex(tr.entry_time).date
    assert len(tr) == 3
    assert list(pd.Series(days).value_counts().sort_index()) == [2, 1]


def test_signal_ignored_while_position_open_and_outside_window():
    rows = flat(96)
    df = make_bars("2024-01-03 00:00", rows)
    s = vb._empty_signals(len(df))
    for i in (20, 40, 41):  # 20 closes 05:15 (out of window); 41 while 40's trade open
        s["dir"][i], s["sl"][i], s["rr"][i], s["max_sl"][i] = 1, 1.1000 - 10 * PIP, 2.0, 25
    tr, _ = vb.simulate(df, s)
    assert len(tr) == 1 and tr.iloc[0].signal_time == pd.Timestamp("2024-01-03 10:00")


def test_daily_lock_on_floating_loss():
    rows = flat(96)
    rows[42] = (1.1000, 1.1001, 1.0993, 1.0995)  # -7 pips floating, SL is -10
    df = make_bars("2024-01-03 00:00", rows)
    s = vb._empty_signals(len(df))
    for i in (40, 60):
        s["dir"][i], s["sl"][i], s["rr"][i], s["max_sl"][i] = 1, 1.1000 - 10 * PIP, 2.0, 25
    tr, _ = vb.simulate(df, s, vb.Config(risk_pct=0.05))  # 5 lots, 10p = -5%
    assert len(tr) == 1                      # second signal blocked by lock
    t = tr.iloc[0]
    assert t.reason == "daily_lock"
    assert t.pnl == pytest.approx(-300.0)    # exactly -3% of 10,000
    assert t.exit == pytest.approx(1.1000 - 5.3 * PIP)


def test_daily_lock_after_realised_gap_loss_then_resets_next_day():
    rows = flat(96)
    rows[42] = (1.0920, 1.0921, 1.0919, 1.0920)  # gap 80p through 10p SL -> -4%
    rows += flat(96)
    df = make_bars("2024-01-03 00:00", rows)
    s = vb._empty_signals(len(df))
    for i in (40, 60, 96 + 40):
        s["dir"][i], s["sl"][i], s["rr"][i], s["max_sl"][i] = 1, 1.1000 - 10 * PIP, 2.0, 25
    s["sl"][96 + 40] = 1.0990
    tr, _ = vb.simulate(df, s)
    assert len(tr) == 2
    assert tr.iloc[0].reason == "sl" and tr.iloc[0].exit == pytest.approx(1.0920)
    assert pd.Timestamp(tr.iloc[1].entry_time).date() == pd.Timestamp("2024-01-04").date()


# ---------------------------------------------------------------- model B
def model_b_rows(c1_high=1.1070):
    c1 = flat(16, 1.1020)
    c1[3] = (1.1020, c1_high, 1.1019, 1.1020)
    c1[9] = (1.1020, 1.1021, 1.1000, 1.1020)
    c2 = flat(16, 1.1010)
    c2[5] = (1.1010, 1.1011, 1.0995, 1.1010)        # sweep C1 low, close 1.1010 inside
    c3 = flat(16, 1.1010)
    c3[4] = (1.1010, 1.1016, 1.1009, 1.1010)         # 09:00 swing high 1.1016
    c3[8] = (1.1010, 1.1021, 1.1009, 1.1020)         # 10:00 bar closes 10:15 > 1.1016 -> BOS
    c3[9:] = flat(7, 1.1020)
    c4 = flat(16, 1.1020)
    c4[0] = (1.1020, 1.1030, 1.1019, 1.1028)         # BOS in C4 -> setup expired
    return c1 + c2 + c3 + c4


def test_crt_setup_detection():
    df = make_bars("2024-01-03 00:00", model_b_rows())
    h4 = vb.h4_bars(df)
    long_, short = vb.crt_setups(h4)
    assert list(long_) == [False, True, False, False]
    assert not short[:3].any()
    s = vb.signals_model_b(df)
    assert list(np.nonzero(s["dir"])[0]) == [32 + 8]
    assert s["sl"][40] == pytest.approx(1.0994) and s["tp"][40] == pytest.approx(1.1070)


def test_crt_requires_close_inside_c1():
    rows = model_b_rows()
    o, h, l, c = rows[31]
    rows[31] = (o, h, 1.0985, 1.0990)  # C2 closes below C1 low -> no setup
    long_, _ = vb.crt_setups(vb.h4_bars(make_bars("2024-01-03 00:00", rows)))
    assert not long_.any()


def test_model_b_trades_and_skips_low_rr():
    df = make_bars("2024-01-03 00:00", model_b_rows(1.1070))
    tr, skips = vb.simulate(df, vb.signals_model_b(df))
    assert len(tr) == 1 and tr.iloc[0].tp == pytest.approx(1.1070)
    assert tr.iloc[0].sl_pips == pytest.approx(26)

    df = make_bars("2024-01-03 00:00", model_b_rows(1.1050))  # TP 30p / SL 26p = 1.15 < 1.5
    tr, skips = vb.simulate(df, vb.signals_model_b(df))
    assert len(tr) == 0 and skips["rr_too_low"] == 1


# ---------------------------------------------------------------- metrics
def test_summary_metrics():
    tr = pd.DataFrame({"R": [1.0, -1.0, -1.0, 2.0], "pnl": [50, -50, -50, 100],
                       "balance": [10050, 10000, 9950, 10050],
                       "exit_time": pd.to_datetime(["2024-01-05", "2024-03-01", "2024-08-01", "2024-09-01"])})
    s = vb.summarize(tr)
    assert s["trades"] == 4 and s["win_rate"] == 50.0 and s["total_R"] == 1.0
    assert s["PF"] == 1.5 and s["max_dd_R"] == 2.0 and s["longest_losing_streak"] == 2
    assert s["per_half_year_R"] == {"2024H1": 0.0, "2024H2": 1.0}


# ================================================================ v2 (C1..C3)
def day_rows(px=1.1000):
    return flat(96, px)          # one server day of M15 bars from 00:00


def _idx(hhmm):
    h, m = map(int, hhmm.split(":"))
    return (h * 60 + m) // 15   # bar index by OPEN time within a day starting 00:00


V2DAY = "2024-01-03 00:00"


def test_c1_box_uses_0200_to_0900_bars_only():
    rows = day_rows()
    rows[_idx("01:45")] = (1.1000, 1.1050, 1.0950, 1.1000)   # before box: ignored
    rows[_idx("03:00")] = (1.1000, 1.1010, 1.0999, 1.1000)   # box high 1.1010
    rows[_idx("08:45")] = (1.1000, 1.1001, 1.0992, 1.1000)   # last box bar (closes 09:00): low 1.0992
    rows[_idx("09:00")] = (1.1000, 1.1009, 1.0993, 1.1000)   # after box, inside -> no break
    rows[_idx("10:00")] = (1.1000, 1.1013, 1.0999, 1.1012)   # closes 10:15 above 1.1010
    df = make_bars(V2DAY, rows)
    long_, short, hi, lo = vb.range_breakout(df, vb.C1_BOX, vb.C1_WIN)
    k = _idx("10:00")
    assert list(np.nonzero(long_)[0]) == [k] and not short.any()
    assert hi[k] == pytest.approx(1.1010) and lo[k] == pytest.approx(1.0992)
    s = vb.signals_model_c(df, "C1", rr=1.5)
    assert list(np.nonzero(s["dir"])[0]) == [k] and s["dir"][k] == 1


def test_c1_only_first_close_outside_counts():
    rows = day_rows()
    rows[_idx("03:00")] = (1.1000, 1.1010, 1.0990, 1.1000)
    rows[_idx("09:15")] = (1.1000, 1.1013, 1.0999, 1.1012)   # first close outside, closes 09:30 (pre-window)
    rows[_idx("10:30")] = (1.1000, 1.1015, 1.0999, 1.1014)   # second break, in window -> does not count
    df = make_bars(V2DAY, rows)
    assert vb.signals_model_c(df, "C1")["dir"].sum() == 0
    # without the early break, the in-window one is the first and fires
    rows[_idx("09:15")] = flat(1)[0]
    df = make_bars(V2DAY, rows)
    s = vb.signals_model_c(df, "C1")
    assert list(np.nonzero(s["dir"])[0]) == [_idx("10:30")]
    # a later opposite break the same day is also not a second signal
    rows[_idx("11:00")] = (1.1000, 1.1001, 1.0985, 1.0986)
    s = vb.signals_model_c(make_bars(V2DAY, rows), "C1")
    assert list(np.nonzero(s["dir"])[0]) == [_idx("10:30")]


def c2_rows(break_ok=True, flow_ok=True, at="13:00"):
    rows = day_rows()
    k = _idx(at)
    rows[k - 10] = (1.1000, 1.1008, 1.0999, 1.1000)           # 16-bar high 1.1008
    rows[k - 4] = (1.1000, 1.1001, 1.0999, 1.1000 if flow_ok else 1.1006)
    for j in range(k - 3, k):
        rows[j] = (1.1000, 1.1004, 1.0999, 1.1003 if j == k - 1 else rows[j][3])
    close = 1.1010 if break_ok else 1.1007
    rows[k] = (1.1003, close + PIP, 1.1002, close)
    return rows, k


def test_c2_needs_16_bar_high_break_and_5_pip_flow():
    rows, k = c2_rows()                                        # break 1.1010 > 1.1008, flow 10p
    s = vb.signals_model_c(make_bars(V2DAY, rows), "C2")
    assert list(np.nonzero(s["dir"])[0]) == [k] and s["dir"][k] == 1
    rows, k = c2_rows(break_ok=False)                          # flow 7p but close 1.1007 < 1.1008
    assert vb.signals_model_c(make_bars(V2DAY, rows), "C2")["dir"].sum() == 0
    rows, k = c2_rows(flow_ok=False)                           # break ok but flow 4p
    assert vb.signals_model_c(make_bars(V2DAY, rows), "C2")["dir"].sum() == 0
    rows, k = c2_rows(at="11:00")                              # closes 11:15, before 12:30 window
    assert vb.signals_model_c(make_bars(V2DAY, rows), "C2")["dir"].sum() == 0
    # short symmetric
    rows, k = c2_rows()
    rows = [(2.2 - o, 2.2 - l, 2.2 - h, 2.2 - c) for o, h, l, c in rows]
    s = vb.signals_model_c(make_bars(V2DAY, rows), "C2")
    assert list(np.nonzero(s["dir"])[0]) == [k] and s["dir"][k] == -1


def test_c3_range_0900_1400_and_window_1500_1730():
    rows = day_rows()
    rows[_idx("08:45")] = (1.1000, 1.1050, 1.0950, 1.1000)   # before range: ignored
    rows[_idx("10:00")] = (1.1000, 1.1010, 1.0995, 1.1000)   # range 1.0995..1.1010
    rows[_idx("15:00")] = (1.1000, 1.1001, 1.0990, 1.0992)   # closes 15:15 below -> short
    df = make_bars(V2DAY, rows)
    long_, short, hi, lo = vb.range_breakout(df, vb.C3_RANGE, vb.C3_WIN)
    k = _idx("15:00")
    assert list(np.nonzero(short)[0]) == [k] and not long_.any()
    assert hi[k] == pytest.approx(1.1010) and lo[k] == pytest.approx(1.0995)
    # break bar closing 17:30 is outside [15:00, 17:30)
    rows[_idx("15:00")] = flat(1)[0]
    rows[_idx("17:15")] = (1.1000, 1.1001, 1.0990, 1.0992)
    assert vb.signals_model_c(make_bars(V2DAY, rows), "C3")["dir"].sum() == 0
    rows[_idx("17:15")] = flat(1)[0]
    rows[_idx("17:00")] = (1.1000, 1.1001, 1.0990, 1.0992)   # closes 17:15 -> in window
    s = vb.signals_model_c(make_bars(V2DAY, rows), "C3")
    assert list(np.nonzero(s["dir"])[0]) == [_idx("17:00")]
    # a break at 14:15 (pre-window) is the first close outside -> no signal that day
    rows[_idx("14:15")] = (1.1000, 1.1012, 1.0999, 1.1011)
    assert vb.signals_model_c(make_bars(V2DAY, rows), "C3")["dir"].sum() == 0


def test_v2_one_entry_per_day_cap():
    rows = day_rows()
    rows[_idx("13:30")] = (1.1000, 1.1001, 1.0900, 1.1000)   # stops first trade out
    rows += day_rows()
    df = make_bars(V2DAY, rows)
    s = vb._empty_signals(len(df))
    for i in (_idx("12:45"), _idx("14:00"), 96 + _idx("12:45")):
        s["dir"][i], s["sl"][i], s["rr"][i], s["max_sl"][i] = 1, 1.1000 - 10 * PIP, 2.0, 25
    s["win"] = vb.window_mask(df, vb.C2_WIN)
    tr, _ = vb.simulate(df, s, vb.Config(max_entries_per_day=1))
    assert len(tr) == 2
    assert [pd.Timestamp(t).date().day for t in tr.entry_time] == [3, 4]
    tr2, _ = vb.simulate(df, s, vb.Config(max_entries_per_day=2))   # v1 cap lets the 2nd in
    assert len(tr2) == 3
    # signal builder also keeps only the first signal of the day
    rows, k = c2_rows()
    rows2, k2 = c2_rows(at="15:00")
    rows = rows[:k + 1] + [(o + 0.002, h + 0.002, l + 0.002, c + 0.002) for o, h, l, c in rows2[k + 1:]]
    s = vb.signals_model_c(make_bars(V2DAY, rows), "C2")
    assert vb.c2_raw(make_bars(V2DAY, rows))[0].sum() >= 2     # several raw breaks that day
    assert (s["dir"] != 0).sum() == 1 and s["dir"][k] == 1


def test_trend_filter_uses_only_completed_h1_bars():
    n_days = 4
    rng = np.random.default_rng(0)
    px = 1.1 + np.cumsum(rng.normal(0, 2e-4, 96 * n_days))
    rows = [(p, p + PIP, p - PIP, p) for p in px]
    df = make_bars("2024-01-01 00:00", rows)
    h1c, ema = vb.h1_trend(df)
    # bar opening 10:30 (closes 10:45): last completed H1 is 09:00 -> its close is bar 09:45's close
    i = 96 * 3 + _idx("10:30")
    assert h1c[i] == pytest.approx(df.close[96 * 3 + _idx("09:45")])
    # bar opening 10:45 closes 11:00 -> H1 10:00 is complete, includes this bar's own close
    j = 96 * 3 + _idx("10:45")
    assert h1c[j] == pytest.approx(df.close[j])
    # no lookahead: changing everything from bar i on leaves values at i unchanged
    df2 = df.copy()
    df2.loc[i:, ["open", "high", "low", "close"]] += 0.05
    h1c2, ema2 = vb.h1_trend(df2)
    assert h1c2[i] == pytest.approx(h1c[i]) and ema2[i] == pytest.approx(ema[i])
    assert not np.isnan(ema[i])
    # EMA matches an independent computation over completed hourly closes
    hourly = df.groupby(df.server_time.dt.floor("1h"))["close"].last()
    ref = hourly.ewm(span=50, adjust=False).mean()
    assert ema[i] == pytest.approx(ref[pd.Timestamp("2024-01-04 09:00")])
    # filter blocks a long when H1 close < EMA
    s_off = vb.signals_model_c(make_bars(V2DAY, c2_rows()[0]), "C2", trend=False)
    s_on = vb.signals_model_c(make_bars(V2DAY, c2_rows()[0]), "C2", trend=True)
    assert s_off["dir"].sum() == 1 and s_on["dir"].sum() == 0   # flat day: <50 H1 bars -> EMA NaN


def test_suite_v2_verdict():
    assert vb.v2_verdict({"trades": 60, "PF": 1.2, "max_dd_R": 10.0})[0]
    ok, why = vb.v2_verdict({"trades": 59, "PF": 1.5, "max_dd_R": 11})
    assert not ok and len(why) == 2
