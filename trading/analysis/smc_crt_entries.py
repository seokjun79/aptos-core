"""FTMO 진입 29건을 SMC·CRT 기준으로 라벨링한다.

입력: data/ftmo_trades.csv, data/ftmo_trade_context_15m_bars.csv
      (15분봉은 진입가 대비 핍. 진입 전 약 4시간 + 보유 구간)
출력: analysis/entry_labels.csv, 그리고 특징별 성적표(표준출력)

모든 값은 거래 방향 기준으로 뒤집는다(매도면 -1을 곱해 '유리한 쪽 = +').
진입 이후 봉은 특징 계산에 쓰지 않는다(미래 정보 금지).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
trades = pd.read_csv(ROOT / "data/ftmo_trades.csv", parse_dates=["open_time_kst"])
bars = pd.read_csv(ROOT / "data/ftmo_trade_context_15m_bars.csv", parse_dates=["bar_start_kst"])


def pre_entry(tid, open_time, sign):
    b = bars[bars.trade_id == tid].sort_values("bar_idx").copy()
    # 진입 시각이 들어 있는 봉 직전까지만 사용
    b = b[b.bar_start_kst + pd.Timedelta(minutes=15) <= open_time + pd.Timedelta(minutes=1)]
    o, h, l, c = (b[k].to_numpy(float) * sign for k in ["open_rel_pips", "high_rel_pips", "low_rel_pips", "close_rel_pips"])
    if sign < 0:  # 뒤집으면 고가와 저가가 바뀐다
        h, l = l, h
    return b.bar_start_kst.to_numpy(), o, h, l, c


def hourly(t, o, h, l, c):
    df = pd.DataFrame({"t": pd.to_datetime(t), "o": o, "h": h, "l": l, "c": c})
    df["hour"] = (df.t + pd.Timedelta(minutes=1)).dt.floor("h")
    g = df.groupby("hour").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), n=("o", "size"))
    return g[g.n == 4]  # 15분봉 4개가 다 있는 완성된 1시간봉만


def swings(h, l):
    hi = [i for i in range(1, len(h) - 1) if h[i] > h[i - 1] and h[i] >= h[i + 1]]
    lo = [i for i in range(1, len(l) - 1) if l[i] < l[i - 1] and l[i] <= l[i + 1]]
    return hi, lo


rows = []
for tr in trades.itertuples():
    sign = 1 if tr.direction == "BUY" else -1
    t, o, h, l, c = pre_entry(tr.id, tr.open_time_kst, sign)
    if len(c) < 8:
        continue
    rng_hi, rng_lo = h.max(), l.min()
    last4_hi, last4_lo = h[-4:].max(), l[-4:].min()
    prev_hi, prev_lo = h[:-4].max(), l[:-4].min()

    # SMC: 유동성 스윕 = 최근 1시간에 이전 3시간 저점(매수 기준)을 찌르고 되돌아옴
    sweep = bool(last4_lo < prev_lo and c[-1] > prev_lo)
    # 돌파 지속 = 최근 1시간에 이전 3시간 고점을 넘고 그 위에서 마감
    breakout = bool(last4_hi > prev_hi and c[-1] > prev_hi)

    # BOS: 진입 전 마지막 스윙 고점을 종가로 넘었는가 / CHoCH: 하락 구조(낮아지는 고점) 뒤 첫 상향 돌파
    sh, sl_ = swings(h, l)
    bos = bool(sh and c[-1] > h[sh[-1]])
    choch = bool(len(sh) >= 2 and h[sh[-1]] < h[sh[-2]] and bos)

    # FVG: 진입 전 최근 6봉 안에 같은 방향 공정가치갭(봉 i-2 고가 < 봉 i 저가)
    fvg = any(h[i - 2] < l[i] for i in range(max(2, len(h) - 6), len(h)))

    # 프리미엄/디스카운트: 4시간 범위에서 진입가(0)의 위치. 0=맨 아래, 1=맨 위
    pd_pos = (0 - rng_lo) / (rng_hi - rng_lo) if rng_hi > rng_lo else 0.5

    # CRT(1시간): 직전 1시간봉(C2)이 그 전 봉(C1)의 저점을 찌르고 C1 범위 안으로 마감
    H = hourly(t, o, h, l, c)
    crt = crt_against = False
    if len(H) >= 2:
        c1, c2 = H.iloc[-2], H.iloc[-1]
        crt = bool(c2.l < c1.l and c1.l < c2.c < c1.h)
        crt_against = bool(c2.h > c1.h and c1.l < c2.c < c1.h)  # 반대 방향 CRT

    rows.append(dict(
        id=tr.id, time=tr.open_time_kst, symbol=tr.symbol, dir=tr.direction, lots=tr.lots,
        pips=tr.pips, mae=tr.mae_pips, mfe=tr.mfe_pips, pattern=tr.pattern, late=tr.late_night,
        sweep=sweep, breakout=breakout, bos=bos, choch=choch, fvg=fvg,
        crt=crt, crt_against=crt_against, pd_pos=round(pd_pos, 2), discount=pd_pos < 0.5,
        range_pips=round(rng_hi - rng_lo, 1),
    ))

lab = pd.DataFrame(rows)
lab.to_csv(ROOT / "analysis/entry_labels.csv", index=False)

# 같은 시각에 같은 방향으로 두 번 들어간 중복 진입은 한 건으로 본다
uniq = lab.drop_duplicates(subset=["time", "symbol", "dir"])
print(f"분석 거래 {len(lab)}건 (중복 진입 제외 {len(uniq)}건)\n")


def report(df, col, label):
    out = []
    for val in [True, False]:
        s = df[df[col] == val]
        if len(s):
            out.append(f"{'예' if val else '아니오'}: {len(s):2d}건 승 {int((s.pips > 0).sum()):2d} "
                       f"합계 {s.pips.sum():+6.1f}핍 평균 {s.pips.mean():+5.1f} 평균역행 {s.mae.mean():+5.1f}")
    print(f"{label:<24}" + " | ".join(out))


for col, label in [("breakout", "돌파 지속(BOS 연속)"), ("sweep", "유동성 스윕 후 반전"),
                   ("bos", "BOS(구조 돌파)"), ("choch", "CHoCH(추세 전환)"),
                   ("fvg", "FVG(공정가치갭)"), ("crt", "CRT 1시간 (내 방향)"),
                   ("crt_against", "CRT 1시간 (반대 방향)"), ("discount", "디스카운트 구간 진입"),
                   ("late", "늦은 밤 진입")]:
    report(uniq, col, label)

print("\n거래별 라벨:")
print(lab[["id", "time", "symbol", "dir", "pips", "mae", "pattern", "breakout", "sweep", "bos",
           "choch", "fvg", "crt", "crt_against", "pd_pos"]].to_string(index=False))
