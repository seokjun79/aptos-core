"""석준님 SMC+CRT 매매법 백테스트 (4H CRT -> M15 MSS -> OB 지정가), 변형 비교용.

정의는 VenusCRTAssistant.mq5(EA)와 trading/rules/smc-crt-analysis.md 에 맞췄다. 매수 기준, 매도는 대칭.
 1. 4H CRT: 직전 마감 4H봉(C1)의 CRH/CRL. 다음 4H봉(C2) 안에서 M15 저가가 CRL 아래로 나가면 '스윕'.
    (기본) C2가 CRL~CRH 안에서 마감해야 성립. 아시아장(뉴욕 19~2시에 시작하는 C2)은 기본 제외.
 2. MSS 선(EA TrueMssLevel 과 같음): 스윕 극값 봉에서 거꾸로 가며 처음 만나는 M15 스윙 고점
    (왼쪽 N봉보다 높고 오른쪽 N봉 이상). CRH 이상인 고점은 건너뜀. C1에서 CRL을 만든 봉 이후만 본다.
    스윙은 오른쪽 N봉이 극값 봉까지 안에 다 있어야 함(= 그 시점에 확정된 스윙만 사용, 미래 엿보기 없음).
    극값이 더 낮아지면 MSS 선을 다시 계산. 확정 = M15 양봉 종가가 MSS 선 위, 종가가 CRL~CRH 안.
 3. OB = 확정 봉 직전부터 극값 봉까지 거꾸로 가며 처음 만나는 음봉(M15).
    진입 지정가: A) OB 고가  B) OB 시가(몸통 위)  C) 극값~돌파 고점 50%.
    주문은 '확정 봉 마감'과 'C2 마감' 중 늦은 시각에 걸린다(C2 마감 조건을 미래 정보 없이 쓰기 위해).
    유효시간 X개 M15봉(기본 16 = 4시간). 체결 전에 CRH(목표 구조)에 먼저 닿으면 취소.
 4. 손절: S1) OB 저가-1핍  S2) 스윕 극값-1핍
          S3) 극값 이후 ~ 체결 직전까지 확정된 M15 저점(앞뒤 1봉) 중 진입가 아래에서
              2핍 이내로 2개 이상 모인 '같은 높이 저점 묶음' 중 가장 낮은 묶음 아래 -1핍. 없으면 S2로 대체.
 5. 목표: T1) CRH  T2) 2R  T3) 3R  T4) 주문 시점에 확정된 직전 4H 스윙 고점(앞뒤 2봉) 중 CRH 위에서
          가장 최근 것. 없으면 CRH로 대체.
 6. 체결·청산은 M5로 본다. 같은 M5 봉에서 손절·목표가 모두 닿으면 손절. 체결한 봉에서는 목표를 인정하지
    않고 손절만 본다(보수적). 스프레드(핍)를 적용: 차트는 bid, 매수는 ask로 사고 bid로 판다.

읽기 전용 분석 스크립트다. MT5 연결·주문 없음. 필요한 것: Python 3.10+, pandas, numpy.
사용 예:
  python crt_backtest.py --data-dir C:\\Users\\kun00\\venus\\mt5_m5_data --out C:\\Users\\kun00\\venus\\crt_bt_out
  python crt_backtest.py --data-dir ... --out ... --symbols EURUSD
  python crt_backtest.py --selftest
"""
import argparse
import os
import sys
import time as _time

try:
    import numpy as np
    import pandas as pd
except ImportError:  # 설치 안내만
    print("pandas/numpy 가 없습니다. 명령창에서 다음을 실행한 뒤 다시 돌려 주세요:\n"
          "  python -m pip install pandas numpy")
    sys.exit(1)

NS_MIN = 60 * 1_000_000_000
NS_H = 60 * NS_MIN
SERVER_MINUS_NY = 7          # IC마켓 서버시간 = 뉴욕 + 7
ENTRIES = ["A", "B", "C"]
STOPS = ["S1", "S2", "S3"]
TARGETS = ["T1", "T2", "T3", "T4"]
ENTRY_DESC = {"A": "OB 고가", "B": "OB 시가(몸통)", "C": "스윕~돌파 50%"}
STOP_DESC = {"S1": "OB 끝-1핍", "S2": "스윕 극값-1핍", "S3": "같은높이 저점묶음 너머-1핍"}
TARGET_DESC = {"T1": "CRH/CRL", "T2": "2R", "T3": "3R", "T4": "직전 4H 스윙"}


# ---------------------------------------------------------------- 데이터 읽기
def _norm(c):
    return str(c).strip().strip("<>").strip().lower().replace(" ", "_")


def load_m5(path, verbose=True):
    """MT5 내보내기 CSV를 유연하게 읽는다. time/open/high/low/close 를 찾아 서버시간 인덱스로 돌려준다."""
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        first = f.readline()
        second = f.readline()
    sep = "\t" if "\t" in first else (";" if first.count(";") > first.count(",") else ",")
    if verbose:
        print(f"  [헤더] {os.path.basename(path)}: {first.strip()[:200]}")
        print(f"  [첫 줄] {second.strip()[:200]}")
    toks = [_norm(x) for x in first.strip().split(sep)]
    has_header = any(t in ("open", "o", "high", "close") for t in toks)
    if has_header:
        df = pd.read_csv(path, sep=sep, encoding="utf-8-sig")
        df.columns = [_norm(c) for c in df.columns]
    else:
        df = pd.read_csv(path, sep=sep, header=None)
        k = df.shape[1]
        # 머리글 없음: date,time,o,h,l,c,... 또는 datetime,o,h,l,c,...
        if k >= 6 and not _is_number(str(df.iloc[0, 1])):
            names = ["date", "time", "open", "high", "low", "close"] + [f"x{i}" for i in range(k - 6)]
        else:
            names = ["time", "open", "high", "low", "close"] + [f"x{i}" for i in range(k - 5)]
        df.columns = names
    cols = set(df.columns)

    def pick(*cands):
        for c in cands:
            if c in cols:
                return c
        return None

    co, ch, cl, cc = pick("open", "o", "bidopen"), pick("high", "h", "bidhigh"), pick("low", "l", "bidlow"), pick("close", "c", "bidclose")
    if not all([co, ch, cl, cc]):
        raise ValueError(f"open/high/low/close 열을 못 찾음: {list(df.columns)}")
    cdate, ctime = pick("date", "day"), pick("time", "datetime", "date_time", "timestamp", "time_(utc)", "gmt_time", "local_time")
    if cdate and ctime and cdate != ctime:
        raw = df[cdate].astype(str).str.strip() + " " + df[ctime].astype(str).str.strip()
        ts = _parse_time(raw)
    elif ctime or cdate:
        ts = _parse_time(df[ctime or cdate])
    else:
        raise ValueError(f"시간 열을 못 찾음: {list(df.columns)}")
    out = pd.DataFrame({"o": pd.to_numeric(df[co], errors="coerce").values,
                        "h": pd.to_numeric(df[ch], errors="coerce").values,
                        "l": pd.to_numeric(df[cl], errors="coerce").values,
                        "c": pd.to_numeric(df[cc], errors="coerce").values}, index=pd.DatetimeIndex(ts))
    out = out[~out.index.isna()].dropna()
    out = out[~out.index.duplicated(keep="first")].sort_index()
    if verbose:
        print(f"  [읽음] {len(out):,}봉, {out.index[0]} ~ {out.index[-1]} (서버시간)")
    return out


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def _parse_time(s):
    s = pd.Series(s)
    if pd.api.types.is_numeric_dtype(s):
        v = s.astype("int64")
        unit = "ms" if v.iloc[0] > 10**12 else "s"
        return pd.to_datetime(v, unit=unit).values
    s = s.astype(str).str.strip().str.replace(".", "-", n=2, regex=False)
    if s.str.fullmatch(r"\d{9,13}").all():
        return _parse_time(s.astype("int64"))
    return pd.to_datetime(s, errors="coerce").values


# ---------------------------------------------------------------- 시간 도구
def bars_from_m5(t, o, h, l, c, minutes):
    """M5 배열을 서버시간 기준으로 묶는다(15분, 240분). 시작시각 라벨."""
    step = minutes * NS_MIN
    key = t - (t % step)
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(t)] - 1
    return dict(t=key[starts], o=o[starts], h=np.maximum.reduceat(h, starts),
                l=np.minimum.reduceat(l, starts), c=c[ends])


def ny_hour(t_ns):
    return ((t_ns // NS_H) - SERVER_MINUS_NY) % 24


def _us_dst_bounds(year):
    mar1 = pd.Timestamp(year=year, month=3, day=1)
    second_sun = mar1 + pd.Timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = pd.Timestamp(year=year, month=11, day=1)
    first_sun = nov1 + pd.Timedelta(days=(6 - nov1.weekday()) % 7)
    return second_sun + pd.Timedelta(hours=2), first_sun + pd.Timedelta(hours=2)


def server_to_kst(ts):
    """서버시간(뉴욕+7) -> 한국시간. 뉴욕 서머타임(3월 둘째 일~11월 첫째 일)이면 +13, 아니면 +14."""
    ts = pd.DatetimeIndex(ts)
    ny = ts - pd.Timedelta(hours=SERVER_MINUS_NY)
    dst = np.zeros(len(ny), dtype=bool)
    for y in np.unique(ny.year):
        a, b = _us_dst_bounds(int(y))
        m = (ny.year == y)
        dst |= m & (ny >= a) & (ny < b)
    return ny + pd.to_timedelta(np.where(dst, 13, 14), unit="h")


def session_of(t_ns):
    h = ny_hour(t_ns)
    if h >= 19 or h < 2:
        return "아시아"
    if h < 8:
        return "런던"
    if h < 17:
        return "뉴욕"
    return "뉴욕마감후"


def default_pip(sym, price):
    s = sym.upper()
    if "JPY" in s:
        return 0.01
    if "XAU" in s:
        return 0.1
    if "XAG" in s:
        return 0.01
    if price > 1000:
        return 1.0
    if price > 20:
        return 0.01
    return 0.0001


# ---------------------------------------------------------------- 구조 판정
def mss_level(d, ext_i, anchor_i, n, crh, crl, H, L, leg_bars=240):
    """EA TrueMssLevel 과 같다. 극값 봉 ext_i 시점에 확정된 스윙만 본다(s + n <= ext_i)."""
    if anchor_i is not None and anchor_i < ext_i:
        lo = max(anchor_i + 1, ext_i - 600)
    else:
        lo = ext_i - leg_bars
    lo = max(lo, n)
    for s in range(ext_i - n, lo - 1, -1):
        if d == 1:
            v = H[s]
            if v >= crh:
                continue
            if np.all(v > H[s - n:s]) and np.all(v >= H[s + 1:s + n + 1]):
                return v
        else:
            v = L[s]
            if v <= crl:
                continue
            if np.all(v < L[s - n:s]) and np.all(v <= L[s + 1:s + n + 1]):
                return v
    return 0.0


def equal_level_stop(d, levels, entry, tol, buf):
    """같은 높이 저점(매도는 고점) 묶음: 진입가 너머에 있는 값들 중 tol 이내로 2개 이상 모인 가장 먼 묶음."""
    lv = np.asarray(levels, dtype=float)
    if d == 1:
        lv = np.sort(lv[lv < entry])
        for i in range(len(lv) - 1):
            if lv[i + 1] - lv[i] <= tol + 1e-12:
                return lv[i] - buf
    else:
        lv = np.sort(lv[lv > entry])[::-1]
        for i in range(len(lv) - 1):
            if lv[i] - lv[i + 1] <= tol + 1e-12:
                return lv[i] + buf
    return None


# ---------------------------------------------------------------- 셋업 찾기
def find_setups(m15, h4, n, pip, opt):
    """M15·H4 배열에서 셋업(주문 직전까지)을 찾는다. 돌려주는 값: 셋업 목록, 깔때기 집계."""
    T, O, H, L, C = m15["t"], m15["o"], m15["h"], m15["l"], m15["c"]
    T4, H4h, H4l, H4c = h4["t"], h4["h"], h4["l"], h4["c"]
    step15 = 15 * NS_MIN
    funnel = dict(c2=0, asia_skip=0, sweep=0, c2_close_ok=0, mss_line=0, mss_confirm=0,
                  no_ob=0, target_before_order=0, setups=0)
    setups = []
    # 4H 스윙 고점/저점(앞뒤 2봉): 확정 시각 = k+2 봉 마감
    k4 = len(T4)
    sh4 = np.zeros(k4, bool)
    sl4 = np.zeros(k4, bool)
    for k in range(2, k4 - 2):
        sh4[k] = H4h[k] > H4h[k - 1] and H4h[k] > H4h[k - 2] and H4h[k] >= H4h[k + 1] and H4h[k] >= H4h[k + 2]
        sl4[k] = H4l[k] < H4l[k - 1] and H4l[k] < H4l[k - 2] and H4l[k] <= H4l[k + 1] and H4l[k] <= H4l[k + 2]
    conf4 = np.r_[T4[2:] + 4 * NS_H, np.full(2, np.iinfo(np.int64).max)]  # k+2 봉 마감 시각

    for i in range(1, k4):
        funnel["c2"] += 1
        c2s, c2e = T4[i], T4[i] + 4 * NS_H
        if not opt.include_asia:
            hny = ny_hour(c2s)
            if hny >= 19 or hny < 2:
                funnel["asia_skip"] += 1
                continue
        crh, crl = H4h[i - 1], H4l[i - 1]
        if crh <= crl:
            continue
        a1 = np.searchsorted(T, T4[i - 1])
        a2 = np.searchsorted(T, c2s)
        a3 = np.searchsorted(T, c2e)
        if a3 - a2 < 4 or a2 - a1 < 4:
            continue
        seg_l = L[a1:a2]
        seg_h = H[a1:a2]
        anchor_lo = a1 + (len(seg_l) - 1 - int(np.argmin(seg_l[::-1])))   # 가장 최근 최저 봉
        anchor_hi = a1 + (len(seg_h) - 1 - int(np.argmax(seg_h[::-1])))
        d, ext, ext_i, mss, conf_j = 0, 0.0, -1, 0.0, -1
        for j in range(a2, a3):
            if d == 0:
                if L[j] < crl:
                    d, ext, ext_i = 1, L[j], j
                elif H[j] > crh:
                    d, ext, ext_i = -1, H[j], j
                else:
                    continue
                mss = mss_level(d, ext_i, anchor_lo if d == 1 else anchor_hi, n, crh, crl, H, L)
            elif (d == 1 and L[j] < ext) or (d == -1 and H[j] > ext):
                ext, ext_i = (L[j] if d == 1 else H[j]), j
                mss = mss_level(d, ext_i, anchor_lo if d == 1 else anchor_hi, n, crh, crl, H, L)
            if mss <= 0:
                continue
            body = (C[j] > mss and C[j] > O[j]) if d == 1 else (C[j] < mss and C[j] < O[j])
            if body and crl < C[j] < crh:
                conf_j = j
                break
        if d == 0:
            continue
        funnel["sweep"] += 1
        c2_ok = crl < H4c[i] < crh
        if opt.c2_close == "required" and not c2_ok:
            continue
        funnel["c2_close_ok"] += 1
        if mss > 0 or conf_j >= 0:
            funnel["mss_line"] += 1
        if conf_j < 0:
            continue
        funnel["mss_confirm"] += 1
        # OB: 확정 봉 직전 ~ 극값 봉, 처음 만나는 반대색 봉
        ob = -1
        for k in range(conf_j - 1, ext_i - 1, -1):
            if (d == 1 and C[k] < O[k]) or (d == -1 and C[k] > O[k]):
                ob = k
                break
        if ob < 0:
            funnel["no_ob"] += 1
            continue
        # 주문 시각: 확정 봉 마감, 또는 (C2 마감 필수일 때) C2 마감 중 늦은 쪽
        t_conf_close = T[conf_j] + step15
        if opt.c2_close == "required" and t_conf_close < c2e:
            t_order = c2e
            last_i = a3 - 1
            gap = slice(conf_j + 1, a3)
            hit = np.any(H[gap] >= crh) if d == 1 else np.any(L[gap] <= crl)
            if hit:
                funnel["target_before_order"] += 1
                continue
        else:
            t_order = t_conf_close
            last_i = conf_j
        px_order = C[last_i]
        brk = H[ext_i:conf_j + 1].max() if d == 1 else L[ext_i:conf_j + 1].min()
        # T4: 주문 시점에 확정된 4H 스윙 중 C1 범위 바깥, 가장 최근
        t4 = None
        for k in range(i - 1, max(-1, i - 1 - opt.t4_lookback), -1):
            if conf4[k] > t_order:
                continue
            if d == 1 and sh4[k] and H4h[k] > crh:
                t4 = H4h[k]
                break
            if d == -1 and sl4[k] and H4l[k] < crl:
                t4 = H4l[k]
                break
        funnel["setups"] += 1
        setups.append(dict(d=d, c1=T4[i - 1], c2=c2s, crh=crh, crl=crl, ext=ext, ext_i=ext_i, mss=mss,
                           t_conf=T[conf_j], conf_j=conf_j, ob_i=ob, ob_h=H[ob], ob_l=L[ob], ob_o=O[ob],
                           brk=brk, t_order=t_order, px_order=px_order, t4=t4))
    return setups, funnel


# ---------------------------------------------------------------- 체결·청산 (M5)
def first_true(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if len(idx) else -1


def simulate_exit(d, f, fill, sl, tp, spread, M, max_hold):
    """체결 봉 f 부터 손절/목표. 돌려줌: (결과, 청산 인덱스, 청산가)."""
    O, H, L, C = M["o"], M["h"], M["l"], M["c"]
    n = len(O)
    # 체결 봉: 손절만 본다
    if (d == 1 and L[f] <= sl) or (d == -1 and H[f] + spread >= sl):
        return "loss", f, sl
    start = f + 1
    end_cap = n if max_hold <= 0 else min(n, f + 1 + max_hold)
    chunk = 3000
    while start < end_cap:
        stop = min(end_cap, start + chunk)
        if d == 1:
            s_hit = first_true(L[start:stop] <= sl)
            t_hit = first_true(H[start:stop] >= tp)
        else:
            s_hit = first_true(H[start:stop] + spread >= sl)
            t_hit = first_true(L[start:stop] + spread <= tp)
        if s_hit >= 0 and (t_hit < 0 or s_hit <= t_hit):
            k = start + s_hit
            gap = (d == 1 and O[k] <= sl) or (d == -1 and O[k] + spread >= sl)
            px = (O[k] if d == 1 else O[k] + spread) if gap else sl
            return "loss", k, px
        if t_hit >= 0:
            return "win", start + t_hit, tp
        start = stop
        chunk *= 4
    if max_hold > 0 and end_cap < n:
        k = end_cap - 1
        return "time", k, (C[k] if d == 1 else C[k] + spread)
    return "open", n - 1, np.nan


def run_symbol(sym, m5df, opt, pip, spread_pips):
    t = m5df.index.values.astype("datetime64[ns]").astype("int64")
    o, h, l, c = (m5df[k].values.astype(float) for k in ("o", "h", "l", "c"))
    M = dict(t=t, o=o, h=h, l=l, c=c)
    m15 = bars_from_m5(t, o, h, l, c, 15)
    h4 = bars_from_m5(t, o, h, l, c, 240)
    spread = spread_pips * pip
    buf = opt.sl_buffer * pip
    tol = opt.eq_tol * pip
    step15 = 15 * NS_MIN
    # M15 1봉 프랙탈 저점/고점 (확정 시각 = 다음 봉 마감)
    L15, H15, T15 = m15["l"], m15["h"], m15["t"]
    fl = np.zeros(len(L15), bool)
    fh = np.zeros(len(H15), bool)
    fl[1:-1] = (L15[1:-1] < L15[:-2]) & (L15[1:-1] <= L15[2:])
    fh[1:-1] = (H15[1:-1] > H15[:-2]) & (H15[1:-1] >= H15[2:])
    trades, funnels = [], []
    for n in opt.swing:
        setups, fun = find_setups(m15, h4, n, pip, opt)
        fun.update(symbol=sym, swing=n)
        fills = {e: 0 for e in ENTRIES}
        skip_px = {e: 0 for e in ENTRIES}
        expired = {e: 0 for e in ENTRIES}
        cancel_tp = {e: 0 for e in ENTRIES}
        for st in setups:
            d = st["d"]
            ent = {"A": st["ob_h"] if d == 1 else st["ob_l"],
                   "B": st["ob_o"],
                   "C": st["ext"] + 0.5 * (st["brk"] - st["ext"])}
            struct_tp = st["crh"] if d == 1 else st["crl"]
            i0 = int(np.searchsorted(t, st["t_order"]))
            i1 = int(np.searchsorted(t, st["t_order"] + opt.expiry_bars * step15))
            if i0 >= len(t):
                continue
            for e in ENTRIES:
                E = ent[e]
                # 지정가는 현재가보다 유리한 쪽에만 걸 수 있다
                if (d == 1 and E >= st["px_order"]) or (d == -1 and E <= st["px_order"]):
                    skip_px[e] += 1
                    continue
                if d == 1:
                    fill_m = l[i0:i1] + spread <= E
                    canc_m = h[i0:i1] >= struct_tp
                else:
                    fill_m = h[i0:i1] >= E
                    canc_m = l[i0:i1] + spread <= struct_tp
                fi, ci = first_true(fill_m), first_true(canc_m)
                if fi < 0 or (0 <= ci < fi):
                    if 0 <= ci and (fi < 0 or ci < fi):
                        cancel_tp[e] += 1
                    else:
                        expired[e] += 1
                    continue
                f = i0 + fi
                if opt.block_asia_fill and session_of(t[f]) == "아시아":
                    expired[e] += 1
                    continue
                fills[e] += 1
                fill = min(E, o[f] + spread) if d == 1 else max(E, o[f])   # 갭이면 더 좋은 값
                # S3 재료: 극값 다음 봉 ~ 체결 전에 확정된 M15 프랙탈
                j_end = int(np.searchsorted(T15, t[f] - step15, side="right"))  # 다음 봉까지 마감된 것
                js = np.arange(st["ext_i"] + 1, max(st["ext_i"] + 1, j_end - 1))
                lv = (L15[js][fl[js]] if d == 1 else H15[js][fh[js]]) if len(js) else np.array([])
                stops = {"S1": (st["ob_l"] - buf) if d == 1 else (st["ob_h"] + buf),
                         "S2": st["ext"] - d * buf}
                s3 = equal_level_stop(d, lv, fill, tol, buf)
                stops["S3"] = s3 if s3 is not None else stops["S2"]
                for s in STOPS:
                    SL = stops[s]
                    risk = d * (fill - SL)
                    if risk <= 0 or risk < opt.min_risk_pips * pip:
                        continue
                    for tg in TARGETS:
                        if tg == "T1":
                            TP, fb = struct_tp, False
                        elif tg == "T2":
                            TP, fb = fill + d * 2 * risk, False
                        elif tg == "T3":
                            TP, fb = fill + d * 3 * risk, False
                        else:
                            TP, fb = (st["t4"], False) if st["t4"] is not None else (struct_tp, True)
                        if d * (TP - fill) <= 0:
                            continue
                        res, k, px = simulate_exit(d, f, fill, SL, TP, spread, M, opt.max_hold_bars)
                        if res == "open":
                            r = np.nan
                        else:
                            r = d * (px - fill) / risk
                        trades.append(dict(
                            symbol=sym, swing=n, entry_v=e, stop_v=s, target_v=tg,
                            combo=f"N{n}-{e}-{s}-{tg}", dir="BUY" if d == 1 else "SELL",
                            c1_server=t2s(st["c1"]), c2_server=t2s(st["c2"]),
                            crh=st["crh"], crl=st["crl"], sweep_ext=st["ext"], mss=st["mss"],
                            mss_confirm_server=t2s(st["t_conf"]), order_server=t2s(st["t_order"]),
                            fill_server=t2s(t[f]), entry=fill, sl=SL, tp=TP,
                            risk_pips=risk / pip, rr_planned=d * (TP - fill) / risk,
                            exit_server=t2s(t[k]), exit_price=px, result=res, R=r,
                            s3_fallback=(s == "S3" and s3 is None), t4_fallback=(tg == "T4" and fb),
                            session=session_of(t[f]), t_fill_ns=t[f]))
        for e in ENTRIES:
            fun[f"fill_{e}"] = fills[e]
            fun[f"expired_{e}"] = expired[e]
            fun[f"cancel_tp_{e}"] = cancel_tp[e]
            fun[f"skip_px_{e}"] = skip_px[e]
        funnels.append(fun)
    return trades, funnels, (t[0], t[-1])


def t2s(x):
    return pd.Timestamp(int(x)).strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------- 통계
def stats(r):
    r = np.asarray(r, float)
    n = len(r)
    if n == 0:
        return dict(n=0)
    w = r > 0
    cum = np.cumsum(r)
    dd = np.max(np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum])
    streak = best = 0
    for x in r:
        streak = streak + 1 if x < 0 else 0
        best = max(best, streak)
    gp, gl = r[w].sum(), -r[r < 0].sum()
    se = r.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return dict(n=n, winrate=w.mean() * 100, avg_win_R=r[w].mean() if w.any() else 0.0,
                avg_R=r.mean(), exp_R=r.mean(), t_stat=(r.mean() / se) if se and se > 0 else np.nan,
                sum_R=r.sum(), pf=(gp / gl) if gl > 0 else np.inf, max_lose_streak=best, max_dd_R=dd)


def summarize(tr, oos_start):
    closed = tr[tr["result"] != "open"].copy()
    closed = closed.sort_values("t_fill_ns")
    closed["year"] = pd.to_datetime(closed["fill_server"]).dt.year
    oos_ns = pd.Timestamp(oos_start).value
    rows = []
    years = sorted(closed["year"].unique())
    sessions = ["런던", "뉴욕", "아시아", "뉴욕마감후"]
    groups = [("ALL", closed)] + [(s, g) for s, g in closed.groupby("symbol")]
    for sym, g in groups:
        for combo, gc in g.groupby("combo"):
            st = stats(gc["R"].values)
            row = dict(symbol=sym, combo=combo, swing=gc["swing"].iloc[0], entry_v=gc["entry_v"].iloc[0],
                       stop_v=gc["stop_v"].iloc[0], target_v=gc["target_v"].iloc[0])
            row.update(st)
            row["n_open"] = int(((tr["combo"] == combo) & (tr["result"] == "open") &
                                 ((tr["symbol"] == sym) | (sym == "ALL"))).sum())
            row["avg_risk_pips"] = gc["risk_pips"].mean()
            is_ = gc[gc["t_fill_ns"] < oos_ns]["R"].values
            oo = gc[gc["t_fill_ns"] >= oos_ns]["R"].values
            row["IS_n"], row["IS_exp_R"] = len(is_), (is_.mean() if len(is_) else np.nan)
            row["OOS_n"], row["OOS_exp_R"] = len(oo), (oo.mean() if len(oo) else np.nan)
            for y in years:
                v = gc[gc["year"] == y]["R"].values
                row[f"exp_{y}"] = v.mean() if len(v) else np.nan
                row[f"n_{y}"] = len(v)
            for s in sessions:
                v = gc[gc["session"] == s]["R"].values
                row[f"exp_{s}"] = v.mean() if len(v) else np.nan
                row[f"n_{s}"] = len(v)
            rows.append(row)
    return pd.DataFrame(rows)


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    return f"{x:+.{nd}f}" if isinstance(x, float) else str(x)


def write_text(path, summ, funnels, meta, opt):
    L = []
    L.append("석준님 CRT 백테스트 요약 (정보 제공용, 매매 결정은 석준님)")
    L.append("=" * 70)
    for k, v in meta.items():
        L.append(f"{k}: {v}")
    L.append("")
    L.append("용어: R = 손절폭 1개 크기. 기대값(R) = 한 번 거래할 때 평균으로 얻는 R. +0.20이면 1% 위험 거래마다 평균 +0.2%.")
    L.append("      최대 낙폭(R) = 누적 R이 고점에서 가장 많이 빠진 크기. IS = 앞 기간(규칙 고르는 데 써도 되는 구간), OOS = 뒤 기간(확인용).")
    L.append("변형: 진입 " + ", ".join(f"{k}={v}" for k, v in ENTRY_DESC.items()))
    L.append("      손절 " + ", ".join(f"{k}={v}" for k, v in STOP_DESC.items()))
    L.append("      목표 " + ", ".join(f"{k}={v}" for k, v in TARGET_DESC.items()) + ", N = MSS 스윙 봉 수")
    L.append("")
    L.append("[셋업 깔때기] (4H 봉 -> 스윕 -> C2 마감 조건 -> MSS 확정 -> 주문 -> 체결)")
    fdf = pd.DataFrame(funnels)
    for _, f in fdf.iterrows():
        L.append(f"  {f['symbol']:<8} N{f['swing']}: C2 {f['c2']}, 아시아제외 {f['asia_skip']}, 스윕 {f['sweep']}, "
                 f"C2마감OK {f['c2_close_ok']}, MSS확정 {f['mss_confirm']}, OB없음 {f['no_ob']}, "
                 f"주문전목표도달 {f['target_before_order']}, 주문 {f['setups']} | 체결 A {f['fill_A']} B {f['fill_B']} C {f['fill_C']}")
    L.append("")
    min_n = opt.min_trades

    def table(df, title, k=10):
        L.append(title)
        L.append(f"  {'조합':<16}{'거래':>6}{'승률%':>7}{'평균이익R':>10}{'기대값R':>9}{'t값':>6}{'최대연패':>8}{'최대낙폭R':>10}{'IS기대':>8}{'OOS기대':>8}{'OOS건':>6}")
        for _, r in df.head(k).iterrows():
            L.append(f"  {r['combo']:<16}{int(r['n']):>6}{r['winrate']:>7.1f}{r['avg_win_R']:>10.2f}{r['exp_R']:>+9.3f}"
                     f"{fmt(r['t_stat'], 1):>6}{int(r['max_lose_streak']):>8}{r['max_dd_R']:>10.1f}"
                     f"{fmt(r['IS_exp_R'], 3):>8}{fmt(r['OOS_exp_R'], 3):>8}{int(r['OOS_n']):>6}")
        L.append("")

    for sym in ["ALL"] + sorted(s for s in summ["symbol"].unique() if s != "ALL"):
        g = summ[(summ["symbol"] == sym) & (summ["n"] >= min_n)]
        if g.empty:
            L.append(f"[{sym}] 거래 {min_n}건 이상인 조합 없음\n")
            continue
        # 고르기는 IS 기대값으로, OOS는 확인용
        g_is = g.sort_values("IS_exp_R", ascending=False)
        table(g_is, f"[{sym}] IS 기대값 상위 (IS로 고르고 OOS로 확인)", 10 if sym == "ALL" else 5)
        if sym == "ALL":
            table(g.sort_values("IS_exp_R"), "[ALL] IS 기대값 하위 (피해야 할 조합 후보)", 5)
            # 변형 하나씩 평균(다른 변형은 고르게 섞음) -> 어떤 축이 효과 있는지
            L.append("[ALL] 축별 평균 기대값(R) — 다른 변형을 모두 평균낸 값, IS / OOS")
            for axis, desc in (("swing", None), ("entry_v", ENTRY_DESC), ("stop_v", STOP_DESC), ("target_v", TARGET_DESC)):
                for v, gv in g.groupby(axis):
                    name = desc[v] if desc else f"N={v}"
                    L.append(f"  {axis:<9}{str(v):<4}{name:<26} IS {fmt(gv['IS_exp_R'].mean(), 3)}  OOS {fmt(gv['OOS_exp_R'].mean(), 3)}")
            L.append("")
            ycols = [c for c in summ.columns if c.startswith("exp_") and c[4:].isdigit()]
            best = g_is.iloc[0]
            L.append(f"[ALL] IS 1위 {best['combo']} 연도별 기대값(R): " +
                     ", ".join(f"{c[4:]} {fmt(best[c], 2)}({int(best['n_' + c[4:]])})" for c in ycols))
            L.append(f"[ALL] IS 1위 {best['combo']} 시간대별 기대값(R, 체결 시각 뉴욕 기준): " +
                     ", ".join(f"{s} {fmt(best['exp_' + s], 2)}({int(best['n_' + s])})" for s in ["런던", "뉴욕", "아시아", "뉴욕마감후"]))
            L.append("")
    L.append("주의")
    L.append(f"- 조합이 {len(summ['combo'].unique())}개라 그중 1등은 운으로도 좋아 보일 수 있다(과최적화). IS로 고른 조합이 OOS에서도 +인지가 핵심.")
    L.append("- t값 2 미만이면 '우연과 구분 안 됨'으로 본다. 같은 셋업을 여러 변형으로 세므로 조합끼리 독립이 아니다.")
    L.append("- 체결 봉에서는 목표를 인정 안 하고, 같은 봉 손절·목표는 손절로 처리해서 결과가 실제보다 약간 나쁘게 나온다.")
    L.append("- M15·M5 봉만 본다. EA(1분봉 MSS)와 결과가 다를 수 있다.")
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(L))
    return "\n".join(L)


# ---------------------------------------------------------------- 실행
def parse_map(s, cast=float):
    out = {}
    if s:
        for part in s.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip().upper()] = cast(v)
    return out


def build_parser():
    p = argparse.ArgumentParser(description="석준님 CRT(4H)+MSS(M15)+OB 백테스트 (읽기 전용)")
    p.add_argument("--data-dir", help="{SYMBOL}_M5.csv 가 있는 폴더")
    p.add_argument("--out", help="결과 폴더 (없으면 만듦)")
    p.add_argument("--symbols", default="", help="쉼표 구분. 비우면 폴더의 *_M5.csv 전부")
    p.add_argument("--swing", default="5,3", help="MSS 스윙 봉 수 목록 (기본 5,3)")
    p.add_argument("--expiry-bars", type=int, default=16, help="지정가 유효시간, M15 봉 수 (기본 16=4시간)")
    p.add_argument("--spread", type=float, default=1.0, help="기본 스프레드 핍 (기본 1.0)")
    p.add_argument("--spread-map", default="", help="종목별 스프레드 핍, 예: EURUSD=0.8,GBPJPY=2.5")
    p.add_argument("--pip-map", default="", help="종목별 1핍 크기, 예: XAUUSD=0.1,US30=1")
    p.add_argument("--sl-buffer", type=float, default=1.0, help="손절 버퍼 핍 (기본 1)")
    p.add_argument("--eq-tol", type=float, default=2.0, help="같은 높이 저점 묶음 허용 핍 (기본 2)")
    p.add_argument("--min-risk-pips", type=float, default=0.0, help="손절폭이 이보다 작으면 거래 안 함 (기본 0)")
    p.add_argument("--c2-close", choices=["required", "ignore"], default="required",
                   help="required: C2가 범위 안 마감해야 성립, 주문은 C2 마감 후(기본). ignore: EA처럼 MSS 확정 즉시 주문")
    p.add_argument("--include-asia", action="store_true", help="아시아장 C2(뉴욕 19~2시 시작)도 포함")
    p.add_argument("--block-asia-fill", action="store_true", help="아시아장에 체결되는 주문은 버림(EA처럼)")
    p.add_argument("--max-hold-bars", type=int, default=0, help="최대 보유 M5 봉 수, 0=제한 없음")
    p.add_argument("--t4-lookback", type=int, default=120, help="T4 4H 스윙 찾을 범위(4H 봉 수)")
    p.add_argument("--oos-start", default="2024-01-01", help="표본 밖(OOS) 시작일 (서버시간)")
    p.add_argument("--start", default="", help="이 날짜 이후 데이터만 (예 2019-01-01)")
    p.add_argument("--min-trades", type=int, default=30, help="요약 표에 넣을 최소 거래 수")
    p.add_argument("--selftest", action="store_true", help="가짜 데이터로 자체 시험만 실행")
    return p


def run_all(opt, files=None, quiet=False):
    t0 = _time.time()
    opt.swing = [int(x) for x in str(opt.swing).split(",") if str(x).strip()] if not isinstance(opt.swing, list) else opt.swing
    if files is None:
        syms = [s.strip().upper() for s in opt.symbols.split(",") if s.strip()]
        allf = sorted(f for f in os.listdir(opt.data_dir) if f.upper().endswith("_M5.CSV"))
        files = {}
        for f in allf:
            s = f[:-len("_M5.csv")].upper()
            if not syms or s in syms:
                files[s] = os.path.join(opt.data_dir, f)
        missing = [s for s in syms if s not in files]
        if missing:
            print(f"! 파일 없음: {missing}")
    if not files:
        print("! 돌릴 파일이 없습니다. --data-dir 와 --symbols 를 확인해 주세요.")
        return None
    os.makedirs(opt.out, exist_ok=True)
    spmap, pipmap = parse_map(opt.spread_map), parse_map(opt.pip_map)
    all_tr, all_fun, meta_rng = [], [], {}
    for sym, path in files.items():
        print(f"\n== {sym} ==")
        df = path if isinstance(path, pd.DataFrame) else load_m5(path, verbose=not quiet)
        if opt.start:
            df = df[df.index >= pd.Timestamp(opt.start)]
        pip = pipmap.get(sym, default_pip(sym, float(df["c"].iloc[-1])))
        sp = spmap.get(sym, opt.spread)
        print(f"  1핍 = {pip}, 스프레드 = {sp}핍")
        tr, fun, rng = run_symbol(sym, df, opt, pip, sp)
        meta_rng[sym] = rng
        all_tr += tr
        all_fun += fun
        print(f"  셋업(주문) {[f['setups'] for f in fun]} (N={opt.swing}), 거래 기록 {len(tr):,}줄, {(_time.time() - t0):.0f}초")
    tr = pd.DataFrame(all_tr)
    tag = f"c2{opt.c2_close}"
    if tr.empty:
        print("! 거래가 하나도 없습니다.")
        pd.DataFrame(all_fun).to_csv(os.path.join(opt.out, f"funnel_{tag}.csv"), index=False, encoding="utf-8-sig")
        return dict(trades=tr, summary=pd.DataFrame(), funnels=all_fun)
    # 한국시간 열
    for col in ("fill_server", "exit_server"):
        tr[col.replace("_server", "_kst")] = server_to_kst(pd.to_datetime(tr[col])).strftime("%Y-%m-%d %H:%M")
    tr["period"] = np.where(tr["t_fill_ns"] < pd.Timestamp(opt.oos_start).value, "IS", "OOS")
    summ = summarize(tr, opt.oos_start)
    rng_txt = "; ".join(f"{s} {t2s(a)}~{t2s(b)}" for s, (a, b) in meta_rng.items())
    lo, hi = min(a for a, _ in meta_rng.values()), max(b for _, b in meta_rng.values())
    meta = {"데이터": f"MT5 M5 CSV ({opt.data_dir or '메모리'})",
            "기간(서버시간)": rng_txt,
            "기간(한국시간)": f"{server_to_kst([pd.Timestamp(lo)])[0]:%Y-%m-%d %H:%M} ~ {server_to_kst([pd.Timestamp(hi)])[0]:%Y-%m-%d %H:%M} KST",
            "시간 기준": "표의 시각은 MT5 서버시간(뉴욕+7). 거래 목록에 한국시간(KST) 열 있음",
            "IS / OOS": f"IS = {opt.oos_start} 이전 체결, OOS = 이후",
            "설정": f"C2마감={opt.c2_close}, 아시아C2 {'포함' if opt.include_asia else '제외'}, 유효 {opt.expiry_bars}봉(M15), "
                   f"스프레드 {opt.spread}핍(+맵 {opt.spread_map or '없음'}), 손절버퍼 {opt.sl_buffer}핍, 같은높이 {opt.eq_tol}핍, 스윙 N={opt.swing}",
            "만든 시각": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M") + " (실행 PC 시각)"}
    out_cols = ["symbol", "combo", "swing", "entry_v", "stop_v", "target_v", "dir", "period", "session",
                "c1_server", "c2_server", "crh", "crl", "sweep_ext", "mss", "mss_confirm_server", "order_server",
                "fill_server", "fill_kst", "entry", "sl", "tp", "risk_pips", "rr_planned",
                "exit_server", "exit_kst", "exit_price", "result", "R", "s3_fallback", "t4_fallback"]
    tr[out_cols].to_csv(os.path.join(opt.out, f"trades_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    summ.to_csv(os.path.join(opt.out, f"summary_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    pd.DataFrame(all_fun).to_csv(os.path.join(opt.out, f"funnel_{tag}.csv"), index=False, encoding="utf-8-sig")
    txt = write_text(os.path.join(opt.out, f"summary_{tag}.txt"), summ, all_fun, meta, opt)
    if not quiet:
        print("\n" + txt)
    print(f"\n완료 {(_time.time() - t0):.0f}초. 결과 폴더: {opt.out}")
    return dict(trades=tr, summary=summ, funnels=all_fun)


# ---------------------------------------------------------------- 자체 시험
def _expand_m15(rows, start, base, pip):
    """M15 (o,h,l,c) 핍 단위 목록 -> M5 3봉씩. 양봉 경로 o->l->h->c, 음봉 o->h->l->c."""
    out = []
    t = pd.Timestamp(start)
    for (o, h, l, c) in rows:
        if c >= o:
            parts = [(o, o, l, l), (l, h, l, h), (h, h, c, c)]
        else:
            parts = [(o, h, o, h), (h, h, l, l), (l, c, l, c)]
        for k, (a, b, cc, dd) in enumerate(parts):
            out.append((t + pd.Timedelta(minutes=5 * k), base + a * pip, base + b * pip, base + cc * pip, base + dd * pip))
        t += pd.Timedelta(minutes=15)
    df = pd.DataFrame(out, columns=["time", "o", "h", "l", "c"]).set_index("time")
    return df


def scenario_rows():
    pre = [(1, 2, 0, 1)] * 32                      # 서버 00:00~07:45 횡보
    c1 = [(1, 2, -5, 0), (0, 8, 0, 8), (8, 16, 8, 16), (16, 24, 16, 24), (24, 30, 24, 28),   # CRL -5, CRH 30
          (28, 28, 22, 22), (22, 22, 16, 16), (16, 16, 12, 12), (12, 12, 10, 10), (10, 13, 10, 13),
          (13, 15, 13, 15), (15, 18, 15, 18), (18, 20, 17, 19),                               # 11:00 스윙 고점 20 = MSS
          (19, 19, 15, 15), (15, 15, 12, 12), (12, 12, 9, 9)]
    c2 = [(9, 9, 5, 5), (5, 5, 1, 1), (1, 1, -3, -3), (-3, -3, -6, -6),                    # 12:45 스윕
          (-6, -5, -8, -7), (-7, -1, -7, -1), (-1, 5, -1, 5),                               # 13:00 극값 -8
          (5, 7, 2, 3),                                                                      # 13:45 OB (음봉 7~2, 시가 5)
          (3, 23, 3, 22)] + [(22, 24, 21, 23)] * 7                                           # 14:00 MSS 확정, C2 마감 23
    c3 = [(23, 23, 15, 15), (15, 15, 6, 8), (8, 18, 8, 18), (18, 31, 18, 31)]               # 16:15 OB 고가 7 체결, 16:45 CRH 30
    post = [(31, 32, 30, 31)] * (4 * 24 * 2)
    return pre + c1 + c2 + c3 + post


def selftest():
    import types
    ok = True
    pip = 0.0001
    print("=== 시험 1: 같은 높이 저점 묶음 (2026-10-27 GBPUSD 예시) ===")
    s3 = equal_level_stop(1, [1.33115, 1.33135, 1.33144], 1.33191, 2 * pip, 1 * pip)
    print(f"  저점 1.33115/1.33135/1.33144, 진입 1.33191 -> 손절 {s3:.5f} (기대 1.33105)")
    ok &= abs(s3 - 1.33105) < 1e-9

    print("=== 시험 2: 손으로 만든 시나리오 (스윕 -> MSS -> OB 되돌림 -> CRH) ===")
    df = _expand_m15(scenario_rows(), "2024-01-08 00:00", 1.10000, pip)
    base = dict(swing="5,3", expiry_bars=16, spread=1.0, spread_map="", pip_map="", sl_buffer=1.0, eq_tol=2.0,
                min_risk_pips=0.0, c2_close="required", include_asia=False, block_asia_fill=False,
                max_hold_bars=0, t4_lookback=120, oos_start="2024-06-01", start="", min_trades=1,
                data_dir="", symbols="")
    import tempfile
    out_dir = tempfile.mkdtemp(prefix="crt_selftest_")
    opt = types.SimpleNamespace(**base, out=out_dir)
    res = run_all(opt, files={"EURUSD": df}, quiet=True)
    tr = res["trades"]
    for n in (5, 3):
        f = [x for x in res["funnels"] if x["swing"] == n][0]
        print(f"  N={n}: 스윕 {f['sweep']}, MSS확정 {f['mss_confirm']}, 주문 {f['setups']}, 체결 A/B/C {f['fill_A']}/{f['fill_B']}/{f['fill_C']}")
        ok &= f["setups"] == 1 and f["fill_A"] == 1 and f["fill_B"] == 0 and f["fill_C"] == 1
    t = tr[tr["combo"] == "N5-A-S2-T1"]
    print(t[["dir", "mss", "order_server", "fill_server", "fill_kst", "entry", "sl", "tp", "result", "R"]].to_string(index=False))
    exp_R = (30 - 7) / (7 + 9)
    ok &= len(t) == 1 and t["result"].iloc[0] == "win" and abs(t["R"].iloc[0] - exp_R) < 1e-9
    ok &= abs(t["mss"].iloc[0] - 1.1020) < 1e-9 and abs(t["entry"].iloc[0] - 1.1007) < 1e-9
    t2 = tr[tr["combo"] == "N5-A-S1-T1"]
    ok &= len(t2) == 1 and abs(t2["R"].iloc[0] - 23 / 6) < 1e-9
    t3 = tr[tr["combo"] == "N5-A-S2-T2"]
    ok &= len(t3) == 1 and t3["result"].iloc[0] == "open"
    ok &= set(tr["dir"]) == {"BUY"}
    ok &= t["fill_kst"].iloc[0] == "2024-01-08 23:20"   # 16:15 M15봉의 둘째 M5(서버 16:20) = 뉴욕 09:20(EST) = 한국 23:20
    print(f"  기대 R {exp_R:.4f}, S1 R {23 / 6:.4f}, T2는 미청산 -> {'통과' if ok else '실패'}")

    print("=== 시험 3: 랜덤워크 (방향 없는 가짜 시세) -> 기대값 0 근처여야 함 ===")
    rng = np.random.default_rng(7)
    idx = pd.date_range("2019-01-01", "2023-12-31 23:55", freq="5min")
    idx = idx[idx.dayofweek < 5]
    m = len(idx)
    steps = rng.normal(0, 2.5 * pip / np.sqrt(5), size=(m, 5)).cumsum(axis=1)   # 1분 5걸음
    start = 1.1 + np.r_[0, steps[:-1, -1]].cumsum()
    path = start[:, None] + steps
    o = start
    c = path[:, -1]
    h = np.maximum(path.max(axis=1), o)
    lo = np.minimum(path.min(axis=1), o)
    rw = pd.DataFrame({"o": o, "h": h, "l": lo, "c": c}, index=idx)
    for sp in (0.0, 1.0):
        base2 = dict(base, spread=sp, oos_start="2022-01-01", min_trades=30)
        opt = types.SimpleNamespace(**base2, out=out_dir)
        res = run_all(opt, files={"RWALK": rw}, quiet=True)
        cl = res["trades"][res["trades"]["result"] != "open"]
        e = cl["R"].mean()
        se = cl.groupby("combo")["R"].agg(lambda r: r.std() / np.sqrt(len(r))).mean()
        by = cl.groupby("combo")["R"].mean()
        print(f"  스프레드 {sp}핍: 기록 {len(cl):,}줄, 전체 평균 R {e:+.3f}, 조합별 평균 범위 {by.min():+.3f} ~ {by.max():+.3f}, 조합 표준오차 약 {se:.3f}")
        if sp == 0.0:
            ok &= abs(e) < 0.15
    print("\n자체 시험:", "모두 통과" if ok else "실패 있음")
    return ok


def main():
    opt = build_parser().parse_args()
    if opt.selftest:
        sys.exit(0 if selftest() else 1)
    if not opt.data_dir or not opt.out:
        print("--data-dir 와 --out 이 필요합니다. 예: python crt_backtest.py --data-dir C:\\...\\mt5_m5_data --out C:\\...\\crt_bt_out")
        sys.exit(2)
    run_all(opt)


if __name__ == "__main__":
    main()
