"""평균회귀(되돌림) 전략 4가족 사전 선언 시험 — 7종목, IS 2019~2023 / OOS 2024~.

규칙과 숫자는 데이터를 보기 전에 정했다 (전략마다 변형 2개 이하). 결과를 보고 바꾸지 않는다.
관례(intraday.py, crt_mss_ob.py와 동일):
- 시각: 서버 = 뉴욕 + 7h. 거래일은 뉴욕 17시에 바뀜 (D1 봉 = 뉴욕 17:00 ~ 다음날 17:00).
- 비용 = max(봉 spread, 현재 실제 스프레드) × point, 거래당 한 번. 매도 손절은 차트(매도호가) 극값 + 비용.
- 같은 봉에서 손절·목표가 둘 다 닿으면 손절 먼저. R = 진입 때 정한 손절 폭 기준.
- 손절 폭 < 비용 4배인 거래는 건너뜀. 종목당 동시에 1포지션.
- 스왑(하룻밤 이자)은 넣지 않았다 → 여러 날 들고 가는 RSI2는 실제보다 약간 좋게 나올 수 있음.

전략:
 RSI2   (D1, Connors) 종가 > SMA200 이고 RSI(2) < 10 → 다음 봉 시가 매수 (매도는 대칭 > 90).
        청산: 종가가 SMA5 위로(매도는 아래로) 마감하면 그 종가, 또는 10봉 뒤 종가. 손절 2.5×ATR(20).
        변형: 문턱 10/90, 5/95.
 BBASIA (H1) 볼린저(20, k). 아시아(뉴욕 19:00~02:00 사이에 마감하는 H1 봉)에서 직전 종가가 밴드 밖,
        이번 종가가 밴드 안 → 그 종가에 반대 진입. 목표 = 진입 때 중심선, 손절 = 밴드 밖 구간 극값 ∓ 0.5×ATR(14).
        뉴욕 03:00 강제 청산. 진입 후 판정은 M15. 변형: k = 2.0, 2.5.
 PDRF   전일 범위 되돌림: 런던(뉴욕 02:00~08:00에 마감하는 H1 봉) 동안 가격이 전일 고가(저가) 너머로 나갔다가
        H1 종가가 전일 범위 안으로 돌아오면 그 종가에 반대 진입. 손절 = 오늘 그때까지 극값 너머.
        목표: (a) 전일 중간값, (b) 1.5R. 뉴욕 12:00 청산. 하루 1번.
 GAP    월요일(주 시작) 갭 되돌림: 주 첫 봉 시가 − 지난 금요일 종가 = 갭. |갭| ≥ m×ATR(20, D1)이고
        뉴욕 18:00(첫 1시간 뒤)까지 갭이 메워지지 않았으면 18:00 시가에 갭 반대 방향 진입.
        목표 = 금요일 종가, 손절 = 진입가에서 |갭| 만큼 반대. 월요일 뉴욕 12:00 청산. 변형: m = 0.25, 0.5.
포트폴리오 CSV의 시각은 서버시각(뉴욕+7h), 화면 출력·내부 계산은 뉴욕시각.
사용: python meanrev_family.py venus_data.zip [portfolio_dir]
"""
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

SERVER_MINUS_NY = 7
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}
SPLIT = pd.Timestamp("2024-01-01")
H = 3600


def load(zp, sym, tf):
    with zipfile.ZipFile(zp) as z:
        df = pd.read_csv(io.BytesIO(z.read(f"{sym}_{tf}.csv")))
    df["ny"] = pd.to_datetime(df.time, unit="s") - pd.Timedelta(hours=SERVER_MINUS_NY)
    df["nys"] = df.time.values - SERVER_MINUS_NY * H          # 뉴욕 시각(초), 비교용
    df["cost"] = np.maximum(df.spread, SPREAD_FLOOR[sym]) * POINT.get(sym, 0.00001)
    return df.reset_index(drop=True)


def atr(df, n):
    pc = df.close.shift()
    tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
    return tr.rolling(n).mean()


def rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def sim(m, i0, d, entry, sl, tp, exit_s, cost):
    """M15 배열 m에서 i0 봉부터 판정. exit_s(뉴욕 초) 이후 첫 봉 시가에 청산. 반환 (청산 인덱스, R)."""
    o, h, l, t = m["o"], m["h"], m["l"], m["t"]
    risk = abs(entry - sl)
    for i in range(i0, len(o)):
        if t[i] >= exit_s:
            return i, (d * (o[i] - entry) - cost) / risk
        if (d == 1 and l[i] <= sl) or (d == -1 and h[i] >= sl):
            return i, (-risk - cost) / risk
        if tp is not None and ((d == 1 and h[i] >= tp) or (d == -1 and l[i] <= tp)):
            return i, (abs(tp - entry) - cost) / risk
    return len(o) - 1, (d * (m["c"][-1] - entry) - cost) / risk


def marr(m15):
    return dict(o=m15.open.values, h=m15.high.values, l=m15.low.values, c=m15.close.values, t=m15.nys.values)


# ---------------------------------------------------------------- 1. RSI2
def rsi2(D, M, H1, sym, thr):
    c = D.close
    sma200, sma5, a = c.rolling(200).mean().values, c.rolling(5).mean().values, atr(D, 20).values
    r2 = rsi(c, 2).values
    o, h, l, cl, t, cost = D.open.values, D.high.values, D.low.values, c.values, D.ny.values, D.cost.values
    out, k = [], 200
    while k < len(D) - 1:
        d = 1 if (cl[k] > sma200[k] and r2[k] < thr) else -1 if (cl[k] < sma200[k] and r2[k] > 100 - thr) else 0
        if d == 0 or np.isnan(a[k]):
            k += 1
            continue
        e = k + 1
        entry, risk = o[e], 2.5 * a[k]
        sl = entry - d * risk + (cost[e] if d == -1 else 0)
        risk = abs(entry - sl)
        res = None
        for j in range(e, min(len(D), e + 10)):
            if (d == 1 and l[j] <= sl) or (d == -1 and h[j] >= sl):
                res = (j, (-risk - cost[e]) / risk)
                break
            if (d == 1 and cl[j] > sma5[j]) or (d == -1 and cl[j] < sma5[j]) or j == e + 9 or j == len(D) - 1:
                res = (j, (d * (cl[j] - entry) - cost[e]) / risk)
                break
        out.append((t[e], t[res[0]] + np.timedelta64(1, "D"), d, res[1]))
        k = res[0] + 1
    return out


# ---------------------------------------------------------------- 2. Bollinger Asia fade
def bbasia(D, M, H1, sym, kstd):
    c = H1.close
    mid, sd = c.rolling(20).mean().values, c.rolling(20).std(ddof=0).values
    up, lo = mid + kstd * sd, mid - kstd * sd
    a = atr(H1, 14).values
    o, h, l, cl, ts, cost = H1.open.values, H1.high.values, H1.low.values, c.values, H1.nys.values, H1.cost.values
    m = marr(M)
    mt = m["t"]
    out, busy = [], -1
    for k in range(21, len(H1)):
        close_s = ts[k] + H
        hr = ((close_s // H) % 24)
        if not (hr >= 20 or hr <= 2):          # 마감 시각이 19:00 초과 ~ 02:00 이하
            continue
        if close_s <= busy or np.isnan(a[k]):
            continue
        if cl[k - 1] < lo[k - 1] and cl[k] > lo[k]:
            d = 1
        elif cl[k - 1] > up[k - 1] and cl[k] < up[k]:
            d = -1
        else:
            continue
        j = k - 1                                # 밴드 밖 구간의 시작까지 거슬러 올라감
        while j - 1 >= 0 and ((d == 1 and cl[j - 1] < lo[j - 1]) or (d == -1 and cl[j - 1] > up[j - 1])):
            j -= 1
        ext = l[j:k + 1].min() if d == 1 else h[j:k + 1].max()
        entry, tp = cl[k], mid[k]
        sl = ext - 0.5 * a[k] if d == 1 else ext + 0.5 * a[k] + cost[k]
        risk = abs(entry - sl)
        if risk < 4 * cost[k] or d * (tp - entry) <= 0:
            continue
        # 강제 청산: 진입 이후 첫 뉴욕 03:00
        day0 = (close_s // 86400) * 86400
        exit_s = day0 + 3 * H if close_s < day0 + 3 * H else day0 + 86400 + 3 * H
        i0 = np.searchsorted(mt, close_s)
        if i0 >= len(mt):
            break
        xi, r = sim(m, i0, d, entry, sl, tp, exit_s, cost[k])
        out.append((pd.Timestamp(close_s, unit="s"), pd.Timestamp(mt[xi], unit="s"), d, r))
        busy = mt[xi]
    return out


# ---------------------------------------------------------------- 3. 전일 범위 되돌림
def pdrf(D, M, H1, sym, tgt):
    m = marr(M)
    mt = m["t"]
    H1 = H1.copy()
    H1["tday"] = ((H1.nys + 7 * H) // 86400)
    o, h, l, cl, ts, cost = H1.open.values, H1.high.values, H1.low.values, H1.close.values, H1.nys.values, H1.cost.values
    groups = [g.index.values for _, g in H1.groupby("tday")]
    out = []
    for gi in range(1, len(groups)):
        p, g = groups[gi - 1], groups[gi]
        if len(p) < 15 or len(g) < 10:
            continue
        ph, pl = h[p].max(), l[p].min()
        pmid = (ph + pl) / 2
        breached_up = breached_dn = False
        for k in g:
            close_s = ts[k] + H
            hr = (close_s // H) % 24
            if 8 < hr < 17:
                break
            if not 3 <= hr <= 8:                 # 런던: 뉴욕 02:00~07:00에 시작하는 H1 봉
                continue
            breached_up |= h[k] > ph
            breached_dn |= l[k] < pl
            if not pl < cl[k] < ph or breached_up == breached_dn:
                continue                         # 아직 안 나갔거나, 양쪽 다 나갔으면 애매 → 건너뜀
            d = -1 if breached_up else 1
            day_idx = g[g <= k]
            ext = l[day_idx].min() if d == 1 else h[day_idx].max()
            entry = cl[k]
            sl = ext if d == 1 else ext + cost[k]
            risk = abs(entry - sl)
            if risk < 4 * cost[k]:
                break
            tp = pmid if tgt == "mid" else entry + d * 1.5 * risk
            if d * (tp - entry) <= 0:
                break
            day0 = (close_s // 86400) * 86400
            i0 = np.searchsorted(mt, close_s)
            if i0 >= len(mt):
                break
            xi, r = sim(m, i0, d, entry, sl, tp, day0 + 12 * H, cost[k])
            out.append((pd.Timestamp(close_s, unit="s"), pd.Timestamp(mt[xi], unit="s"), d, r))
            break
    return out


# ---------------------------------------------------------------- 4. 주초 갭 되돌림
def gap(D, M, H1, sym, mult):
    m = marr(M)
    mt, mo, mc = m["t"], m["o"], m["c"]
    cost = M.cost.values
    a = atr(D, 20).values
    dt = D.nys.values
    out = []
    jumps = np.flatnonzero(np.diff(mt) > 36 * H) + 1     # 주말 공백 뒤 첫 봉
    for i in jumps:
        fri_close, wk_open = mc[i - 1], mo[i]
        di = np.searchsorted(dt, mt[i - 1], side="right") - 1
        if di < 20 or np.isnan(a[di]):
            continue
        g = wk_open - fri_close
        if abs(g) < mult * a[di]:
            continue
        d = -1 if g > 0 else 1
        e = np.searchsorted(mt, mt[i] + H)
        if e >= len(mt) or mt[e] > mt[i] + 2 * H:
            continue
        seg = slice(i, e)
        if (d == -1 and m["l"][seg].min() <= fri_close) or (d == 1 and m["h"][seg].max() >= fri_close):
            continue                                   # 첫 1시간 안에 이미 메워짐
        entry = mo[e]
        if d * (fri_close - entry) <= 0:
            continue
        sl = entry - d * abs(g) + (cost[e] if d == -1 else 0)
        risk = abs(entry - sl)
        if risk < 4 * cost[e]:
            continue
        day0 = ((mt[i] + 7 * H) // 86400) * 86400      # 월요일 (뉴욕 날짜)
        xi, r = sim(m, e, d, entry, sl, fri_close, day0 + 12 * H, cost[e])
        out.append((pd.Timestamp(mt[e], unit="s"), pd.Timestamp(mt[xi], unit="s"), d, r))
    return out


STRATS = [("RSI2_10", rsi2, 10), ("RSI2_5", rsi2, 5),
          ("BBASIA_2.0", bbasia, 2.0), ("BBASIA_2.5", bbasia, 2.5),
          ("PDRF_mid", pdrf, "mid"), ("PDRF_1.5R", pdrf, "r15"),
          ("GAP_0.25", gap, 0.25), ("GAP_0.5", gap, 0.5)]


def stats(df):
    r = df.R.values
    if len(r) == 0:
        return dict(n=0, avg=np.nan, pf=np.nan, dd=0.0, sum=0.0)
    w, ls = r[r > 0].sum(), -r[r <= 0].sum()
    eq = np.cumsum(df.sort_values("exit_time").R.values)
    dd = float((np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]).max())
    return dict(n=len(r), avg=r.mean(), pf=w / ls if ls > 0 else 9.0, dd=dd, sum=r.sum())


def main(zp, pdir):
    os.makedirs(pdir, exist_ok=True)
    data = {s: (load(zp, s, "D1"), load(zp, s, "M15"), load(zp, s, "H1")) for s in SYMBOLS}
    last = max(v[1].ny.max() for v in data.values())
    days = {"IS": len(pd.bdate_range("2019-01-01", "2023-12-31")), "OOS": len(pd.bdate_range("2024-01-01", last))}
    rows, alltr = [], []
    for name, fn, p in STRATS:
        for s in SYMBOLS:
            tr = pd.DataFrame(fn(*data[s], s, p), columns=["entry_time", "exit_time", "dir", "R"])
            tr.insert(2, "symbol", s)
            tr["strat"] = name
            alltr.append(tr)
            for part, sub in (("IS", tr[tr.entry_time < SPLIT]), ("OOS", tr[tr.entry_time >= SPLIT])):
                rows.append(dict(strat=name, sym=s, part=part, **stats(sub)))
    T = pd.DataFrame(rows)
    A = pd.concat(alltr, ignore_index=True)
    A.to_csv(os.path.join(os.path.dirname(pdir.rstrip("/")), "data", "meanrev_all_trades.csv"), index=False)
    print(f"기간: 2019-01-02 ~ {last:%Y-%m-%d} (뉴욕시각), 거래일 IS {days['IS']} / OOS {days['OOS']}")
    verdict = []
    for name, _, _ in STRATS:
        g = T[T.strat == name]
        a = A[A.strat == name]
        piv = g.pivot(index="sym", columns="part", values="avg")
        both = [s for s in SYMBOLS if piv.loc[s, "IS"] > 0 and piv.loc[s, "OOS"] > 0]
        tot = {part: stats(a[(a.entry_time < SPLIT) if part == "IS" else (a.entry_time >= SPLIT)]) for part in ("IS", "OOS")}
        print(f"\n## {name}  IS·OOS 둘 다 + : {len(both)}/7 {','.join(both)}")
        for part in ("IS", "OOS"):
            x = tot[part]
            print(f"  7종목 {part:3s}: {x['n']:5d}건 평균 {x['avg']:+.3f}R PF {x['pf']:.2f} 합 {x['sum']:+7.1f}R "
                  f"낙폭 {x['dd']:5.1f}R 하루 {x['n'] / days[part]:.2f}회")
        for s in SYMBOLS:
            i, o = g[(g.sym == s) & (g.part == "IS")].iloc[0], g[(g.sym == s) & (g.part == "OOS")].iloc[0]
            cell_pass = o.pf >= 1.2 and o.dd <= 10 and o.n >= 60 and i.avg > 0 and o.avg > 0
            print(f"   {s}: IS {i.n:4d} {i.avg:+.3f}R PF{i.pf:4.2f} DD{i.dd:5.1f} | OOS {o.n:4d} {o.avg:+.3f}R "
                  f"PF{o.pf:4.2f} DD{o.dd:5.1f} {o.n / days['OOS']:.2f}/일 {'PASS' if cell_pass else ''}")
            if s in both:
                sub = a[a.symbol == s][["entry_time", "exit_time", "symbol", "dir", "R"]].copy()
                for col in ("entry_time", "exit_time"):     # 다른 포트폴리오 파일과 맞춰 서버시각으로 저장
                    sub[col] = sub[col] + pd.Timedelta(hours=SERVER_MINUS_NY)
                sub.to_csv(os.path.join(pdir, f"{name}_{s}.csv"), index=False)
        port_pass = (tot["OOS"]["pf"] >= 1.2 and tot["OOS"]["dd"] <= 15 and tot["OOS"]["n"] >= 60
                     and tot["IS"]["avg"] > 0 and tot["OOS"]["avg"] > 0)
        verdict.append((name, port_pass, len(both)))
    print("\n판정(7종목 합 기준):", verdict)
    T.to_csv(os.path.join(os.path.dirname(pdir.rstrip("/")), "data", "meanrev_results.csv"), index=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "portfolio")
