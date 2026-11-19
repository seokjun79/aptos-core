"""하루 1~3회 거래 전략 연구: 7종목 × 세션별 규칙을 M15 봉으로 시험한다.

원칙 (오늘 배운 것):
- 규칙과 숫자는 미리 정한다. 우리 데이터로 고르지 않는다. 변형은 손익비(RR) 몇 개만 본다.
- 비용 = max(봉 spread, 현재 실제 스프레드). 같은 봉에서 손절·목표가 둘 다 닿으면 손절 먼저(보수적).
- 손절 폭이 비용의 4배보다 작은 거래는 하지 않는다 (비용이 R의 25%를 넘으면 기대값이 사라짐).
- 학습 IS 2019~2023 / 검증 OOS 2024~. 7종목 중 다수에서 IS·OOS 모두 + 여야 후보.

전략:
  ORB_L  런던 오프닝 레인지 돌파: NY 02:00~03:00 범위, 03:00~06:00 돌파 진입, 손절=반대편, 청산 11:00
  ORB_N  뉴욕 오프닝 레인지 돌파: NY 08:00~09:00 범위, 09:00~12:00 돌파 진입, 손절=반대편, 청산 16:00
  FADE_L 아시아 범위 스윕 되돌림: NY 19:00~02:00 범위, 02:00~05:00에 범위 밖을 찌르고 안으로 마감하면 반대 진입,
         손절=찌른 봉 끝, 목표=범위 반대편(RR 상한), 청산 11:00
  PDH    전일 고저 돌파 지속: 전일(NY 17시 기준) 고/저를 03:00~11:00에 돌파 마감하면 같은 방향 진입,
         손절=돌파 봉 반대 끝, 청산 16:00
사용: python intraday.py venus_data.zip
"""
import io
import sys
import zipfile

import numpy as np
import pandas as pd

SERVER_MINUS_NY = 7
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
SPREAD_FLOOR = {"EURUSD": 8, "GBPUSD": 9, "USDJPY": 10, "AUDUSD": 8, "USDCAD": 10, "USDCHF": 9, "XAUUSD": 15}
POINT = {"USDJPY": 0.001, "XAUUSD": 0.01}


def load(zip_path, symbol):
    with zipfile.ZipFile(zip_path) as z:
        df = pd.read_csv(io.BytesIO(z.read(f"{symbol}_M15.csv")))
    ny = pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=SERVER_MINUS_NY)
    df["ny"] = ny
    df["date"] = ny.dt.normalize()
    df["min"] = ny.dt.hour * 60 + ny.dt.minute
    # 거래일: 뉴욕 17시에 바뀜 (17시 이후는 다음날로)
    df["tday"] = (ny + pd.Timedelta(hours=7)).dt.normalize()
    pt = POINT.get(symbol, 0.00001)
    df["cost"] = np.maximum(df["spread"], SPREAD_FLOOR[symbol]) * pt
    return df


def simulate(o, h, l, c, mins, i0, d, entry, sl, tp, exit_min, cost):
    """i0 봉에서 진입가 entry로 들어간 뒤 결과를 R로 돌려준다. 같은 봉 SL/TP는 SL 우선."""
    risk = abs(entry - sl)
    for i in range(i0, len(o)):
        if mins[i] >= exit_min:
            return (d * (o[i] - entry) - cost) / risk
        if d == 1:
            if l[i] <= sl:
                return (-risk - cost) / risk
            if tp is not None and h[i] >= tp:
                return (tp - entry - cost) / risk
        else:
            if h[i] >= sl:
                return (-risk - cost) / risk
            if tp is not None and l[i] <= tp:
                return (entry - tp - cost) / risk
    return (d * (c[-1] - entry) - cost) / risk


def day_arrays(g):
    return g.open.values, g.high.values, g.low.values, g.close.values, g["min"].values, g.cost.values


def orb(df, r0, r1, e1, xmin, rr):
    out = []
    for day, g in df.groupby("date"):
        o, h, l, c, m, cost = day_arrays(g)
        rng = (m >= r0) & (m < r1)
        if rng.sum() < 3:
            continue
        hi, lo = h[rng].max(), l[rng].min()
        idx = np.where((m >= r1) & (m < e1))[0]
        for i in idx:
            up, dn = h[i] > hi, l[i] < lo
            if up and dn:
                break
            if up or dn:
                d = 1 if up else -1
                entry = hi if up else lo  # 스프레드는 simulate에서 한 번만 뺀다
                sl = lo if up else hi
                risk = abs(entry - sl)
                if risk < 4 * cost[i]:
                    break
                tp = entry + d * rr * risk if rr else None
                # 돌파 봉 안에서 손절까지 닿았는지는 알 수 없어 다음 봉부터 판정하되, 돌파 봉 종가가 손절 너머면 손절
                if (d == 1 and c[i] <= sl) or (d == -1 and c[i] >= sl):
                    out.append((day, -1 - cost[i] / risk))
                else:
                    out.append((day, simulate(o, h, l, c, m, i + 1, d, entry, sl, tp, xmin, cost[i])))
                break
    return out


def fade_asia(df, rr):
    out = []
    for tday, g in df.groupby("tday"):
        o, h, l, c, m, cost = day_arrays(g)
        asia = (m >= 19 * 60) | (m < 2 * 60)
        # tday 안에서 19:00~24:00은 전날 저녁, 00:00~02:00은 당일 새벽
        if asia.sum() < 20:
            continue
        hi, lo = h[asia].max(), l[asia].min()
        idx = np.where((m >= 2 * 60) & (m < 5 * 60))[0]
        for i in idx:
            if h[i] > hi and c[i] < hi:
                d, entry, sl = -1, c[i], h[i] + cost[i]
            elif l[i] < lo and c[i] > lo:
                d, entry, sl = 1, c[i], l[i]
            elif c[i] > hi or c[i] < lo:
                break  # 범위 밖에서 마감하면 셋업 무효
            else:
                continue
            risk = abs(entry - sl)
            if risk < 4 * cost[i]:
                break
            target = lo if d == -1 else hi
            tp = target
            if rr and d * (target - entry) > rr * risk:
                tp = entry + d * rr * risk
            if d * (tp - entry) <= 0:
                break
            out.append((tday, simulate(o, h, l, c, m, i + 1, d, entry, sl, tp, 11 * 60, cost[i])))
            break
    return out


def pdh(df, rr):
    out = []
    days = list(df.groupby("tday"))
    for k in range(1, len(days)):
        _, prev = days[k - 1]
        tday, g = days[k]
        ph, pl = prev.high.max(), prev.low.min()
        o, h, l, c, m, cost = day_arrays(g)
        idx = np.where((m >= 3 * 60) & (m < 11 * 60))[0]
        for i in idx:
            if c[i] > ph:
                d, entry, sl = 1, c[i], l[i]
            elif c[i] < pl:
                d, entry, sl = -1, c[i], h[i] + cost[i]
            else:
                continue
            risk = abs(entry - sl)
            if risk < 4 * cost[i]:
                break
            tp = entry + d * rr * risk if rr else None
            out.append((tday, simulate(o, h, l, c, m, i + 1, d, entry, sl, tp, 16 * 60, cost[i])))
            break
    return out


STRATS = {
    "ORB_L": lambda df, rr: orb(df, 2 * 60, 3 * 60, 6 * 60, 11 * 60, rr),
    "ORB_N": lambda df, rr: orb(df, 8 * 60, 9 * 60, 12 * 60, 16 * 60, rr),
    "FADE_L": fade_asia,
    "PDH": pdh,
}


def stats(rs):
    rs = np.asarray(rs)
    if len(rs) == 0:
        return dict(n=0, avg=0, pf=0, t=0)
    w, l = rs[rs > 0].sum(), -rs[rs <= 0].sum()
    t = rs.mean() / (rs.std(ddof=1) / np.sqrt(len(rs))) if len(rs) > 1 and rs.std() > 0 else 0
    return dict(n=len(rs), avg=rs.mean(), pf=w / l if l > 0 else 9, t=t)


def main(zip_path, rrs=(1.0, 1.5, 2.0, None)):
    data = {s: load(zip_path, s) for s in SYMBOLS}
    rows = []
    for name, fn in STRATS.items():
        for rr in rrs:
            for s in SYMBOLS:
                res = pd.DataFrame(fn(data[s], rr), columns=["day", "r"])
                if res.empty:
                    continue
                for part, sub in [("IS", res[res.day < "2024-01-01"]), ("OOS", res[res.day >= "2024-01-01"])]:
                    st = stats(sub.r)
                    rows.append(dict(strat=name, rr=rr if rr else "끝까지", sym=s, part=part, **st))
    t = pd.DataFrame(rows)
    t.to_csv("intraday_results.csv", index=False)
    for (name, rr), g in t.groupby(["strat", "rr"], sort=False):
        is_ = g[g.part == "IS"].set_index("sym")
        oos = g[g.part == "OOS"].set_index("sym")
        both = [s for s in SYMBOLS if s in is_.index and s in oos.index and is_.loc[s, "avg"] > 0 and oos.loc[s, "avg"] > 0]
        tot_n = g.n.sum()
        print(f"\n## {name} RR={rr}  (IS·OOS 둘 다 + 인 종목 {len(both)}/7: {','.join(both)})  하루 평균 거래 {tot_n / 2000:.2f}회(7종목 합)")
        for s in SYMBOLS:
            if s in is_.index and s in oos.index:
                a, b = is_.loc[s], oos.loc[s]
                print(f"  {s}: IS {a.n:4.0f}건 {a.avg:+.3f}R PF{a.pf:.2f} t{a.t:+.1f} | OOS {b.n:4.0f}건 {b.avg:+.3f}R PF{b.pf:.2f} t{b.t:+.1f}")


if __name__ == "__main__":
    main(sys.argv[1])
