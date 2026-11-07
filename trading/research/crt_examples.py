"""H4 CRT + M15 MSS/FVG 장면 찾기 (예시 차트용, 성과 검증 아님)."""
import io, zipfile
import pandas as pd

P = 0.0001


def load(zip_path):
    m = pd.read_csv(io.BytesIO(zipfile.ZipFile(zip_path).read("EURUSD_M15.csv")))
    m["srv"] = pd.to_datetime(m.time, unit="s")
    return m.set_index("srv")


def setups(m, start="2025-01-01"):
    h4 = m.resample("4h", origin="epoch").agg({"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
    for k in range(1, len(h4) - 1):
        t2 = h4.index[k]
        if t2 < pd.Timestamp(start) or (t2 - pd.Timedelta(hours=7)).hour not in (1, 5):
            continue
        c1, c2 = h4.iloc[k - 1], h4.iloc[k]
        if not (20 <= (c1.high - c1.low) / P <= 60):
            continue
        for d in (1, -1):
            ok = (c2.low < c1.low if d == 1 else c2.high > c1.high) and c1.low < c2.close < c1.high
            if not ok:
                continue
            r = trace(m, h4.index[k - 1], t2, d, c1)
            if r:
                yield r


def trace(m, t1, t2, d, c1):
    w = m.loc[t1:t2 + pd.Timedelta(hours=8) - pd.Timedelta(minutes=15)]
    n1, n2 = len(m.loc[t1:t2 - pd.Timedelta(minutes=15)]), len(m.loc[t1:t2 + pd.Timedelta(hours=4) - pd.Timedelta(minutes=15)])
    h, l, c = w.high.values, w.low.values, w.close.values
    seg = range(n1, n2)
    ws = min(seg, key=lambda i: l[i]) if d == 1 else max(seg, key=lambda i: h[i])
    ext = l[ws] if d == 1 else h[ws]
    sh = next((k for k in range(ws - 1, 2, -1)
               if (d == 1 and h[k] > h[k - 1] and h[k] >= h[k - 2] and h[k] >= h[k + 1] and h[k] >= h[k + 2]) or
               (d == -1 and l[k] < l[k - 1] and l[k] <= l[k - 2] and l[k] <= l[k + 1] and l[k] <= l[k + 2])), None)
    if sh is None:
        return None
    lvl = h[sh] if d == 1 else l[sh]
    mss = None
    for k in range(ws + 1, n2):           # MSS는 C2 안에서
        if (d == 1 and l[k] < ext) or (d == -1 and h[k] > ext):
            return None                   # MSS 전에 스윕 극값을 다시 깨면 무효
        if (d == 1 and c[k] > lvl) or (d == -1 and c[k] < lvl):
            mss = k
            break
    if mss is None:
        return None
    fvg = next(((k, h[k - 2], l[k]) if d == 1 else (k, l[k - 2], h[k])
                for k in range(max(ws + 2, mss - 2), min(mss + 3, len(w)))
                if (d == 1 and h[k - 2] < l[k]) or (d == -1 and l[k - 2] > h[k])), None)
    if fvg is None:
        return None
    entry = fvg[2]
    ei = next((k for k in range(fvg[0] + 1, len(w)) if (d == 1 and l[k] <= entry) or (d == -1 and h[k] >= entry)), None)
    if ei is None:
        return None
    sl = ext - d * P
    tp = c1.high if d == 1 else c1.low
    risk = abs(entry - sl)
    rr = d * (tp - entry) / risk
    if rr < 2:
        return None
    res = None
    for k in range(ei, len(w)):
        if (d == 1 and l[k] <= sl) or (d == -1 and h[k] >= sl):
            res = "손절"; break
        if (d == 1 and h[k] >= tp) or (d == -1 and l[k] <= tp):
            res = "목표"; break
    return dict(t1=t1, t2=t2, d=d, ws=ws, sh=sh, mss=mss, fvg=fvg, ei=ei, entry=entry, sl=sl, tp=tp, rr=rr, res=res, n1=n1, n2=n2)


if __name__ == "__main__":
    import sys
    m = load(sys.argv[1])
    for s in setups(m):
        print(s["t2"], "매수" if s["d"] == 1 else "매도", f"RR {s['rr']:.1f}", s["res"], f"손절 {abs(s['entry']-s['sl'])/P:.1f}핍")
