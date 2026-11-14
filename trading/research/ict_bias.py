"""프로젝트 2 ICT 2차: 일일 바이어스가 얼마나 맞아야 하나(A) + 미리 알 수 있는 바이어스 규칙의 적중률(B).
읽기 전용 분석 스크립트, 주문 없음. 정보 제공용이며 매매 결정은 석준님이 해요.

규칙 원문(사람용): trading/projects/02-ict/rules_bias.md — 이 docstring과 같은 내용이다.
규칙·숫자는 실제 데이터를 보기 전에(2026-10-29) 고정했다. 결과를 보고 바꾸지 않는다.

1차 코드 trading/research/ict_backtest.py(커밋 a2d7682)를 import 해서 데이터 읽기·시간·체결(simulate)·통계를 그대로 쓴다.
→ 이 파일과 ict_backtest.py 를 같은 폴더에 둔다. ict_backtest.py 의 결과 로직은 바꾸지 않는다.

시간: 데이터 = MT5 서버시간(= 뉴욕 + 7). 규칙 시각은 뉴욕(NY). 한국시간 = NY + 13(서머타임) / + 14.
오늘의 방향(정답) = sign( NY 16:00 종가(서버 22:55 봉 종가) − 자정 시가 MO(NY 00:00 = 서버 07:00 봉 시가) ). 0 이면 제외.
 (서버 D1이 아니라 '자정 → 16시'로 고정: PO3 거래와 1차 89% 통계가 이 구간을 쓴다.)
유효일: 거래일 인덱스 ≥ 21, ADR20 > 0, 아시아 범위(NY19~24) 봉 ≥ 30, 자정~11시 봉 있음, 그날 마지막 봉 ≥ NY 13:00.

A. 정답 섞기(오라클) — 거래 모델 5개, 진입·손절은 1차 그대로, 매도는 가격 뒤집기로 완전 대칭:
 PO3-2R  : 자정~11시 MO − 1u 매수 지정가, 손절 진입 − 2u, 목표 2R(4u), 아니면 NY16:00 종가 (= 1차 M2-MO-PO3)
 PO3-T11 : 같은 진입·손절, 목표 없음, NY 11:00 직전 봉 종가 청산
 PO3-T16 : 같은 진입·손절, 목표 없음, NY 16:00 직전 봉 종가 청산
 BRK-2R  : 좁은 AR(≤0.4 ADR20), 자정 뒤 AR 저가가 먼저 깨진 뒤 AR 고가 매수 스톱, 손절 그때까지 최저 − 1핍(최소 1u),
           목표 2R (= 1차 M2-ASIA-BRK)
 BRK-T16 : 같은 진입·손절, 목표 없음, NY 16:00 청산
 맞은 쪽 거래(그날 실제 방향 쪽) R합 Sc·건수 Nc, 틀린 쪽(반대) Sw·Nw.
 정확도 p 기대 평균 R(p) = (p·Sc + (1−p)·Sw) / (p·Nc + (1−p)·Nw).  손익분기 p* = Sw / (Sw − Sc)  (Sc > 0 > Sw).
 Sc ≤ 0 → p* 없음(정답을 알아도 손해). Sw ≥ 0 → 바이어스 없어도 +(p* ≤ 0.5).
 p = 0.50..1.00 (0.05 간격). 확인용 몬테카를로 200회(시드 고정): 5%·50%·95%.
 B 관문에 쓰는 p* = 모델별 '9종목 합계 IS' 값.

B. 바이어스 규칙 15개 (모두 NY 00:00 = 서버 07:00 봉 직전에 알려진 정보만):
 P = 서버 07:00 직전 봉 종가. PD = D−1 일봉, PDH/PDL = D−2 일봉 고·저. 지난주 = 완성된 직전 주봉.
 P0  PH1-B       : 1차 바이어스(지난주 종가 vs 그 전 주 중간, D−1 종가 vs D−2 중간, 같으면 그 방향)
 P1  PD-CE       : D−1 종가 vs D−1 범위 중간
 P2  PD-RULE     : D−1이 PDH 넘고 종가 > PDH → +1, 넘었는데 종가 ≤ PDH → −1. PDL 거울. 둘 다 넘으면 종가 PDH 위 +1 / PDL 아래 −1 / 사이 0
 P3  SWEEP-LAST  : D−1 안에서 마지막에 쓸린 쪽(PDH/PDL)의 반대. 한쪽만이면 그 반대. 같은 봉 동시 → 0
 P4  CLOSE-LOC   : D−1 종가가 범위 위 25% → +1, 아래 25% → −1
 P5  WEEK-DRAW   : PWH·PWL 중 이번 주 아직 안 깨진 쪽으로. 둘 다 안 깨졌으면 P에서 가까운 쪽. 둘 다 깨졌으면 0
 P6  DAILY-FVG   : 최근 60일 일봉 FVG 중 생긴 뒤 CE까지 안 닿은 것, P 위·아래 중 가까운 쪽으로(P가 안에 있으면 제외)
 P7  WEEK-OPEN   : P vs 이번 주 시가
 P8  MT-EXTREME  : 수·목·금만. 이번 주 완성된 날 중 최저가가 월·화이고 최고가가 그 뒤 날 → +1, 거울 → −1
 P9  ASIA-PD     : AR 중간 > D−1 범위 중간(프리미엄) → −1, < → +1
 P10 EMA20       : 일봉 종가 EMA20 기울기(D−1 − D−2)  (기준선)
 P11 RET5        : D−1 종가 − D−6 종가  (기준선)
 C1 = P2∧P5 일치, C2 = P5∧P6 일치, C3 = P2∧P5∧P7 일치
 적중률 = 맞은 날 / 예측한 날(유효일, 예측≠0, 방향≠0). t = (h−0.5)/√(0.25/n). Bonferroni 한쪽 5%·15개 → 2.71.
 관문 = 9종목 합계 IS 적중률 > p*(모델) 그리고 9종목 합계 OOS 적중률 > 같은 p*.
 관문 통과 쌍만 정식 판정(README 기준): OOS ≥ 60건, OOS 평균R > 0, OOS PF ≥ 1.2, IS 평균R > 0, 종목 과반 IS·OOS 둘 다 +,
 연도 과반 +, IS t ≥ Bonferroni(15 × 5 = 75쌍 고정 → 3.21), 랜덤워크 2개(스프레드 0) t < 2.
 모두 통과 = 합격 / IS·OOS 평균 둘 다 + = 후보(실전 권유 안 함) / 그 밖 불합격. 관문 못 넘은 쌍은 참고로만 CSV에.

사용:
  py -3.12 ict_bias.py --selftest
  py -3.12 ict_bias.py --data-dir C:\\Users\\kun00\\venus\\mt5_m5_data --out C:\\Users\\kun00\\venus\\ict_bias_out
  옵션: --symbols EURUSD,GBPUSD  --spread-map GBPJPY=2.5  --pip-map XAUUSD=0.1  --rw 2  --seeds 200  --no-chart
필요: Python 3.10+, pandas, numpy (matplotlib 있으면 그림 PNG도 저장).
"""
import argparse
import copy
import hashlib
import math
import os
import sys
import time as _time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("pandas/numpy not found. Run:  py -3.12 -m pip install pandas numpy")
    sys.exit(1)
try:
    import ict_backtest as ib
except ImportError:
    print("ict_backtest.py 를 이 파일과 같은 폴더에 두세요 (trading/research/ict_backtest.py, 커밋 a2d7682).")
    sys.exit(1)

NS_D, NS_H = ib.NS_D, ib.NS_H
IB_SHA256 = "629772f329a7fbe8d981323a6d55f2fa208598a9890d1e86b01af0fb1599017c"   # 1차 실행에 쓴 ict_backtest.py
TRADE_MODELS = ["PO3-2R", "PO3-T11", "PO3-T16", "BRK-2R", "BRK-T16"]
MODEL_DESC = {"PO3-2R": "자정시가-1u 매수, 2R 목표 (1차 M2-MO-PO3)", "PO3-T11": "같은 진입, NY11시 청산",
              "PO3-T16": "같은 진입, NY16시 청산", "BRK-2R": "아시아 박스 털고 돌파, 2R (1차 M2-ASIA-BRK)",
              "BRK-T16": "같은 진입, NY16시 청산"}
BASE_PRED = ["P0-PH1B", "P1-PDCE", "P2-PDRULE", "P3-SWEEPLAST", "P4-CLOSELOC", "P5-WEEKDRAW", "P6-DAILYFVG",
             "P7-WEEKOPEN", "P8-MTEXTREME", "P9-ASIAPD", "P10-EMA20", "P11-RET5"]
COMBOS = {"C1-RULE+WEEK": ("P2-PDRULE", "P5-WEEKDRAW"),
          "C2-WEEK+FVG": ("P5-WEEKDRAW", "P6-DAILYFVG"),
          "C3-RULE+WEEK+WO": ("P2-PDRULE", "P5-WEEKDRAW", "P7-WEEKOPEN")}
PREDICTORS = BASE_PRED + list(COMBOS)
P_GRID = np.round(np.arange(0.50, 1.0001, 0.05), 2)
FVG_LOOKBACK = 60
EMA_N = 20
BONF_HIT = ib.norm_ppf(1 - 0.05 / len(PREDICTORS))                       # 15개 → 2.71
BONF_TRADE = ib.norm_ppf(1 - 0.05 / (len(PREDICTORS) * len(TRADE_MODELS)))  # 75쌍 → 3.21
SEED0 = 20261029


# ---------------------------------------------------------------- 작은 판정 함수 (자체 시험 대상, 원래 가격 기준)
def sgn(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def pd_rule(pdh, pdl, h, l, c):
    """P2 ICT 일봉 규칙. pdh/pdl = D−2 고저, h/l/c = D−1 고저종."""
    th, tl = h > pdh, l < pdl
    if th and tl:
        return 1 if c > pdh else (-1 if c < pdl else 0)
    if th:
        return 1 if c > pdh else -1
    if tl:
        return -1 if c < pdl else 1
    return 0


def sweep_last(ih, il):
    """P3: ih/il = D−1 안에서 PDH/PDL을 처음 넘은 M5 봉 순번(-1 = 안 넘음). 마지막에 쓸린 쪽의 반대."""
    if ih < 0 and il < 0:
        return 0
    if il < 0:
        return -1
    if ih < 0:
        return 1
    if ih == il:
        return 0
    return -1 if ih > il else 1


def close_loc(h, l, c):
    """P4: 종가 위치 위 25% → +1, 아래 25% → −1."""
    rg = h - l
    if not rg > 0:
        return 0
    x = (c - l) / rg
    return 1 if x >= 0.75 else (-1 if x <= 0.25 else 0)


def week_draw(p, pwh, pwl, hi_sofar, lo_sofar):
    """P5: 이번 주 지금까지 고저(hi_sofar/lo_sofar, 없으면 −inf/+inf)로 안 깨진 지난주 고저 쪽."""
    up, dn = hi_sofar < pwh, lo_sofar > pwl
    if up and dn:
        a, b = pwh - p, p - pwl
        return 1 if a < b else (-1 if b < a else 0)
    if up:
        return 1
    if dn:
        return -1
    return 0


def fvg_draw(p, dH, dL, d, pre_h, pre_l, lookback=FVG_LOOKBACK):
    """P6: 일봉 k(d−1 ~ d−lookback)에서 생긴 FVG 중 생긴 뒤(k+1 ~ 지금) CE까지 안 닿은 것. 가까운 쪽 방향.
    pre_h/pre_l = 오늘 판단 시점 전 봉의 고저(없으면 −inf/+inf)."""
    run_h, run_l = pre_h, pre_l
    best_up = best_dn = math.inf
    for k in range(d - 1, max(2, d - lookback) - 1, -1):
        zones = []
        if dL[k] > dH[k - 2]:
            zones.append((dH[k - 2], dL[k]))
        if dH[k] < dL[k - 2]:
            zones.append((dH[k], dL[k - 2]))
        for lo, hi in zones:
            ce = (lo + hi) / 2
            if lo > p:
                if run_h < ce:
                    best_up = min(best_up, lo - p)
            elif hi < p:
                if run_l > ce:
                    best_dn = min(best_dn, p - hi)
        run_h = max(run_h, dH[k])
        run_l = min(run_l, dL[k])
    if best_up < best_dn:
        return 1
    if best_dn < best_up:
        return -1
    return 0


def mt_extreme(dows, lows, highs):
    """P8: 이번 주 완성된 날들(요일·저가·고가 목록, 시간 순). 최저 날이 월·화이고 최고 날이 그 뒤 → +1, 거울 → −1."""
    if not dows:
        return 0
    jl, jh = int(np.argmin(lows)), int(np.argmax(highs))
    if dows[jl] <= 1 and jh > jl:
        return 1
    if dows[jh] <= 1 and jl > jh:
        return -1
    return 0


def breakeven(sc, nc, sw, nw):
    """손익분기 정확도 p*. 돌려줌 (p*, 메모). p* NaN = 없음."""
    if nc == 0 or sc <= 0:
        return np.nan, "정답 알아도 손해"
    if sw >= 0:
        return 0.0, "바이어스 없어도 +"
    return sw / (sw - sc), ""


def exp_avg(p, sc, nc, sw, nw):
    den = p * nc + (1 - p) * nw
    return (p * sc + (1 - p) * sw) / den if den > 0 else np.nan


# ---------------------------------------------------------------- 종목 하나 → 날짜 표
def day_frame(X, S1):
    """날마다 판단 시점 인덱스·유효일·정답."""
    t, nd = X.t, X.nd
    base = X.dkey * NS_D
    ra = np.searchsorted(t, base + 2 * NS_H)
    rb = np.searchsorted(t, base + 7 * NS_H)
    te = np.searchsorted(t, base + 18 * NS_H)
    ex16 = X.exit_idx
    ex11 = te - 1
    ok = np.zeros(nd, bool)
    lab = np.zeros(nd, int)
    for d in range(21, nd):
        if not S1.adr20[d] > 0:
            continue
        if not (rb[d] - ra[d] >= 30 and te[d] > rb[d] + 1 and rb[d] < X.dend[d]):
            continue
        e = int(ex16[d])
        if e < rb[d] or e >= X.n or X.bar_day[e] != d or t[e] < base[d] + 20 * NS_H:
            continue
        ok[d] = True
        lab[d] = sgn(S1.C[e] - S1.O[rb[d]])
    return dict(ra=ra, rb=rb, te=te, ex11=ex11, valid=ok, label=lab)


def dir_trades(S, X, X11, info):
    """한 공간(매수 / 뒤집은 매도)의 날마다 거래 R. {모델: R 배열(없으면 NaN)} + 체결 인덱스. 진입·손절은 ib.model_m2 그대로."""
    nd = X.nd
    R = {m: np.full(nd, np.nan) for m in TRADE_MODELS}
    F = {m: np.full(nd, -1, np.int64) for m in TRADE_MODELS}
    H, L, O = S.H, S.L, S.O

    def rec(m, XX, f, entry, sl, tp, d):
        risk = entry - sl
        if risk <= 0 or risk < X.min_risk or tp <= entry:
            return
        xi, px, _ = ib.simulate(S, XX, f, entry, sl, tp, True)
        R[m][d] = (px - entry - X.cost) / risk
        F[m][d] = f

    for i in np.flatnonzero(info["valid"]):
        i = int(i)
        adr = S.adr20[i]
        u = adr / ib.ICT_PIP_DIV
        ra, rb, te = int(info["ra"][i]), int(info["rb"][i]), int(info["te"][i])
        ah, al = H[ra:rb].max(), L[ra:rb].min()
        rg = ah - al
        mo = O[rb]
        entry = mo - u
        f = ib.first_true(L[rb:te] <= entry)
        if f >= 0:
            f += rb
            sl = entry - 2 * u
            rec("PO3-2R", X, f, entry, sl, entry + 4 * u, i)
            rec("PO3-T11", X11, f, entry, sl, math.inf, i)
            rec("PO3-T16", X, f, entry, sl, math.inf, i)
        if 0 < rg <= ib.CONSOL_X * adr:
            slo = ib.first_true(L[rb:te] < al)
            shi = ib.first_true(H[rb:te] >= ah)
            if slo >= 0 and shi > slo:
                f = rb + shi
                entry = max(ah, O[f])
                sl = min(L[rb:f].min() - X.buf, entry - u)
                rec("BRK-2R", X, f, entry, sl, entry + 2 * (entry - sl), i)
                rec("BRK-T16", X, f, entry, sl, math.inf, i)
    return R, F


def predictors(X, S1, info):
    """15개 규칙 → {이름: int8 배열}. 원래 가격(S1) 기준. 판단 시점(rb) 전 정보만 쓴다."""
    nd, t = X.nd, X.t
    H, L, O, C = S1.H, S1.L, S1.O, S1.C
    dO, dH, dL, dC = S1.dO, S1.dH, S1.dL, S1.dC
    dHl, dLl = S1.dHl, S1.dLl
    rb, ra = info["rb"], info["ra"]
    dow = ((X.dkey + 3) % 7).astype(int)                         # 0 = 월 (서버 날짜 = 그날 NY 자정 날짜)
    out = {p: np.zeros(nd, np.int8) for p in PREDICTORS}
    out["P0-PH1B"][:] = S1.bias
    # EMA20
    a = 2.0 / (EMA_N + 1)
    ema = np.empty(nd)
    ema[0] = dC[0]
    for k in range(1, nd):
        ema[k] = ema[k - 1] + a * (dC[k] - ema[k - 1])
    for d in range(7, nd):
        r = int(rb[d])
        if r <= 0:
            continue
        p = C[r - 1]
        s0 = int(X.dstart[d])
        pre_h = H[s0:r].max() if r > s0 else -math.inf
        pre_l = L[s0:r].min() if r > s0 else math.inf
        h1, l1, c1 = dH[d - 1], dL[d - 1], dC[d - 1]
        out["P1-PDCE"][d] = sgn(c1 - (h1 + l1) / 2)
        pdh, pdl = dH[d - 2], dL[d - 2]
        out["P2-PDRULE"][d] = pd_rule(pdh, pdl, h1, l1, c1)
        s, e = int(X.dstart[d - 1]), int(X.dend[d - 1])
        out["P3-SWEEPLAST"][d] = sweep_last(ib.first_true(H[s:e] > pdh), ib.first_true(L[s:e] < pdl))
        out["P4-CLOSELOC"][d] = close_loc(h1, l1, c1)
        w = int(X.dweek[d])
        wf = int(X.wfirst_d[w])
        if w >= 1:
            hs = max(max(dHl[wf:d]) if d > wf else -math.inf, pre_h)
            ls = min(min(dLl[wf:d]) if d > wf else math.inf, pre_l)
            out["P5-WEEKDRAW"][d] = week_draw(p, S1.wH[w - 1], S1.wL[w - 1], hs, ls)
        out["P6-DAILYFVG"][d] = fvg_draw(p, dHl, dLl, d, pre_h, pre_l)
        out["P7-WEEKOPEN"][d] = sgn(p - O[int(X.dstart[wf])])
        if dow[d] in (2, 3, 4) and d > wf:
            out["P8-MTEXTREME"][d] = mt_extreme(list(dow[wf:d]), dLl[wf:d], dHl[wf:d])
        if r - int(ra[d]) >= 30:
            am = (H[int(ra[d]):r].max() + L[int(ra[d]):r].min()) / 2
            out["P9-ASIAPD"][d] = -sgn(am - (h1 + l1) / 2)
        out["P10-EMA20"][d] = sgn(ema[d - 1] - ema[d - 2])
        out["P11-RET5"][d] = sgn(dC[d - 1] - dC[d - 6])
    for name, parts in COMBOS.items():
        arr = np.stack([out[q] for q in parts])
        agree = (arr == arr[0]).all(axis=0) & (arr[0] != 0)
        out[name] = np.where(agree, arr[0], 0).astype(np.int8)
    return out


def symbol_table(sym, df, pip, spread_pips):
    """종목 하나 → 날마다 한 줄(정답, 규칙 15개, 모델별 매수/매도 거래 R)."""
    X = ib.Ctx(df, pip, spread_pips)
    o, h, l, c = (df[x].values.astype(float) for x in ("o", "h", "l", "c"))
    S1, Sm = ib.Space(X, o, h, l, c, 1), ib.Space(X, o, h, l, c, -1)
    info = day_frame(X, S1)
    X11 = copy.copy(X)
    X11.exit_idx = info["ex11"]
    Rb, Fb = dir_trades(S1, X, X11, info)
    Rs, Fs = dir_trades(Sm, X, X11, info)
    pr = predictors(X, S1, info)
    day_ts = pd.to_datetime(X.dkey * NS_D)
    tab = pd.DataFrame({"symbol": sym, "date": pd.DatetimeIndex(day_ts).strftime("%Y-%m-%d"),
                        "dow": ((X.dkey + 3) % 7).astype(int), "year": pd.DatetimeIndex(day_ts).year,
                        "period": np.where(day_ts < pd.Timestamp(ib.OOS_START), "IS", "OOS"),
                        "valid": info["valid"], "label": info["label"],
                        "mo_server": pd.DatetimeIndex(pd.to_datetime(X.dkey * NS_D + 7 * NS_H)).strftime("%Y-%m-%d %H:%M"),
                        "mo_kst": ib.server_to_kst(pd.to_datetime(X.dkey * NS_D + 7 * NS_H)).strftime("%Y-%m-%d %H:%M")})
    for p in PREDICTORS:
        tab[p] = pr[p]
    for m in TRADE_MODELS:
        tab[f"{m}|BUY"] = Rb[m]
        tab[f"{m}|SELL"] = Rs[m]
    rng = (int(X.t[0]), int(X.t[-1]))
    return tab, rng, dict(X=X, S1=S1, Sm=Sm, info=info, Fb=Fb, Fs=Fs, rb=info["rb"])


# ---------------------------------------------------------------- A: 오라클
def oracle_parts(g, m):
    """g = 날짜 표 일부. 맞은 쪽·틀린 쪽 R 배열(NaN = 거래 없음)."""
    v = g[g["valid"] & (g["label"] != 0)]
    up = (v["label"] == 1).values
    rb_, rs_ = v[f"{m}|BUY"].values, v[f"{m}|SELL"].values
    return np.where(up, rb_, rs_), np.where(up, rs_, rb_)


def part_a(tab, seeds):
    curves, bes = [], []
    syms = sorted(tab["symbol"].unique())
    for m in TRADE_MODELS:
        for sym in syms + ["ALL"]:
            gs = tab if sym == "ALL" else tab[tab["symbol"] == sym]
            for per in ("IS", "OOS", "ALL"):
                g = gs if per == "ALL" else gs[gs["period"] == per]
                rc, rw = oracle_parts(g, m)
                mc_, mw_ = ~np.isnan(rc), ~np.isnan(rw)
                sc, nc, sw, nw = rc[mc_].sum(), int(mc_.sum()), rw[mw_].sum(), int(mw_.sum())
                ps, note = breakeven(sc, nc, sw, nw)
                bes.append(dict(model=m, symbol=sym, period=per, days=len(rc), Nc=nc, avgR_correct=sc / nc if nc else np.nan,
                                Nw=nw, avgR_wrong=sw / nw if nw else np.nan, avgR_p50=exp_avg(0.5, sc, nc, sw, nw),
                                avgR_p100=exp_avg(1.0, sc, nc, sw, nw), p_star=ps, note=note))
                rng = np.random.default_rng(SEED0 + len(curves))
                n = len(rc)
                for p in P_GRID:
                    row = dict(model=m, symbol=sym, period=per, p=p, exp_avgR=exp_avg(p, sc, nc, sw, nw),
                               exp_trades=p * nc + (1 - p) * nw)
                    if seeds > 0 and n > 0 and (sym == "ALL" or seeds <= 50):
                        cor = rng.random((seeds, n)) < p
                        rr = np.where(cor, rc[None, :], rw[None, :])
                        cnt = (~np.isnan(rr)).sum(axis=1)
                        avg = np.where(cnt > 0, np.nansum(rr, axis=1) / np.maximum(cnt, 1), np.nan)
                        row.update(mc_p05=np.nanpercentile(avg, 5), mc_p50=np.nanpercentile(avg, 50),
                                   mc_p95=np.nanpercentile(avg, 95))
                    curves.append(row)
    return pd.DataFrame(curves), pd.DataFrame(bes)


# ---------------------------------------------------------------- B: 적중률·관문·거래
def hit_stats(pred, lab):
    m = (pred != 0) & (lab != 0)
    n = int(m.sum())
    if n == 0:
        return dict(n_pred=0, hits=0, hit=np.nan, t=np.nan, share_up_pred=np.nan)
    hits = int((pred[m] == lab[m]).sum())
    h = hits / n
    return dict(n_pred=n, hits=hits, hit=h, t=(h - 0.5) / math.sqrt(0.25 / n), share_up_pred=(pred[m] == 1).mean())


def part_b_hits(tab):
    rows = []
    syms = sorted(tab["symbol"].unique())
    for p in PREDICTORS:
        for sym in syms + ["ALL"]:
            gs = tab if sym == "ALL" else tab[tab["symbol"] == sym]
            for per in ("IS", "OOS"):
                g = gs[(gs["period"] == per) & gs["valid"] & (gs["label"] != 0)]
                lab, pr = g["label"].values, g[p].values
                st = hit_stats(pr, lab)
                u = (lab == 1).mean() if len(lab) else np.nan
                q = st["share_up_pred"]
                eh = q * u + (1 - q) * (1 - u) if st["n_pred"] else np.nan
                z_adj = (st["hit"] - eh) / math.sqrt(eh * (1 - eh) / st["n_pred"]) if st["n_pred"] and 0 < eh < 1 else np.nan
                rows.append(dict(predictor=p, symbol=sym, period=per, days=len(lab), coverage=st["n_pred"] / len(lab) if len(lab) else np.nan,
                                 **st, up_day_rate=u, exp_hit_from_base=eh, z_vs_base=z_adj,
                                 bonf_pass=bool(st["n_pred"] and st["t"] >= BONF_HIT)))
    return pd.DataFrame(rows)


def bias_trades(tab, pred_col, m):
    """규칙을 바이어스로 실제 거래(정답 안 씀). 돌려줌 거래 표(symbol, period, year, R)."""
    v = tab[tab["valid"] & (tab[pred_col] != 0)]
    b = v[pred_col].values
    r = np.where(b == 1, v[f"{m}|BUY"].values, v[f"{m}|SELL"].values)
    k = ~np.isnan(r)
    return pd.DataFrame({"symbol": v["symbol"].values[k], "period": v["period"].values[k],
                         "year": v["year"].values[k], "R": r[k]})


def judge_pair(tr, symbols, rw_tr):
    si = ib.stats(tr[tr["period"] == "IS"]["R"].values)
    so = ib.stats(tr[tr["period"] == "OOS"]["R"].values)
    both = 0
    for s in symbols:
        g = tr[tr["symbol"] == s]
        if g[g["period"] == "IS"]["R"].sum() > 0 and g[g["period"] == "OOS"]["R"].sum() > 0:
            both += 1
    yr = tr.groupby("year")["R"].sum() if len(tr) else pd.Series(dtype=float)
    ypos, ny = int((yr > 0).sum()), len(yr)
    rws = ib.stats(rw_tr["R"].values) if rw_tr is not None else None
    checks = {"OOS≥60건": so["n"] >= 60, "OOS평균>0": so["n"] > 0 and so["avg"] > 0,
              "OOS PF≥1.2": so["n"] > 0 and so["pf"] >= 1.2, "IS평균>0": si["n"] > 0 and si["avg"] > 0,
              "종목과반 둘다+": both > len(symbols) / 2, "연도과반+": ny > 0 and ypos > ny / 2,
              f"IS t≥{BONF_TRADE:.2f}": si["n"] > 1 and si["t"] >= BONF_TRADE,
              "랜덤워크 t<2": rws is not None and (rws["n"] < 2 or not (rws["t"] >= 2.0))}
    fails = [k for k, ok in checks.items() if not ok]
    if not fails:
        verdict = "합격"
    elif si["n"] and so["n"] and si["avg"] > 0 and so["avg"] > 0:
        verdict = "후보"
    else:
        verdict = "불합격"
    return dict(IS_n=si["n"], IS_avgR=si["avg"], IS_PF=si["pf"], IS_t=si["t"], OOS_n=so["n"], OOS_avgR=so["avg"],
                OOS_PF=so["pf"], OOS_t=so["t"], OOS_dd=so["dd"], sym_both_pos=both, n_sym=len(symbols),
                years_pos=ypos, n_years=ny, RW_n=rws["n"] if rws else np.nan, RW_avgR=rws["avg"] if rws else np.nan,
                RW_t=rws["t"] if rws else np.nan, verdict=verdict, fails=", ".join(fails))


def part_b_trades(tab, hits, be, rw_tab):
    symbols = sorted(tab["symbol"].unique())
    pooled = hits[hits["symbol"] == "ALL"].set_index(["predictor", "period"])
    pstar = be[(be["symbol"] == "ALL") & (be["period"] == "IS")].set_index("model")["p_star"]
    rows = []
    for p in PREDICTORS:
        h_is, h_oos = pooled.loc[(p, "IS"), "hit"], pooled.loc[(p, "OOS"), "hit"]
        for m in TRADE_MODELS:
            ps = pstar.get(m, np.nan)
            gate = bool(np.isfinite(ps) and h_is > ps and h_oos > ps)
            tr = bias_trades(tab, p, m)
            rw_tr = bias_trades(rw_tab, p, m) if rw_tab is not None else None
            row = dict(predictor=p, model=m, p_star_IS=ps, hit_IS=h_is, hit_OOS=h_oos, gate=gate)
            row.update(judge_pair(tr, symbols, rw_tr))
            row["official"] = gate
            if not gate:
                row["verdict"] = "참고(관문 미통과)"
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 출력
def f3(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else ("inf" if np.isinf(x) else f"{x:+.3f}")


def pct(x):
    return "-" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.1f}%"


def write_summary(path, meta, cur, be, hits, trd):
    L = ["프로젝트 2 ICT 2차: 바이어스 정확도 분석 (정보 제공용. 매매 결정은 석준님)", "=" * 78]
    for k, v in meta.items():
        L.append(f"{k}: {v}")
    L.append("")
    bA = be[(be["symbol"] == "ALL")]
    off = trd[trd["official"]]
    n_ok = int((off["verdict"] == "합격").sum())
    n_c = int((off["verdict"] == "후보").sum())
    ps_is = bA[bA["period"] == "IS"].set_index("model")["p_star"]
    best = hits[(hits["symbol"] == "ALL")].pivot(index="predictor", columns="period", values="hit")
    bp = best["IS"].idxmax() if best["IS"].notna().any() else "-"
    L.append("[① 한 줄 결론]")
    L.append(f"  본전 정확도(전 종목 IS): " + ", ".join(f"{m} {pct(ps_is.get(m))}" for m in TRADE_MODELS)
             + f" / 규칙 15개 중 IS 적중률 최고 {bp} IS {pct(best.loc[bp, 'IS']) if bp != '-' else '-'}"
             f" OOS {pct(best.loc[bp, 'OOS']) if bp != '-' else '-'} / 관문 통과 쌍 {len(off)}개 → 합격 {n_ok}, 후보 {n_c}.")
    L.append("")
    L.append("[② A. 정답을 알면 — 전 종목 합계]  맞은쪽 = 그날 실제 방향 거래, 틀린쪽 = 반대 방향 거래")
    L.append("  모델      기간  맞은쪽 건수·평균R  틀린쪽 건수·평균R   p=0.5   p=1.0   본전 p*")
    for m in TRADE_MODELS:
        for per in ("IS", "OOS", "ALL"):
            r = bA[(bA["model"] == m) & (bA["period"] == per)].iloc[0]
            L.append(f"  {m:<8} {per:<4} {r['Nc']:6d}·{f3(r['avgR_correct']):>7}   {r['Nw']:6d}·{f3(r['avgR_wrong']):>7}"
                     f"   {f3(r['avgR_p50']):>7} {f3(r['avgR_p100']):>7}  {pct(r['p_star']):>6} {r['note']}")
    L.append("")
    L.append("  정확도별 기대 평균R (전 종목 합계, IS | OOS)")
    L.append("  p     " + "  ".join(f"{m:>17}" for m in TRADE_MODELS))
    ca = cur[cur["symbol"] == "ALL"]
    for p in P_GRID:
        cells = []
        for m in TRADE_MODELS:
            a = ca[(ca["model"] == m) & (ca["p"] == p)].set_index("period")["exp_avgR"]
            cells.append(f"{f3(a.get('IS'))}|{f3(a.get('OOS'))}".rjust(17))
        L.append(f"  {p:.2f}  " + "  ".join(cells))
    L.append("")
    L.append("  종목별 본전 p* (IS / OOS)")
    for m in TRADE_MODELS:
        g = be[(be["model"] == m) & (be["symbol"] != "ALL")]
        parts = []
        for s in sorted(g["symbol"].unique()):
            x = g[g["symbol"] == s].set_index("period")["p_star"]
            parts.append(f"{s} {pct(x.get('IS'))}/{pct(x.get('OOS'))}")
        L.append(f"  {m:<8} " + ", ".join(parts))
    L.append("")
    L.append(f"[② B. 바이어스 규칙 적중률 — 전 종목 합계]  t 기준(Bonferroni 15개, 한쪽 5%) = {BONF_HIT:.2f}")
    L.append("  규칙               IS 예측일·적중률·t        OOS 예측일·적중률·t       IS 상승일 기대 적중률")
    hA = hits[hits["symbol"] == "ALL"]
    for p in PREDICTORS:
        a = hA[(hA["predictor"] == p) & (hA["period"] == "IS")].iloc[0]
        b = hA[(hA["predictor"] == p) & (hA["period"] == "OOS")].iloc[0]
        L.append(f"  {p:<18} {a['n_pred']:6d}·{pct(a['hit']):>6}·{a['t']:+5.2f}{'*' if a['bonf_pass'] else ' '}"
                 f"   {b['n_pred']:6d}·{pct(b['hit']):>6}·{b['t']:+5.2f}{'*' if b['bonf_pass'] else ' '}   {pct(a['exp_hit_from_base'])}")
    L.append("  (* = Bonferroni 통과. 상승일 기대 적중률 = 예측의 +/− 비율과 그 기간 상승일 비율만으로 나오는 적중률)")
    L.append("")
    L.append("  종목별 적중률 (IS/OOS)")
    for p in PREDICTORS:
        g = hits[(hits["predictor"] == p) & (hits["symbol"] != "ALL")]
        parts = []
        for s in sorted(g["symbol"].unique()):
            x = g[g["symbol"] == s].set_index("period")["hit"]
            parts.append(f"{s} {pct(x.get('IS'))}/{pct(x.get('OOS'))}")
        L.append(f"  {p:<18} " + ", ".join(parts))
    L.append("")
    L.append(f"[③ 관문 통과 쌍의 실제 거래 판정] (관문: 전 종목 IS·OOS 적중률 모두 > 모델 IS p*, 거래 t 기준 {BONF_TRADE:.2f})")
    if off.empty:
        L.append("  관문을 넘은 (규칙, 모델) 쌍 없음 → 정식 판정 대상 없음.")
    for _, r in off.iterrows():
        L.append(f"  {r['predictor']:<18} × {r['model']:<8} IS {r['IS_n']:5d}·{f3(r['IS_avgR'])}·PF {r['IS_PF']:.2f}·t {r['IS_t']:+.2f}"
                 f" | OOS {r['OOS_n']:4d}·{f3(r['OOS_avgR'])}·PF {r['OOS_PF']:.2f}·t {r['OOS_t']:+.2f}"
                 f" | 종목 {r['sym_both_pos']}/{r['n_sym']} 연도 {r['years_pos']}/{r['n_years']} | RW t {r['RW_t']:+.2f} → {r['verdict']}")
        if r["fails"]:
            L.append(f"      못 넘은 기준: {r['fails']}")
    L.append("")
    L.append("[④ 주의]")
    L.append("  - A는 '정답을 안다'는 불가능한 가정. p*는 바닥선일 뿐, 그 정확도면 번다는 보장이 아님(맞히는 날의 크기가 다름).")
    L.append("  - 관문 못 넘은 쌍의 거래 성적은 partB_trades_all.csv 에 '참고'로만 있음. 거기서 좋아 보이는 것을 고르면 과최적화.")
    L.append("  - 손절은 정확히 손절가 체결(미끄러짐 없음), 같은 봉 손절 우선. 실제는 더 나쁨.")
    L.append("")
    L.append("용어: R = 손절폭 1개. p* = 바이어스가 이 비율 이상 맞아야 평균 R이 0보다 커지는 선. 적중률 t ≥ 2.71 이어야 우연과 구분.")
    txt = "\n".join(L)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    return txt


def write_chart(path, cur, be, hits):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  (matplotlib 없음 → 그림 생략)")
        return False
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#b9b8b1", "axes.labelcolor": "#52514e",
                         "xtick.color": "#52514e", "ytick.color": "#52514e"})
    for fn in ("Malgun Gothic", "AppleGothic", "NanumGothic"):
        try:
            from matplotlib import font_manager
            if any(fn in f.name for f in font_manager.fontManager.ttflist):
                plt.rcParams["font.family"] = fn
                break
        except Exception:
            pass
    plt.rcParams["axes.unicode_minus"] = False
    col = {"IS": "#2a78d6", "OOS": "#eb6834"}
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), facecolor="#fcfcfb")
    ca = cur[cur["symbol"] == "ALL"]
    for k, m in enumerate(TRADE_MODELS):
        ax = axes.flat[k]
        ax.set_facecolor("#fcfcfb")
        for per in ("IS", "OOS"):
            g = ca[(ca["model"] == m) & (ca["period"] == per)]
            ax.plot(g["p"], g["exp_avgR"], color=col[per], lw=2, marker="o", ms=4, label=per)
            if "mc_p05" in g:
                ax.fill_between(g["p"], g["mc_p05"], g["mc_p95"], color=col[per], alpha=0.12, lw=0)
        ax.axhline(0, color="#8a8984", lw=1)
        ps = be[(be["model"] == m) & (be["symbol"] == "ALL") & (be["period"] == "IS")]["p_star"].iloc[0]
        if np.isfinite(ps):
            ax.axvline(ps, color="#52514e", lw=1, ls="--")
            ax.text(ps, ax.get_ylim()[1], f" p*={ps:.2f}", va="top", fontsize=8, color="#0b0b0b")
        ax.set_title(m, fontsize=10, color="#0b0b0b", loc="left")
        ax.set_xlabel("바이어스 정확도 p")
        ax.set_ylabel("평균 R")
        ax.grid(color="#e6e5e0", lw=0.6)
        ax.legend(frameon=False, fontsize=8)
    ax = axes.flat[5]
    ax.set_facecolor("#fcfcfb")
    hA = hits[hits["symbol"] == "ALL"].pivot(index="predictor", columns="period", values="hit").reindex(PREDICTORS)
    y = np.arange(len(PREDICTORS))
    ax.barh(y - 0.2, hA["IS"], height=0.38, color=col["IS"], label="IS")
    ax.barh(y + 0.2, hA["OOS"], height=0.38, color=col["OOS"], label="OOS")
    ax.set_yticks(y)
    ax.set_yticklabels(PREDICTORS, fontsize=7)
    ax.invert_yaxis()
    ax.axvline(0.5, color="#8a8984", lw=1)
    ps_all = be[(be["symbol"] == "ALL") & (be["period"] == "IS")]["p_star"]
    ps_min = np.nanmin(ps_all.values) if np.isfinite(ps_all.values).any() else np.nan
    if np.isfinite(ps_min):
        ax.axvline(ps_min, color="#52514e", lw=1, ls="--")
        ax.text(ps_min, -0.8, f" 가장 낮은 p*={ps_min:.2f}", fontsize=7, color="#0b0b0b")
    lo = np.nanmin(np.r_[hA.values.ravel(), 0.45])
    ax.set_xlim(max(0.3, lo - 0.02), max(0.62, (ps_min if np.isfinite(ps_min) else 0.6) + 0.03))
    ax.set_title("규칙 적중률 (전 종목 합계)", fontsize=10, color="#0b0b0b", loc="left")
    ax.grid(axis="x", color="#e6e5e0", lw=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.suptitle("ICT 2차: 바이어스가 p만큼 맞을 때 기대 평균 R (비용 포함, 띠 = 몬테카를로 5~95%)", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor="#fcfcfb")
    plt.close(fig)
    return True


# ---------------------------------------------------------------- 실행
def build_tables(files, opt, quiet=False):
    spmap, pipmap = ib.parse_map(opt.spread_map), ib.parse_map(opt.pip_map)
    tabs, rng, sp_used = [], {}, {}
    t0 = _time.time()
    for sym, path in files.items():
        print(f"\n== {sym} ==")
        df = path if isinstance(path, pd.DataFrame) else ib.load_m5(path, verbose=not quiet)
        if opt.start:
            df = df[df.index >= pd.Timestamp(opt.start)]
        pip = pipmap.get(sym, ib.default_pip(sym, float(df["c"].iloc[-1])))
        floor = ib.SPREAD_FLOOR.get(sym, 1.0)
        sp = spmap.get(sym, max(opt.spread, floor))
        if sp < floor:
            print(f"  ! spread {sp} below README floor {floor} pips -> {floor}")
            sp = floor
        sp_used[sym] = sp
        tab, r, _ = symbol_table(sym, df, pip, sp)
        tabs.append(tab)
        rng[sym] = r
        print(f"  pip {pip}, spread {sp} pips, 유효일 {int(tab['valid'].sum()):,}, {(_time.time() - t0):.0f}s")
    return pd.concat(tabs, ignore_index=True), rng, sp_used


def rw_table(count, start, end):
    out = []
    for s in range(count):
        df = ib.random_walk(1000 + s, start, end, 0.0001)
        tab, _, _ = symbol_table(f"RW{s}", df, 0.0001, 0.0)
        out.append(tab)
        print(f"  RW{s}: 유효일 {int(tab['valid'].sum()):,}")
    return pd.concat(out, ignore_index=True) if out else None


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def run_all(opt, files=None, quiet=False):
    t0 = _time.time()
    ib_sha = file_sha(ib.__file__)
    if ib_sha != IB_SHA256:
        print(f"! 주의: ict_backtest.py SHA256 {ib_sha[:12]}… ≠ 1차 실행본 {IB_SHA256[:12]}… (결과 비교 시 버전 확인)")
    if files is None:
        syms = [s.strip().upper() for s in opt.symbols.split(",") if s.strip()]
        files = {}
        for f in sorted(os.listdir(opt.data_dir)):
            if f.upper().endswith("_M5.CSV"):
                s = f[:-len("_M5.csv")].upper()
                if not syms or s in syms:
                    files[s] = os.path.join(opt.data_dir, f)
        missing = [s for s in syms if s not in files]
        if missing:
            print(f"! missing files: {missing}")
    if not files:
        print("! no files to run. check --data-dir and --symbols")
        return None
    os.makedirs(opt.out, exist_ok=True)
    tab, rng, sp_used = build_tables(files, opt, quiet)
    rw = None
    if opt.rw > 0:
        lo, hi = min(a for a, _ in rng.values()), max(b for _, b in rng.values())
        print(f"\n== random walk x{opt.rw} (spread 0) ==")
        rw = rw_table(opt.rw, pd.Timestamp(lo).floor("D"), pd.Timestamp(hi))
    print("\n== A: 오라클 ==")
    cur, be = part_a(tab, opt.seeds)
    print("== B: 적중률·관문·거래 ==")
    hits = part_b_hits(tab)
    trd = part_b_trades(tab, hits, be, rw)
    lo, hi = min(a for a, _ in rng.values()), max(b for _, b in rng.values())
    meta = {"데이터": f"MT5 M5 CSV ({opt.data_dir or '메모리'}), 종목 {', '.join(files)}",
            "기간(서버시간)": "; ".join(f"{s} {pd.Timestamp(a):%Y-%m-%d %H:%M}~{pd.Timestamp(b):%Y-%m-%d %H:%M}" for s, (a, b) in rng.items()),
            "기간(한국시간)": f"{ib.server_to_kst([pd.Timestamp(lo)])[0]:%Y-%m-%d %H:%M} ~ {ib.server_to_kst([pd.Timestamp(hi)])[0]:%Y-%m-%d %H:%M} KST",
            "방향 정의": "NY 16:00 종가 − 자정 시가(NY 00:00 = 서버 07:00 = KST 13:00 여름/14:00 겨울)",
            "IS / OOS": f"거래일 {ib.OOS_START} 이전 = IS, 이후 = OOS",
            "비용": "스프레드 " + ", ".join(f"{s} {v}핍" for s, v in sp_used.items()) + " (거래당 1번), 손절 버퍼 1핍, 같은 봉 손절 우선",
            "랜덤워크": f"{opt.rw}개 (스프레드 0)" if opt.rw > 0 else "건너뜀 → 랜덤워크 기준 불합격 처리",
            "몬테카를로": f"{opt.seeds}회 (시드 {SEED0}~)",
            "규칙": "trading/projects/02-ict/rules_bias.md (2026-10-29 고정)",
            "코드": f"ict_bias.py SHA256 {file_sha(os.path.abspath(__file__))[:16]}…, ict_backtest.py {ib_sha[:16]}…",
            "만든 시각": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M") + " (실행 PC 시각)"}
    o = opt.out
    tab.to_csv(os.path.join(o, "daily_bias_table.csv"), index=False, encoding="utf-8-sig", float_format="%.6g")
    cur.to_csv(os.path.join(o, "partA_oracle_curve.csv"), index=False, encoding="utf-8-sig", float_format="%.5f")
    be.to_csv(os.path.join(o, "partA_breakeven.csv"), index=False, encoding="utf-8-sig", float_format="%.5f")
    hits.to_csv(os.path.join(o, "partB_hitrate.csv"), index=False, encoding="utf-8-sig", float_format="%.5f")
    trd.to_csv(os.path.join(o, "partB_trades_all.csv"), index=False, encoding="utf-8-sig", float_format="%.5f")
    trd[trd["official"]].to_csv(os.path.join(o, "partB_trades_official.csv"), index=False, encoding="utf-8-sig", float_format="%.5f")
    txt = write_summary(os.path.join(o, "summary_bias.txt"), meta, cur, be, hits, trd)
    if not opt.no_chart:
        write_chart(os.path.join(o, "bias_chart.png"), cur, be, hits)
    if not quiet:
        print("\n" + txt)
    print(f"\ndone {(_time.time() - t0):.0f}s. output folder: {o}  (summary_bias.txt is UTF-8)")
    return dict(tab=tab, cur=cur, be=be, hits=hits, trd=trd, rw=rw)


def build_parser():
    p = argparse.ArgumentParser(description="ICT phase 2: daily bias oracle break-even + bias predictors (read-only)")
    p.add_argument("--data-dir", help="folder with {SYMBOL}_M5.csv")
    p.add_argument("--out", help="output folder (created if missing)")
    p.add_argument("--symbols", default="", help="comma list. empty = all *_M5.csv in folder")
    p.add_argument("--spread", type=float, default=ib.DEFAULT_SPREAD, help="default spread pips (floor 1, gold 2)")
    p.add_argument("--spread-map", default="", help="per-symbol spread pips, e.g. GBPJPY=2.5")
    p.add_argument("--pip-map", default="", help="per-symbol pip size, e.g. XAUUSD=0.1")
    p.add_argument("--start", default="", help="use data from this date (server time)")
    p.add_argument("--rw", type=int, default=2, help="random-walk series for the RW criterion (default 2)")
    p.add_argument("--seeds", type=int, default=200, help="Monte Carlo draws per p (default 200, 0 = skip)")
    p.add_argument("--no-chart", action="store_true", help="skip PNG chart")
    p.add_argument("--selftest", action="store_true", help="run self tests on synthetic data only")
    return p


# ---------------------------------------------------------------- 자체 시험
def _check(ok, cond, msg):
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    return ok and bool(cond)


def selftest():
    ok = True
    t0 = _time.time()
    print("=== 1. 손익분기 공식 ===")
    ps, _ = breakeven(30.0, 100, -50.0, 100)
    ok = _check(ok, abs(ps - 0.625) < 1e-12 and abs(exp_avg(ps, 30.0, 100, -50.0, 100)) < 1e-12,
                "Sc=+30, Sw=−50 (각 100건) → p* = 0.625, 그때 기대 평균R = 0")
    ok = _check(ok, np.isnan(breakeven(-1.0, 50, -5.0, 50)[0]) and breakeven(5.0, 50, 1.0, 50)[0] == 0.0,
                "Sc ≤ 0 → p* 없음, Sw ≥ 0 → 0 (바이어스 없어도 +)")
    rng = np.random.default_rng(1)
    rc = np.where(rng.random(4000) < 0.7, rng.normal(0.4, 1, 4000), np.nan)
    rw_ = np.where(rng.random(4000) < 0.6, rng.normal(-0.5, 1, 4000), np.nan)
    tab = pd.DataFrame({"symbol": ["T"] * 4000, "period": ["IS"] * 4000, "valid": [True] * 4000,
                        "label": rng.choice([1, -1], 4000), "year": [2020] * 4000})
    for m in TRADE_MODELS:
        tab[f"{m}|BUY"] = np.where(tab["label"] == 1, rc, rw_)
        tab[f"{m}|SELL"] = np.where(tab["label"] == 1, rw_, rc)
    cur, be = part_a(tab, 300)
    c = cur[(cur["symbol"] == "ALL") & (cur["period"] == "IS") & (cur["model"] == "PO3-2R")]
    gap = (c["mc_p50"] - c["exp_avgR"]).abs().max()
    ok = _check(ok, gap < 0.02, f"몬테카를로 중앙값 ≈ 계산식 (최대 차이 {gap:.4f} < 0.02)")
    r = be[(be["symbol"] == "ALL") & (be["period"] == "IS") & (be["model"] == "PO3-2R")].iloc[0]
    sc, nc, sw, nw = np.nansum(rc), int((~np.isnan(rc)).sum()), np.nansum(rw_), int((~np.isnan(rw_)).sum())
    ok = _check(ok, abs(r["p_star"] - sw / (sw - sc)) < 1e-9, f"표의 p* {r['p_star']:.4f} = 직접 계산 {sw / (sw - sc):.4f}")
    # 정답을 바이어스로 쓰면 실제 거래 경로 평균 = 계산식 p=1
    tab["ORACLE"] = tab["label"]
    tr = bias_trades(tab, "ORACLE", "PO3-2R")
    ok = _check(ok, abs(tr["R"].mean() - r["avgR_p100"]) < 1e-12, "정답 바이어스로 실제 거래 경로 평균 = 오라클 p=1 값")
    tab["ORACLE"] = -tab["label"]
    tr = bias_trades(tab, "ORACLE", "PO3-2R")
    ok = _check(ok, abs(tr["R"].mean() - sw / nw) < 1e-12, "반대 바이어스(항상 틀림) = 틀린 쪽 평균")

    print("=== 2. 규칙 단위 시험 ===")
    ok = _check(ok, pd_rule(1.10, 1.09, 1.105, 1.095, 1.102) == 1 and pd_rule(1.10, 1.09, 1.105, 1.095, 1.098) == -1
                and pd_rule(1.10, 1.09, 1.099, 1.085, 1.088) == -1 and pd_rule(1.10, 1.09, 1.099, 1.085, 1.092) == 1
                and pd_rule(1.10, 1.09, 1.099, 1.091, 1.095) == 0 and pd_rule(1.10, 1.09, 1.11, 1.08, 1.095) == 0,
                "P2: PDH 넘고 위 마감 +1 / 넘고 되돌림 −1 / PDL 거울 / 안쪽 0 / 둘 다 넘고 사이 0")
    ok = _check(ok, sweep_last(10, 5) == -1 and sweep_last(5, 10) == 1 and sweep_last(-1, 3) == 1 and sweep_last(3, -1) == -1
                and sweep_last(-1, -1) == 0 and sweep_last(4, 4) == 0, "P3: 마지막에 쓸린 쪽 반대")
    ok = _check(ok, close_loc(2, 1, 1.8) == 1 and close_loc(2, 1, 1.2) == -1 and close_loc(2, 1, 1.5) == 0, "P4: 위·아래 25%")
    ok = _check(ok, week_draw(1.10, 1.12, 1.07, 1.105, 1.095) == 1 and week_draw(1.10, 1.12, 1.07, 1.125, 1.095) == -1
                and week_draw(1.10, 1.12, 1.07, 1.125, 1.06) == 0 and week_draw(1.10, 1.105, 1.07, -math.inf, math.inf) == 1,
                "P5: 둘 다 안 깨짐 → 가까운 쪽, 한쪽 깨짐 → 다른 쪽, 둘 다 깨짐 → 0")
    # P6: 하락 FVG(봉 3: 고가 1.00 < 봉 1 저가 1.02) 위에 있고 안 닿음 → +1
    dH = [1.05, 1.04, 1.03, 1.00, 0.99, 0.985]
    dL = [1.03, 1.02, 1.01, 0.98, 0.97, 0.975]
    ok = _check(ok, fvg_draw(0.98, dH, dL, 6, 0.982, 0.978) == 1, "P6: 위쪽 안 닿은 하락 FVG(1.00~1.02) → +1")
    ok = _check(ok, fvg_draw(0.98, dH, dL, 6, 1.012, 0.978) == 0, "P6: 오늘 판단 전 CE(1.01)까지 닿음 → 무효 → 0")
    ok = _check(ok, mt_extreme([0, 1, 2], [1.0, 1.1, 1.05], [1.2, 1.3, 1.4]) == 1
                and mt_extreme([0, 1, 2], [1.0, 0.9, 0.8], [1.4, 1.3, 1.2]) == -1
                and mt_extreme([0, 1, 2], [1.0, 0.9, 1.0], [1.1, 1.3, 1.2]) == 0, "P8: 월·화 극값 뒤 반대쪽 확장")

    print("=== 3. 1차 코드와 같은 거래 (PO3-2R = M2-MO-PO3, BRK-2R = M2-ASIA-BRK, 랜덤워크 3년) ===")
    df = ib.random_walk(31, "2020-01-01", "2022-12-31 23:55", 0.0001)
    tab3, _, aux = symbol_table("RWC", df, 0.0001, 0.5)
    X = aux["X"]
    same = True
    detail = []
    for S, side, F in ((aux["S1"], "BUY", aux["Fb"]), (aux["Sm"], "SELL", aux["Fs"])):
        col = ib.Collector(X)
        ib.model_m2(S, X, col)
        raw = pd.DataFrame(col.rows, columns=ib.COLS)
        for base, mine in (("M2-MO-PO3", "PO3-2R"), ("M2-ASIA-BRK", "BRK-2R")):
            g = raw[raw["variant_base"] == base]
            ref = {(int(k[0]), int(f)): round(float(r), 9) for k, f, r in zip(g["key"], g["fill_i"], g["R"])
                   if tab3["valid"].iloc[int(k[0])]}
            got = {(int(d), int(F[mine][d])): round(float(tab3[f"{mine}|{side}"].iloc[d]), 9)
                   for d in np.flatnonzero(~np.isnan(tab3[f"{mine}|{side}"].values))}
            detail.append(f"{mine}/{side} {len(got)}")
            same = same and ref == got and len(got) > 50
    ok = _check(ok, same, "1차 ict_backtest.model_m2 거래와 날짜·체결 봉·R 완전히 같음 (" + ", ".join(detail) + ")")

    print("=== 4. 랜덤워크 4개 × 8년: 적중률 ≈ 50%, 오라클 동작 ===")
    tabs = []
    for s in (41, 42, 43, 44):
        df = ib.random_walk(s, "2017-01-01", "2024-12-31 23:55", 0.0001)
        t1 = _time.time()
        tb, _, _ = symbol_table(f"RW{s}", df, 0.0001, 0.0)
        tabs.append(tb)
    per_sym = _time.time() - t1
    rwt = pd.concat(tabs, ignore_index=True)
    rwt["period"] = "IS"
    hits = part_b_hits(rwt)
    hA = hits[(hits["symbol"] == "ALL") & (hits["period"] == "IS")]
    worst = hA.loc[hA["t"].abs().idxmax()]
    ok = _check(ok, (hA["t"].abs() < 3).all() and (hA["n_pred"] > 300).all(),
                f"규칙 15개 적중률 |t| < 3 (가장 큰 |t|: {worst['predictor']} {worst['hit']:.3f} t {worst['t']:+.2f}, "
                f"범위 {hA['hit'].min():.3f}~{hA['hit'].max():.3f})")
    ok = _check(ok, (hA["hit"].sub(0.5).abs() < 0.03).all(), "모든 규칙 적중률 0.47~0.53")
    cur, be = part_a(rwt, 50)
    bA = be[(be["symbol"] == "ALL") & (be["period"] == "IS")].set_index("model")
    good = all(bA.loc[m, "avgR_p100"] > bA.loc[m, "avgR_p50"] + 0.1 and bA.loc[m, "avgR_correct"] > 0 > bA.loc[m, "avgR_wrong"]
               for m in TRADE_MODELS)
    ok = _check(ok, good, "오라클: 모든 모델에서 맞은쪽 평균 > 0 > 틀린쪽 평균, p=1이 p=0.5보다 0.1R 이상 큼 ("
                + ", ".join(f"{m} p*={bA.loc[m, 'p_star']:.2f}" for m in TRADE_MODELS) + ")")
    for m in TRADE_MODELS:
        both = rwt[rwt["valid"]][[f"{m}|BUY", f"{m}|SELL"]].values.ravel()
        both = both[~np.isnan(both)]
        st = ib.stats(both)
        ok = _check(ok, abs(st["t"]) < 3.5 and -0.15 < st["avg"] < 0.05,
                    f"{m} 바이어스 없이(매수·매도 모두) {st['n']}건 평균 {st['avg']:+.3f}R t {st['t']:+.2f} (≈ 0, 보수적 체결로 약간 −)")
    rwt2 = rwt.copy()
    rwt2["period"] = np.where(rwt2["date"] < "2021-01-01", "IS", "OOS")
    hits2 = part_b_hits(rwt2)
    trd = part_b_trades(rwt2, hits2, part_a(rwt2, 0)[1], None)
    mx = trd.loc[trd["IS_t"].abs().idxmax()]
    ok = _check(ok, (trd["IS_t"].abs() < 3.5).all(), f"규칙 × 모델 75쌍 실제 거래 IS |t| < 3.5 (최대 {mx['predictor']}×{mx['model']} t {mx['IS_t']:+.2f})")

    print("=== 5. 미래 엿보기 검사: 데이터를 잘라도 그 전 날의 규칙 값·거래가 같아야 함 ===")
    df = ib.random_walk(51, "2019-01-01", "2021-06-30 23:55", 0.0001)
    full, _, auxf = symbol_table("RWT", df, 0.0001, 0.5)
    cuts = [pd.Timestamp("2020-03-11 07:00"), pd.Timestamp("2020-08-12 13:37"), pd.Timestamp("2020-11-30 07:00"),
            pd.Timestamp("2021-02-17 03:10"), pd.Timestamp("2019-09-06 07:00")]
    all_same, n_cmp, n_tr = True, 0, 0
    for cut in cuts:
        part, _, auxp = symbol_table("RWT", df[df.index < cut], 0.0001, 0.5)
        dec_t = auxp["X"].dkey * NS_D + 7 * NS_H
        dd = np.flatnonzero(dec_t <= cut.value)                    # 판단 시점(서버 07:00)이 자른 시각 이전인 날
        dd = dd[dd < len(full)]
        a = full.iloc[dd][PREDICTORS].values
        b = part.iloc[dd][PREDICTORS].values
        same_p = (a == b).all()
        # 거래: 잘린 날 하루 전까지 완성된 날
        cday = (cut.normalize() - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        ff, pp = full[full["date"] < cday], part[part["date"] < cday]
        rc = [f"{m}|{s}" for m in TRADE_MODELS for s in ("BUY", "SELL")] + ["label", "valid"]
        same_t = ff[rc].reset_index(drop=True).equals(pp[rc].reset_index(drop=True))
        n_cmp += len(dd)
        n_tr += int(ff[rc[:-2]].notna().values.sum())
        cut_day_in = part["date"].iloc[dd[-1]] == cut.strftime("%Y-%m-%d") if cut.hour == 7 else True
        all_same = all_same and same_p and same_t and cut_day_in
        if not (same_p and same_t):
            print(f"    cut {cut}: 규칙 같음 {same_p}, 거래 같음 {same_t}")
    ok = _check(ok, all_same and n_cmp > 1000,
                f"5개 자름 시점: 규칙 값 {n_cmp}일·거래 {n_tr}건 완전히 같음 (07:00 정각 자름 → 그날 규칙도 포함 비교)")

    est = per_sym * 9 * 1.0 + 9 * 15 + 2 * per_sym
    print(f"\n  속도: 랜덤워크 8년 1종목 {per_sym:.1f}s → 9종목 + RW 2개 예상 약 {est / 60:.1f}분(CSV 읽기 약 15초/종목 포함)")
    ok = _check(ok, est < 600, "예상 실행 시간 < 10분")
    print(f"\n자체 시험 {'모두 통과' if ok else '실패 있음'} ({_time.time() - t0:.0f}s)")
    return ok


def main():
    opt = build_parser().parse_args()
    if opt.selftest:
        sys.exit(0 if selftest() else 1)
    if not opt.data_dir or not opt.out:
        print("need --data-dir and --out (or --selftest)")
        sys.exit(2)
    run_all(opt)


if __name__ == "__main__":
    main()
