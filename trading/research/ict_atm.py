"""ICT 'ATM Method' (H1) 기계화 백테스트 — 정직하게, 변형은 미리 정한 12개만.

매수 기준 (매도는 대칭, 가격을 음수로 뒤집어 같은 코드로 처리):
 1. 스윕: 가장 최근 확정된 H1 스윙 저점(프랙탈, 앞뒤 N=3봉)을 저가가 깨면 그 봉 = 스윕.
    한 번 깨진 스윙 저점은 소모(새 스윙 저점이 확정될 때까지 다음 스윕 없음).
    스윕 이후 MSS 전까지 최저가(극값)를 계속 갱신.
 2. MSS(체크 표시): 스윕 후 K=24봉 안에 H1 종가가 '극값 이전의 가장 가까운 확정 스윙 고점(N=3)' 위로 마감.
 3. 진입(지정가, 24봉 유효): (a) MSS 다리 50% = 극값 + 0.5×(MSS 봉 고가 − 극값)
                          (b) OB = 극값 이전(극값 봉 포함, 10봉 안)의 마지막 음봉 고가
    체결 전에 목표가 먼저 닿거나, 종가가 극값 아래로 마감하면 취소. 진입가가 MSS 종가 이상이면 셋업 제외.
 4. 손절 = 극값 − 1핍 − 비용.
 5. 목표: liq = 스윕 전 200봉 안의 프랙탈(N=5) 스윙 고점 중 MSS 레벨 위이고 MSS 봉까지 아직 안 깨진
              가장 최근(= 가장 가까운) 것 / rr2, rr3 = 고정 손익비.
    손익비 < 1.5 또는 손절폭 < 4×비용이면 제외.
 6. 세션 필터(옵션): MSS 봉이 뉴욕 02:00~12:00 안에 있는 것만 (봉 시작 NY 02~11시).
 7. 종목당 동시 1포지션. 진입 후 120봉 지나면 종가 청산.
관례(crt_mss_ob.py·intraday.py와 동일): 비용 = max(봉 spread, SPREAD_FLOOR)×point, 거래당 1회 차감(체결 봉 기준).
같은 봉에서 손절·목표 모두 닿으면 손절 먼저. 체결 봉에서는 목표 판정 안 함(보수적). 결과는 R.
IS = 2019~2023, OOS = 2024~. 최선 변형은 IS 거래당 평균 R로 고른다(미리 정함).
사용: python ict_atm.py venus_data.zip [trades_out.csv]
"""
import bisect
import io
import sys
import zipfile

import numpy as np
import pandas as pd

SERVER_MINUS_NY = 7
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
PIP = {"USDJPY": 0.01, "XAUUSD": 0.1}
N_SW, N_TGT, K_MSS, ORDER_BARS, HOLD_BARS, LOOKBACK_TGT, MIN_RR = 3, 5, 24, 24, 120, 200, 1.5
SPLIT = np.datetime64("2024-01-01")
VARIANTS = [(e, t, s) for e in ("a50", "bOB") for t in ("liq", "rr2", "rr3") for s in (False, True)]


def load(zp, sym):
    df = pd.read_csv(io.BytesIO(zipfile.ZipFile(zp).read(f"{sym}_H1.csv")))
    df["ny"] = pd.to_datetime(df.time, unit="s") - pd.Timedelta(hours=SERVER_MINUS_NY)
    df["cost"] = np.maximum(df.spread, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    return df.reset_index(drop=True)


def fractal_high(h, n):
    m = len(h)
    ok = np.zeros(m, bool)
    ok[n:m - n] = True
    for j in range(1, n + 1):
        ok[n:m - n] &= (h[n:m - n] > h[n - j:m - n - j]) & (h[n:m - n] >= h[n + j:m - n + j])
    return np.flatnonzero(ok)


def setups(o, h, l, c, sess):
    """뒤집힌 가격 공간에서 매수 셋업 목록: (스윕, 극값, MSS봉, MSS레벨, OB봉, 유동성목표)."""
    n = len(o)
    sl_idx = fractal_high(-l, N_SW)           # 스윙 저점
    sh_idx = list(fractal_high(h, N_SW))      # 스윙 고점
    tg_idx = fractal_high(h, N_TGT)
    out, act, p = [], None, 0
    for i in range(n):
        while p < len(sl_idx) and sl_idx[p] + N_SW <= i - 1:   # 바 i 시작 시점에 확정된 스윙 저점
            act = l[sl_idx[p]]
            p += 1
        if act is None or l[i] >= act:
            continue
        act, s, ext = None, i, i
        for k in range(s + 1, min(n, s + K_MSS + 1)):
            if l[k] < l[ext]:
                ext = k
            j = bisect.bisect_left(sh_idx, min(ext, k - N_SW + 1)) - 1
            if j < 0 or c[k] <= h[sh_idx[j]]:
                continue
            lvl = h[sh_idx[j]]
            ob = next((m for m in range(ext, max(ext - 11, -1), -1) if c[m] < o[m]), None)
            # 유동성 목표: 스윕 전에 확정된 프랙탈5 고점, MSS 레벨 위, MSS 봉까지 안 깨짐, 가장 최근
            tp = None
            q = np.searchsorted(tg_idx, s - N_TGT, side="left") - 1
            while q >= 0 and tg_idx[q] >= s - LOOKBACK_TGT:
                m = tg_idx[q]
                if h[m] > lvl and h[m + 1:k + 1].max() < h[m]:
                    tp = h[m]
                    break
                q -= 1
            out.append((s, ext, k, lvl, ob, tp, sess[k]))
            break
    return out


def trade(o, h, l, c, cost, pip, st, ent, tgt):
    s, ext, k, lvl, ob, tp_liq, _ = st
    n = len(o)
    if ent == "a50":
        entry = l[ext] + 0.5 * (h[k] - l[ext])
    else:
        if ob is None:
            return None
        entry = h[ob]
    if entry >= c[k]:
        return None
    sl = l[ext] - pip - cost[k]
    risk = entry - sl
    if risk < 4 * cost[k]:
        return None
    if tgt == "liq":
        if tp_liq is None or (tp_liq - entry) < MIN_RR * risk:
            return None
        tp = tp_liq
    else:
        tp = entry + (2.0 if tgt == "rr2" else 3.0) * risk
    if h[k] >= tp:
        return None
    for m in range(k + 1, min(n, k + 1 + ORDER_BARS)):
        if h[m] >= tp:
            return None                                  # 체결 전 목표 도달 → 취소
        if l[m] <= entry:
            cst, last = cost[m], min(n - 1, m + HOLD_BARS)
            for i in range(m, last + 1):
                if l[i] <= sl:
                    return m, i, (-risk - cst) / risk, risk / pip
                if i > m and h[i] >= tp:
                    return m, i, (tp - entry - cst) / risk, risk / pip
            return m, last, (c[last] - entry - cst) / risk, risk / pip
        if c[m] < l[ext]:
            return None
    return None


def run_symbol(df, sym):
    pip = PIP.get(sym, 0.0001)
    o, h, l, c, cost = (df[x].values.astype(float) for x in ["open", "high", "low", "close", "cost"])
    hr = df.ny.dt.hour.values
    sess = (hr >= 2) & (hr < 12)
    t = df.ny.values
    spaces = {1: (o, h, l, c), -1: (-o, -l, -h, -c)}
    sets = {d: setups(*spaces[d], sess) for d in (1, -1)}
    res = {}
    for v in VARIANTS:
        ent, tgt, filt = v
        cand = []
        for d in (1, -1):
            oo, hh, ll, cc = spaces[d]
            for st in sets[d]:
                if filt and not st[6]:
                    continue
                r = trade(oo, hh, ll, cc, cost, pip, st, ent, tgt)
                if r:
                    cand.append((r[0], r[1], d, r[2], r[3]))
        cand.sort()
        rows, busy = [], -1
        for fi, xi, d, r, rp in cand:
            if fi <= busy:
                continue
            rows.append((t[fi], sym, d, r, rp))
            busy = xi
        res[v] = pd.DataFrame(rows, columns=["t", "sym", "d", "r", "risk_pips"])
    return res


def max_streak(r):
    m = s = 0
    for x in r:
        s = s + 1 if x <= 0 else 0
        m = max(m, s)
    return m


def stats(df, days):
    r = df.sort_values("t").r.values
    if len(r) < 2:
        return dict(n=len(r), perday=len(r) / days, win=np.nan, avg=np.nan, tot=r.sum(), pf=np.nan, t=np.nan, dd=np.nan, streak=0)
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max()
    return dict(n=len(r), perday=len(r) / days, win=100 * (r > 0).mean(), avg=r.mean(), tot=r.sum(),
                pf=w / ls if ls else np.inf, t=r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), dd=dd, streak=max_streak(r))


def fmt(s):
    return (f"{s['n']:5d}건 {s['perday']:.2f}/일 승률 {s['win']:4.1f}% 평균 {s['avg']:+.3f}R 합계 {s['tot']:+7.1f}R "
            f"PF {s['pf']:.2f} t{s['t']:+.1f} 낙폭 {s['dd']:.1f}R 연패 {s['streak']}")


def main(zp, out_csv=None):
    data = {s: load(zp, s) for s in SYMBOLS}
    t_all = pd.concat([d.ny for d in data.values()])
    days = {"IS": t_all[t_all < SPLIT].dt.normalize().nunique(), "OOS": t_all[t_all >= SPLIT].dt.normalize().nunique()}
    days["ALL"] = days["IS"] + days["OOS"]
    print(f"데이터: H1 {t_all.min()} ~ {t_all.max()} (NY 시각), 거래일 IS {days['IS']} / OOS {days['OOS']}")
    per = {s: run_symbol(data[s], s) for s in SYMBOLS}
    allres, summary = [], []
    for v in VARIANTS:
        tot = pd.concat([per[s][v] for s in SYMBOLS]).sort_values("t")
        tot["variant"] = "/".join([v[0], v[1], "sess" if v[2] else "all"])
        allres.append(tot)
        parts = {"IS": tot[tot.t < SPLIT], "OOS": tot[tot.t >= SPLIT]}
        both = sum(1 for s in SYMBOLS if all(g[g.sym == s].r.sum() > 0 for g in parts.values()))
        si, so = stats(parts["IS"], days["IS"]), stats(parts["OOS"], days["OOS"])
        summary.append(dict(v=tot.variant.iloc[0] if len(tot) else str(v), key=v, IS=si, OOS=so, both=both))
        print(f"\n## {summary[-1]['v']}  (IS·OOS 둘 다 + 종목 {both}/7)")
        print("  IS ", fmt(si))
        print("  OOS", fmt(so))
        yr = tot.groupby(pd.DatetimeIndex(tot.t).year).r.sum()
        print("   연도별 " + " ".join(f"{y}:{x:+.1f}" for y, x in yr.items()))
    best = max(summary, key=lambda x: x["IS"]["avg"])
    print(f"\n### IS 최선(거래당 평균 R 기준): {best['v']} — OOS 종목별 (변경 없이)")
    for s in SYMBOLS:
        g = per[s][best["key"]]
        print(f"  {s}: IS {fmt(stats(g[g.t < SPLIT], days['IS']))}")
        print(f"  {s}: OOS {fmt(stats(g[g.t >= SPLIT], days['OOS']))}")
    print("\n### 합격 기준(OOS PF≥1.2, OOS 낙폭≤10R, OOS≥60건, IS·OOS 둘 다 + 종목 ≥4/7)")
    for x in summary:
        o = x["OOS"]
        ok = o["pf"] >= 1.2 and o["dd"] <= 10 and o["n"] >= 60 and x["both"] >= 4
        print(f"  {x['v']:16s} PF {o['pf']:.2f} 낙폭 {o['dd']:.1f}R {o['n']}건 둘다+ {x['both']}/7 → {'합격' if ok else '불합격'}")
    if out_csv:
        pd.concat(allres).to_csv(out_csv, index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
