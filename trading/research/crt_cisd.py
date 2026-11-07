"""고객님 SMC+CRT 매매법 백테스트 (매매일지 25.10.29 성공 / 25.10.17 실패에서 정리한 규칙 v1).

규칙 (매수 기준, 매도는 대칭):
 1. 4H CRT: C1 범위(CRH~CRL). C2가 CRL 아래를 찌르고(스윕) CRL 위에서 마감.
 2. C2 마감 후 최대 8시간 동안 15분봉을 '마감된 봉'으로만 본다 (반성 1: 진행 중 캔들 매매 금지).
 3. 스윕 극값 = C2 시작 이후 최저점. CISD 전에 더 낮아지면 극값 갱신.
 4. CISD 선 = 극값을 만든 연속 음봉 묶음의 첫 음봉 시가. 어떤 봉이 그 위에서 '몸통 마감'하면 CISD 확정 (반성 2·3).
 5. FVG = 극값~CISD 확정 봉 사이에서 가장 최근의 상승 FVG (봉 k-2 고가 < 봉 k 저가).
 6. 진입: CISD 이후 어떤 봉이 FVG 위쪽까지 내려왔다가 FVG 아래쪽보다 위에서 마감(반등)하면 다음 봉 시가에 매수.
    FVG 아래로 마감하면 셋업 무효.
 7. 손절 = 극값 − 1핍. 목표 = CRH. 손익비 < 1이면 진입 안 함. 손절 폭 < 비용 4배면 진입 안 함.
 8. 청산: 손절/목표(같은 봉이면 손절 먼저) 또는 진입 후 24시간.
비용 = max(봉 spread, 현재 실제 스프레드). 학습 IS 2019~2023 / 검증 OOS 2024~.
"""
import io
import sys
import zipfile

import numpy as np
import pandas as pd

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
PIP = {"USDJPY": 0.01, "XAUUSD": 0.1}


def load(zip_path, sym):
    df = pd.read_csv(io.BytesIO(zipfile.ZipFile(zip_path).read(f"{sym}_M15.csv")))
    df["srv"] = pd.to_datetime(df.time, unit="s")
    df["cost"] = np.maximum(df.spread, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    return df.reset_index(drop=True)


def backtest(df, sym, wait_bars=32, hold_bars=96):
    pip = PIP.get(sym, 0.0001)
    o, h, l, c, cost = (df[k].values for k in ["open", "high", "low", "close", "cost"])
    t = df.srv.values
    bin4 = (df.srv - pd.Timestamp(0)).dt.total_seconds().astype("int64") // (4 * 3600)
    starts = np.flatnonzero(np.r_[True, bin4.values[1:] != bin4.values[:-1]])
    out = []
    busy_until = -1
    for j in range(1, len(starts) - 1):
        a1, a2 = starts[j - 1], starts[j]
        a3 = starts[j + 1]                       # C2 끝 = C3 시작
        if a3 - a2 < 12 or a2 - a1 < 12:          # 4시간봉이 거의 다 있어야 함
            continue
        crh, crl = h[a1:a2].max(), l[a1:a2].min()
        c2h, c2l, c2c = h[a2:a3].max(), l[a2:a3].min(), c[a3 - 1]
        for d in (1, -1):
            if d == 1 and not (c2l < crl and crl < c2c < crh):
                continue
            if d == -1 and not (c2h > crh and crl < c2c < crh):
                continue
            if a3 <= busy_until:
                continue
            r = setup(o, h, l, c, cost, a2, a3, d, crh, crl, pip, wait_bars, hold_bars)
            if r:
                out.append((t[r[0]], d, r[1], r[2]))
                busy_until = r[3]
    return pd.DataFrame(out, columns=["t", "d", "r", "risk_pips"])


def setup(o, h, l, c, cost, a2, a3, d, crh, crl, pip, wait_bars, hold_bars):
    n = len(o)
    # 극값과 그 위치 (C2 시작 이후)
    seg = np.arange(a2, a3)
    ei = seg[np.argmin(l[seg])] if d == 1 else seg[np.argmax(h[seg])]
    ext = l[ei] if d == 1 else h[ei]
    end = min(n - 1, a3 + wait_bars)
    k = a3
    cisd_i = None
    while k < end:
        # CISD 전 극값 갱신
        if (d == 1 and l[k] < ext) or (d == -1 and h[k] > ext):
            ei, ext = k, (l[k] if d == 1 else h[k])
        lvl = cisd_level(o, c, ei, d)
        if lvl is not None and ((d == 1 and c[k] > lvl) or (d == -1 and c[k] < lvl)) and k > ei:
            cisd_i = k
            break
        k += 1
    if cisd_i is None:
        return None
    # FVG: 극값 ~ CISD 봉 사이 가장 최근
    fvg = None
    for m in range(cisd_i, ei + 1, -1):
        if d == 1 and h[m - 2] < l[m]:
            fvg = (h[m - 2], l[m]); break          # (아래, 위)
        if d == -1 and l[m - 2] > h[m]:
            fvg = (h[m], l[m - 2]); break
    if fvg is None:
        return None
    fb, ft = fvg
    for m in range(cisd_i + 1, min(n - 1, cisd_i + wait_bars)):
        touched = (d == 1 and l[m] <= ft) or (d == -1 and h[m] >= fb)
        if not touched:
            continue
        if (d == 1 and c[m] < fb) or (d == -1 and c[m] > ft):
            return None                            # FVG를 뚫고 마감 → 무효
        if (d == 1 and l[m] <= ext) or (d == -1 and h[m] >= ext):
            return None
        ei_entry = m + 1
        entry = o[ei_entry]
        sl = ext - d * pip
        tp = crh if d == 1 else crl
        risk = abs(entry - sl)
        if d * (entry - sl) <= 0 or risk < 4 * cost[m]:
            return None
        if d * (tp - entry) < risk:
            return None
        return simulate(o, h, l, c, cost[m], ei_entry, d, entry, sl, tp, hold_bars, pip)
    return None


def cisd_level(o, c, ei, d):
    # 극값 봉에서 거꾸로, 연속된 음봉(매수 셋업) 묶음의 첫 봉 시가
    k = ei
    bear = (lambda i: c[i] < o[i]) if d == 1 else (lambda i: c[i] > o[i])
    if not bear(k):
        k -= 1
        if k < 0 or not bear(k):
            return None
    while k - 1 >= 0 and bear(k - 1):
        k -= 1
    return o[k]


def simulate(o, h, l, c, cost, i0, d, entry, sl, tp, hold, pip):
    risk = abs(entry - sl)
    last = min(len(o) - 1, i0 + hold)
    for i in range(i0, last + 1):
        if (d == 1 and l[i] <= sl) or (d == -1 and h[i] >= sl):
            return i0, (-risk - cost) / risk, risk / pip, i
        if (d == 1 and h[i] >= tp) or (d == -1 and l[i] <= tp):
            return i0, (abs(tp - entry) - cost) / risk, risk / pip, i
    return i0, (d * (c[last] - entry) - cost) / risk, risk / pip, last


def stats(r):
    r = np.asarray(r)
    if len(r) < 2:
        return f"{len(r)}건"
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    t = r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
    eq = np.cumsum(r); dd = (np.maximum.accumulate(eq) - eq).max()
    return f"{len(r):4d}건 승률 {100*(r>0).mean():4.1f}% 평균 {r.mean():+.3f}R 합계 {r.sum():+6.1f}R PF {w/ls if ls else 9:.2f} t{t:+.1f} 낙폭 {dd:.1f}R"


def main(zp):
    allr = []
    for s in SYMBOLS:
        res = backtest(load(zp, s), s)
        res["sym"] = s
        allr.append(res)
        print(f"[{s}] 손절 중앙값 {res.risk_pips.median():.1f}핍")
        print("   IS ", stats(res[res.t < np.datetime64("2024-01-01")].r))
        print("   OOS", stats(res[res.t >= np.datetime64("2024-01-01")].r))
    a = pd.concat(allr)
    days = (a.t.max() - a.t.min()) / np.timedelta64(1, "D") * 5 / 7
    print(f"\n[7종목 합계] 하루 평균 {len(a)/days:.2f}회")
    print("   IS ", stats(a[a.t < np.datetime64("2024-01-01")].r))
    print("   OOS", stats(a[a.t >= np.datetime64("2024-01-01")].r))
    a.to_csv("crt_cisd_trades.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1])
