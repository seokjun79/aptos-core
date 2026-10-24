"""Venus Sweep Duo v2.10 (trading/mt5/VenusSweepDuo.mq5) 파이썬 이식 + 다종목·견고성 점검.

사용: python -I sweepduo_py.py <venus_data.zip> [--out DIR]

EA 규칙 그대로 (뉴욕 시각, 서버 = 뉴욕 + 7h, 하루 경계 = 뉴욕 17:00):
 모델 1 런던: 레인지 19~02 → 스윕 킬존 02~05 → 진입 마감 08 → 강제 청산 12
 모델 2 뉴욕: 레인지 02~07 → 스윕 킬존 07~10 → 진입 마감 11 → 강제 청산 15
 스윕(레인지 고/저 돌파) → 반대편 종가 이탈이면 무효 → MSS(LenC=2 스윙을 종가로 교차)
 → SL = 스윕 극값 ∓ 0.2×ATR14 → FVG(스윕 이후 3봉 안)면 FVG 지정가(1시간 유효), 아니면 다음 봉 시가 시장가
 → TP = 레인지 반대편(RR>8이면 8R) → 점수(4H 구조추세·FVG·전일고저 스윕·할인/프리미엄·RR≥3·스윕 깊이≥0.5ATR) ≥5, RR≥2
 하루 손실 2회 또는 연속 3패(오늘 손실로 도달)면 그날 중단. 종목당 포지션/대기주문 1개.
백테스트 관례 (crt_mss_ob.py와 동일): 비용 = max(봉 spread, 바닥값)×point 1회, 같은 봉 SL 우선,
 지정가 체결 봉에서는 SL만 검사, R = (손익 − 비용)/실제 위험. IS 2019~2023 / OOS 2024~.
주의: EA는 M5 전용. M5 데이터는 EURUSD뿐 → 다른 종목은 M15로 근사 (EURUSD M5↔M15 차이로 근사 오차를 함께 보고).
"""
import argparse
import io
import itertools
import os
import sys
import zipfile

import numpy as np
import pandas as pd

SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
SYMS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
OOS = pd.Timestamp("2024-01-01")
SRV_MINUS_NY = 7 * 3600

BASE = dict(min_score=5, min_rr=2.0, max_rr=8.0, buf_atr=0.2, len_c=2, wait_sec=3600, max_spread=25,
            max_daily_loss=2, max_consec=3,
            models=((19, 2, 2, 5, 8, 12), (2, 7, 7, 10, 11, 15)))   # (RS, RE, KS, KE, EE, XE) 뉴욕 시각


def read(zp, name):
    with zipfile.ZipFile(zp) as z:
        return pd.read_csv(io.BytesIO(z.read(name)))


def prepare(zp, sym, tf):
    df = read(zp, f"{sym}_{tf}.csv")
    pt = POINT.get(sym, 0.00001)
    t = df.time.values.astype(np.int64)
    ny = t - SRV_MINUS_NY
    d = dict(sym=sym, t=t, o=df.open.values, h=df.high.values, l=df.low.values, c=df.close.values,
             spread=df.spread.values, cost=np.maximum(df.spread.values, SPREAD_FLOOR[sym]) * pt)
    d["m"] = (ny % 86400) // 60                                       # 뉴욕 분
    d["nymid"] = ny - ny % 86400                                      # 뉴욕 자정 (NyClockOfDay 기준)
    d["dkey"] = (ny + 7 * 3600) // 86400                              # 뉴욕 17:00 경계 거래일
    # ATR14 (MT5 iATR = TR 단순이동평균)
    pc = np.r_[d["c"][0], d["c"][:-1]]
    tr = np.maximum(d["h"], pc) - np.minimum(d["l"], pc)
    d["atr"] = pd.Series(tr).rolling(14).mean().bfill().values
    # 전일(서버 날짜 기준 직전 D1 봉) 고저
    d1 = read(zp, f"{sym}_D1.csv")
    d1day = d1.time.values // 86400
    idx = np.searchsorted(d1day, t // 86400, side="left") - 1         # 오늘 서버 날짜보다 앞선 마지막 D1
    idx = np.clip(idx, 0, len(d1) - 1)
    d["pdh"], d["pdl"] = d1.high.values[idx], d1.low.values[idx]
    # 4H 구조 추세 (H1 → 서버시각 4시간 봉, 스윙 5/5, 종가 돌파로 추세 전환) — 직전 마감 4H봉 기준
    h1 = read(zp, f"{sym}_H1.csv")
    h1["b"] = h1.time // 14400
    h4 = h1.groupby("b").agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    hb, H, L, C = h4.index.values, h4.high.values, h4.low.values, h4.close.values
    # EA Trend4H 그대로: 직전 마감봉 L에서 과거 300봉만 다시 훑어 마지막 구조 돌파 방향
    nb, n5 = len(hb), 5
    isH = np.zeros(nb, bool); isL = np.zeros(nb, bool)
    for p in range(n5, nb - n5):
        isH[p] = all(H[p - k] <= H[p] for k in range(1, 6)) and all(H[p + k] < H[p] for k in range(1, 6))
        isL[p] = all(L[p - k] >= L[p] for k in range(1, 6)) and all(L[p + k] > L[p] for k in range(1, 6))
    tr4 = np.zeros(nb, dtype=int)
    for Lq in range(nb):
        st, hsh, hsl, sh, sl = 0, False, False, 0.0, 0.0
        for q in range(max(Lq - 300, 2 * n5 + 2), Lq + 1):
            p = q - n5
            if isH[p]:
                sh, hsh = H[p], True
            if isL[p]:
                sl, hsl = L[p], True
            if hsh and C[q] > sh:
                st, hsh = 1, False
            if hsl and C[q] < sl:
                st, hsl = -1, False
        tr4[Lq] = st
    pos = np.searchsorted(hb, t // 14400, side="left") - 1            # 진행 중 4H봉의 직전 봉
    d["tr4"] = np.where(pos >= 0, tr4[np.clip(pos, 0, None)], 0)
    for k in ("o", "h", "l", "c", "cost", "atr", "pdh", "pdl", "spread"):
        d[k] = d[k].tolist()
    for k in ("t", "m", "nymid", "dkey", "tr4"):
        d[k] = d[k].tolist()
    return d


def inwin(m, a, b):
    return (a <= m < b) if a <= b else (m >= a or m < b)


def run(d, p=BASE, log=None):
    o, h, l, c, t, m, cost, atr = d["o"], d["h"], d["l"], d["c"], d["t"], d["m"], d["cost"], d["atr"]
    n, lenc = len(o), p["len_c"]
    MD = [tuple(x * 60 for x in mm) for mm in p["models"]]
    st = [None, None]
    day = None
    lastPH = lastPL = None
    pend = None      # dict(k, s, e, stp, tp, t0, xe, i0)
    posn = None      # dict(k, s, e, stp, tp, xe, i, cost, risk)
    closed = []      # (entry_t, exit_t, k, s, R, kind)

    def close_pos(i, px, kind):
        nonlocal posn
        r = (posn["s"] * (px - posn["e"]) - posn["cost"]) / posn["risk"]
        closed.append((t[posn["i"]], t[i], posn["k"], posn["s"], r, kind, posn["sc"]))
        posn = None

    def day_stopped(ds):
        lt = cons = 0
        last_loss = -1
        for tr in closed[-40:]:
            if tr[4] < 0:
                cons += 1
                last_loss = tr[1]
                if tr[1] >= ds:
                    lt += 1
            else:
                cons = 0
        return lt >= p["max_daily_loss"] or (cons >= p["max_consec"] and last_loss >= ds)

    for i in range(1, n):
        ti = t[i]
        # (1) ExpireModel / ManagePending (봉 첫 틱 = 시가)
        if posn and ti >= posn["xe"]:
            close_pos(i, o[i], "time")
        if pend and (ti >= pend["xe"] or ti - pend["t0"] > p["wait_sec"]):
            pend = None
        # (2) 직전 확정봉 j = i-1 처리 (ProcessBar)
        j = i - 1
        if d["dkey"][j] != day:
            day = d["dkey"][j]
            st = [dict(hasA=False, swept=0, done=False) for _ in range(2)]
            pend = None
        # UpdateSwings: 피벗 q = j - lenc
        q = j - lenc
        if q - lenc >= 0:
            hp, lp = h[q], l[q]
            if all(h[q - k] <= hp and h[q + k] < hp for k in range(1, lenc + 1)):
                lastPH = hp
            if all(l[q - k] >= lp and l[q + k] > lp for k in range(1, lenc + 1)):
                lastPL = lp
        mj = m[j]
        for k in range(2):
            RS, RE, KS, KE, EE, XE = MD[k]
            s_ = st[k]
            if inwin(mj, RS, RE):
                if not s_["hasA"]:
                    s_.update(hasA=True, aH=h[j], aL=l[j])
                else:
                    s_["aH"] = max(s_["aH"], h[j]); s_["aL"] = min(s_["aL"], l[j])
                continue
            if not s_["hasA"] or s_["done"]:
                continue
            if inwin(mj, KS, KE) and s_["swept"] == 0:
                if h[j] > s_["aH"]:
                    s_.update(swept=-1, swExt=h[j], swT=t[j], swPD=h[j] > d["pdh"][j])
                elif l[j] < s_["aL"]:
                    s_.update(swept=1, swExt=l[j], swT=t[j], swPD=l[j] < d["pdl"][j])
            if s_["swept"] == 0 or not inwin(mj, KS, EE):
                continue
            s = s_["swept"]
            s_["swExt"] = max(s_["swExt"], h[j]) if s == -1 else min(s_["swExt"], l[j])
            if (s == -1 and c[j] < s_["aL"]) or (s == 1 and c[j] > s_["aH"]):
                s_["done"] = True
                continue
            if posn or pend:
                continue
            mss = lastPL if s == -1 else lastPH
            if mss is None or t[j] <= s_["swT"]:
                continue
            crossed = (c[j] < mss <= c[j - 1]) if s == -1 else (c[j] > mss >= c[j - 1])
            if not crossed:
                continue
            a = atr[j]
            stp = s_["swExt"] - s * p["buf_atr"] * a
            hasF, fvg = False, 0.0
            for jj in (j, j - 1, j - 2):
                if t[jj - 2] < s_["swT"]:
                    break
                if s == -1 and h[jj] < l[jj - 2]:
                    fvg, hasF = h[jj], True; break
                if s == 1 and l[jj] > h[jj - 2]:
                    fvg, hasF = l[jj], True; break
            tp = s_["aH"] if s == 1 else s_["aL"]
            useLimit = hasF
            e = fvg if useLimit else c[j]
            if useLimit and s * (e - stp) <= 0:
                useLimit, e = False, c[j]
            risk = abs(e - stp)
            rr = s * (tp - e) / risk if risk > 0 else 0
            mid = (s_["aH"] + s_["aL"]) / 2
            score = ((d["tr4"][j] == s) + hasF + bool(s_["swPD"]) + ((e < mid) if s == 1 else (e > mid))
                     + (rr >= 3) + (abs(s_["swExt"] - (s_["aL"] if s == 1 else s_["aH"])) >= 0.5 * a))
            s_["done"] = True
            if log is not None:
                log.append(dict(t=t[j], k=k, s=s, score=score, rr=rr, t4=d["tr4"][j], hasF=hasF, pd=s_["swPD"],
                                e=e, stp=stp, tp=tp, aH=s_["aH"], aL=s_["aL"], swExt=s_["swExt"], atr=a))
            if rr < p["min_rr"] or score < p["min_score"]:
                continue
            if rr > p["max_rr"]:
                tp = e + s * p["max_rr"] * risk
            ds = (ti - SRV_MINUS_NY + 7 * 3600) // 86400 * 86400 - 7 * 3600 + SRV_MINUS_NY   # 오늘 뉴욕 17:00 (서버)
            if day_stopped(ds):
                continue
            if d["spread"][i] > p["max_spread"]:
                continue
            xe = d["nymid"][i] + XE * 60 + SRV_MINUS_NY
            mind = 2 * (POINT.get(d["sym"], 0.00001))
            if useLimit and s * (o[i] - e) > mind:
                if abs(e - stp) < mind or abs(tp - e) < mind:
                    continue
                pend = dict(k=k, s=s, e=e, stp=stp, tp=tp, t0=ti, xe=xe, sc=score)
            else:
                e = o[i]
                if s * (tp - e) <= mind or s * (e - stp) <= mind:
                    continue
                posn = dict(k=k, s=s, e=e, stp=stp, tp=tp, xe=xe, i=i, cost=cost[i], risk=abs(e - stp), fill=i, sc=score)
        # (3) 봉 i 안의 경로
        if pend:
            s = pend["s"]
            if (s == 1 and h[i] >= pend["tp"]) or (s == -1 and l[i] <= pend["tp"]):
                pend = None
            elif (s == 1 and l[i] <= pend["e"]) or (s == -1 and h[i] >= pend["e"]):
                posn = dict(k=pend["k"], s=s, e=pend["e"], stp=pend["stp"], tp=pend["tp"], xe=pend["xe"], i=i,
                            cost=cost[i], risk=abs(pend["e"] - pend["stp"]), fill=i, lim=True, sc=pend["sc"])
                pend = None
        if posn:
            s = posn["s"]
            if (s == 1 and l[i] <= posn["stp"]) or (s == -1 and h[i] >= posn["stp"]):
                close_pos(i, posn["stp"], "sl")
            elif not (posn.get("lim") and posn["fill"] == i) and (
                    (s == 1 and h[i] >= posn["tp"]) or (s == -1 and l[i] <= posn["tp"])):
                close_pos(i, posn["tp"], "tp")
    res = pd.DataFrame(closed, columns=["entry_t", "exit_t", "model", "dir", "R", "kind", "score"])
    for col in ("entry_t", "exit_t"):
        res[col] = pd.to_datetime(res[col], unit="s")
    res["symbol"] = d["sym"]
    return res


def stats(r, days):
    r = np.asarray(r, dtype=float)
    if len(r) == 0:
        return dict(n=0, avgR=np.nan, sumR=0.0, PF=np.nan, DD=0.0, win=np.nan, tpd=0.0)
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max()
    return dict(n=len(r), avgR=r.mean(), sumR=r.sum(), PF=w / ls if ls else np.inf, DD=dd,
                win=(r > 0).mean() * 100, tpd=len(r) / days)


def split(res, d):
    tdays = pd.to_datetime(np.unique(d["dkey"]) * 86400, unit="s")
    nis, noos = (tdays < OOS).sum(), (tdays >= OOS).sum()
    a = res[res.entry_t < OOS]
    b = res[res.entry_t >= OOS]
    return stats(a.R, nis), stats(b.R, noos), stats(res.R, nis + noos)


def fmt(x):
    return (f"{x['n']:4d} {x['avgR']:+.3f} {x['sumR']:+6.1f}R PF {x['PF']:.2f} DD {x['DD']:5.1f}R "
            f"win {x['win']:4.1f}% {x['tpd']:.3f}/d") if x["n"] else "   0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    work = os.path.join(a.out, "_sweepduo_work")
    os.makedirs(work, exist_ok=True)
    rows = []
    cache = {}
    # 0) 이식 검증: EURUSD M5 (EA와 같은 시간프레임) vs M15
    for tf in ("M5", "M15"):
        d = prepare(a.zip, "EURUSD", tf)
        cache[("EURUSD", tf)] = d
        res = run(d)
        res.to_csv(os.path.join(work, f"eurusd_{tf}_trades.csv"), index=False)
        i_, o_, all_ = split(res, d)
        print(f"EURUSD {tf} ALL {fmt(all_)}\n          IS  {fmt(i_)}\n          OOS {fmt(o_)}")
        for k, g in res.groupby("model"):
            print(f"    model {'London' if k == 0 else 'NY'}: {fmt(stats(g.R, 1))}")
        for y, g in res.groupby(res.entry_t.dt.year):
            print(f"    {y}: {len(g):3d} {g.R.sum():+6.1f}R", end="")
        print("\n    exit kinds:", res.kind.value_counts().to_dict())
    # 1) 7종목 같은 파라미터 (EURUSD는 M5, 나머지 M15)
    for sym in SYMS:
        tf = "M5" if sym == "EURUSD" else "M15"
        d = cache.get((sym, tf)) or prepare(a.zip, sym, tf)
        cache[(sym, tf)] = d
        res = run(d)
        i_, o_, _ = split(res, d)
        rows.append(dict(symbol=sym, tf=tf, **{f"IS_{k}": v for k, v in i_.items()},
                         **{f"OOS_{k}": v for k, v in o_.items()}))
        res.to_csv(os.path.join(work, f"trades_{sym}_{tf}.csv"), index=False)
        if i_["n"] and o_["n"] and i_["avgR"] > 0 and o_["avgR"] > 0:
            out = res[["entry_t", "exit_t", "symbol", "dir", "R"]].rename(columns={"entry_t": "entry_time", "exit_t": "exit_time"})
            # EA 원래 시간프레임(M5)으로 돈 종목만 포트폴리오 후보. M15 근사는 검증 실패라 작업 폴더에만.
            name = f"sweepduo_{sym}.csv" if tf == "M5" else f"_sweepduo_work/m15proxy_{sym}.csv"
            out.to_csv(os.path.join(a.out, name), index=False)
        print(f"{sym} {tf} IS {fmt(i_)} | OOS {fmt(o_)}")
    pd.DataFrame(rows).to_csv(os.path.join(work, "symbols.csv"), index=False)
    # 2) 견고성 격자 (IS만, EURUSD M5): buf_atr, min_rr, max_rr 각 ±25% (미리 선언)
    d = cache[("EURUSD", "M5")]
    cut = int(np.searchsorted(np.asarray(d["t"]), int(OOS.timestamp())))
    dis = {k: (v[:cut] if isinstance(v, list) else v) for k, v in d.items()}
    grid = []
    for b, rr, mx in itertools.product((0.15, 0.2, 0.25), (1.5, 2.0, 2.5), (6.0, 8.0, 10.0)):
        pr = dict(BASE, buf_atr=b, min_rr=rr, max_rr=mx)
        r = run(dis, pr)
        s_ = stats(r.R, 1)
        grid.append(dict(buf_atr=b, min_rr=rr, max_rr=mx, n=s_["n"], avgR=s_["avgR"], sumR=s_["sumR"], PF=s_["PF"], DD=s_["DD"]))
        print(f"grid buf {b:.2f} minRR {rr:.1f} maxRR {mx:4.1f}: {fmt(s_)}")
    pd.DataFrame(grid).to_csv(os.path.join(work, "grid_is.csv"), index=False)
    # 2b) 빈도 늘리기 변형 (미리 선언, 1개): 최소 점수 4
    for sc in (4, 6):
        r = run(d, dict(BASE, min_score=sc))
        i_, o_, _ = split(r, d)
        print(f"EURUSD min_score={sc}: IS {fmt(i_)} | OOS {fmt(o_)}")


if __name__ == "__main__":
    main()
