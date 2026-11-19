"""고객님 SMC+CRT 매매법 v2 — 성공 일지(25.10.22, 25.10.29) 그대로: 4H CRT + 5분 MSS + OB 지정가.

매수 기준 (매도는 대칭):
 1. 4H CRT: C1 범위(CRH~CRL). C2 또는 C3 동안 가격이 CRL 아래로 내려감(스윕).
 2. 5분봉 MSS: 스윕 이후, 직전 단기 고점(앞뒤 2봉 스윙)을 '몸통 마감'으로 돌파. 그 봉 종가가 CRL 위(범위 안)여야 함.
 3. OB: MSS를 만든 상승 이전의 마지막 음봉(스윕 저점 부근). 박스 = 그 봉 고가~저가.
 4. MSS 마감 후 OB 고가에 매수 지정가. 2시간(24봉) 안에 체결 안 되면 취소.
    체결 전에 가격이 목표(CRH)에 먼저 닿거나 OB 저가 아래로 마감하면 취소.
 5. 손절 = OB 저가 − 1핍 (옵션: 스윕 저점 − 1핍). 목표 = CRH.
 6. 같은 봉에서 손절·목표가 모두 닿으면 손절 먼저. 진입 후 24시간이 지나면 청산.
비용 = max(봉 spread, 현재 실제 스프레드). 학습 IS 2019~2023 / 검증 OOS 2024~.
"""
import io
import sys
import zipfile

import numpy as np
import pandas as pd

SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
PIP = {"USDJPY": 0.01, "XAUUSD": 0.1}


def load(zp, sym, tf="M5"):
    df = pd.read_csv(io.BytesIO(zipfile.ZipFile(zp).read(f"{sym}_{tf}.csv")))
    df["srv"] = pd.to_datetime(df.time, unit="s")
    df["cost"] = np.maximum(df.spread, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    return df.reset_index(drop=True)


def swing_high(h, k, n=2):
    return all(h[k] > h[k - j] for j in range(1, n + 1)) and all(h[k] >= h[k + j] for j in range(1, n + 1))


def swing_low(l, k, n=2):
    return all(l[k] < l[k - j] for j in range(1, n + 1)) and all(l[k] <= l[k + j] for j in range(1, n + 1))


def run(df, sym, sl_mode="ob", min_rr=1.0, order_bars=24, hold_bars=288):
    pip = PIP.get(sym, 0.0001)
    o, h, l, c, cost = (df[k].values for k in ["open", "high", "low", "close", "cost"])
    t = df.srv.values
    n = len(o)
    bins = ((df.srv - pd.Timestamp(0)).dt.total_seconds().astype("int64") // 14400).values
    starts = np.flatnonzero(np.r_[True, bins[1:] != bins[:-1]])
    trades, busy = [], -1
    for j in range(1, len(starts) - 2):
        a1, a2, a4 = starts[j - 1], starts[j], starts[j + 2]     # C1 시작, C2 시작, C3 끝
        if a2 - a1 < 40:
            continue
        crh, crl = h[a1:a2].max(), l[a1:a2].min()
        for d in (1, -1):
            if a2 <= busy:
                continue
            r = one(o, h, l, c, cost, a2, a4, d, crh, crl, pip, sl_mode, min_rr, order_bars, hold_bars, n)
            if r:
                trades.append((t[r[0]], d, r[1], r[2]))
                busy = r[3]
    return pd.DataFrame(trades, columns=["t", "d", "r", "risk_pips"])


def one(o, h, l, c, cost, a2, a4, d, crh, crl, pip, sl_mode, min_rr, order_bars, hold_bars, n):
    # 1) 스윕: C2~C3 안에서 CRL(매수)/CRH(매도) 너머로 처음 나간 봉
    sw = next((k for k in range(a2, a4) if (d == 1 and l[k] < crl) or (d == -1 and h[k] > crh)), None)
    if sw is None:
        return None
    ext_i = sw
    for k in range(sw + 1, a4):
        # 극값 갱신 (MSS 전까지)
        if (d == 1 and l[k] < l[ext_i]) or (d == -1 and h[k] > h[ext_i]):
            ext_i = k
        # 2) MSS: 극값 이전에 확정된 마지막 스윙 고점(매수)을 몸통 마감으로 돌파, 종가는 범위 안
        if k - ext_i < 1:
            continue
        sp = next((m for m in range(ext_i - 1, max(ext_i - 60, 2), -1)
                   if (swing_high(h, m) if d == 1 else swing_low(l, m))), None)
        if sp is None:
            continue
        lvl = h[sp] if d == 1 else l[sp]
        body_break = (d == 1 and c[k] > lvl and o[k] < c[k]) or (d == -1 and c[k] < lvl and o[k] > c[k])
        inside = crl < c[k] < crh
        if not (body_break and inside):
            continue
        # 3) OB: 극값 부근(극값 봉 포함, 이후 MSS 전까지)의 마지막 반대색 봉
        ob = None
        for m in range(k - 1, ext_i - 3, -1):
            if (d == 1 and c[m] < o[m]) or (d == -1 and c[m] > o[m]):
                if m <= ext_i + 3:
                    ob = m
                    break
        if ob is None:
            return None
        ob_hi, ob_lo = h[ob], l[ob]
        entry = ob_hi if d == 1 else ob_lo
        if sl_mode == "ob":
            sl = (ob_lo - pip) if d == 1 else (ob_hi + pip)
        else:
            sl = (l[ext_i] - pip) if d == 1 else (h[ext_i] + pip)
        tp = crh if d == 1 else crl
        risk = abs(entry - sl)
        if risk < 4 * cost[k] or d * (tp - entry) < min_rr * risk:
            return None
        # 4) 지정가 대기
        for m in range(k + 1, min(n - 1, k + 1 + order_bars)):
            if (d == 1 and h[m] >= tp) or (d == -1 and l[m] <= tp):
                return None                       # 체결 전 목표 도달 → 취소
            filled = (d == 1 and l[m] <= entry) or (d == -1 and h[m] >= entry)
            if filled:
                return sim(o, h, l, c, cost[m], m, d, entry, sl, tp, hold_bars, pip, n)
            if (d == 1 and c[m] < ob_lo) or (d == -1 and c[m] > ob_hi):
                return None
        return None
    return None


def sim(o, h, l, c, cost, i0, d, entry, sl, tp, hold, pip, n):
    risk = abs(entry - sl)
    last = min(n - 1, i0 + hold)
    for i in range(i0, last + 1):
        # 체결 봉 안에서도 손절 가능 (보수적으로 손절 먼저)
        if (d == 1 and l[i] <= sl) or (d == -1 and h[i] >= sl):
            return i0, (-risk - cost) / risk, risk / pip, i
        if i > i0 and ((d == 1 and h[i] >= tp) or (d == -1 and l[i] <= tp)):
            return i0, (abs(tp - entry) - cost) / risk, risk / pip, i
    return i0, (d * (c[last] - entry) - cost) / risk, risk / pip, last


def stats(r):
    r = np.asarray(r)
    if len(r) < 2:
        return f"{len(r)}건"
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(eq) - eq).max()
    return (f"{len(r):4d}건 승률 {100 * (r > 0).mean():4.1f}% 평균 {r.mean():+.3f}R 합계 {r.sum():+6.1f}R "
            f"PF {w / ls if ls else 9:.2f} t{t:+.1f} 낙폭 {dd:.1f}R 최대연패 {max_streak(r)}")


def max_streak(r):
    m = s = 0
    for x in r:
        s = s + 1 if x <= 0 else 0
        m = max(m, s)
    return m


if __name__ == "__main__":
    zp, sym = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "EURUSD")
    df = load(zp, sym)
    for sl_mode in ("ob", "sweep"):
        for rr in (1.0, 2.0):
            res = run(df, sym, sl_mode=sl_mode, min_rr=rr)
            days = (res.t.max() - res.t.min()) / np.timedelta64(1, "D") * 5 / 7 if len(res) else 1
            print(f"\n## {sym} 손절={sl_mode} 최소손익비={rr}  하루 {len(res) / days:.2f}회  손절 중앙값 {res.risk_pips.median():.1f}핍")
            print("  IS ", stats(res[res.t < np.datetime64("2024-01-01")].r))
            print("  OOS", stats(res[res.t >= np.datetime64("2024-01-01")].r))
            for y, g in res.groupby(pd.DatetimeIndex(res.t).year):
                print(f"    {y}: {len(g):3d}건 {g.r.sum():+6.1f}R", end="")
            print()
