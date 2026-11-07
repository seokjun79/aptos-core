"""추세추종·돌파 '교과서' 전략 4종 × 변형 2개 × 7종목 시험 (2026-10-24). 규칙·숫자는 데이터를 보기 전에 정함.

공통 관례 (crt_mss_ob.py / intraday.py와 동일):
- 비용 = max(봉 spread, 현재 실제 스프레드) × point, 거래당 한 번만 뺀다. 스왑(이자)은 기본 결과에 넣지 않음 → 별도 민감도 열.
- 같은 봉에서 손절과 다른 청산이 겹치면 손절 먼저. 손절이 갭으로 넘어가면 시가(더 나쁜 값)로 체결.
- R = 진입 때 정한 초기 손절폭(k×ATR) 기준. ATR = 진폭(TR)의 단순 이동평균.
- 학습 IS 2019~2023 / 검증 OOS 2024~ (진입 시각 기준). 시각은 서버 시각(뉴욕+7h).
- 종목당 포지션은 하나. 신호는 봉 마감에서 판단, 다음 봉 시가에 진입.

전략 (변형은 각 2개, 미리 정함):
 DON_D1_20 / DON_D1_55 : 일봉 종가가 직전 20(55)일 최고가 위로 '새로' 돌파 → 다음날 시가 매수 (매도 대칭).
                         초기 손절 2×ATR(20). 종가가 직전 10(20)일 최저가 아래면 다음 시가 청산.
 DON_H4_20 / DON_H4_55 : 같은 규칙을 H1→H4(서버시각 4시간 묶음)로. 청산 채널 10/20봉.
 MAPB_RR2 / MAPB_RR3   : 전일 D1 종가 > SMA50(D1)일 때만 매수(반대면 매도). H1 저가가 EMA50에 닿은 되돌림 뒤
                         H1 종가가 EMA20 위로 다시 올라오면 다음 봉 시가 진입. 손절 1.5×ATR(H1,14), 목표 2R/3R,
                         48봉 지나면 종가 청산.
 TSM_3M / TSM_12M      : 매달 첫 거래일 시가에 리밸런스. 직전 63(252)거래일 수익률 > 0 이면 매수, 아니면 매도,
                         다음 달 첫 시가에 청산(매달 한 건, 비용 매달 부과). 손절 없음, R 단위 = 2×ATR(20).
사용: python trend_family.py venus_data.zip [portfolio_dir]
"""
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
# 현재 스왑(포인트/1박, symbols_info.txt). 2019~2021 저금리 때는 훨씬 작았으므로 '최근 수준' 민감도로만 쓴다.
SWAP = {"EURUSD": (-8.012, 1.328), "GBPUSD": (-4.83, -3.183), "USDJPY": (7.954, -16.653), "AUDUSD": (-2.308, -4.687),
        "USDCAD": (3.386, -11.119), "USDCHF": (6.106, -13.02), "XAUUSD": (-55.402, 38.28)}
SPLIT = np.datetime64("2024-01-01")
IS_DAYS = np.busday_count("2019-01-02", "2024-01-01")
OOS_DAYS = np.busday_count("2024-01-01", "2026-10-23")


def load(zp, sym, tf):
    df = pd.read_csv(io.BytesIO(zipfile.ZipFile(zp).read(f"{sym}_{tf}.csv")))
    df["srv"] = pd.to_datetime(df.time, unit="s")
    df["cost"] = np.maximum(df.spread, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    return df.reset_index(drop=True)


def to_h4(h1):
    g = h1.groupby(h1.srv.dt.floor("4h"))
    out = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                        "cost": g.cost.first()})
    out.index.name = "srv"
    return out.reset_index()


def atr(df, n):
    pc = df.close.shift(1)
    tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
    return tr.rolling(n).mean().values


def rec(t, i0, i1, d, r, risk):
    return (t[i0], t[i1], d, r, risk)


def donchian(df, n_in, n_out, k_atr=2.0, atr_n=20):
    o, h, l, c, cost = (df[k].values for k in ["open", "high", "low", "close", "cost"])
    t = df.srv.values
    a = atr(df, atr_n)
    hi_in = df.high.rolling(n_in).max().shift(1).values
    lo_in = df.low.rolling(n_in).min().shift(1).values
    hi_out = df.high.rolling(n_out).max().shift(1).values
    lo_out = df.low.rolling(n_out).min().shift(1).values
    up = c > hi_in
    dn = c < lo_in
    trades, i, n = [], max(n_in, atr_n) + 1, len(o)
    while i < n - 1:
        d = 1 if (up[i] and not up[i - 1]) else (-1 if (dn[i] and not dn[i - 1]) else 0)
        if d == 0 or np.isnan(a[i]):
            i += 1
            continue
        e = i + 1
        entry, risk = o[e], k_atr * a[i]
        sl = entry - d * risk
        x = None
        for k in range(e, n):
            if (d == 1 and l[k] <= sl) or (d == -1 and h[k] >= sl):
                px = min(o[k], sl) if d == 1 else max(o[k], sl)
                if k == e:
                    px = sl
                x = (k, px)
                break
            if k + 1 < n and ((d == 1 and c[k] < lo_out[k]) or (d == -1 and c[k] > hi_out[k])):
                x = (k + 1, o[k + 1])
                break
        if x is None:
            x = (n - 1, c[n - 1])
        trades.append(rec(t, e, x[0], d, (d * (x[1] - entry) - cost[e]) / risk, risk))
        i = x[0]  # 청산 봉 마감부터 새 신호 판단
    return trades


def ma_pullback(h1, d1, rr, k_atr=1.5, hold=48):
    o, h, l, c, cost = (h1[k].values for k in ["open", "high", "low", "close", "cost"])
    t = h1.srv.values
    e20 = h1.close.ewm(span=20, adjust=False).mean().values
    e50 = h1.close.ewm(span=50, adjust=False).mean().values
    a = atr(h1, 14)
    sma = d1.close.rolling(50).mean()
    bias = pd.Series(np.where(sma.isna(), 0, np.where(d1.close > sma, 1, -1)), index=d1.srv.dt.normalize())
    bias = bias.shift(1)  # 전일 마감 기준 (오늘 일봉은 아직 안 끝남)
    b = h1.srv.dt.normalize().map(bias).fillna(0).values
    trades, n, busy = [], len(o), -1
    touch_l = touch_s = False
    for i in range(60, n - 1):
        if l[i] <= e50[i]:
            touch_l = True
        if h[i] >= e50[i]:
            touch_s = True
        sig = 0
        if b[i] == 1 and touch_l and c[i] > e20[i] and c[i - 1] <= e20[i - 1]:
            sig = 1
        elif b[i] == -1 and touch_s and c[i] < e20[i] and c[i - 1] >= e20[i - 1]:
            sig = -1
        if c[i] > e20[i]:
            touch_l = False
        if c[i] < e20[i]:
            touch_s = False
        if sig == 0 or i < busy or np.isnan(a[i]):
            continue
        d, e = sig, i + 1
        entry, risk = o[e], k_atr * a[i]
        if risk < 4 * cost[e]:
            continue
        sl, tp = entry - d * risk, entry + d * rr * risk
        last = min(n - 1, e + hold - 1)
        x = None
        for k in range(e, last + 1):
            if (d == 1 and l[k] <= sl) or (d == -1 and h[k] >= sl):
                px = sl if k == e else (min(o[k], sl) if d == 1 else max(o[k], sl))
                x = (k, d * (px - entry))
                break
            if (d == 1 and h[k] >= tp) or (d == -1 and l[k] <= tp):
                px = tp if k == e else (max(o[k], tp) if d == 1 else min(o[k], tp))
                x = (k, d * (px - entry))
                break
        if x is None:
            x = (last, d * (c[last] - entry))
        trades.append(rec(t, e, x[0], d, (x[1] - cost[e]) / risk, risk))
        busy = x[0] + 1
    return trades


def tsmom(d1, look, k_atr=2.0):
    o, c, cost = d1.open.values, d1.close.values, d1.cost.values
    t = d1.srv.values
    a = atr(d1, 20)
    m = d1.srv.dt.to_period("M").values
    firsts = np.flatnonzero(np.r_[True, m[1:] != m[:-1]])
    trades = []
    for f, g in zip(firsts[:-1], firsts[1:]):
        if f - 1 - look < 0 or np.isnan(a[f - 1]):
            continue
        d = 1 if c[f - 1] / c[f - 1 - look] - 1 > 0 else -1
        risk = k_atr * a[f - 1]
        trades.append(rec(t, f, g, d, (d * (o[g] - o[f]) - cost[f]) / risk, risk))
    return trades


def stats(r):
    r = np.asarray(r, float)
    if len(r) == 0:
        return dict(n=0, avg=np.nan, pf=np.nan, dd=0.0, tot=0.0)
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max()
    return dict(n=len(r), avg=r.mean(), pf=w / ls if ls > 0 else 9.0, dd=dd, tot=r.sum())


def swap_r(tr, sym):
    """현재 스왑을 들고 있던 날짜 수만큼 적용했을 때 R 변화 (주말 3배는 달력일로 근사)."""
    nights = (tr.exit_time - tr.entry_time).dt.total_seconds() / 86400
    pts = np.where(tr.dir == 1, SWAP[sym][0], SWAP[sym][1]) * POINT.get(sym, 0.00001)
    return tr.R + nights.round() * pts / tr.risk


def main(zp, pdir):
    os.makedirs(pdir, exist_ok=True)
    data = {s: (load(zp, s, "D1"), load(zp, s, "H1")) for s in SYMBOLS}
    strats = {
        "DON_D1_20": lambda d1, h1: donchian(d1, 20, 10),
        "DON_D1_55": lambda d1, h1: donchian(d1, 55, 20),
        "DON_H4_20": lambda d1, h1: donchian(to_h4(h1), 20, 10),
        "DON_H4_55": lambda d1, h1: donchian(to_h4(h1), 55, 20),
        "MAPB_RR2": lambda d1, h1: ma_pullback(h1, d1, 2.0),
        "MAPB_RR3": lambda d1, h1: ma_pullback(h1, d1, 3.0),
        "TSM_3M": lambda d1, h1: tsmom(d1, 63),
        "TSM_12M": lambda d1, h1: tsmom(d1, 252),
    }
    rows, eqs = [], {}
    for name, fn in strats.items():
        allt = []
        for s in SYMBOLS:
            tr = pd.DataFrame(fn(*data[s]), columns=["entry_time", "exit_time", "dir", "R", "risk"])
            tr["symbol"] = s
            tr["Rswap"] = swap_r(tr, s)
            allt.append(tr)
            ins, oos = tr[tr.entry_time < SPLIT], tr[tr.entry_time >= SPLIT]
            a, b = stats(ins.R), stats(oos.R)
            rows.append(dict(strat=name, sym=s, **{f"is_{k}": v for k, v in a.items()},
                             **{f"oos_{k}": v for k, v in b.items()}, oos_avg_swap=oos.Rswap.mean()))
            if a["avg"] > 0 and b["avg"] > 0:
                tr[["entry_time", "exit_time", "symbol", "dir", "R"]].to_csv(f"{pdir}/{name}_{s}.csv", index=False)
        p = pd.concat(allt).sort_values("exit_time")
        eqs[name] = p
        ins, oos = p[p.entry_time < SPLIT], p[p.entry_time >= SPLIT]
        a, b = stats(ins.R), stats(oos.R)
        sub = pd.DataFrame([r for r in rows if r["strat"] == name])
        both = int(((sub.is_avg > 0) & (sub.oos_avg > 0)).sum())
        cell_pass = int(((sub.is_avg > 0) & (sub.oos_avg > 0) & (sub.oos_pf >= 1.2) & (sub.oos_dd <= 10)).sum())
        ok = b["pf"] >= 1.2 and b["dd"] <= 15 and b["n"] >= 60 and a["avg"] > 0 and b["avg"] > 0
        rows.append(dict(strat=name, sym="ALL", **{f"is_{k}": v for k, v in a.items()},
                         **{f"oos_{k}": v for k, v in b.items()}, oos_avg_swap=oos.Rswap.mean(),
                         both_pos=f"{both}/7", cell_pass=cell_pass,
                         is_tpd=a["n"] / IS_DAYS, oos_tpd=b["n"] / OOS_DAYS, PASS=ok))
    t = pd.DataFrame(rows)
    pd.set_option("display.width", 250, "display.max_columns", 30)
    fmt = {c: "{:.2f}".format for c in t.columns if t[c].dtype == float}
    print(t[t.sym == "ALL"].drop(columns="sym").to_string(index=False, formatters=fmt))
    print()
    print(t[t.sym != "ALL"][["strat", "sym", "is_n", "is_avg", "is_pf", "is_dd", "oos_n", "oos_avg", "oos_pf", "oos_dd",
                             "oos_avg_swap"]].to_string(index=False, formatters=fmt))
    t.to_csv(f"{pdir}/../data/trend_family_results.csv", index=False)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 5))
        for name, p in eqs.items():
            ax.plot(p.exit_time, p.R.cumsum(), label=name, lw=1.2)
        ax.axvline(pd.Timestamp("2024-01-01"), color="gray", ls="--")
        ax.set_title("7-symbol cumulative R (no swap), IS | OOS split 2024-01-01, server time")
        ax.legend(fontsize=8, ncol=2)
        ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(f"{pdir}/../data/trend_family_equity.png", dpi=110)
    except ImportError:
        pass


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(sys.argv[1]))
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else os.path.join(here, "..", "portfolio"))
