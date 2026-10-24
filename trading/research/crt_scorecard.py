"""고객님 SMC+CRT 셋업 점수표 (2026-10-24) — 모든 셋업을 기록하고, 진입 시점에 알 수 있는 특징만으로
'걸러서 이기는 조건'이 있는지 IS(2019~2023)에서 찾고 OOS(2024~)에서 그대로 확인한다.

셋업 (매수 기준, 매도는 가격을 뒤집어 같은 코드):
 1. CRT: C1 = 직전 마감 H4봉(서버시각 0/4/8.. 시작, M15에서 조립) 범위 CRH~CRL.
 2. 스윕: C2(다음 H4봉) 동안 M15 저가가 CRL 아래로 처음 나간 봉.
 3. MSS 선 (user_smc_crt_rules.md 'MSS 선 정정'): 스윕 극값 이전에서 가장 가까운 M15 프랙탈 스윙 고점(N=3,
    오른쪽 3봉이 마감돼 확정된 것만). 극값이 더 내려가면 선도 다시 계산. C2 시작~C3 끝 안에서
    M15 양봉이 그 선 위로 '종가 마감'하고 종가가 CRT 범위 안(CRL<종가<CRH)이면 확정.
 4. OB = 확정 봉 직전의 마지막 음봉 (확정 봉 − 1부터 극값 − 10봉까지 거꾸로).
 5. 진입: 확정 후 24봉(6h) 안에 가격이 OB 고가까지 내려오고(터치), 그 뒤(같은 봉 포함) M15 양봉이 OB 고가 위로
    마감하면 다음 M15 시가 진입. 진입 전 극값 아래로 내려가거나 CRH에 먼저 닿으면 취소.
 6. 손절: 기본 = 극값 − 1핍, 타이트 = OB 저가 − 1핍. 목표: opp(CRH) / RR2 / RR3. 최대 보유 24시간(종가 청산).
 7. 종목당 동시 1셋업: 진입 순서대로, 앞 거래(기본 손절의 세 목표 중 가장 늦은 청산)가 끝나야 다음 진입.
관례(crt_cisd.py·ict_atm.py): 비용 = max(봉 spread, SPREAD_FLOOR)×point, 거래당 1회(진입 봉 기준) 차감,
같은 봉 손절·목표 동시면 손절 먼저, 손절폭 < 4×비용이면 제외. 결과는 R. 서버시각 = 뉴욕+7h.
특징은 모두 진입 시점(확인 봉 마감)까지 알 수 있는 값만 사용.
사용: python -I crt_scorecard.py venus_data.zip [out_dir]
"""
import io
import json
import math
import os
import sys
import zipfile
from itertools import combinations

import numpy as np
import pandas as pd

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
PIP = {"USDJPY": 0.01, "XAUUSD": 0.1}
SERVER_MINUS_NY = 7
N_FR, MSS_LOOKBACK, OB_BACK, ENTRY_WAIT, HOLD_H = 3, 96, 10, 24, 24
SPLIT = np.datetime64("2024-01-01")
OUTCOMES = ["r_opp", "r_rr2", "r_rr3", "rt_opp", "rt_rr2", "rt_rr3"]
SEARCH_OUTCOMES = ["r_opp", "r_rr2", "r_rr3"]      # 탐색은 기본 손절 3개 목표만 (미리 정함)
MIN_CELL = 80


# ---------------------------------------------------------------- data
def read(zp, sym, tf):
    df = pd.read_csv(io.BytesIO(zipfile.ZipFile(zp).read(f"{sym}_{tf}.csv")))
    df["srv"] = pd.to_datetime(df.time, unit="s")
    return df.reset_index(drop=True)


def h4_from_m15(m):
    b = (m.time.values // 14400)
    g = pd.DataFrame({"b": b, "open": m.open, "high": m.high, "low": m.low, "close": m.close}).groupby("b", sort=True)
    h4 = pd.DataFrame({"open": g.open.first(), "high": g.high.max(), "low": g.low.min(), "close": g.close.last(),
                       "nbar": g.size()}).reset_index()
    h4["start"] = h4.b * 14400
    h4["end"] = h4.start + 14400
    return h4


def ea_bias(h, l, c, L, n=150):
    """VenusCRTAssistant.mq5 Bias() 그대로: 마지막 마감봉 = 앞으로 인덱스 L."""
    if L - n - 4 < 0:
        return 0
    last_hi = last_lo = 0.0
    bias = 0
    for k in range(n, 0, -1):
        f = L - k + 1
        j = f - 2
        if h[j] > h[j - 1] and h[j] > h[j - 2] and h[j] >= h[j + 1] and h[j] >= h[j + 2]:
            last_hi = h[j]
        if l[j] < l[j - 1] and l[j] < l[j - 2] and l[j] <= l[j + 1] and l[j] <= l[j + 2]:
            last_lo = l[j]
        if last_hi > 0 and c[f] > last_hi:
            bias, last_hi = 1, 0.0
        if last_lo > 0 and c[f] < last_lo:
            bias, last_lo = -1, 0.0
    return bias


def fractal_high_mask(h, n):
    m = len(h)
    ok = np.zeros(m, bool)
    ok[n:m - n] = True
    for j in range(1, n + 1):
        ok[n:m - n] &= (h[n:m - n] > h[n - j:m - n - j]) & (h[n:m - n] >= h[n + j:m - n + j])
    return ok


def sim(h, l, c, i0, last, entry, sl, tp, cost):
    risk = entry - sl
    for i in range(i0, last + 1):
        if l[i] <= sl:
            return (-risk - cost) / risk, i
        if h[i] >= tp:
            return (tp - entry - cost) / risk, i
    return (c[last] - entry - cost) / risk, last


# ---------------------------------------------------------------- setups
def scan(zp, sym):
    pip = PIP.get(sym, 0.0001)
    m = read(zp, sym, "M15")
    d1 = read(zp, sym, "D1")
    cost_all = np.maximum(m.spread.values, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    tsec = m.time.values.astype(np.int64)
    h4 = h4_from_m15(m)
    H4h, H4l, H4c = h4.high.values, h4.low.values, h4.close.values
    tr = np.maximum(H4h - H4l, np.maximum(abs(H4h - np.r_[H4c[0], H4c[:-1]]), abs(H4l - np.r_[H4c[0], H4c[:-1]])))
    atr = pd.Series(tr).rolling(14).mean().values                 # ATR(14) 단순평균, 봉 마감 기준
    D1h, D1l, D1c = d1.high.values, d1.low.values, d1.close.values
    d1_day = (d1.time.values // 86400).astype(np.int64)
    bias_cache = {}

    def bias_at(kind, L):
        key = (kind, L)
        if key not in bias_cache:
            bias_cache[key] = ea_bias(H4h, H4l, H4c, L) if kind == "h4" else ea_bias(D1h, D1l, D1c, L)
        return bias_cache[key]

    # 봉 인덱스: H4 bin → M15 시작 인덱스
    m_bin = tsec // 14400
    starts = np.flatnonzero(np.r_[True, m_bin[1:] != m_bin[:-1]])
    bin_to_h4 = {b: i for i, b in enumerate(h4.b.values)}
    cands = []
    for d in (1, -1):
        if d == 1:
            o, h, l, c = m.open.values, m.high.values, m.low.values, m.close.values
        else:
            o, h, l, c = -m.open.values, -m.low.values, -m.high.values, -m.close.values
        fh = fractal_high_mask(h, N_FR)
        n = len(o)
        for j in range(1, len(starts) - 2):
            a1, a2, a3, a4 = starts[j - 1], starts[j], starts[j + 1], starts[j + 2]
            if a2 - a1 < 12 or a3 - a2 < 8 or m_bin[a2] - m_bin[a1] != 1:
                continue
            crh, crl = h[a1:a2].max(), l[a1:a2].min()
            sw = next((k for k in range(a2, a3) if l[k] < crl), None)
            if sw is None:
                continue
            ext = sw
            mss = None
            for k in range(sw, a4):
                if l[k] < l[ext]:
                    ext = k
                if k == ext:
                    continue
                # 극값 이전 가장 가까운 '이미 확정된' 스윙 고점 (극값이 갱신되면 자동으로 다시 계산)
                sp = next((q for q in range(ext - 1, max(ext - MSS_LOOKBACK, N_FR), -1)
                           if fh[q] and q + N_FR <= k), None)
                if sp is None:
                    continue
                if c[k] > h[sp] and c[k] > o[k] and crl < c[k] < crh:
                    mss = k
                    break
            if mss is None:
                continue
            ob = next((q for q in range(mss - 1, max(ext - OB_BACK, 0) - 1, -1) if c[q] < o[q]), None)
            if ob is None:
                continue
            ob_hi, ob_lo = h[ob], l[ob]
            ext_px = l[ext]
            touched, conf = False, None
            for q in range(mss + 1, min(n - 1, mss + 1 + ENTRY_WAIT)):
                if l[q] < ext_px or h[q] >= crh:
                    break
                if l[q] <= ob_hi:
                    touched = True
                if touched and c[q] > ob_hi and c[q] > o[q]:
                    conf = q
                    break
            if conf is None:
                continue
            i0 = conf + 1
            entry = o[i0]
            cost = cost_all[i0]
            sl = ext_px - pip
            risk = entry - sl
            if risk < 4 * cost:
                continue
            last = int(np.searchsorted(tsec, tsec[i0] + HOLD_H * 3600) - 1)
            res = {}
            ex = []
            for name, tp in (("opp", crh), ("rr2", entry + 2 * risk), ("rr3", entry + 3 * risk)):
                if tp <= entry:
                    res["r_" + name] = np.nan
                    continue
                r, xi = sim(h, l, c, i0, last, entry, sl, tp, cost)
                res["r_" + name] = r
                ex.append(xi)
            slt = ob_lo - pip
            riskt = entry - slt
            for name, tp in (("opp", crh), ("rr2", entry + 2 * riskt), ("rr3", entry + 3 * riskt)):
                if riskt < 4 * cost or tp <= entry:
                    res["rt_" + name] = np.nan
                    continue
                res["rt_" + name] = sim(h, l, c, i0, last, entry, slt, tp, cost)[0]
            # ---- 진입 시점 특징
            t_entry = tsec[i0]
            hL = int(np.searchsorted(h4.end.values, t_entry, side="right") - 1)   # 마감된 마지막 H4
            day = t_entry // 86400
            dL = int(np.searchsorted(d1_day, day, side="left") - 1)                # 마감된 마지막 D1
            b_d1 = bias_at("d1", dL) * d
            b_h4 = bias_at("h4", hL) * d
            a = atr[bin_to_h4[m_bin[a1]]]
            ny = pd.Timestamp(t_entry, unit="s") - pd.Timedelta(hours=SERVER_MINUS_NY)
            hr = ny.hour
            sess = "asia" if (hr >= 19 or hr < 2) else "london" if hr < 8 else "ny" if hr < 12 else "late"
            sw_day = tsec[ext] // 86400
            pdi = int(np.searchsorted(d1_day, sw_day, side="left") - 1)
            pdl = D1l[pdi] if d == 1 else -D1h[pdi]
            rng = crh - crl
            cands.append(dict(
                sym=sym, d=d, t=pd.Timestamp(t_entry, unit="s"), i0=i0, exit=max(ex) if ex else i0,
                entry=entry * d, risk_pips=risk / pip, **res,
                bias_d1=b_d1, bias_h4=b_h4, aligned=int(b_d1 == 1) + int(b_h4 == 1),
                sess=sess, ny_hour=hr, dow=int(ny.dayofweek),
                sweep_atr=(crl - ext_px) / a, range_atr=rng / a, mss_leg_atr=(h[mss] - ext_px) / a,
                rr_opp=(crh - entry) / risk, min_sweep_conf=(tsec[mss] - tsec[sw]) / 60,
                pd_sweep=int(ext_px < pdl), pd_pos=(entry - crl) / rng, cost_stop=cost / risk,
            ))
    df = pd.DataFrame(cands).sort_values("i0").reset_index(drop=True)
    keep, busy = [], -1
    for r in df.itertuples():
        if r.i0 > busy:
            keep.append(r.Index)
            busy = r.exit
    return df.loc[keep].reset_index(drop=True), len(df)


# ---------------------------------------------------------------- stats
def st(r):
    r = np.asarray(r, float)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return dict(n=len(r), win=np.nan, avg=np.nan, pf=np.nan, t=np.nan, dd=np.nan, sum=np.nan)
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    eq = np.cumsum(r)
    return dict(n=len(r), win=100 * (r > 0).mean(), avg=r.mean(), pf=w / ls if ls else 9.0,
                t=r.mean() / (r.std(ddof=1) / math.sqrt(len(r))), dd=(np.maximum.accumulate(eq) - eq).max(), sum=r.sum())


def fmt(s):
    if s["n"] < 2:
        return f"{s['n']}건"
    return (f"{s['n']:5d}건 승률 {s['win']:4.1f}% 평균 {s['avg']:+.3f}R PF {s['pf']:.2f} t{s['t']:+.1f} "
            f"합계 {s['sum']:+7.1f}R 낙폭 {s['dd']:5.1f}R")


def bucketize(a, is_mask):
    """연속 특징은 IS 3분위 경계로 나눔 (경계는 IS에서만 정함)."""
    b = pd.DataFrame(index=a.index)
    b["aligned"] = a.aligned.astype(str)
    b["bias_d1"] = a.bias_d1.astype(str)
    b["bias_h4"] = a.bias_h4.astype(str)
    b["sess"] = a.sess
    b["dow"] = a.dow.astype(str)
    b["pd_sweep"] = a.pd_sweep.astype(str)
    b["discount"] = np.where(a.pd_pos < 0.5, "disc", "prem")
    b["dir"] = np.where(a.d == 1, "buy", "sell")
    edges = {}
    for f in ["sweep_atr", "range_atr", "mss_leg_atr", "rr_opp", "min_sweep_conf", "cost_stop"]:
        q = np.nanquantile(a.loc[is_mask, f], [1 / 3, 2 / 3])
        edges[f] = [float(x) for x in q]
        b[f] = np.select([a[f] <= q[0], a[f] <= q[1]], ["T1", "T2"], "T3")
    return b, edges


def nz(p):
    return 0.5 * math.erfc(-p / math.sqrt(2))


def z_for(alpha):
    lo, hi = 0.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 1 - nz(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return hi


def main(zp, out):
    os.makedirs(out, exist_ok=True)
    parts, raw = [], 0
    for s in SYMBOLS:
        t, nraw = scan(zp, s)
        raw += nraw
        parts.append(t)
        print(f"[{s}] 진입 셋업 {nraw} → 동시 1셋업 적용 {len(t)}  손절 중앙값 {t.risk_pips.median():.1f}핍", flush=True)
    a = pd.concat(parts).sort_values("t").reset_index(drop=True)
    a.to_csv(os.path.join(out, "crt_scorecard_trades.csv"), index=False)
    is_m = a.t.values < SPLIT
    days = (a.t.max() - a.t.min()) / pd.Timedelta(days=1) * 5 / 7
    print(f"\n기간 {a.t.min()} ~ {a.t.max()} (서버시각), 거래 {len(a)}건, 7종목 합 하루 {len(a) / days:.2f}회")

    print("\n## 1. 전부 진입 (기준선)")
    for o in OUTCOMES:
        print(f"  {o:7s} IS ", fmt(st(a.loc[is_m, o])))
        print(f"  {o:7s} OOS", fmt(st(a.loc[~is_m, o])))

    b, edges = bucketize(a, is_m)
    feats = list(b.columns)
    cells = []
    for o in SEARCH_OUTCOMES:
        keys = [(f,) for f in feats] + list(combinations(feats, 2))
        for fk in keys:
            g = b[list(fk)].astype(str).agg("|".join, axis=1)
            for val in g.unique():
                sel = (g == val).values
                si = st(a.loc[sel & is_m, o])
                if si["n"] < MIN_CELL:
                    continue
                cells.append(dict(outcome=o, feat="+".join(fk), val=val, is_n=si["n"], is_avg=si["avg"], is_t=si["t"],
                                  is_pf=si["pf"], sel=sel))
    ncell = len(cells)
    zb = z_for(0.05 / ncell)
    print(f"\n## 2. IS 탐색: 특징 {len(feats)}개(단일 {len(feats)} + 2개조합 {len(feats) * (len(feats) - 1) // 2}) × 목표 3개,"
          f" IS {MIN_CELL}건 이상 칸 {ncell}개 시험. 본페로니 기준 IS t ≥ {zb:.2f}")
    cells.sort(key=lambda x: -x["is_avg"])
    top, seen = [], set()
    for cdict in cells:
        sig = (cdict["feat"], cdict["val"])
        if sig in seen:
            continue
        seen.add(sig)
        top.append(cdict)
        if len(top) == 5:
            break
    print(f"  IS t ≥ {zb:.2f} 통과 칸 수: {sum(1 for x in cells if x['is_t'] >= zb)}")
    sym_pos_needed = 4
    results = []
    for cnd in top:
        o, sel = cnd["outcome"], cnd["sel"]
        si, so = st(a.loc[sel & is_m, o]), st(a.loc[sel & ~is_m, o])
        sub = a.loc[sel & ~is_m]
        sym_pos = sum(1 for s in SYMBOLS if np.nansum(sub.loc[sub.sym == s, o]) > 0)
        oos_days = (a.t.max() - pd.Timestamp(SPLIT)) / pd.Timedelta(days=1) * 5 / 7
        passed = (so["pf"] >= 1.2 and so["dd"] <= 10 and so["n"] >= 60 and si["avg"] > 0 and so["avg"] > 0
                  and sym_pos >= sym_pos_needed)
        yrs = a.loc[sel].groupby(a.loc[sel].t.dt.year)[o].agg(["count", "sum"])
        print(f"\n  후보 {cnd['feat']}={cnd['val']} [{o}]")
        print("    IS ", fmt(si))
        print("    OOS", fmt(so), f" OOS 양수 종목 {sym_pos}/7  하루 {so['n'] / oos_days:.2f}회  → {'합격' if passed else '불합격'}")
        print("    연도별:", "  ".join(f"{y}:{int(r['count'])}건 {r['sum']:+.1f}R" for y, r in yrs.iterrows()))
        results.append(dict(rule=f"{cnd['feat']}={cnd['val']}", target=o, IS=si, OOS=so, oos_sym_pos=sym_pos,
                            trades_per_day_oos=so["n"] / oos_days, passed=bool(passed)))
    # OOS 전체 칸 분포 (참고: IS 상위가 OOS에서도 위인지)
    is_rank = pd.DataFrame([dict(is_avg=x["is_avg"], oos_avg=st(a.loc[x["sel"] & ~is_m, x["outcome"]])["avg"]) for x in cells])
    rho = is_rank.rank().corr().iloc[0, 1]
    print(f"\n  모든 칸 IS 평균R vs OOS 평균R 순위상관 = {rho:+.2f} (0이면 IS 순위가 OOS를 예측 못 함)")

    # ---- 3. 등급표: 추세 일치 수 × 세션
    grade_rows = []
    for al in (0, 1, 2):
        for se in ("asia", "london", "ny", "late"):
            sel = ((a.aligned == al) & (a.sess == se)).values
            row = dict(aligned=al, session=se)
            for o in ("r_rr3", "r_opp"):
                f, i, s2 = st(a.loc[sel, o]), st(a.loc[sel & is_m, o]), st(a.loc[sel & ~is_m, o])
                tag = o.split("_")[1]
                row.update({f"n_{tag}": f["n"], f"win_{tag}": round(f["win"], 1), f"avgR_{tag}": round(f["avg"], 3),
                            f"is_avgR_{tag}": round(i["avg"], 3), f"oos_avgR_{tag}": round(s2["avg"], 3)})
            fr, ir, orr = row["avgR_rr3"], row["is_avgR_rr3"], row["oos_avgR_rr3"]
            if row["n_rr3"] >= 80 and ir > 0 and orr > 0:
                g = "A"
            elif fr >= 0 and orr >= -0.05:
                g = "B"
            elif fr > -0.10:
                g = "C"
            else:
                g = "D"
            row["grade"] = g
            grade_rows.append(row)
    sym_rows = []
    for s in SYMBOLS:
        sel = (a.sym == s).values
        r = dict(symbol=s)
        for o in ("r_rr3", "r_opp"):
            f, i, s2 = st(a.loc[sel, o]), st(a.loc[sel & is_m, o]), st(a.loc[sel & ~is_m, o])
            tag = o.split("_")[1]
            r.update({f"n_{tag}": f["n"], f"win_{tag}": round(f["win"], 1), f"avgR_{tag}": round(f["avg"], 3),
                      f"is_avgR_{tag}": round(i["avg"], 3), f"oos_avgR_{tag}": round(s2["avg"], 3)})
        sym_rows.append(r)
    print("\n## 3. 등급표 (추세 일치 수 × 세션, RR3 기준 등급)")
    print(pd.DataFrame(grade_rows).to_string(index=False))
    print(pd.DataFrame(sym_rows).to_string(index=False))
    gj = dict(
        generated="2026-10-24", script="trading/research/crt_scorecard.py",
        data="IC Markets M15/D1, 7 symbols, server time = NY+7h", period=f"{a.t.min()} ~ {a.t.max()} (server)",
        split="IS < 2024-01-01 <= OOS", cost="max(bar spread, floor) x point, once per trade",
        setup="H4 CRT sweep -> M15 MSS (fractal N=3, body close inside range) -> OB touch -> M15 close beyond OB -> next open; "
              "SL sweep extreme - 1 pip; max hold 24h",
        keys=dict(aligned="count of D1 and H4 Bias() (EA function) equal to trade direction at entry",
                  session="NY hour of entry bar: asia 19-02, london 02-08, ny 08-12, late 12-19"),
        grade_rule="A: n>=80 and RR3 avg R > 0 in BOTH IS and OOS; B: full avg >= 0 and OOS avg >= -0.05; "
                   "C: full avg > -0.10; D: otherwise",
        warning="No bucket passes the mechanical-system bar; grades are relative, not proof of an edge.",
        grades=grade_rows, symbols=sym_rows,
        candidates=[{k: (v if not isinstance(v, dict) else {kk: (round(float(vv), 3) if vv == vv else None) for kk, vv in v.items()})
                     for k, v in r.items()} for r in results],
        tests=ncell, bonferroni_t=round(zb, 2), is_oos_rank_corr=round(float(rho), 2), bucket_edges=edges,
    )
    with open(os.path.join(out, "crt_grades.json"), "w") as f:
        json.dump(gj, f, ensure_ascii=False, indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ".")
