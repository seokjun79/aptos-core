"""석준님 SMC+CRT 매매법 백테스트 (4H CRT -> M15 MSS -> OB 지정가), 변형 + 필터 비교용.

정의는 VenusCRTAssistant.mq5(EA)와 trading/rules/smc-crt-analysis.md 에 맞췄다. 매수 기준, 매도는 대칭.
 1. 4H CRT: 직전 마감 4H봉(C1)의 CRH/CRL. 다음 4H봉(C2) 안에서 M15 저가가 CRL 아래로 나가면 '스윕'.
    (기본) C2가 CRL~CRH 안에서 마감해야 성립. 아시아 C2는 기본 제외.
    아시아 C2 = 4H봉의 가운데 시각이 아시아장(뉴욕 19~02시)인 봉 = 뉴욕 17시·21시에 시작하는 4H봉.
    (2026-10-28 수정: 예전에는 '뉴욕 19~2시에 시작'으로 판정해서 런던 개장 봉(뉴욕 01시 시작)을 빼고
     뉴욕 17시 봉을 남기는 버그가 있었다.)
 2. MSS 선(EA TrueMssLevel 과 같음): 스윕 극값 봉에서 거꾸로 가며 처음 만나는 M15 스윙 고점
    (왼쪽 N봉보다 높고 오른쪽 N봉 이상). CRH 이상인 고점은 건너뜀. C1에서 CRL을 만든 봉 이후만 본다.
    스윙은 오른쪽 N봉이 극값 봉까지 안에 다 있어야 함(= 그 시점에 확정된 스윙만 사용, 미래 엿보기 없음).
    극값이 더 낮아지면 MSS 선을 다시 계산. 확정 = M15 양봉 종가가 MSS 선 위, 종가가 CRL~CRH 안.
 3. OB = 확정 봉 직전부터 극값 봉까지 거꾸로 가며 처음 만나는 음봉(M15).
    진입 지정가: A) OB 고가  B) OB 시가(몸통 위)  C) 극값~돌파 고점 50%.
    주문은 '확정 봉 마감'과 'C2 마감' 중 늦은 시각에 걸린다(C2 마감 조건을 미래 정보 없이 쓰기 위해).
    그래서 C2 마감 필수(기본)이면 체결은 늘 C2 '다음' 4H봉 안에서 난다.
    유효시간 X개 M15봉(기본 16 = 4시간). 체결 전에 CRH(목표 구조)에 먼저 닿으면 취소.
 4. 손절: S1) OB 저가-1핍  S2) 스윕 극값-1핍
          S3) 극값 이후 ~ 체결 직전까지 확정된 M15 저점(앞뒤 1봉) 중 진입가 아래에서
              2핍 이내로 2개 이상 모인 '같은 높이 저점 묶음' 중 가장 낮은 묶음 아래 -1핍. 없으면 S2로 대체.
 5. 목표: T1) CRH  T2) 2R  T3) 3R  T4) 주문 시점에 확정된 직전 4H 스윙 고점(앞뒤 2봉) 중 CRH 위에서
          가장 최근 것. 없으면 CRH로 대체.
 6. 체결·청산은 M5로 본다. 같은 M5 봉에서 손절·목표가 모두 닿으면 손절. 체결한 봉에서는 목표를 인정하지
    않고 손절만 본다(보수적). 스프레드(핍)를 적용: 차트는 bid, 매수는 ask로 사고 bid로 판다.

필터(각각 켜고 끄는 옵션, 기본 꺼짐). 켠 필터는 '켬/끔' 모든 조합을 한 번에 계산해서 표로 낸다.
 F1H 큰 흐름(H4 구조): 주문 시점에 확정된 4H 스윙(앞뒤 2봉) 마지막 고점·저점이 둘 다 직전보다 높음(매수).
 F1D 큰 흐름(D1 EMA): 주문 시점 직전 마감 D1 종가 > D1 EMA20 (매수). 서버시간 자정 기준 일봉.
 F2  확인 캔들 진입(EA 방식): 지정가 대신, 가격이 OB 끝(매수 OB 고가)에 닿은 뒤 M15(옵션 M5) 양봉이
     OB 고가 위에서 마감하면 그 봉 종가에 시장가 진입(진입 종류 K). 닿은 봉이 곧바로 확인 캔들이어도 됨.
     확인 전에 CRH에 닿으면 취소. 켜면 진입 변형 K가 추가되고, 필터 표에서 F2 켬 = K, 끔 = A/B/C.
 F3  무효(EA 규칙): 확정 봉 다음부터 체결(K는 확인 캔들 마감) 전까지 M15 종가가 OB 저가 아래로
     마감한 적 있으면 셋업 취소.
 F4  시간대: 체결 시각이 뉴욕 02~05시(런던) 또는 07~11시(뉴욕 오전)일 때만.
     주의: C2 마감 필수 + 아시아 C2 제외(기본)에서는 구조상 런던 02~05시 체결이 거의 없다.
 F5  위치: 스윕 극값이 HTF 유동성을 '처음' 넘었을 때만.
     전날 저가(PDL, 그날 스윕 전에는 안 깨졌던 것) 또는
     확정 4H 스윙 저점 중 아직 안 깨진 것들이 2핍 이내로 2개 이상 모인 '같은 높이 묶음'(기본 cluster).
     --f5-h4 swing 이면 안 깨진 확정 4H 스윙 저점 하나만 넘어도 인정.

추세 기본 조건 (--trend, 2026-10-28 추가). 석준님 정의: "4H 스윕이 먼저가 아니라, 전체 추세와 방향이 일치하는 4H 스윕".
 필터가 아니라 '기본 조건'이다: 상승 추세면 CRL 스윕 매수만, 하락 추세면 CRH 스윕 매도만 센다.
 --trend 를 켜면 C2마다 매수 쪽 스윕(CRL)과 매도 쪽 스윕(CRH)을 각각 따로 찾는다(먼저 난 쪽만 보던 기본 방식과 다름).
 그래서 C2 하나가 위·아래를 다 쓸면 셋업 2개가 될 수 있다. 추세 판정 시각 = 스윕이 처음 난 M15봉의 시작 시각.
 그 시각까지 '마감한' 봉과 '확정된' 스윙만 쓴다(미래 엿보기 없음).
 시장 구조(공통): 스윙 고점 = 앞 n봉보다 높고 뒤 n봉 이상(--trend-swing, 기본 2), 뒤 n봉이 마감해야 확정.
   봉 종가가 '가장 최근 확정 스윙 고점' 위로 마감 -> 상승 BOS, '가장 최근 확정 스윙 저점' 아래로 마감 -> 하락 BOS.
   추세 = 마지막 BOS 방향 (BOS 전에는 0 = 판정 없음).
 T_D1S  D1 시장 구조 (서버 자정 기준 일봉).
 T_W1S  W1 시장 구조 (서버 월요일 00시 시작 주봉).
 T_D1H4 D1 구조와 H4 구조(같은 BOS 방식) 둘 다 같은 방향.
 T_EMA  직전 마감 D1 종가가 EMA50 위(아래) + EMA50이 --trend-slope(기본 5)일 전보다 높음(낮음).
 T_PDA  D1 구조 상승 + 스윕 극값이 D1 딜링 레인지 50% 아래(디스카운트)일 때만 매수. 하락은 대칭(프리미엄에서 매도).
        딜링 레인지(매수) = 마지막 확정 D1 스윙 저점 ~ max(마지막 확정 스윙 고점, 그 저점 이후 마감 D1 최고가).
 결과 열 trend_{정의}: +1 추세와 같은 방향, -1 반대, 0 판정 없음. 요약 맨 위에 추세 정의별 표와 상위 5 표.
 --trend 를 켜면 확인 캔들 진입 K도 같이 계산한다(F2 필터 표와는 별개).

2026-10-28 추가 (석준님 설명: 주봉+4H 방향 일치 우선, 4H는 외부 구조, 되돌림 위치, 4H 스윙로우 몸통 이탈 = 하락 신호)
 T_H4EXT   H4 외부(스윙) 구조. 추세 = 마지막 외부 BOS 방향. 보호 저점 = 그 BOS를 만든 다리가 시작된 저점.
           H4 종가가 보호 저점 아래로 마감할 때만 하락 전환(되돌림 안 내부 저점 깨짐은 무시). ext_structure() 참고.
 T_W1H4EXT 주판정(사전 지정). W1 구조 = H4 외부 구조 방향일 때만 그 방향 셋업. 추세 모드에서 늘 계산.
 T_W1H4    같은 조건을 H4 내부 구조(structure_states)로 본 비교판. 늘 계산.
 위치      스윕 시작 시각까지 마감한 H4 기준 외부 딜링 레인지(매수: 보호 저점 SL ~ 그 뒤 최고가 SH).
           깊이 = (SH-극값)/(SH-SL), 구간 0%미만/0~25/25~50/50~75/75~100(100% 포함)/100%+/없음(외부 추세 반대·없음).
           H4 OB = 보호 저점 봉부터 거꾸로 처음 만나는 음봉. 극값이 OB 안/전(안닿음)/관통. 내부 스윙 레인지 깊이는 depth_int.
 F_SLB     스윕 시작 이후 H4 종가가 보호 저점 너머로 마감하면: 그 시각이 체결 이전(같은 시각 포함)이면 셋업 취소,
           보유 중이면 그 H4봉 마지막 M5까지 손절·목표가 없을 때 그 봉 종가로 청산. 켬/끔 둘 다 계산(R, R_slb).
 --mss-tf  M15(기본), M5, 또는 M15,M5. MSS·OB·F3·S3를 그 시간봉으로 본다. M5면 확인 캔들 K도 M5. 조합 이름 앞에 'M5-'.
           석준님 실제 진입은 1분봉이지만 데이터가 M5뿐이라 1분봉은 시험 못 함.
 요약 맨 위 순서: [주판정 T_W1H4EXT] -> [위치 구간] -> [F_SLB 비교] -> [T1] -> [T2] -> 기존 표. 위치·F_SLB 상세는 location_*.csv.

읽기 전용 분석 스크립트다. MT5 연결·주문 없음. 필요한 것: Python 3.10+, pandas, numpy.
사용 예:
  py -3.12 crt_backtest.py --data-dir C:\\Users\\kun00\\venus\\mt5_m5_data --out C:\\Users\\kun00\\venus\\crt_bt_out
  py -3.12 crt_backtest.py --data-dir ... --out ... --all-filters --stops S2 --targets T2,T3
  py -3.12 crt_backtest.py --data-dir ... --out ... --trend T_D1S,T_W1S,T_D1H4,T_EMA,T_PDA --stops S2 --targets T2,T3
  py -3.12 crt_backtest.py --data-dir ... --out ... --trend ALL --mss-tf M15,M5 --stops S2 --targets T2,T3
  py -3.12 crt_backtest.py --selftest
"""
import argparse
import math
import os
import sys
import time as _time
from itertools import combinations

try:
    import numpy as np
    import pandas as pd
except ImportError:  # 설치 안내만
    print("pandas/numpy not found. Run:  py -3.12 -m pip install pandas numpy")
    sys.exit(1)

NS_MIN = 60 * 1_000_000_000
NS_H = 60 * NS_MIN
NS_INF = np.iinfo(np.int64).max
SERVER_MINUS_NY = 7          # IC마켓 서버시간 = 뉴욕 + 7
ENTRIES = ["A", "B", "C"]
STOPS = ["S1", "S2", "S3"]
TARGETS = ["T1", "T2", "T3", "T4"]
ENTRY_DESC = {"A": "OB 고가", "B": "OB 시가(몸통)", "C": "스윕~돌파 50%", "K": "확인 캔들 종가(F2)"}
STOP_DESC = {"S1": "OB 끝-1핍", "S2": "스윕 극값-1핍", "S3": "같은높이 저점묶음 너머-1핍"}
TARGET_DESC = {"T1": "CRH/CRL", "T2": "2R", "T3": "3R", "T4": "직전 4H 스윙"}
FILTERS = ["F1H", "F1D", "F2", "F3", "F4", "F5"]
FILTER_DESC = {"F1H": "큰 흐름 H4 구조", "F1D": "큰 흐름 D1>EMA20", "F2": "확인 캔들 진입",
               "F3": "OB 몸통 이탈 무효", "F4": "런던/뉴욕오전 체결", "F5": "HTF 유동성 스윕"}
SESSIONS = ["런던", "뉴욕", "아시아", "뉴욕마감후"]
TRENDS = ["T_W1H4EXT", "T_W1H4", "T_H4EXT", "T_D1S", "T_W1S", "T_D1H4", "T_EMA", "T_PDA"]
MAIN_TREND = "T_W1H4EXT"     # 주 판정(사전 지정): 석준님 "주봉과 4H 방향 일치 우선, 4H는 외부(스윙) 구조"
TREND_DESC = {"T_W1H4EXT": "W1+H4외부구조 같은 방향(주판정)", "T_W1H4": "W1+H4내부구조 같은 방향(비교)",
              "T_H4EXT": "H4 외부 구조(보호 저점 종가 이탈)",
              "T_D1S": "D1 구조(BOS)", "T_W1S": "W1 구조(BOS)",
              "T_D1H4": "D1+H4 구조 같은 방향",
              "T_EMA": "D1 EMA50 위+기울기", "T_PDA": "D1 구조+디스카운트/프리미엄", "NONE": "추세 조건 없음"}
MSS_TFS = ["M15", "M5"]
DEPTH_BUCKETS = ["0%미만", "0~25%", "25~50%", "50~75%", "75~100%", "100%+", "없음"]
OB_POS = ["OB안", "OB전(안닿음)", "OB관통", "없음"]
NS_D = 24 * NS_H


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
        print(f"  [header] {os.path.basename(path)}: {first.strip()[:200]}")
        print(f"  [row1] {second.strip()[:200]}")
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
        raise ValueError(f"open/high/low/close columns not found: {list(df.columns)}")
    cdate, ctime = pick("date", "day"), pick("time", "datetime", "date_time", "timestamp", "time_(utc)", "gmt_time", "local_time")
    if cdate and ctime and cdate != ctime:
        raw = df[cdate].astype(str).str.strip() + " " + df[ctime].astype(str).str.strip()
        ts = _parse_time(raw)
    elif ctime or cdate:
        ts = _parse_time(df[ctime or cdate])
    else:
        raise ValueError(f"time column not found: {list(df.columns)}")
    out = pd.DataFrame({"o": pd.to_numeric(df[co], errors="coerce").values,
                        "h": pd.to_numeric(df[ch], errors="coerce").values,
                        "l": pd.to_numeric(df[cl], errors="coerce").values,
                        "c": pd.to_numeric(df[cc], errors="coerce").values}, index=pd.DatetimeIndex(ts))
    out = out[~out.index.isna()].dropna()
    out = out[~out.index.duplicated(keep="first")].sort_index()
    if verbose:
        print(f"  [read] {len(out):,} bars, {out.index[0]} ~ {out.index[-1]} (server time)")
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
    """M5 배열을 서버시간 기준으로 묶는다(15분, 240분, 1440분). 시작시각 라벨."""
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
    """한 시각의 시간대(뉴욕 기준). 아시아 19~02, 런던 02~08, 뉴욕 08~17, 뉴욕마감후 17~19."""
    h = ny_hour(t_ns)
    if h >= 19 or h < 2:
        return "아시아"
    if h < 8:
        return "런던"
    if h < 17:
        return "뉴욕"
    return "뉴욕마감후"


def c2_session(c2_start_ns):
    """4H봉의 시간대 = 봉 가운데 시각(시작+2시간)의 시간대.
    뉴욕 17·21시 시작 = 아시아, 01·05시 = 런던, 09·13시 = 뉴욕."""
    return session_of(c2_start_ns + 2 * NS_H)


def parse_windows(s):
    out = []
    for part in str(s).split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            out.append((int(a), int(b)))
    return tuple(out)


def f4_ok(t_ns, windows):
    """체결 시각(뉴욕 시)이 창 안인지. 창 (2,5) = 02:00~04:59."""
    h = ny_hour(t_ns)
    return any(a <= h < b for a, b in windows)


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


def h4_swings(H4h, H4l, T4):
    """4H 스윙 고점/저점(앞뒤 2봉). 확정 시각 = k+2 봉 마감."""
    k4 = len(T4)
    sh4 = np.zeros(k4, bool)
    sl4 = np.zeros(k4, bool)
    for k in range(2, k4 - 2):
        sh4[k] = H4h[k] > H4h[k - 1] and H4h[k] > H4h[k - 2] and H4h[k] >= H4h[k + 1] and H4h[k] >= H4h[k + 2]
        sl4[k] = H4l[k] < H4l[k - 1] and H4l[k] < H4l[k - 2] and H4l[k] <= H4l[k + 1] and H4l[k] <= H4l[k + 2]
    conf4 = np.r_[T4[2:] + 4 * NS_H, np.full(min(2, k4), NS_INF)][:k4]
    sh_idx, sl_idx = np.flatnonzero(sh4), np.flatnonzero(sl4)
    return dict(sh4=sh4, sl4=sl4, conf4=conf4, sh_idx=sh_idx, sh_conf=conf4[sh_idx],
                sl_idx=sl_idx, sl_conf=conf4[sl_idx])


def h4_trend_at(sw, H4h, H4l, t):
    """F1H: 시각 t에 확정된 마지막 두 스윙 고점·저점. 둘 다 높아짐 +1, 둘 다 낮아짐 -1, 그 밖 0."""
    a = int(np.searchsorted(sw["sh_conf"], t, side="right"))
    b = int(np.searchsorted(sw["sl_conf"], t, side="right"))
    if a < 2 or b < 2:
        return 0
    h1, h0 = H4h[sw["sh_idx"][a - 1]], H4h[sw["sh_idx"][a - 2]]
    l1, l0 = H4l[sw["sl_idx"][b - 1]], H4l[sw["sl_idx"][b - 2]]
    if h1 > h0 and l1 > l0:
        return 1
    if h1 < h0 and l1 < l0:
        return -1
    return 0


def d1_context(t, o, h, l, c, span):
    d1 = bars_from_m5(t, o, h, l, c, 1440)
    d1["ema"] = pd.Series(d1["c"]).ewm(span=span, adjust=False).mean().values
    d1["span"] = span
    return d1


def d1_bias_at(d1, t):
    """F1D: 시각 t 직전에 마감한 D1의 종가 vs EMA. 위 +1, 아래 -1, 자료 부족 0."""
    j = int(np.searchsorted(d1["t"], t, side="right")) - 1   # t가 들어 있는 날
    p = j - 1                                                 # 직전 마감한 날
    if p < d1["span"] - 1:
        return 0
    c, e = d1["c"][p], d1["ema"][p]
    return 1 if c > e else (-1 if c < e else 0)


# ---------------------------------------------------------------- 추세 기본 조건 (--trend)
def _group_bars(t, o, h, l, c, key):
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    ends = np.r_[starts[1:], len(t)] - 1
    return dict(t=key[starts], o=o[starts], h=np.maximum.reduceat(h, starts),
                l=np.minimum.reduceat(l, starts), c=c[ends])


def w1_bars_from_m5(t, o, h, l, c):
    """주봉: 서버시간 월요일 00:00 시작. (혹시 일요일 봉이 있으면 다음 주에 붙인다.)"""
    day = t - (t % NS_D)
    wd = ((day // NS_D) + 3) % 7          # 1970-01-01 = 목요일 -> 월=0 ... 일=6
    key = np.where(wd == 6, day + NS_D, day - wd * NS_D)
    return _group_bars(t, o, h, l, c, key)


def structure_states(H, L, C, close_t, n):
    """시장 구조. 봉 b 마감 직후의 상태(마지막 BOS 방향)와 그때까지 확정된 마지막 스윙.
    스윙 s 는 봉 s+n 마감 때 확정. 봉 b 종가가 그 시점 마지막 확정 스윙 고점 위 -> +1, 저점 아래 -> -1."""
    k = len(H)
    state = np.zeros(k, np.int8)
    sh, sl = np.full(k, np.nan), np.full(k, np.nan)
    shi, sli = np.full(k, -1), np.full(k, -1)
    cur, hv, hi, lv, li = 0, np.nan, -1, np.nan, -1
    for b in range(k):
        s = b - n
        if s >= n:
            if H[s] > H[s - n:s].max() and H[s] >= H[s + 1:b + 1].max():
                hv, hi = H[s], s
            if L[s] < L[s - n:s].min() and L[s] <= L[s + 1:b + 1].min():
                lv, li = L[s], s
        up = hi >= 0 and C[b] > hv
        dn = li >= 0 and C[b] < lv
        if up and not dn:
            cur = 1
        elif dn and not up:
            cur = -1
        state[b], sh[b], shi[b], sl[b], sli[b] = cur, hv, hi, lv, li
    return dict(close_t=np.asarray(close_t), state=state, sh=sh, sh_i=shi, sl=sl, sl_i=sli, H=H, L=L)


def _last_closed(ss, t):
    """시각 t 까지 마감한 마지막 봉 인덱스 (없으면 -1)."""
    return int(np.searchsorted(ss["close_t"], t, side="right")) - 1


def state_at(ss, t):
    b = _last_closed(ss, t)
    return int(ss["state"][b]) if b >= 0 else 0


def ema_states(d1, span, slope_days):
    """T_EMA: D1 종가 > EMA 이고 EMA[p] > EMA[p-slope] -> +1 (반대 -1). 봉 p 마감 직후 상태."""
    c = np.asarray(d1["c"], float)
    ema = pd.Series(c).ewm(span=span, adjust=False).mean().values
    k = len(c)
    st = np.zeros(k, np.int8)
    p = np.arange(k)
    ok = (p >= span - 1) & (p >= slope_days)
    prev = np.r_[np.full(min(slope_days, k), np.nan), ema[:k - slope_days]][:k] if slope_days > 0 else ema
    up = ok & (c > ema) & (ema > prev)
    dn = ok & (c < ema) & (ema < prev)
    st[up], st[dn] = 1, -1
    return dict(close_t=np.asarray(d1["t"]) + NS_D, state=st, ema=ema)


def pda_ok(ss, d, ext, t):
    """T_PDA 위치: D1 딜링 레인지 50% 기준 디스카운트(매수)/프리미엄(매도)에서 스윕했는지."""
    b = _last_closed(ss, t)
    if b < 0 or ss["sh_i"][b] < 0 or ss["sl_i"][b] < 0:
        return False
    if d == 1:
        lo, si = ss["sl"][b], ss["sl_i"][b]
        hi = max(ss["sh"][b], ss["H"][si + 1:b + 1].max()) if si < b else ss["sh"][b]
    else:
        hi, si = ss["sh"][b], ss["sh_i"][b]
        lo = min(ss["sl"][b], ss["L"][si + 1:b + 1].min()) if si < b else ss["sl"][b]
    if not hi > lo:
        return False
    mid = 0.5 * (hi + lo)
    return bool(ext < mid) if d == 1 else bool(ext > mid)


def trend_context(t, o, h, l, c, n=2, ema_span=50, slope_days=5):
    """M5 배열에서 D1·W1·H4 구조와 D1 EMA 상태를 만든다. 모두 '봉 마감 시각' 기준으로 조회."""
    d1 = bars_from_m5(t, o, h, l, c, 1440)
    w1 = w1_bars_from_m5(t, o, h, l, c)
    h4 = bars_from_m5(t, o, h, l, c, 240)
    return dict(d1s=structure_states(d1["h"], d1["l"], d1["c"], d1["t"] + NS_D, n),
                w1s=structure_states(w1["h"], w1["l"], w1["c"], w1["t"] + 7 * NS_D, n),
                h4s=structure_states(h4["h"], h4["l"], h4["c"], h4["t"] + 4 * NS_H, n),
                ema=ema_states(d1, ema_span, slope_days),
                rng=h4_range_ctx(h4, n),
                h4x=ext_structure(h4, h4["t"] + 4 * NS_H, n))


def ext_structure(h4, close_t, n=2):
    """H4 외부(스윙) 구조. 석준님 정의(2026-10-28): 추세 = 마지막 외부 BOS 방향.
    보호 저점(상승 때) = 그 BOS를 만든 상승 다리가 시작된 저점. 추세는 H4 봉 '종가'가 보호 저점 아래로 마감할 때만 하락으로 바뀐다.
    되돌림 안의 내부 저점이 깨지는 것(내부 CHoCH)은 추세 변화가 아니다. 꼬리로만 찌르면 그대로 상승.
    상승 중 계속(BOS): 다리 최고가가 '확정'(그 뒤 n봉이 더 높지 않게 마감)된 뒤 종가가 그 위로 마감하면,
      그 고점 이후 ~ 이번 봉까지의 최저가가 새 보호 저점. 하락은 대칭.
    처음(판정 없음) = 내부 스윙(앞뒤 n봉) 고점 위 종가 마감 -> 상승, 보호 저점 = 그 고점 이후 최저가. 저점 쪽 대칭.
    봉 b 마감 직후 상태: state, prot(보호 극값)/prot_i, lx(보호점 이후 다리 극값: 상승이면 최고가)/lx_i."""
    H, L, C = (np.asarray(h4[k], float) for k in ("h", "l", "c"))
    k = len(H)
    st = np.zeros(k, np.int8)
    pp, pi, xp, xi = np.full(k, np.nan), np.full(k, -1), np.full(k, np.nan), np.full(k, -1)
    dr, prot_p, prot_i, lx_p, lx_i = 0, np.nan, -1, np.nan, -1
    shv, shi, slv, sli = np.nan, -1, np.nan, -1
    for b in range(k):
        s = b - n
        if s >= n:
            if H[s] > H[s - n:s].max() and H[s] >= H[s + 1:b + 1].max():
                shv, shi = H[s], s
            if L[s] < L[s - n:s].min() and L[s] <= L[s + 1:b + 1].min():
                slv, sli = L[s], s
        if dr == 0:
            if shi >= 0 and C[b] > shv:
                dr = 1
                prot_i = shi + int(np.argmin(L[shi:b + 1]))
                prot_p = L[prot_i]
                lx_i = prot_i + int(np.argmax(H[prot_i:b + 1]))
                lx_p = H[lx_i]
            elif sli >= 0 and C[b] < slv:
                dr = -1
                prot_i = sli + int(np.argmax(H[sli:b + 1]))
                prot_p = H[prot_i]
                lx_i = prot_i + int(np.argmin(L[prot_i:b + 1]))
                lx_p = L[lx_i]
        elif dr == 1:
            if C[b] < prot_p:                                   # 보호 저점 아래 종가 = 하락 전환
                hi = prot_i + int(np.argmax(H[prot_i:b + 1]))
                dr, prot_p, prot_i = -1, H[hi], hi
                lx_i = hi + int(np.argmin(L[hi:b + 1]))
                lx_p = L[lx_i]
            else:
                if lx_i >= 0 and (b - 1) - lx_i >= n and C[b] > lx_p:   # 확정된 다리 고점 위 종가 = 상승 BOS
                    lo = lx_i + 1 + int(np.argmin(L[lx_i + 1:b + 1]))
                    prot_p, prot_i = L[lo], lo
                if H[b] > lx_p:
                    lx_p, lx_i = H[b], b
        else:
            if C[b] > prot_p:                                   # 보호 고점 위 종가 = 상승 전환
                lo = prot_i + int(np.argmin(L[prot_i:b + 1]))
                dr, prot_p, prot_i = 1, L[lo], lo
                lx_i = lo + int(np.argmax(H[lo:b + 1]))
                lx_p = H[lx_i]
            else:
                if lx_i >= 0 and (b - 1) - lx_i >= n and C[b] < lx_p:
                    hi = lx_i + 1 + int(np.argmax(H[lx_i + 1:b + 1]))
                    prot_p, prot_i = H[hi], hi
                if L[b] < lx_p:
                    lx_p, lx_i = L[b], b
        st[b], pp[b], pi[b], xp[b], xi[b] = dr, prot_p, prot_i, lx_p, lx_i
    return dict(close_t=np.asarray(close_t), state=st, prot=pp, prot_i=pi, lx=xp, lx_i=xi,
                o=np.asarray(h4["o"], float), c=C, h=H, l=L)


def ext_range(x, d, t):
    """외부 구조 딜링 레인지(시각 t 까지 마감한 H4 기준). 외부 추세가 d 와 같을 때만:
    기준점 = 보호 저점(매수), 먼 끝 = 그 뒤 최고가(SH). H4 OB = 보호 저점 봉부터 거꾸로 처음 만나는 음봉. 아니면 None."""
    b = _last_closed(x, t)
    if b < 0 or int(x["state"][b]) != d:
        return None
    s, O, C, H, L = int(x["prot_i"][b]), x["o"], x["c"], x["h"], x["l"]
    ob = -1
    for k in range(s, max(-1, s - 10), -1):
        if (d == 1 and C[k] < O[k]) or (d == -1 and C[k] > O[k]):
            ob = k
            break
    return dict(origin=float(x["prot"][b]), far=float(x["lx"][b]), origin_i=s, far_i=int(x["lx_i"][b]),
                ob_l=float(L[ob]) if ob >= 0 else np.nan, ob_h=float(H[ob]) if ob >= 0 else np.nan)


# ---------------------------------------------------------------- 위치(H4 딜링 레인지) / F_SLB
def h4_range_ctx(h4, n):
    """H4 스윙 목록(앞 n봉보다 높고 뒤 n봉 이상, structure_states 와 같은 규칙). 확정 시각 = 봉 s+n 마감."""
    H, L = np.asarray(h4["h"], float), np.asarray(h4["l"], float)
    k = len(H)
    hi, lo = [], []
    for s in range(n, k - n):
        if H[s] > H[s - n:s].max() and H[s] >= H[s + 1:s + n + 1].max():
            hi.append(s)
        if L[s] < L[s - n:s].min() and L[s] <= L[s + 1:s + n + 1].min():
            lo.append(s)
    hi, lo = np.array(hi, int), np.array(lo, int)
    T4 = np.asarray(h4["t"])
    conf = lambda idx: T4[idx + n] + 4 * NS_H if len(idx) else np.array([], np.int64)   # noqa: E731
    return dict(t=T4, o=np.asarray(h4["o"], float), h=H, l=L, c=np.asarray(h4["c"], float), n=n,
                hi_idx=hi, hi_conf=conf(hi), lo_idx=lo, lo_conf=conf(lo))


def dealing_range(rc, d, t, max_back=50):
    """시각 t 에 확정된 H4 스윙으로 만든 딜링 레인지. 매수(d=1):
    기준점 = 확정 스윙 저점 중 그 뒤에 확정 스윙 고점이 있는 가장 최근 것(SL), 먼 끝 = 그 뒤 확정 스윙 고점 중 최고(SH).
    (가장 최근 저점 뒤에 고점이 아직 없으면 = 되돌림 중 작은 저점, 그 앞 저점으로 간다.)
    H4 OB = SL 봉부터 거꾸로 처음 만나는 음봉(SH로 가는 상승 직전 마지막 하락 H4봉). 매도는 대칭.
    돌려줌 dict(origin, far, origin_i, far_i, ob_l, ob_h) 또는 None."""
    H, L, O, C = rc["h"], rc["l"], rc["o"], rc["c"]
    mh = int(np.searchsorted(rc["hi_conf"], t, side="right"))
    ml = int(np.searchsorted(rc["lo_conf"], t, side="right"))
    his, los = rc["hi_idx"][:mh], rc["lo_idx"][:ml]
    origins, others = (los, his) if d == 1 else (his, los)
    for s in origins[::-1][:max_back]:
        after = others[np.searchsorted(others, s, side="right"):]
        if len(after) == 0:
            continue
        far_i = int(after[np.argmax(H[after])]) if d == 1 else int(after[np.argmin(L[after])])
        ob = -1
        for k in range(s, max(-1, s - 10), -1):
            if (d == 1 and C[k] < O[k]) or (d == -1 and C[k] > O[k]):
                ob = k
                break
        return dict(origin=float(L[s] if d == 1 else H[s]), far=float(H[far_i] if d == 1 else L[far_i]),
                    origin_i=int(s), far_i=far_i,
                    ob_l=float(L[ob]) if ob >= 0 else np.nan, ob_h=float(H[ob]) if ob >= 0 else np.nan)
    return None


def depth_of(rg, ext):
    """되돌림 깊이 = (먼 끝 - 극값)/(먼 끝 - 기준점). 매수: (SH-극값)/(SH-SL). 0 = SH, 1 = SL. 매도도 같은 식."""
    if rg is None or rg["far"] == rg["origin"]:
        return np.nan
    return (rg["far"] - ext) / (rg["far"] - rg["origin"])


def depth_bucket(depth):
    """구간: 0%미만(먼 끝 너머), 0~25, 25~50, 50~75, 75~100(100% = 기준점 딱 닿음 포함), 100%+(기준점 너머 꼬리 스윕)."""
    if depth is None or not np.isfinite(depth):
        return "없음"
    if depth < 0:
        return "0%미만"
    if depth > 1:
        return "100%+"
    if depth < 0.25:
        return "0~25%"
    if depth < 0.5:
        return "25~50%"
    if depth < 0.75:
        return "50~75%"
    return "75~100%"


def ob_position(rg, d, ext):
    """스윕 극값이 H4 OB 범위 안인지. 매수: 안 = ob_l<=극값<=ob_h, OB전 = 극값>ob_h, 관통 = 극값<ob_l."""
    if rg is None or not np.isfinite(rg["ob_l"]):
        return "없음"
    if rg["ob_l"] <= ext <= rg["ob_h"]:
        return "OB안"
    before = ext > rg["ob_h"] if d == 1 else ext < rg["ob_l"]
    return "OB전(안닿음)" if before else "OB관통"


def location_of(rc, d, ext, t, x=None):
    """위치. x(외부 구조)가 있으면 주 위치 = 외부 레인지(보호 저점 ~ 그 뒤 최고가), 내부 스윙 레인지는 depth_int 로 따로."""
    ri = dealing_range(rc, d, t) if rc is not None else None
    rg = ext_range(x, d, t) if x is not None else ri
    dep = depth_of(rg, ext)
    di = depth_of(ri, ext)
    return dict(rng=rg, depth=dep, bucket=depth_bucket(dep), ob_pos=ob_position(rg, d, ext),
                origin=(rg["origin"] if rg else np.nan), far=(rg["far"] if rg else np.nan),
                h4ob_l=(rg["ob_l"] if rg else np.nan), h4ob_h=(rg["ob_h"] if rg else np.nan),
                depth_int=di, bucket_int=depth_bucket(di))


def slb_break(d, origin, t_from, CT4, C4):
    """F_SLB: 시각 t_from 이후 마감한 H4 봉 중 종가가 기준점 너머(매수: SL 아래)인 첫 봉. 돌려줌 (마감 시각, 종가).
    꼬리만 찌르면 해당 없음(몸통 마감만). 없거나 기준점이 없으면 (NS_INF, nan)."""
    if origin is None or not np.isfinite(origin):
        return NS_INF, np.nan
    a = int(np.searchsorted(CT4, t_from, side="right"))
    seg = C4[a:]
    k = first_true(seg < origin) if d == 1 else first_true(seg > origin)
    return (int(CT4[a + k]), float(C4[a + k])) if k >= 0 else (NS_INF, np.nan)


def slb_apply(d, td, res, k, px, tbreak, pbreak, t, spread):
    """F_SLB 켬 결과. td = 체결(판단) 시각, (res, k, px) = 끔일 때 결과.
    tbreak <= td -> 체결 전 무효 = 셋업 취소('cancel'). 보유 중 깨지면 그 H4 봉 마지막 M5(k_x)까지 손절·목표가 안 났을 때
    그 봉 종가로 청산('slb'; 매수는 bid 종가, 매도는 ask = 종가+스프레드)."""
    if tbreak <= td:
        return "cancel", -1, np.nan
    if tbreak >= NS_INF:
        return res, k, px
    kx = int(np.searchsorted(t, tbreak)) - 1
    if res != "open" and k <= kx:
        return res, k, px
    return "slb", kx, (pbreak if d == 1 else pbreak + spread)


def trend_align(tc, d, ext, t):
    """시각 t(스윕 시작)에 셋업 방향 d가 각 추세 정의와 맞는지. +1 같은 방향, -1 반대, 0 판정 없음."""
    sd, sw, s4, se = (state_at(tc[k], t) for k in ("d1s", "w1s", "h4s", "ema"))
    sx = state_at(tc["h4x"], t) if "h4x" in tc else 0
    out = {"T_W1H4EXT": (sw * d) if (sw != 0 and sw == sx) else 0,
           "T_W1H4": (sw * d) if (sw != 0 and sw == s4) else 0,
           "T_H4EXT": sx * d,
           "T_D1S": sd * d, "T_W1S": sw * d, "T_EMA": se * d,
           "T_D1H4": (sd * d) if (sd != 0 and sd == s4) else 0}
    if sd == d:
        out["T_PDA"] = 1 if pda_ok(tc["d1s"], d, ext, t) else 0
    else:
        out["T_PDA"] = -1 if sd == -d else 0
    return out


def htf_swept(d, ext, sweep_j, i, T, H, L, d1, sw, T4, H4h, H4l, tol, lookback, mode="cluster"):
    """F5: 스윕(극값 ext)이 HTF 유동성을 처음 넘었는지. 돌려줌 (bool, 종류 문자열).
    PDL/PDH: 스윕 시작 봉 sweep_j 의 전날 저가/고가, 그날 sweep_j 전에는 안 깨졌어야 함.
    H4: sweep_j 시각에 확정된 4H 스윙 저점(고점) 중 형성 후 sweep_j 전까지 안 깨진 것.
        cluster = 그런 것들이 tol 이내로 2개 이상 모인 묶음 전체를 넘음, swing = 하나라도 넘음."""
    ts = T[sweep_j]
    kinds = []
    j = int(np.searchsorted(d1["t"], ts, side="right")) - 1
    if j >= 1:
        a = int(np.searchsorted(T, d1["t"][j]))
        if d == 1:
            lvl = d1["l"][j - 1]
            before = L[a:sweep_j].min() if sweep_j > a else np.inf
            if ext < lvl and before >= lvl:
                kinds.append("PDL")
        else:
            lvl = d1["h"][j - 1]
            before = H[a:sweep_j].max() if sweep_j > a else -np.inf
            if ext > lvl and before <= lvl:
                kinds.append("PDH")
    idx, conf = (sw["sl_idx"], sw["sl_conf"]) if d == 1 else (sw["sh_idx"], sw["sh_conf"])
    m = int(np.searchsorted(conf, ts, side="right"))
    cand = idx[:m]
    cand = cand[cand >= i - lookback]
    fresh = []
    for k in cand:
        lvl = H4l[k] if d == 1 else H4h[k]
        if d * (lvl - ext) <= 0:          # 극값이 이 높이를 넘지 못함
            continue
        a = int(np.searchsorted(T, T4[k] + 4 * NS_H))
        if sweep_j > a:
            seg = L[a:sweep_j] if d == 1 else H[a:sweep_j]
            if (d == 1 and seg.min() < lvl) or (d == -1 and seg.max() > lvl):
                continue                  # 이미 깨진 높이
        fresh.append(lvl)
    if fresh:
        if mode == "swing":
            kinds.append("H4swing")
        elif len(fresh) >= 2 and np.any(np.diff(np.sort(fresh)) <= tol + 1e-12):
            kinds.append("H4eq")
    return bool(kinds), "+".join(kinds)


def first_invalid_close(d, C, T, j0, j1, far, step):
    """F3: M15 j0..j1-1 중 종가가 OB 먼 끝(매수 OB 저가) 너머로 처음 마감한 봉의 마감 시각. 없으면 NS_INF."""
    if j1 <= j0:
        return NS_INF
    seg = C[j0:j1]
    k = first_true(seg < far) if d == 1 else first_true(seg > far)
    return int(T[j0 + k] + step) if k >= 0 else NS_INF


def confirm_entry(d, bo, bh, bl, bc, b0, b1, edge, target, spread=0.0):
    """F2: EA Track 순서. 봉 b0..b1-1을 보며
    목표(CRH) 먼저 닿음 -> 취소, OB 끝 닿음 -> 대기, 닿은 뒤(같은 봉 포함) 양봉이 OB 끝 위에서 마감 -> 진입.
    돌려줌 ('entry'|'cancel_tp'|'expired', 봉 인덱스)."""
    touched = False
    for b in range(b0, b1):
        if (d == 1 and bh[b] >= target) or (d == -1 and bl[b] + spread <= target):
            return "cancel_tp", b
        if not touched:
            if (d == 1 and bl[b] <= edge) or (d == -1 and bh[b] >= edge):
                touched = True
            else:
                continue
        if (d == 1 and bc[b] > bo[b] and bc[b] > edge) or (d == -1 and bc[b] < bo[b] and bc[b] < edge):
            return "entry", b
    return "expired", -1


# ---------------------------------------------------------------- 셋업 찾기
def find_setups(m15, h4, n, pip, opt, ctx=None, side=0, step=15 * NS_MIN):
    """MSS 시간봉(기본 M15, --mss-tf M5 면 M5)·H4 배열에서 셋업(주문 직전까지)을 찾는다. 돌려주는 값: 셋업 목록, 깔때기 집계.
    side=0: C2 안에서 먼저 난 스윕 방향(기본). side=1: CRL 스윕(매수)만 찾음, side=-1: CRH 스윕(매도)만.
    step = MSS 시간봉 길이(ns). 변수 이름은 m15 지만 M5 봉도 같은 방식으로 받는다."""
    T, O, H, L, C = m15["t"], m15["o"], m15["h"], m15["l"], m15["c"]
    T4, H4h, H4l, H4c = h4["t"], h4["h"], h4["l"], h4["c"]
    step15 = step
    funnel = dict(c2=0, asia_skip=0, sweep=0, c2_close_ok=0, mss_line=0, mss_confirm=0,
                  no_ob=0, target_before_order=0, setups=0)
    if ctx and ctx.get("trend") is not None:
        funnel.update({f"aligned_{k}": 0 for k in TRENDS})
    setups = []
    sw = ctx["sw"] if ctx else h4_swings(H4h, H4l, T4)
    d1 = ctx["d1"] if ctx else None
    sh4, sl4, conf4 = sw["sh4"], sw["sl4"], sw["conf4"]
    k4 = len(T4)
    tol = getattr(opt, "eq_tol", 2.0) * pip

    for i in range(1, k4):
        funnel["c2"] += 1
        c2s, c2e = T4[i], T4[i] + 4 * NS_H
        if not opt.include_asia and c2_session(c2s) == "아시아":
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
        d, ext, ext_i, mss, conf_j, sweep_j = 0, 0.0, -1, 0.0, -1, -1
        for j in range(a2, a3):
            if d == 0:
                if side >= 0 and L[j] < crl:
                    d, ext, ext_i = 1, L[j], j
                elif side <= 0 and H[j] > crh:
                    d, ext, ext_i = -1, H[j], j
                else:
                    continue
                sweep_j = j
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
        # 필터 재료 (모두 주문 시점까지의 정보만)
        h4tr = h4_trend_at(sw, H4h, H4l, t_order)
        d1b = d1_bias_at(d1, t_order) if d1 is not None else 0
        if d1 is not None:
            f5, f5k = htf_swept(d, ext, sweep_j, i, T, H, L, d1, sw, T4, H4h, H4l, tol,
                                opt.t4_lookback, getattr(opt, "f5_h4", "cluster"))
        else:
            f5, f5k = False, ""
        tc = ctx.get("trend") if ctx else None
        tv = trend_align(tc, d, ext, T[sweep_j]) if tc is not None else {}
        if tc is not None:   # 위치: 스윕 시작 시각에 확정된 H4 스윙만 사용
            loc = location_of(tc["rng"], d, ext, T[sweep_j], tc.get("h4x"))
        else:
            loc = dict(rng=None, depth=np.nan, bucket="없음", ob_pos="없음", origin=np.nan, far=np.nan,
                       h4ob_l=np.nan, h4ob_h=np.nan, depth_int=np.nan, bucket_int="없음")
        for k_, v_ in tv.items():
            funnel[f"aligned_{k_}"] = funnel.get(f"aligned_{k_}", 0) + int(v_ == 1)
        funnel["setups"] += 1
        setups.append(dict(d=d, c1=T4[i - 1], c2=c2s, crh=crh, crl=crl, ext=ext, ext_i=ext_i, mss=mss,
                           t_conf=T[conf_j], conf_j=conf_j, ob_i=ob, ob_h=H[ob], ob_l=L[ob], ob_o=O[ob],
                           brk=brk, t_order=t_order, px_order=px_order, t4=t4, sweep_j=sweep_j,
                           h4_trend=h4tr, d1_bias=d1b, f1h=(h4tr == d), f1d=(d1b == d), f5=f5, f5_kind=f5k,
                           c2_sess=c2_session(c2s), trend=tv, t_sweep=T[sweep_j], loc=loc))
    return setups, funnel


# ---------------------------------------------------------------- 체결·청산 (M5)
def first_true(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if len(idx) else -1


def simulate_exit(d, f, fill, sl, tp, spread, M, max_hold, check_fill_bar=True):
    """체결 봉 f 부터 손절/목표. 돌려줌: (결과, 청산 인덱스, 청산가).
    check_fill_bar=True(지정가): 봉 f 안에서 체결 -> 그 봉은 손절만 본다.
    check_fill_bar=False(확인 캔들 종가 진입): 봉 f 마감에 진입 -> f+1 부터 본다."""
    O, H, L, C = M["o"], M["h"], M["l"], M["c"]
    n = len(O)
    if check_fill_bar and ((d == 1 and L[f] <= sl) or (d == -1 and H[f] + spread >= sl)):
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


def _list_opt(v, allowed):
    if isinstance(v, (list, tuple)):
        out = [str(x).strip().upper() for x in v]
    else:
        out = [x.strip().upper() for x in str(v).split(",") if x.strip()]
    bad = [x for x in out if x not in allowed]
    if bad:
        raise ValueError(f"unknown value {bad}, allowed {allowed}")
    return out


def trend_list(opt):
    v = getattr(opt, "trend", "")
    if not v:
        return []
    out = _list_opt(v, TRENDS + ["ALL"])
    out = list(TRENDS) if "ALL" in out else out
    for k in ("T_W1H4", MAIN_TREND):   # 주 판정과 내부구조 비교판은 추세 모드에서 늘 같이 계산
        if k not in out:
            out = [k] + out
    return out


def enabled_filters(opt):
    on = {"F1H": opt.f1h4, "F1D": opt.f1d1, "F2": opt.f2, "F3": opt.f3, "F4": opt.f4, "F5": opt.f5}
    return [f for f in FILTERS if on[f]]


def mss_tf_list(opt):
    return _list_opt(getattr(opt, "mss_tf", "M15"), MSS_TFS)


def run_symbol(sym, m5df, opt, pip, spread_pips):
    t = m5df.index.values.astype("datetime64[ns]").astype("int64")
    o, h, l, c = (m5df[k].values.astype(float) for k in ("o", "h", "l", "c"))
    M = dict(t=t, o=o, h=h, l=l, c=c)
    m15 = bars_from_m5(t, o, h, l, c, 15)
    h4 = bars_from_m5(t, o, h, l, c, 240)
    ctx = dict(sw=h4_swings(h4["h"], h4["l"], h4["t"]), d1=d1_context(t, o, h, l, c, opt.d1_ema))
    trends = trend_list(opt)
    if trends:
        ctx["trend"] = trend_context(t, o, h, l, c, opt.trend_swing, opt.trend_ema, opt.trend_slope)
        rc = ctx["trend"]["rng"]
        CT4 = rc["t"] + 4 * NS_H
        okc = CT4 <= t[-1] + 5 * NS_MIN            # 끝의 덜 끝난 H4봉은 F_SLB 판정에 안 씀
        CT4, C4 = CT4[okc], rc["c"][okc]
    else:
        CT4, C4 = np.array([], np.int64), np.array([], float)
    spread = spread_pips * pip
    buf = opt.sl_buffer * pip
    tol = opt.eq_tol * pip
    step15 = 15 * NS_MIN
    entries = _list_opt(opt.entries, ENTRIES)
    stops_on = _list_opt(opt.stops, STOPS)
    targets_on = _list_opt(opt.targets, TARGETS)
    use_k = bool(opt.f2) or bool(trends)
    all_e = entries + (["K"] if use_k else [])
    windows = parse_windows(opt.f4_windows)
    trades, funnels = [], []
    for tf in mss_tf_list(opt):
        # MSS 시간봉: M15(기본) 또는 M5. 유효시간·만료는 시간으로 같게(expiry_bars x 15분).
        B, stp = (m15, step15) if tf == "M15" else (M, 5 * NS_MIN)
        pre = "" if tf == "M15" else f"{tf}-"
        if tf == "M5" or opt.f2_tf.upper() == "M5":
            KB, kstep = M, 5 * NS_MIN          # MSS를 M5로 보면 확인 캔들도 M5
        else:
            KB, kstep = m15, step15
        # MSS 시간봉 1봉 프랙탈 저점/고점 (확정 시각 = 다음 봉 마감), S3 재료
        L15, H15, T15, C15 = B["l"], B["h"], B["t"], B["c"]
        fl = np.zeros(len(L15), bool)
        fh = np.zeros(len(H15), bool)
        fl[1:-1] = (L15[1:-1] < L15[:-2]) & (L15[1:-1] <= L15[2:])
        fh[1:-1] = (H15[1:-1] > H15[:-2]) & (H15[1:-1] >= H15[2:])
        for n in opt.swing:
            if trends:
                # 추세 모드: 매수 쪽·매도 쪽 스윕을 각각 따로 찾는다(먼저 난 쪽만 보면 추세 방향 셋업을 놓침)
                sb, fb_ = find_setups(B, h4, n, pip, opt, ctx, side=1, step=stp)
                ss_, fs_ = find_setups(B, h4, n, pip, opt, ctx, side=-1, step=stp)
                setups = sorted(sb + ss_, key=lambda x: x["t_order"])
                fun = {k: (fb_[k] if k in ("c2", "asia_skip") else fb_[k] + fs_[k]) for k in fb_}
            else:
                setups, fun = find_setups(B, h4, n, pip, opt, ctx, step=stp)
            fun.update(symbol=sym, swing=n, mss_tf=tf)
            cnt = {k: {e: 0 for e in all_e} for k in ("fill", "skip_px", "expired", "cancel_tp", "f3_invalid", "slb_cancel")}
            for st in setups:
                d = st["d"]
                lc = st["loc"]
                ent = {"A": st["ob_h"] if d == 1 else st["ob_l"],
                       "B": st["ob_o"],
                       "C": st["ext"] + 0.5 * (st["brk"] - st["ext"])}
                struct_tp = st["crh"] if d == 1 else st["crl"]
                edge = st["ob_h"] if d == 1 else st["ob_l"]     # 가격이 먼저 닿는 OB 끝
                far = st["ob_l"] if d == 1 else st["ob_h"]      # 이 너머로 마감하면 무효(F3)
                t_end = st["t_order"] + opt.expiry_bars * step15
                i0 = int(np.searchsorted(t, st["t_order"]))
                i1 = int(np.searchsorted(t, t_end))
                if i0 >= len(t):
                    continue
                j1 = int(np.searchsorted(T15, t_end + stp))
                inv_t = first_invalid_close(d, C15, T15, st["conf_j"] + 1, j1, far, stp)
                # F_SLB: 스윕 시작 이후 처음으로 H4 몸통이 딜링 레인지 기준점(SL) 너머 마감한 시각
                tbreak, pbreak = slb_break(d, lc["origin"], st["t_sweep"], CT4, C4) if trends else (NS_INF, np.nan)
                fills = []   # (진입 종류, 진입 M5 인덱스, 진입가, 판단 시각, 체결 봉 손절 검사)
                for e in entries:
                    E = ent[e]
                    # 지정가는 현재가보다 유리한 쪽에만 걸 수 있다
                    if (d == 1 and E >= st["px_order"]) or (d == -1 and E <= st["px_order"]):
                        cnt["skip_px"][e] += 1
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
                            cnt["cancel_tp"][e] += 1
                        else:
                            cnt["expired"][e] += 1
                        continue
                    f = i0 + fi
                    if opt.block_asia_fill and session_of(t[f]) == "아시아":
                        cnt["expired"][e] += 1
                        continue
                    fill = min(E, o[f] + spread) if d == 1 else max(E, o[f])   # 갭이면 더 좋은 값
                    fills.append((e, f, fill, int(t[f]), True))
                if use_k:
                    b0 = int(np.searchsorted(KB["t"], st["t_order"]))
                    b1 = int(np.searchsorted(KB["t"], t_end))
                    res_k, b = confirm_entry(d, KB["o"], KB["h"], KB["l"], KB["c"], b0, b1, edge, struct_tp, spread)
                    if res_k == "entry":
                        tc = int(KB["t"][b] + kstep)                      # 확인 캔들 마감 시각
                        f = int(np.searchsorted(t, tc)) - 1               # 그 봉의 마지막 M5
                        if opt.block_asia_fill and session_of(tc) == "아시아":
                            cnt["expired"]["K"] += 1
                        elif f + 1 < len(t):
                            fills.append(("K", f, KB["c"][b] + (spread if d == 1 else 0.0), tc, False))
                    else:
                        cnt["expired" if res_k == "expired" else "cancel_tp"]["K"] += 1
                for e, f, fill, td, chk in fills:
                    cnt["fill"][e] += 1
                    f3 = not (inv_t <= td)
                    if not f3:
                        cnt["f3_invalid"][e] += 1
                    if tbreak <= td:
                        cnt["slb_cancel"][e] += 1
                    f4 = f4_ok(td, windows)
                    # S3 재료: 극값 다음 봉 ~ 판단 시각 전에 확정된 프랙탈 (MSS 시간봉)
                    j_end = int(np.searchsorted(T15, td - stp, side="right"))  # 판단 시각까지 마감된 봉 수
                    js = np.arange(st["ext_i"] + 1, max(st["ext_i"] + 1, j_end - 1))
                    lv = (L15[js][fl[js]] if d == 1 else H15[js][fh[js]]) if len(js) else np.array([])
                    stops = {"S1": (st["ob_l"] - buf) if d == 1 else (st["ob_h"] + buf),
                             "S2": st["ext"] - d * buf}
                    s3 = equal_level_stop(d, lv, fill, tol, buf)
                    stops["S3"] = s3 if s3 is not None else stops["S2"]
                    for s in stops_on:
                        SL = stops[s]
                        risk = d * (fill - SL)
                        if risk <= 0 or risk < opt.min_risk_pips * pip:
                            continue
                        for tg in targets_on:
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
                            res, k, px = simulate_exit(d, f, fill, SL, TP, spread, M, opt.max_hold_bars, chk)
                            r = np.nan if res == "open" else d * (px - fill) / risk
                            res2, k2, px2 = slb_apply(d, td, res, k, px, tbreak, pbreak, t, spread)
                            r2 = np.nan if res2 in ("open", "cancel") else d * (px2 - fill) / risk
                            trades.append(dict(
                                symbol=sym, swing=n, mss_tf=tf, entry_v=e, stop_v=s, target_v=tg,
                                combo=f"{pre}N{n}-{e}-{s}-{tg}", dir="BUY" if d == 1 else "SELL",
                                c1_server=t2s(st["c1"]), c2_server=t2s(st["c2"]), c2_session=st["c2_sess"],
                                crh=st["crh"], crl=st["crl"], sweep_ext=st["ext"], mss=st["mss"],
                                ob_h=st["ob_h"], ob_l=st["ob_l"],
                                mss_confirm_server=t2s(st["t_conf"]), order_server=t2s(st["t_order"]),
                                fill_server=t2s(td if not chk else t[f]), entry=fill, sl=SL, tp=TP,
                                risk_pips=risk / pip, rr_planned=d * (TP - fill) / risk,
                                exit_server=t2s(t[k]), exit_price=px, result=res, R=r,
                                s3_fallback=(s == "S3" and s3 is None), t4_fallback=(tg == "T4" and fb),
                                session=session_of(td), t_fill_ns=td,
                                h4_trend=st["h4_trend"], d1_bias=st["d1_bias"],
                                f1h=st["f1h"], f1d=st["f1d"], f3=f3, f4=f4, f5=st["f5"], f5_kind=st["f5_kind"],
                                rng_origin=lc["origin"], rng_far=lc["far"], depth=lc["depth"],
                                depth_bucket=lc["bucket"], h4ob_l=lc["h4ob_l"], h4ob_h=lc["h4ob_h"], ob_pos=lc["ob_pos"],
                                depth_int=lc["depth_int"], depth_bucket_int=lc["bucket_int"],
                                slb_break_server=(t2s(tbreak) if tbreak < NS_INF else ""),
                                slb_cancel=(res2 == "cancel"), result_slb=res2, R_slb=r2,
                                exit_slb_server=(t2s(t[k2]) if k2 >= 0 else ""),
                                setup_id=f"{sym}|{tf}|{n}|{t2s(st['c2'])}|{d}",
                                **{f"trend_{k_}": v_ for k_, v_ in st["trend"].items()}))
            for k, v in cnt.items():
                for e in all_e:
                    fun[f"{k}_{e}"] = v[e]
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
            for s in SESSIONS:
                v = gc[gc["session"] == s]["R"].values
                row[f"exp_{s}"] = v.mean() if len(v) else np.nan
                row[f"n_{s}"] = len(v)
                v = gc[gc["c2_session"] == s]["R"].values
                row[f"c2exp_{s}"] = v.mean() if len(v) else np.nan
                row[f"c2n_{s}"] = len(v)
            rows.append(row)
    return pd.DataFrame(rows)


def _agg(df, keys):
    """keys 별 n, 평균, t값 (전체·IS·OOS). 빠르게 groupby 로."""
    def one(g, pre):
        a = g.groupby(keys)["R"].agg(["count", "mean", "std"])
        se = a["std"] / np.sqrt(a["count"])
        a["t"] = np.where(se > 0, a["mean"] / se, np.nan)
        a = a.drop(columns="std")
        a.columns = [f"{pre}n", f"{pre}exp_R", f"{pre}t"]
        return a
    out = one(df, "")
    for p in ("IS", "OOS"):
        out = out.join(one(df[df["period"] == p], p + "_"), how="left")
    for p in ("IS_", "OOS_"):
        out[p + "n"] = out[p + "n"].fillna(0).astype(int)
    return out.reset_index()


def filter_table(tr, enabled):
    """켠 필터들의 모든 켬/끔 조합 x 기본 조합(N-진입-손절-목표) 결과. symbol=ALL 과 종목별."""
    closed = tr[tr["result"] != "open"]
    rows = []
    for r in range(len(enabled) + 1):
        for sub in combinations(enabled, r):
            m = np.ones(len(closed), bool)
            if "F2" in enabled:
                isk = (closed["entry_v"] == "K").values
                m &= isk if "F2" in sub else ~isk
            for f in sub:
                if f != "F2":
                    m &= closed[f.lower()].values.astype(bool)
            g = closed[m]
            if g.empty:
                continue
            a = _agg(g, ["combo"])
            a.insert(0, "symbol", "ALL")
            b = _agg(g, ["symbol", "combo"])
            ab = pd.concat([a, b], ignore_index=True)
            ab.insert(1, "filters", "+".join(sub) if sub else "none")
            ab.insert(2, "n_filters", len(sub))
            rows.append(ab)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    out["base"] = out["combo"].str.replace(r"-[ABCK]-", "-*-", regex=True)
    return out


def trend_table(tr, trends):
    """추세 정의별 x 조합 결과. align: with(추세와 같은 방향만 = 기본 조건), against(반대, 비교용).
    NONE = 추세 조건 없이 모든 셋업(매수·매도 양쪽 따로 찾은 것)."""
    closed = tr[tr["result"] != "open"]
    rows = []
    for name in ["NONE"] + list(trends):
        for side, lab in ((1, "with"), (-1, "against")):
            if name == "NONE":
                if side == -1:
                    continue
                g = closed
            else:
                g = closed[closed[f"trend_{name}"] == side]
            if g.empty:
                continue
            a = _agg(g, ["combo"])
            a.insert(0, "symbol", "ALL")
            b = _agg(g, ["symbol", "combo"])
            ab = pd.concat([a, b], ignore_index=True)
            ab.insert(1, "trend", name)
            ab.insert(2, "align", lab)
            rows.append(ab)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _scopes(closed):
    """주판정·위치 표의 범위: 주판정(T_W1H4EXT) 추세 일치 / 추세 조건 없음."""
    col = f"trend_{MAIN_TREND}"
    out = [(f"{MAIN_TREND} 일치", closed[closed[col] == 1] if col in closed else closed.iloc[0:0])]
    out.append(("추세없음", closed))
    return out


def _cstat(g, col="R"):
    """조합별 n·기대값·승률·표준오차를 구해 조합끼리 평균. t = 평균 기대값 / 평균 표준오차. 셋업 = 겹치지 않게 센 셋업 수."""
    g = g[g[col].notna()]
    if g.empty:
        return dict(setups=0, n=0.0, exp=np.nan, wr=np.nan, t=np.nan)
    a = g.groupby("combo")[col].agg(["count", "mean", "std"])
    a["wr"] = g.assign(_w=(g[col] > 0).astype(float)).groupby("combo")["_w"].mean()
    se = (a["std"] / np.sqrt(a["count"])).mean()
    e = a["mean"].mean()
    return dict(setups=int(g["setup_id"].nunique()), n=float(a["count"].mean()), exp=e, wr=a["wr"].mean() * 100,
                t=(e / se) if (np.isfinite(se) and se > 0) else np.nan)


def _pstats(g, col="R"):
    """전체·IS·OOS 묶음."""
    return {p: _cstat(g if p == "ALL" else g[g["period"] == p], col) for p in ("ALL", "IS", "OOS")}


def location_table(tr):
    """위치 구간·H4 OB 위치·F_SLB 켬/끔별 x 조합 결과(CSV 용). scope = 주판정 일치 / 추세없음."""
    if "depth_bucket" not in tr:
        return pd.DataFrame()
    closed = tr[tr["result"] != "open"]
    rows = []
    for scope, g in _scopes(closed):
        if g.empty:
            continue
        for kind, key in (("depth", "depth_bucket"), ("h4ob", "ob_pos")):
            a = _agg(g, ["mss_tf", key, "combo"]).rename(columns={key: "cat"})
            a.insert(0, "scope", scope)
            a.insert(1, "kind", kind)
            rows.append(a)
        gs = g[~g["slb_cancel"] & g["R_slb"].notna()].assign(R=lambda x: x["R_slb"])
        for lab, gg in (("F_SLB 끔", g), ("F_SLB 켬", gs)):
            if gg.empty:
                continue
            a = _agg(gg, ["mss_tf", "combo"])
            a.insert(0, "scope", scope)
            a.insert(1, "kind", "f_slb")
            a.insert(3, "cat", lab)
            rows.append(a)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _row(label, st, w=18):
    a, i, o = st["ALL"], st["IS"], st["OOS"]
    wr = f"{a['wr']:.1f}" if np.isfinite(a["wr"]) else "-"
    return (f"  {_wpad(label, w)}{a['setups']:>6}{fmt(a['exp'], 3):>8}{wr:>7}"
            f"{fmt(a['t'], 1):>6} |{i['setups']:>6}{fmt(i['exp'], 3):>8}{fmt(i['t'], 1):>6} |"
            f"{o['setups']:>7}{fmt(o['exp'], 3):>8}{fmt(o['t'], 1):>6}")


def _rpad(s, w):
    """한글 폭 2를 고려해 오른쪽 정렬."""
    import unicodedata
    n = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)
    return " " * max(1, w - n) + s


def _hdr(first, w=18):
    return (f"  {_wpad(first, w)}" + "".join(_rpad(x, k) for x, k in (("셋업", 6), ("기대R", 8), ("승률%", 7), ("t", 6)))
            + " |" + "".join(_rpad(x, k) for x, k in (("IS셋업", 6), ("IS기대", 8), ("IS t", 6)))
            + " |" + "".join(_rpad(x, k) for x, k in (("OOS셋업", 7), ("OOS기대", 8), ("OOS t", 6))))


def main_text(tr, opt):
    """요약 맨 위: [주판정 T_W1H4EXT] -> [위치 구간] -> [F_SLB 비교]."""
    L = []
    if tr is None or tr.empty or f"trend_{MAIN_TREND}" not in tr:
        return [f"[주판정 {MAIN_TREND}] 거래 없음", ""]
    closed = tr[tr["result"] != "open"]
    tfs = [x for x in MSS_TFS if x in set(closed["mss_tf"])]
    min_n, min_oos = opt.min_trades, max(10, opt.min_trades // 3)
    col = f"trend_{MAIN_TREND}"
    L.append(f"[주판정 {MAIN_TREND}] 주봉 구조와 H4 외부(스윙) 구조가 같은 방향일 때 그 방향 스윕만 (매수 = 둘 다 상승)")
    L.append("  사전 지정 정의: 석준님 설명 '주봉과 4H 방향 일치 우선, 4H는 외부 구조로 본다'를 결과를 보기 전에 옮긴 것.")
    L.append("  H4 외부 구조: 추세 = 마지막 외부 BOS 방향. 보호 저점 = 그 BOS를 만든 다리가 시작된 저점.")
    L.append("  H4 봉 종가가 보호 저점 아래로 마감할 때만 하락 전환(되돌림 안 내부 저점 깨짐 = 내부 CHoCH 는 추세 유지).")
    L.append("  T_W1H4 = 같은 조건을 내부 구조(가장 최근 확정 스윙 BOS)로 본 것, 비교용. 다른 추세 정의(아래 추세 정의별 표)는 참고용이다.")
    L.append("  결과를 보고 더 좋은 정의로 갈아타면 과최적화가 된다.")
    L.append("  MSS 시간봉: " + ", ".join(tfs) + ". 석준님 실제 진입은 1분봉이지만 데이터가 M5뿐이라 1분봉 진입은 시험하지 못했다.")
    L.append("  값 = 조합(N-진입-손절-목표)별 값의 평균, t = 평균 기대값 / 평균 표준오차, 셋업 = 겹치지 않게 센 셋업 수.")
    for tf in tfs:
        g = closed[closed["mss_tf"] == tf]
        L.append(f"  -- MSS {tf} --")
        L.append(_hdr("구분"))
        rows = [(f"{MAIN_TREND} 일치", g[g[col] == 1]), (f"{MAIN_TREND} 반대", g[g[col] == -1]),
                ("방향 엇갈림/없음", g[g[col] == 0]), ("추세없음(전체)", g)]
        if "trend_T_W1H4" in g:
            rows.append(("(비교)T_W1H4 내부 일치", g[g["trend_T_W1H4"] == 1]))
        for lab, gg in rows:
            L.append(_row(lab, _pstats(gg)))
        st = _pstats(rows[0][1])
        i, o = st["IS"], st["OOS"]
        if i["n"] < min_n or o["n"] < min_oos:
            verdict = f"표본 적음(조합당 IS {i['n']:.0f}건 / OOS {o['n']:.0f}건) -> 결론 못 냄"
        elif i["exp"] > 0 and o["exp"] > 0 and np.isfinite(o["t"]) and o["t"] >= 2:
            verdict = "IS·OOS 모두 + 이고 OOS t>=2 -> 전진 시험 후보(확정 아님)"
        elif i["exp"] > 0 and o["exp"] > 0:
            verdict = "IS·OOS 모두 + 지만 t<2 -> 우연과 구분 안 됨"
        else:
            verdict = "비용 후 엣지 확인 안 됨"
        L.append(f"  판정(MSS {tf}): {verdict}")
    L.append("")
    # ---- 위치
    L.append("[위치 구간] 스윕 극값이 H4 외부 딜링 레인지의 어디였나 (스윕 시작 시각까지 마감한 H4 봉만 사용)")
    L.append("  매수: 레인지 = H4 외부 구조의 보호 저점 SL ~ 그 뒤 최고가 SH (외부 추세가 상승일 때만 있음).")
    L.append("  깊이 = (SH - 극값)/(SH - SL). 0% = SH, 100% = SL(딱 닿음은 75~100%), 100%+ = SL 아래 꼬리 스윕,")
    L.append("  0%미만 = SH 위(새 고점 영역). 없음 = H4 외부 추세가 셋업과 반대이거나 판정 없음. 매도는 대칭.")
    L.append("  H4 OB = 보호 저점 봉부터 거꾸로 처음 만나는 음봉(SH로 가는 상승 직전 마지막 하락 H4봉). 내부 스윙 레인지 깊이는 CSV(depth_int).")
    for scope, g0 in _scopes(closed):
        for tf in tfs:
            g = g0[g0["mss_tf"] == tf]
            if g.empty:
                continue
            L.append(f"  -- {scope}, MSS {tf} --")
            L.append(_hdr("깊이 구간"))
            for b in DEPTH_BUCKETS:
                gb = g[g["depth_bucket"] == b]
                if not gb.empty:
                    L.append(_row(b, _pstats(gb)))
            sh = g[g["depth_bucket"].isin(["0%미만", "0~25%", "25~50%"])]
            dp = g[g["depth_bucket"].isin(["50~75%", "75~100%", "100%+"])]
            a, b_ = _pstats(dp), _pstats(sh)
            L.append(f"  사전 가설(깊을수록 좋다) 확인: 깊음(50%+) - 얕음(50% 미만) 기대값 차이  "
                     f"IS {fmt(a['IS']['exp'] - b_['IS']['exp'], 3)}, OOS {fmt(a['OOS']['exp'] - b_['OOS']['exp'], 3)}")
            L.append(_hdr("H4 OB 위치"))
            for b in OB_POS:
                gb = g[g["ob_pos"] == b]
                if not gb.empty:
                    L.append(_row(b, _pstats(gb)))
    L.append("  주의: 구간 x 범위 x 시간봉으로 칸이 많다. 칸마다 표본이 작아 가장 좋은 칸을 골라 규칙으로 삼으면 과최적화다.")
    L.append("  미리 정한 비교는 '깊음 vs 얕음' 한 줄뿐이다. IS와 OOS가 같은 방향이고 t가 2 이상일 때만 의미 있게 본다.")
    L.append("")
    # ---- F_SLB
    L.append("[F_SLB 비교] H4 봉이 보호 저점 SL(매수 기준) 아래로 몸통 마감하면: 체결 전이면 셋업 취소, 보유 중이면 그 봉 종가에 청산")
    L.append("  판정 구간 = 스윕 시작 이후 마감한 H4 봉. 레인지가 없는 셋업(외부 추세 반대·없음)은 규칙이 적용 안 돼 끔과 같다.")
    for scope, g0 in _scopes(closed):
        for tf in tfs:
            g = g0[g0["mss_tf"] == tf]
            if g.empty:
                continue
            gs = g[~g["slb_cancel"] & g["R_slb"].notna()]
            L.append(f"  -- {scope}, MSS {tf} --")
            L.append(_hdr("F_SLB"))
            L.append(_row("끔", _pstats(g)))
            L.append(_row("켬", _pstats(gs, "R_slb")))
            ns = g["setup_id"].nunique()
            nc = g[g["slb_cancel"]]["setup_id"].nunique()
            nx = gs[gs["result_slb"] == "slb"]
            L.append(f"  켬: 체결 전 취소 셋업 {nc}/{ns}, 보유 중 강제 청산 거래 비율 {100 * len(nx) / max(len(gs), 1):.1f}%")
    L.append("")
    return L


def _wpad(s, w):
    """한글(폭 2) 섞인 글자를 콘솔 폭 w 칸에 맞춘다."""
    import unicodedata
    n = sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in s)
    return s + " " * max(1, w - n)


def _avg_exp_t(g, period):
    """조합별 평균 R과 표준오차를 구해 조합 평균. t = 평균 기대값 / 평균 표준오차 (부호가 기대값과 같게)."""
    g = g[g["period"] == period]
    if g.empty:
        return 0.0, np.nan, np.nan
    a = g.groupby("combo")["R"].agg(["count", "mean", "std"])
    a["se"] = a["std"] / np.sqrt(a["count"])
    e, se = a["mean"].mean(), a["se"].mean()
    return a["count"].mean(), e, (e / se if se and np.isfinite(se) and se > 0 else np.nan)


def trend_text(tt, tr, trends, opt):
    """요약 맨 위: [T1] 추세 정의별 IS->OOS, [T2] 추세 정의 x 진입 x 목표 상위 5 (IS로 고르고 OOS 확인)."""
    L = []
    if tt.empty:
        L.append("[T1] 추세 조건: 거래 없음")
        return L
    g = tt[tt["symbol"] == "ALL"]
    min_n = opt.min_trades
    min_oos = max(10, min_n // 3)
    closed = tr[tr["result"] != "open"]
    L.append("[T1] 추세 정의별 결과 (기본 조건 = 추세와 같은 방향 스윕만), ALL 종목, 조합(N-진입-손절-목표) 평균")
    L.append("     셋업 = 실제 체결까지 간 셋업 수(겹치지 않게 셈). n/기대값 = 조합별 값의 평균, t = 평균 기대값 / 평균 표준오차.")
    L.append("     반대 = 추세 반대 방향 셋업(비교용). T_PDA 의 '반대'는 D1 구조 반대와 같다.")
    L.append(f"  {'trend':<8}{_wpad('desc', 30)}{'셋업 IS/OOS':>13}{'IS n':>7}{'IS exp':>8}{'IS t':>6}"
             f"{'OOS n':>7}{'OOS exp':>9}{'OOS t':>7}{'반대 IS/OOS exp':>17}  비고")
    warn = []
    for name in ["NONE"] + list(trends):
        w = g[(g["trend"] == name) & (g["align"] == "with")]
        if w.empty:
            L.append(f"  {name:<8}{_wpad(TREND_DESC[name], 30)} (거래 없음)")
            warn.append(name)
            continue
        cg = closed if name == "NONE" else closed[closed[f"trend_{name}"] == 1]
        s_is = cg[cg["period"] == "IS"]["setup_id"].nunique()
        s_oo = cg[cg["period"] == "OOS"]["setup_id"].nunique()
        ag = g[(g["trend"] == name) & (g["align"] == "against")]
        against = (f"{fmt(ag['IS_exp_R'].mean(), 3)}/{fmt(ag['OOS_exp_R'].mean(), 3)}" if not ag.empty else "-")
        note = ""
        if w["IS_n"].mean() < min_n or w["OOS_n"].mean() < min_oos:
            note = f"표본 적음! (IS {min_n}건/OOS {min_oos}건 미만)"
            warn.append(name)
        else:
            dis, doo = w["IS_exp_R"].mean(), w["OOS_exp_R"].mean()
            if np.isfinite(dis) and np.isfinite(doo) and dis > 0 and doo <= 0:
                note = "IS+ -> OOS 뒤집힘"
        n_i, e_i, t_i = _avg_exp_t(cg, "IS")
        n_o, e_o, t_o = _avg_exp_t(cg, "OOS")
        L.append(f"  {name:<8}{_wpad(TREND_DESC[name], 30)}{s_is:>6}/{s_oo:<6}{n_i:>7.0f}{fmt(e_i, 3):>8}"
                 f"{fmt(t_i, 1):>6}{n_o:>7.0f}{fmt(e_o, 3):>9}{fmt(t_o, 1):>7}{against:>17}  {note}")
    if warn:
        L.append(f"  경고: {', '.join(warn)} 은(는) 추세 일치 셋업이 너무 적다. 이 숫자로 결론 내리면 안 된다(우연 범위가 매우 넓음).")
    L.append("")
    cand = g[(g["trend"] != "NONE") & (g["align"] == "with") & (g["IS_n"] >= min_n) & (g["OOS_n"] >= min_oos)]
    M = len(cand)
    L.append(f"[T2] 추세 정의 x 진입 x 목표 상위 5 (IS 기대값으로 고름, IS {min_n}건+ / OOS {min_oos}건+, ALL 종목)")
    if M == 0:
        L.append("  조건을 채우는 조합 없음 (표본 부족)")
    else:
        zb = norm_ppf(1 - 0.05 / (2 * M))
        base = g[g["trend"] == "NONE"].set_index("combo")["OOS_exp_R"]
        L.append(f"  {'trend':<8}{'combo':<16}{'IS n':>6}{'IS exp':>8}{'IS t':>6}{'OOS n':>7}{'OOS exp':>9}{'OOS t':>7}"
                 f"{'추세없음OOS':>12}  t>{zb:.2f}?")
        for _, r in cand.sort_values("IS_exp_R", ascending=False).head(5).iterrows():
            L.append(f"  {r['trend']:<8}{r['combo']:<16}{int(r['IS_n']):>6}{fmt(r['IS_exp_R'], 3):>8}{fmt(r['IS_t'], 1):>6}"
                     f"{int(r['OOS_n']):>7}{fmt(r['OOS_exp_R'], 3):>9}{fmt(r['OOS_t'], 1):>7}"
                     f"{fmt(base.get(r['combo'], np.nan), 3):>12}  "
                     f"{'IS' if r['IS_t'] > zb else '-'}/{'OOS' if r['OOS_t'] > zb else '-'}")
        L.append("")
        L.append(f"  비교한 (추세 정의 x 조합) 수 = {M}개. Bonferroni 기준: IS t > {zb:.2f} 이어야 '우연 아닐 수도'.")
        L.append("  IS 1등이 OOS에서도 + 이고 OOS t 2 이상일 때만 전진 시험 후보. 추세 정의끼리 셋업이 많이 겹쳐 독립 시험이 아니다.")
        L.append("  추세 정의를 결과 보고 고르면 그것도 과최적화다. 석준님이 원래 생각한 정의를 먼저 정하고 그 줄을 보는 게 맞다.")
    L.append("")
    return L


def norm_ppf(p):
    """표준정규 역함수(이분법). scipy 없이 Bonferroni 기준 계산용."""
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if 0.5 * math.erfc(-mid / math.sqrt(2)) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def filter_text(ft, enabled, opt):
    """요약 맨 위 두 표: 필터 하나씩 IS->OOS 변화, 필터 조합 상위 5 (IS로 고르고 OOS 확인)."""
    L = []
    if ft.empty or not enabled:
        return L
    g = ft[ft["symbol"] == "ALL"]
    min_n = opt.min_trades
    L.append("[1] Filter one at a time / 필터 하나씩 켰을 때 IS -> OOS 변화 (ALL, 조합 평균 기대값 R)")
    L.append("    끔(none)과 켬을 같은 조합끼리 짝지어 평균. F2는 끔=지정가 A/B/C, 켬=확인 캔들 K (손절·목표·N 같은 것끼리).")
    L.append(f"  {'filter':<7}{'desc':<19}{'IS n/조합':>14}{'IS exp off->on':>22}{'OOS n/조합':>14}{'OOS exp off->on':>22}  same-dir")
    base = g[g["filters"] == "none"]
    for f in enabled:
        on = g[g["filters"] == f]
        if on.empty:
            L.append(f"  {f:<6}{FILTER_DESC[f]:<20} (거래 없음)")
            continue
        if f == "F2":
            key = "base"
            b = base.groupby("base")[["IS_n", "IS_exp_R", "OOS_n", "OOS_exp_R"]].mean()
            o2 = on.set_index("base")[["IS_n", "IS_exp_R", "OOS_n", "OOS_exp_R"]]
        else:
            key = "combo"
            b = base.set_index("combo")[["IS_n", "IS_exp_R", "OOS_n", "OOS_exp_R"]]
            o2 = on.set_index(key)[["IS_n", "IS_exp_R", "OOS_n", "OOS_exp_R"]]
        common = b.index.intersection(o2.index)
        b, o2 = b.loc[common], o2.loc[common]
        dis = o2["IS_exp_R"].mean() - b["IS_exp_R"].mean()
        doo = o2["OOS_exp_R"].mean() - b["OOS_exp_R"].mean()
        same = "-" if not (np.isfinite(dis) and np.isfinite(doo)) else ("YES" if dis * doo > 0 else "NO(뒤집힘)")
        L.append(f"  {f:<6}{FILTER_DESC[f]:<20}{b['IS_n'].mean():>6.0f}->{o2['IS_n'].mean():<6.0f}"
                 f"{fmt(b['IS_exp_R'].mean(), 3):>9}->{fmt(o2['IS_exp_R'].mean(), 3):<7}({fmt(dis, 3)})"
                 f"{b['OOS_n'].mean():>6.0f}->{o2['OOS_n'].mean():<6.0f}"
                 f"{fmt(b['OOS_exp_R'].mean(), 3):>9}->{fmt(o2['OOS_exp_R'].mean(), 3):<7}({fmt(doo, 3)})  {same}")
    L.append("")
    min_oos = max(10, min_n // 3)
    cand = g[(g["IS_n"] >= min_n) & (g["OOS_n"] >= min_oos)]
    M = len(cand)
    L.append(f"[2] Top 5 filter combos / 가장 좋은 필터 조합 상위 5 (IS 기대값으로 고름, IS {min_n}건+ / OOS {min_oos}건+)")
    if M == 0:
        L.append("  조건을 채우는 조합 없음")
    else:
        zb = norm_ppf(1 - 0.05 / (2 * M))
        L.append(f"  {'filters':<20}{'combo':<16}{'IS n':>6}{'IS exp':>8}{'IS t':>6}{'OOS n':>7}{'OOS exp':>9}{'OOS t':>7}  t>3?")
        for _, r in cand.sort_values("IS_exp_R", ascending=False).head(5).iterrows():
            L.append(f"  {r['filters']:<20}{r['combo']:<16}{int(r['IS_n']):>6}{fmt(r['IS_exp_R'], 3):>8}{fmt(r['IS_t'], 1):>6}"
                     f"{int(r['OOS_n']):>7}{fmt(r['OOS_exp_R'], 3):>9}{fmt(r['OOS_t'], 1):>7}  "
                     f"{'IS' if r['IS_t'] > 3 else '-'}/{'OOS' if r['OOS_t'] > 3 else '-'}")
        L.append("")
        L.append(f"  경고: 이번에 비교한 (필터 조합 x 기본 조합) 수 = {M}개. 많이 비교할수록 '운으로 1등'이 꼭 나온다.")
        L.append(f"  Bonferroni 기준(대략): t > 3 이어야 '우연 아닐 수도' 수준. 정확히 계산하면 {M}개 비교에서 t > {zb:.2f}.")
        L.append("  IS 1등이 OOS에서 + 이고 OOS t도 2 이상일 때만 다음 단계(전진 시험)로 넘길 후보로 본다.")
        L.append("  같은 셋업이 여러 조합에 겹쳐 들어가므로 조합끼리 독립이 아니다(실제 '독립 시험 수'는 이보다 적다).")
    L.append("")
    return L


def fmt(x, nd=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "-"
    return f"{x:+.{nd}f}" if isinstance(x, float) else str(x)


def write_text(path, summ, funnels, meta, opt, ft=None, enabled=(), tt=None, tr=None, trends=()):
    L = []
    L.append("석준님 CRT 백테스트 요약 (정보 제공용, 매매 결정은 석준님)")
    L.append("=" * 70)
    for k, v in meta.items():
        L.append(f"{k}: {v}")
    L.append("")
    if trends:
        L.append("추세 정의: " + ", ".join(f"{k}={TREND_DESC[k]}" for k in trends))
        L.append("")
        L += main_text(tr, opt)
        L += trend_text(tt if tt is not None else pd.DataFrame(), tr, list(trends), opt)
    if enabled:
        L.append("필터: " + ", ".join(f"{f}={FILTER_DESC[f]}" for f in enabled))
        L.append("")
        L += filter_text(ft, list(enabled), opt)
    L.append("용어: R = 손절폭 1개 크기. 기대값(R) = 한 번 거래할 때 평균으로 얻는 R. +0.20이면 1% 위험 거래마다 평균 +0.2%.")
    L.append("      최대 낙폭(R) = 누적 R이 고점에서 가장 많이 빠진 크기. IS = 앞 기간(규칙 고르는 데 써도 되는 구간), OOS = 뒤 기간(확인용).")
    L.append("변형: 진입 " + ", ".join(f"{k}={v}" for k, v in ENTRY_DESC.items()))
    L.append("      손절 " + ", ".join(f"{k}={v}" for k, v in STOP_DESC.items()))
    L.append("      목표 " + ", ".join(f"{k}={v}" for k, v in TARGET_DESC.items()) + ", N = MSS 스윙 봉 수")
    L.append("")
    L.append("[셋업 깔때기] (4H 봉 -> 스윕 -> C2 마감 조건 -> MSS 확정 -> 주문 -> 체결)")
    fdf = pd.DataFrame(funnels)
    ecols = [c[5:] for c in fdf.columns if c.startswith("fill_")]
    for _, f in fdf.iterrows():
        L.append(f"  {f['symbol']:<8} {f.get('mss_tf', 'M15')} N{f['swing']}: C2 {f['c2']}, 아시아제외 {f['asia_skip']}, 스윕 {f['sweep']}, "
                 f"C2마감OK {f['c2_close_ok']}, MSS확정 {f['mss_confirm']}, OB없음 {f['no_ob']}, "
                 f"주문전목표도달 {f['target_before_order']}, 주문 {f['setups']} | 체결 " +
                 " ".join(f"{e} {f['fill_' + e]}" for e in ecols) +
                 (" | 추세일치 주문 " + " ".join(f"{k} {int(f['aligned_' + k])}" for k in trends)
                  if trends and 'aligned_T_D1S' in f else "") +
                 (" | F_SLB 체결전취소 " + " ".join(f"{e} {f['slb_cancel_' + e]}" for e in ecols)
                  if trends and 'slb_cancel_K' in f else ""))
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

    L.append("아래 표는 필터·추세 조건 없이(모든 거래) 본 결과다." +
             (" 추세 모드라 매수·매도 스윕을 각각 따로 찾은 셋업이다." if trends else ""))
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
            L.append("[ALL] 축별 평균 기대값(R): 다른 변형을 모두 평균낸 값, IS / OOS")
            for axis, desc in (("swing", None), ("entry_v", ENTRY_DESC), ("stop_v", STOP_DESC), ("target_v", TARGET_DESC)):
                for v, gv in g.groupby(axis):
                    name = desc[v] if desc else f"N={v}"
                    L.append(f"  {axis:<9}{str(v):<4}{name:<26} IS {fmt(gv['IS_exp_R'].mean(), 3)}  OOS {fmt(gv['OOS_exp_R'].mean(), 3)}")
            L.append("")
            ycols = [c for c in summ.columns if c.startswith("exp_") and c[4:].isdigit()]
            best = g_is.iloc[0]
            L.append(f"[ALL] IS 1위 {best['combo']} 연도별 기대값(R): " +
                     ", ".join(f"{c[4:]} {fmt(best[c], 2)}({int(best['n_' + c[4:]])})" for c in ycols))
            L.append(f"[ALL] IS 1위 {best['combo']} 체결 시각 시간대별 기대값(R, 뉴욕 기준): " +
                     ", ".join(f"{s} {fmt(best['exp_' + s], 2)}({int(best['n_' + s])})" for s in SESSIONS))
            L.append(f"[ALL] IS 1위 {best['combo']} C2(셋업 4H봉) 시간대별 기대값(R): " +
                     ", ".join(f"{s} {fmt(best['c2exp_' + s], 2)}({int(best['c2n_' + s])})" for s in SESSIONS))
            L.append("      (C2 마감 필수면 체결은 C2 다음 4H봉: C2 런던(뉴욕01·05시) -> 체결 05~13시, C2 뉴욕 13시 -> 체결 17~21시)")
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
    p = argparse.ArgumentParser(description="CRT(4H)+MSS(M15)+OB backtest with optional filters (read-only)")
    p.add_argument("--data-dir", help="folder with {SYMBOL}_M5.csv")
    p.add_argument("--out", help="output folder (created if missing)")
    p.add_argument("--symbols", default="", help="comma list. empty = all *_M5.csv in folder")
    p.add_argument("--swing", default="5,3", help="MSS swing bars list (default 5,3)")
    p.add_argument("--entries", default="A,B,C", help="limit entries to test (default A,B,C)")
    p.add_argument("--stops", default="S1,S2,S3", help="stops to test, e.g. S2 (default S1,S2,S3)")
    p.add_argument("--targets", default="T1,T2,T3,T4", help="targets to test, e.g. T2,T3 (default all)")
    p.add_argument("--expiry-bars", type=int, default=16, help="order/watch life in M15 bars (default 16=4h)")
    p.add_argument("--spread", type=float, default=1.0, help="default spread pips (default 1.0)")
    p.add_argument("--spread-map", default="", help="per-symbol spread pips, e.g. EURUSD=0.8,GBPJPY=2.5")
    p.add_argument("--pip-map", default="", help="per-symbol pip size, e.g. XAUUSD=0.1,US30=1")
    p.add_argument("--sl-buffer", type=float, default=1.0, help="stop buffer pips (default 1)")
    p.add_argument("--eq-tol", type=float, default=2.0, help="equal highs/lows tolerance pips (default 2)")
    p.add_argument("--min-risk-pips", type=float, default=0.0, help="skip trade if stop distance below this")
    p.add_argument("--c2-close", choices=["required", "ignore"], default="required",
                   help="required: C2 must close inside range, order after C2 close (default). ignore: order right after MSS confirm (EA style)")
    p.add_argument("--include-asia", action="store_true", help="also use Asia C2 (4H bars starting NY 17h, 21h)")
    p.add_argument("--block-asia-fill", action="store_true", help="drop fills in Asia session (NY 19-02), like EA")
    p.add_argument("--max-hold-bars", type=int, default=0, help="max hold in M5 bars, 0 = no limit")
    p.add_argument("--t4-lookback", type=int, default=120, help="H4 bars to look back for T4 / F5 swings")
    p.add_argument("--oos-start", default="2024-01-01", help="OOS start date (server time)")
    p.add_argument("--start", default="", help="use data from this date (e.g. 2019-01-01)")
    p.add_argument("--min-trades", type=int, default=30, help="min trades for summary tables")
    # 필터 (기본 꺼짐)
    p.add_argument("--f1h4", action="store_true", help="F1H: trade with H4 structure (HH+HL for buys)")
    p.add_argument("--f1d1", action="store_true", help="F1D: buys only if last D1 close > D1 EMA")
    p.add_argument("--d1-ema", type=int, default=20, help="EMA length for F1D (default 20)")
    p.add_argument("--f2", action="store_true", help="F2: confirm-candle market entry (entry K) in addition to limits")
    p.add_argument("--f2-tf", choices=["M15", "M5"], default="M15", help="F2 confirm candle timeframe")
    p.add_argument("--f3", action="store_true", help="F3: cancel if M15 body closes beyond OB before fill")
    p.add_argument("--f4", action="store_true", help="F4: fills only in NY-hour windows (--f4-windows)")
    p.add_argument("--f4-windows", default="2-5,7-11", help="F4 NY-hour windows (default 2-5,7-11)")
    p.add_argument("--f5", action="store_true", help="F5: sweep must take fresh PDH/PDL or H4 equal highs/lows")
    p.add_argument("--f5-h4", choices=["cluster", "swing"], default="cluster", help="F5 H4 level type (default cluster)")
    p.add_argument("--all-filters", action="store_true", help="turn on F1H,F1D,F2,F3,F4,F5")
    p.add_argument("--trend", default="", help="trend base conditions, comma list of T_W1H4EXT,T_W1H4,T_H4EXT,T_D1S,T_W1S,"
                                               "T_D1H4,T_EMA,T_PDA or ALL (T_W1H4EXT main verdict and T_W1H4 always added)")
    p.add_argument("--mss-tf", default="M15", help="MSS/OB timeframe list: M15, M5 or M15,M5 (no M1 data)")
    p.add_argument("--trend-swing", type=int, default=2, help="swing bars each side for D1/W1/H4 structure (default 2)")
    p.add_argument("--trend-ema", type=int, default=50, help="D1 EMA length for T_EMA (default 50)")
    p.add_argument("--trend-slope", type=int, default=5, help="T_EMA slope lookback in D1 bars (default 5)")
    p.add_argument("--selftest", action="store_true", help="run self tests on synthetic data only")
    return p


def default_opts(**kw):
    o = build_parser().parse_args([])
    for k, v in kw.items():
        setattr(o, k, v)
    return o


def run_all(opt, files=None, quiet=False):
    t0 = _time.time()
    if getattr(opt, "all_filters", False):
        opt.f1h4 = opt.f1d1 = opt.f2 = opt.f3 = opt.f4 = opt.f5 = True
    opt.swing = [int(x) for x in str(opt.swing).split(",") if str(x).strip()] if not isinstance(opt.swing, list) else opt.swing
    enabled = enabled_filters(opt)
    trends = trend_list(opt)
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
            print(f"! missing files: {missing}")
    if not files:
        print("! no files to run. check --data-dir and --symbols")
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
        print(f"  pip = {pip}, spread = {sp} pips")
        tr, fun, rng = run_symbol(sym, df, opt, pip, sp)
        meta_rng[sym] = rng
        all_tr += tr
        all_fun += fun
        print(f"  setups {[f['setups'] for f in fun]} (N={opt.swing}), trade rows {len(tr):,}, {(_time.time() - t0):.0f}s")
    tr = pd.DataFrame(all_tr)
    tfs = mss_tf_list(opt)
    tag = (f"c2{opt.c2_close}" + (("_" + "".join(f.lower() for f in enabled)) if enabled else "") + ("_trend" if trends else "")
           + ("" if tfs == ["M15"] else "_" + "".join(x.lower() for x in tfs)))
    if tr.empty:
        print("! no trades.")
        pd.DataFrame(all_fun).to_csv(os.path.join(opt.out, f"funnel_{tag}.csv"), index=False, encoding="utf-8-sig")
        return dict(trades=tr, summary=pd.DataFrame(), funnels=all_fun, filters=pd.DataFrame(), trends=pd.DataFrame())
    # 한국시간 열
    for col in ("fill_server", "exit_server"):
        tr[col.replace("_server", "_kst")] = server_to_kst(pd.to_datetime(tr[col])).strftime("%Y-%m-%d %H:%M")
    tr["period"] = np.where(tr["t_fill_ns"] < pd.Timestamp(opt.oos_start).value, "IS", "OOS")
    summ = summarize(tr, opt.oos_start)
    ft = filter_table(tr, enabled) if enabled else pd.DataFrame()
    tt = trend_table(tr, trends) if trends else pd.DataFrame()
    rng_txt = "; ".join(f"{s} {t2s(a)}~{t2s(b)}" for s, (a, b) in meta_rng.items())
    lo, hi = min(a for a, _ in meta_rng.values()), max(b for _, b in meta_rng.values())
    meta = {"데이터": f"MT5 M5 CSV ({opt.data_dir or '메모리'})",
            "기간(서버시간)": rng_txt,
            "기간(한국시간)": f"{server_to_kst([pd.Timestamp(lo)])[0]:%Y-%m-%d %H:%M} ~ {server_to_kst([pd.Timestamp(hi)])[0]:%Y-%m-%d %H:%M} KST",
            "시간 기준": "표의 시각은 MT5 서버시간(뉴욕+7). 거래 목록에 한국시간(KST) 열 있음",
            "IS / OOS": f"IS = {opt.oos_start} 이전 체결, OOS = 이후",
            "설정": f"C2마감={opt.c2_close}, 아시아C2(뉴욕17·21시 시작 4H) {'포함' if opt.include_asia else '제외'}, 유효 {opt.expiry_bars}봉(M15), "
                   f"스프레드 {opt.spread}핍(+맵 {opt.spread_map or '없음'}), 손절버퍼 {opt.sl_buffer}핍, 같은높이 {opt.eq_tol}핍, 스윙 N={opt.swing}, "
                   f"진입 {opt.entries}{'+K' if (opt.f2 or trends) else ''}, 손절 {opt.stops}, 목표 {opt.targets}",
            "추세 설정": (f"--trend {','.join(trends)}, 스윙 앞뒤 {opt.trend_swing}봉, EMA{opt.trend_ema}, 기울기 {opt.trend_slope}일, "
                       "판정 시각 = 스윕 봉 시작(그때까지 마감한 봉·확정 스윙만). 주판정 = T_W1H4EXT(사전 지정, H4 외부 구조)") if trends else "꺼짐",
            "MSS 시간봉": f"{','.join(tfs)} (석준님 실제 진입은 1분봉. 데이터가 M5뿐이라 1분봉 진입은 시험 못 함)",
            "필터 설정": f"켠 필터 {enabled or '없음'}, D1 EMA {opt.d1_ema}, F2 {opt.f2_tf}, F4 뉴욕 {opt.f4_windows}시, F5 H4={opt.f5_h4}",
            "만든 시각": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M") + " (실행 PC 시각)"}
    out_cols = ["symbol", "combo", "swing", "entry_v", "stop_v", "target_v", "dir", "period", "session", "c2_session",
                "c1_server", "c2_server", "crh", "crl", "sweep_ext", "mss", "ob_h", "ob_l", "mss_confirm_server", "order_server",
                "fill_server", "fill_kst", "entry", "sl", "tp", "risk_pips", "rr_planned",
                "exit_server", "exit_kst", "exit_price", "result", "R", "s3_fallback", "t4_fallback",
                "h4_trend", "d1_bias", "f1h", "f1d", "f3", "f4", "f5", "f5_kind", "setup_id", "mss_tf",
                "rng_origin", "rng_far", "depth", "depth_bucket", "h4ob_l", "h4ob_h", "ob_pos", "depth_int", "depth_bucket_int",
                "slb_break_server", "slb_cancel", "result_slb", "R_slb", "exit_slb_server"]
    out_cols += [f"trend_{k}" for k in TRENDS if f"trend_{k}" in tr.columns]
    tr[out_cols].to_csv(os.path.join(opt.out, f"trades_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    summ.to_csv(os.path.join(opt.out, f"summary_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    if not tt.empty:
        tt.to_csv(os.path.join(opt.out, f"trends_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
        lt = location_table(tr)
        if not lt.empty:
            lt.to_csv(os.path.join(opt.out, f"location_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    if not ft.empty:
        ft.to_csv(os.path.join(opt.out, f"filters_{tag}.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    pd.DataFrame(all_fun).to_csv(os.path.join(opt.out, f"funnel_{tag}.csv"), index=False, encoding="utf-8-sig")
    txt = write_text(os.path.join(opt.out, f"summary_{tag}.txt"), summ, all_fun, meta, opt, ft, enabled, tt, tr, trends)
    if not quiet:
        print("\n" + txt)
    print(f"\ndone {(_time.time() - t0):.0f}s. output folder: {opt.out}  (summary_{tag}.txt is UTF-8)")
    return dict(trades=tr, summary=summ, funnels=all_fun, filters=ft, trends=tt)


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


def scenario_rows(c3=None):
    pre = [(1, 2, 0, 1)] * 32                      # 서버 00:00~07:45 횡보
    c1 = [(1, 2, -5, 0), (0, 8, 0, 8), (8, 16, 8, 16), (16, 24, 16, 24), (24, 30, 24, 28),   # CRL -5, CRH 30
          (28, 28, 22, 22), (22, 22, 16, 16), (16, 16, 12, 12), (12, 12, 10, 10), (10, 13, 10, 13),
          (13, 15, 13, 15), (15, 18, 15, 18), (18, 20, 17, 19),                               # 11:00 스윙 고점 20 = MSS
          (19, 19, 15, 15), (15, 15, 12, 12), (12, 12, 9, 9)]
    c2 = [(9, 9, 5, 5), (5, 5, 1, 1), (1, 1, -3, -3), (-3, -3, -6, -6),                    # 12:45 스윕
          (-6, -5, -8, -7), (-7, -1, -7, -1), (-1, 5, -1, 5),                               # 13:00 극값 -8
          (5, 7, 2, 3),                                                                      # 13:45 OB (음봉 7~2, 시가 5)
          (3, 23, 3, 22)] + [(22, 24, 21, 23)] * 7                                           # 14:00 MSS 확정, C2 마감 23
    if c3 is None:
        c3 = [(23, 23, 15, 15), (15, 15, 6, 8), (8, 18, 8, 18), (18, 31, 18, 31)]           # 16:15 OB 고가 7 체결, 16:45 CRH 30
    post = [(31, 32, 30, 31)] * (4 * 24 * 2)
    return pre + c1 + c2 + c3 + post


def _random_walk(seed, start, end, pip):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="5min")
    idx = idx[idx.dayofweek < 5]
    m = len(idx)
    steps = rng.normal(0, 2.5 * pip / np.sqrt(5), size=(m, 5)).cumsum(axis=1)   # 1분 5걸음
    st = 1.1 + np.r_[0, steps[:-1, -1]].cumsum()
    path = st[:, None] + steps
    return pd.DataFrame({"o": st, "c": path[:, -1], "h": np.maximum(path.max(axis=1), st),
                         "l": np.minimum(path.min(axis=1), st)}, index=idx)[["o", "h", "l", "c"]]


def _check(ok, cond, msg):
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    return ok and bool(cond)


def selftest():
    import tempfile
    ok = True
    pip = 0.0001
    S = lambda s: pd.Timestamp(s).value   # noqa: E731  (서버시간 문자열 -> ns)
    out_dir = tempfile.mkdtemp(prefix="crt_selftest_")
    print("=== Test 1: equal-lows stop (2026-10-27 GBPUSD example) ===")
    s3 = equal_level_stop(1, [1.33115, 1.33135, 1.33144], 1.33191, 2 * pip, 1 * pip)
    ok = _check(ok, abs(s3 - 1.33105) < 1e-9, f"lows 1.33115/1.33135/1.33144, entry 1.33191 -> stop {s3:.5f} (expect 1.33105)")

    print("=== Test 2: hand scenario (sweep -> MSS -> OB pullback -> CRH), filters off ===")
    df = _expand_m15(scenario_rows(), "2024-01-08 00:00", 1.10000, pip)
    opt = default_opts(oos_start="2024-06-01", min_trades=1, out=out_dir)
    res = run_all(opt, files={"EURUSD": df}, quiet=True)
    tr = res["trades"]
    for n in (5, 3):
        f = [x for x in res["funnels"] if x["swing"] == n][0]
        ok = _check(ok, f["setups"] == 1 and f["fill_A"] == 1 and f["fill_B"] == 0 and f["fill_C"] == 1,
                    f"N={n}: sweep {f['sweep']}, confirm {f['mss_confirm']}, setups {f['setups']}, fills A/B/C {f['fill_A']}/{f['fill_B']}/{f['fill_C']}")
    t = tr[tr["combo"] == "N5-A-S2-T1"]
    exp_R = (30 - 7) / (7 + 9)
    ok = _check(ok, len(t) == 1 and t["result"].iloc[0] == "win" and abs(t["R"].iloc[0] - exp_R) < 1e-9, f"N5-A-S2-T1 win R {exp_R:.4f}")
    ok = _check(ok, abs(t["mss"].iloc[0] - 1.1020) < 1e-9 and abs(t["entry"].iloc[0] - 1.1007) < 1e-9, "MSS 1.1020, entry 1.1007")
    t2 = tr[tr["combo"] == "N5-A-S1-T1"]
    ok = _check(ok, len(t2) == 1 and abs(t2["R"].iloc[0] - 23 / 6) < 1e-9, "N5-A-S1-T1 R 23/6")
    t3 = tr[tr["combo"] == "N5-A-S2-T2"]
    ok = _check(ok, len(t3) == 1 and t3["result"].iloc[0] == "open", "N5-A-S2-T2 still open")
    ok = _check(ok, set(tr["dir"]) == {"BUY"}, "only BUY")
    # 16:15 M15봉의 둘째 M5(서버 16:20) = 뉴욕 09:20(EST) = 한국 23:20
    ok = _check(ok, t["fill_kst"].iloc[0] == "2024-01-08 23:20", "fill KST 2024-01-08 23:20")
    ok = _check(ok, t["c2_session"].iloc[0] == "런던" and t["session"].iloc[0] == "뉴욕",
                "C2 (NY 05h) labelled London, fill (NY 09:20) labelled New York")

    print("=== Test 3: session bug fix (Asia C2 = 4H bars starting NY 17h/21h) ===")
    hours = {h: c2_session(S("2024-01-08 00:00") + ((h + 7) % 24) * NS_H) for h in (17, 21, 1, 5, 9, 13)}
    ok = _check(ok, hours == {17: "아시아", 21: "아시아", 1: "런던", 5: "런던", 9: "뉴욕", 13: "뉴욕"},
                f"C2 session by NY start hour: {hours}")
    rw = _random_walk(7, "2019-01-01", "2023-12-31 23:55", pip)
    r0 = run_all(default_opts(oos_start="2022-01-01", out=out_dir), files={"RW": rw}, quiet=True)["trades"]
    c2h = sorted(((pd.to_datetime(r0["c2_server"]).dt.hour - 7) % 24).unique().tolist())
    ok = _check(ok, c2h == [1, 5, 9, 13], f"random walk: C2 NY start hours used = {c2h} (expect [1, 5, 9, 13])")
    lon = int((r0["session"] == "런던").sum())
    ok = _check(ok, lon > 0, f"random walk: London-session fills now {lon} rows (was 0 before fix)")

    print("=== Test 4: F1H H4 structure ===")
    k = np.arange(30)
    zig = np.tile([0.0, 2.0, 4.0, 2.0], 8)[:30]
    T4 = S("2024-01-01") + k * 4 * NS_H
    for drift, want in ((0.5, 1), (-0.5, -1)):
        hh = zig + drift * k + 10
        ll = hh - 1
        sw = h4_swings(hh, ll, T4)
        tr_ = h4_trend_at(sw, hh, ll, T4[-1] + 4 * NS_H)
        ok = _check(ok, tr_ == want, f"drift {drift:+}: trend {tr_} (expect {want}); buy kept={tr_ == 1}")
    sw = h4_swings(zig + 10, zig + 9, T4)
    ok = _check(ok, h4_trend_at(sw, zig + 10, zig + 9, T4[-1]) == 0, "flat zigzag -> 0 (buy and sell both filtered)")
    ok = _check(ok, h4_trend_at(sw, zig + 10, zig + 9, T4[3]) == 0, "not enough confirmed swings yet -> 0")

    print("=== Test 5: F1D D1 close vs EMA20 ===")
    days = S("2024-01-01") + np.arange(40) * 24 * NS_H
    for closes, want, name in ((np.linspace(1.0, 1.4, 40), 1, "rising"), (np.linspace(1.4, 1.0, 40), -1, "falling")):
        d1 = dict(t=days, c=closes, ema=pd.Series(closes).ewm(span=20, adjust=False).mean().values, span=20)
        b = d1_bias_at(d1, days[-1] + 3 * NS_H)
        ok = _check(ok, b == want, f"{name} closes -> bias {b} (expect {want})")
        ok = _check(ok, d1_bias_at(d1, days[10]) == 0, f"{name}: only 10 days of history -> 0")
    days41 = S("2024-01-01") + np.arange(41) * 24 * NS_H
    cl = np.r_[np.linspace(1.0, 1.4, 39), 1.2, 1.2]   # 39번째 날 급락: 그 날 안에서는 아직 +, 다음 날부터 -
    d1 = dict(t=days41, c=cl, ema=pd.Series(cl).ewm(span=20, adjust=False).mean().values, span=20)
    a1, a2 = d1_bias_at(d1, days41[39] + NS_H), d1_bias_at(d1, days41[40] + NS_H)
    ok = _check(ok, a1 == 1 and a2 == -1, f"uses previous completed day only (no look-ahead): during drop day {a1}, next day {a2}")

    print("=== Test 6: F2 confirm candle ===")
    #          o   h   l   c          OB 끝(edge) 10, 목표 30
    bars = np.array([[20, 22, 15, 16],   # 0 안 닿음
                     [16, 17, 9, 12],    # 1 닿음, 음봉 -> 아님
                     [12, 12, 9, 9.5],   # 2 음봉
                     [9.5, 9.9, 9, 9.8], # 3 양봉이지만 OB 끝 아래 마감 -> 아님
                     [9.8, 14, 9.5, 13], # 4 양봉, 10 위 마감 -> 진입
                     [13, 31, 13, 30]], float)
    o_, h_, l_, c_ = bars.T
    r = confirm_entry(1, o_, h_, l_, c_, 0, 6, 10.0, 30.0)
    ok = _check(ok, r == ("entry", 4), f"touch then bullish close above OB -> {r} (expect entry at bar 4)")
    r = confirm_entry(1, o_, h_, l_, c_, 0, 4, 10.0, 30.0)
    ok = _check(ok, r == ("expired", -1), f"window ends before confirm -> {r}")
    r = confirm_entry(1, o_, h_, l_, c_, 0, 6, 10.0, 21.0)
    ok = _check(ok, r == ("cancel_tp", 0), f"target reached before touch -> {r}")
    r = confirm_entry(1, np.array([12.0]), np.array([14.0]), np.array([9.0]), np.array([13.0]), 0, 1, 10.0, 30.0)
    ok = _check(ok, r == ("entry", 0), "touching bar itself can be the confirm candle")
    opt = default_opts(oos_start="2024-06-01", min_trades=1, out=out_dir, f2=True)
    tr = run_all(opt, files={"EURUSD": df}, quiet=True)["trades"]
    tk = tr[tr["combo"] == "N5-K-S2-T1"]
    expk = (30 - 19) / (19 + 9)    # 16:30 양봉 종가 18 + 스프레드 1 = 19, 손절 -9, 목표 30
    ok = _check(ok, len(tk) == 1 and tk["result"].iloc[0] == "win" and abs(tk["R"].iloc[0] - expk) < 1e-9
                and tk["fill_server"].iloc[0] == "2024-01-08 16:45",
                f"scenario K entry 16:45 at 1.1019, R {expk:.4f}")

    print("=== Test 7: F3 OB body-close invalidation ===")
    C_ = np.array([5.0, 3.0, 1.5, 4.0])
    T_ = S("2024-01-08") + np.arange(4) * 15 * NS_MIN
    ok = _check(ok, first_invalid_close(1, C_, T_, 0, 4, 2.0, 15 * NS_MIN) == T_[2] + 15 * NS_MIN,
                "first close below OB low -> that bar's close time")
    ok = _check(ok, first_invalid_close(1, C_, T_, 3, 4, 2.0, 15 * NS_MIN) == NS_INF, "no close below -> none")
    ok = _check(ok, bool(tk["f3"].iloc[0]), "base scenario: K trade valid (f3 True)")
    c3_bad = [(23, 23, 15, 15), (15, 15, 0, 1), (1, 18, 1, 18), (18, 31, 18, 31)]   # 16:15 봉이 OB 저가 2 아래 1로 마감
    dfb = _expand_m15(scenario_rows(c3_bad), "2024-01-08 00:00", 1.10000, pip)
    trb = run_all(opt, files={"EURUSD": dfb}, quiet=True)["trades"]
    kb = trb[trb["combo"] == "N5-K-S2-T1"]
    ab = trb[trb["combo"] == "N5-A-S2-T1"]
    ok = _check(ok, len(kb) == 1 and not bool(kb["f3"].iloc[0]),
                "close below OB before confirm candle -> K trade flagged invalid (F3 removes it)")
    ok = _check(ok, len(ab) == 1 and bool(ab["f3"].iloc[0]),
                "limit A filled at 16:20, invalid close came later (16:30) -> A kept")
    ftb = filter_table(trb, ["F2", "F3"])
    ok = _check(ok, not ((ftb["filters"] == "F2+F3") & (ftb["combo"] == "N5-K-S2-T1")).any()
                and ((ftb["filters"] == "F2") & (ftb["combo"] == "N5-K-S2-T1")).any(),
                "filter table: K trade present with F2, gone with F2+F3")

    print("=== Test 8: F4 time window ===")
    w = parse_windows("2-5,7-11")
    cases = {"2024-01-08 10:00": True, "2024-01-08 13:00": False, "2024-01-08 16:59": True,
             "2024-01-08 18:00": False, "2024-01-08 08:59": False, "2024-01-08 09:00": True}
    got = {k: f4_ok(S(k), w) for k in cases}
    ok = _check(ok, got == cases, "server 10:00(NY03) in, 13:00(NY06) out, 16:59(NY09:59) in, 18:00(NY11) out, 08:59(NY01:59) out")
    ok = _check(ok, bool(t["session"].iloc[0] == "뉴욕") and bool(tk["f4"].iloc[0]), "scenario fill NY 09:45 -> F4 kept")

    print("=== Test 9: F5 HTF liquidity sweep ===")
    T15 = S("2024-01-08") + np.arange(192) * 15 * NS_MIN    # 이틀
    Lw = np.full(192, 102.0)
    Hw = np.full(192, 103.0)
    Lw[10] = 100.0                                         # 첫날 저가 100 = PDL
    d1 = dict(t=np.array([S("2024-01-08"), S("2024-01-09")]), l=np.array([100.0, 99.0]), h=np.array([103.0, 103.0]))
    T4 = S("2024-01-08") + np.arange(12) * 4 * NS_H
    H4h = np.full(12, 103.0)
    H4l = np.full(12, 102.0)
    H4l[2], H4l[3] = 101.0, 101.015                        # 4H 같은 높이 저점 두 개 (1.5핍 차이)
    sw = dict(sl_idx=np.array([2, 3]), sl_conf=T4[[2, 3]] + 3 * 4 * NS_H, sh_idx=np.array([], int), sh_conf=np.array([], np.int64))
    sj, i4 = 96 + 20, 7                                    # 둘째 날 05:00 스윕
    a = htf_swept(1, 99.5, sj, i4, T15, Hw, Lw, d1, sw, T4, H4h, H4l, 0.02, 120)
    ok = _check(ok, a == (True, "PDL+H4eq"), f"fresh PDL and H4 equal lows both taken -> {a}")
    a = htf_swept(1, 100.5, sj, i4, T15, Hw, Lw, d1, sw, T4, H4h, H4l, 0.02, 120)
    ok = _check(ok, a == (True, "H4eq"), f"above PDL but below H4 equal lows -> {a}")
    a = htf_swept(1, 101.5, sj, i4, T15, Hw, Lw, d1, sw, T4, H4h, H4l, 0.02, 120)
    ok = _check(ok, a == (False, ""), f"sweep did not reach any HTF level -> {a}")
    L2 = Lw.copy()
    L2[96 + 5] = 99.8                                      # 같은 날 스윕 전에 이미 깨짐
    a = htf_swept(1, 99.5, sj, i4, T15, Hw, L2, d1, sw, T4, H4h, H4l, 0.02, 120)
    ok = _check(ok, a == (False, ""), f"levels already taken earlier -> not fresh -> {a}")
    sw1 = dict(sw, sl_idx=np.array([2]), sl_conf=sw["sl_conf"][:1])
    a = htf_swept(1, 100.5, sj, i4, T15, Hw, Lw, d1, sw1, T4, H4h, H4l, 0.02, 120)
    b = htf_swept(1, 100.5, sj, i4, T15, Hw, Lw, d1, sw1, T4, H4h, H4l, 0.02, 120, mode="swing")
    ok = _check(ok, a == (False, "") and b == (True, "H4swing"), f"single H4 low: cluster mode {a}, swing mode {b}")
    sc = tr[tr["combo"] == "N5-A-S2-T1"]
    ok = _check(ok, not bool(sc["f1h"].iloc[0]) and not bool(sc["f1d"].iloc[0]) and not bool(sc["f5"].iloc[0]),
                "scenario has no HTF history -> F1H/F1D/F5 all filter it out")

    print("=== Test 10: random walk with filters -> expectancy near 0 ===")
    rw2 = _random_walk(11, "2016-01-01", "2023-12-31 23:55", pip)
    opt = default_opts(oos_start="2021-01-01", min_trades=30, out=out_dir, spread=0.0, all_filters=True,
                       stops="S1,S2", targets="T1,T2,T3")
    res = run_all(opt, files={"RW": rw2}, quiet=True)
    ft = res["filters"]
    cl = res["trades"][res["trades"]["result"] != "open"]
    for sub in ["none"] + FILTERS + ["F1H+F1D+F2+F3+F4+F5"]:
        m = np.ones(len(cl), bool)
        parts = [] if sub == "none" else sub.split("+")
        isk = (cl["entry_v"] == "K").values
        m &= isk if "F2" in parts else ~isk
        for f in parts:
            if f != "F2":
                m &= cl[f.lower()].values.astype(bool)
        g = cl[m]
        if len(g) == 0:
            print(f"  {sub:<22} no trades")
            continue
        # 같은 셋업이 여러 조합에 겹치므로 표준오차는 '체결 수'(셋업 단위)로 잡는다
        nfill = g.groupby(["fill_server", "entry_v", "swing"]).ngroups
        se = g["R"].std(ddof=1) / np.sqrt(max(nfill, 2)) if len(g) > 1 else np.inf
        good = abs(g["R"].mean()) < max(0.15, 3 * se)
        ok = _check(ok, good, f"{sub:<22} rows {len(g):>5}, fills {nfill:>4}, mean R {g['R'].mean():+.3f} (3*SE {3 * se:.3f})")
    labels = set(ft["filters"]) if not ft.empty else set()
    ok = _check(ok, {"none", *FILTERS} <= labels and len(labels) >= 40,
                f"filter table: no-filter + every single filter present, {len(labels)} of 64 on/off combos have trades")
    print("  F5 kinds on random walk:", cl.drop_duplicates(["fill_server", "swing"])["f5_kind"].value_counts().to_dict())
    ok = selftest_trend(ok, out_dir)
    ok = selftest_location(ok, out_dir)
    print("\nSELFTEST:", "ALL PASS" if ok else "SOME FAILED")
    return ok


def _daily_to_m5(daily, start):
    """일봉 (o,h,l,c) 목록 -> 평일마다 M5 4개(00,06,12,18시). 양봉 o->l->h->c, 음봉 o->h->l->c."""
    rows, day = [], pd.Timestamp(start)
    for (o, h, l, c) in daily:
        while day.dayofweek >= 5:
            day += pd.Timedelta(days=1)
        path = [o, l, h, c] if c >= o else [o, h, l, c]
        for k in range(4):
            a, b = path[k], path[min(k + 1, 3)]
            rows.append((day + pd.Timedelta(hours=6 * k), a, max(a, b), min(a, b), b))
        day += pd.Timedelta(days=1)
    return pd.DataFrame(rows, columns=["time", "o", "h", "l", "c"]).set_index("time")


def _trend_daily(sign, ndays=538, period=30, amp=0.03, drift=0.0015):
    """추세 + 큰 지그재그(되돌림이 있어야 D1·W1 스윙이 생김). sign=+1 상승, -1 하락.
    538일 = 마지막이 추세 방향 다리의 끝 쪽(되돌림 중이면 H4 구조는 정상적으로 반대가 된다)."""
    k = np.arange(ndays + 1)
    tri = amp * (2 * np.abs((k % period) / period - 0.5) * 2 - 1)    # -amp..+amp 삼각파
    c = 1.2 + sign * (drift * k + tri)          # 하락은 상승의 거울상
    out = []
    for i in range(1, ndays + 1):
        o, cc = c[i - 1], c[i]
        out.append((o, max(o, cc) + 0.0008, min(o, cc) - 0.0008, cc))
    return out


def selftest_trend(ok, out_dir):
    S = lambda s: pd.Timestamp(s).value   # noqa: E731
    print("=== Test 11: market structure BOS by hand (n=2) ===")
    #        H     L     C       bar
    bars = [(10.0, 8.0, 9.0),     # 0
            (11.0, 9.0, 10.0),    # 1
            (12.0, 10.0, 11.0),   # 2 스윙 고점 12 (봉 4 마감에 확정)
            (11.0, 9.0, 9.5),     # 3
            (10.0, 8.0, 8.5),     # 4 스윙 저점 8 (봉 6 마감에 확정)
            (10.5, 8.5, 10.0),    # 5
            (11.5, 9.5, 11.0),    # 6
            (12.5, 11.0, 12.4),   # 7 종가 12.4 > 12 -> 상승 BOS (+1). 봉 7 고점 12.5 = 새 스윙 고점(봉 9에 확정)
            (12.3, 10.0, 10.2),   # 8
            (10.5, 9.0, 9.2),     # 9
            (9.5, 7.5, 7.8)]      # 10 종가 7.8 < 8 -> 하락 BOS (-1)
    H_, L_, C_ = (np.array(x) for x in zip(*bars))
    T_ = S("2024-01-01") + np.arange(len(bars)) * NS_D
    ss = structure_states(H_, L_, C_, T_ + NS_D, 2)
    want = [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, -1]
    ok = _check(ok, ss["state"].tolist() == want, f"states {ss['state'].tolist()} (expect {want})")
    ok = _check(ok, ss["sh_i"][3] == -1 and ss["sh_i"][4] == 2 and ss["sl_i"][5] == -1 and ss["sl_i"][6] == 4
                and ss["sh_i"][9] == 7, "swing high 2 known only after bar 4 closes, low 4 after bar 6, high 7 after bar 9")
    tin = T_[7] + 12 * NS_H                               # 봉 7 진행 중(가격은 이미 12 위)
    ok = _check(ok, state_at(ss, tin) == 0 and state_at(ss, T_[7] + NS_D) == 1,
                "during bar 7 (not closed) -> 0; at bar 7 close -> +1 (no look-ahead)")
    ok = _check(ok, state_at(ss, T_[10] + NS_D - 1) == 1 and state_at(ss, T_[10] + NS_D) == -1,
                "bearish BOS counts only after bar 10 closes")
    # PDA: 봉 7 마감 후 상승. 레인지 = 저점 8 ~ max(고점 12, 저점 이후 최고 12.5) -> 50% = 10.25
    t8 = T_[7] + NS_D
    ok = _check(ok, pda_ok(ss, 1, 10.0, t8) and not pda_ok(ss, 1, 10.5, t8),
                "PDA buy: range 8~12.5, mid 10.25 -> sweep 10.0 discount OK, 10.5 premium rejected")
    ok = _check(ok, pda_ok(ss, -1, 10.5, t8) and not pda_ok(ss, -1, 10.0, t8),
                "PDA sell side mirror (range 8~12, mid 10) -> 10.5 premium OK, 10.0 rejected")

    print("=== Test 12: each trend definition on hand-made up / down markets ===")
    for sign, name in ((1, "uptrend"), (-1, "downtrend")):
        m5 = _daily_to_m5(_trend_daily(sign), "2020-01-06")
        t = m5.index.values.astype("datetime64[ns]").astype("int64")
        o, h, l, c = (m5[k].values for k in ("o", "h", "l", "c"))
        tc = trend_context(t, o, h, l, c, 2, 50, 5)
        tq = int(t[-1]) + NS_D
        sts = {k: state_at(tc[k], tq) for k in ("d1s", "w1s", "h4s", "ema")}
        ok = _check(ok, all(v == sign for v in sts.values()), f"{name}: D1/W1/H4/EMA states {sts} (expect all {sign:+d})")
        a = trend_align(tc, sign, float(c.min() if sign == 1 else c.max()), tq)
        ok = _check(ok, all(v == 1 for v in a.values()), f"{name}: setup WITH trend, sweep deep in discount/premium -> {a}")
        b = trend_align(tc, -sign, float(c.min() if sign == 1 else c.max()), tq)
        ok = _check(ok, all(v == -1 for v in b.values()), f"{name}: setup AGAINST trend -> {b}")
        ext_bad = float(np.max(c[-5:])) if sign == 1 else float(np.min(c[-5:]))
        pa = trend_align(tc, sign, ext_bad, tq)["T_PDA"]
        ok = _check(ok, pa == 0, f"{name}: with-trend sweep on wrong half (buy in premium / sell in discount) -> T_PDA {pa} (expect 0)")
        w = tc["w1s"]
        wd = pd.to_datetime(w["close_t"] - 7 * NS_D).dayofweek
        ok = _check(ok, bool((wd == 0).all()), "weekly bars start on Monday 00:00 server time")
    ok = _check(ok, state_at(tc["d1s"], int(t[0]) + 3 * NS_D) == 0 and state_at(tc["ema"], int(t[0]) + 10 * NS_D) == 0,
                "too little history -> 0 (no trend)")

    print("=== Test 13: no look-ahead (trend at time t equals trend from data cut at t) ===")
    rw = _random_walk(5, "2019-01-01", "2021-06-30 23:55", 0.0001)
    t = rw.index.values.astype("datetime64[ns]").astype("int64")
    arr = [rw[k].values for k in ("o", "h", "l", "c")]
    full = trend_context(t, *arr, 2, 50, 5)
    rng = np.random.default_rng(3)
    qs = np.sort(rng.choice(np.arange(len(t) // 3, len(t)), 25, replace=False))
    same = 0
    for q in qs:
        tq = int(t[q])
        cut = trend_context(t[:q], *(x[:q] for x in arr), 2, 50, 5)    # 시각 tq 이전 데이터만
        ext = float(rw["l"].values[q])
        good = all(trend_align(full, d, ext, tq) == trend_align(cut, d, ext, tq) for d in (1, -1))
        same += int(good)
    ok = _check(ok, same == len(qs), f"{same}/{len(qs)} random times: full-data trend == cut-data trend (all 5 definitions)")
    vals = pd.Series([trend_align(full, 1, float(rw["l"].values[q]), int(t[q]))["T_D1S"] for q in qs]).value_counts().to_dict()
    ok = _check(ok, len(vals) >= 2, f"random walk D1 structure flips both ways {vals}")

    print("=== Test 14: hand scenario in trend mode ===")
    df = _expand_m15(scenario_rows(), "2024-01-08 00:00", 1.10000, 0.0001)
    res = run_all(default_opts(oos_start="2024-06-01", min_trades=1, out=out_dir, trend="ALL"),
                  files={"EURUSD": df}, quiet=True)
    trs = res["trades"]
    tA = trs[trs["combo"] == "N5-A-S2-T1"]
    ok = _check(ok, len(tA) == 1 and abs(tA["R"].iloc[0] - 23 / 16) < 1e-9 and "N5-K-S2-T1" in set(trs["combo"]),
                "buy setup still found (R 23/16), K entry included automatically")
    ok = _check(ok, all((trs[f"trend_{k}"] == 0).all() for k in TRENDS),
                "no D1/W1 history in scenario -> every trend = 0 -> excluded from trend rows")
    ok = _check(ok, set(res["trends"]["trend"]) == {"NONE"}, "trend table holds only NONE baseline")

    print("=== Test 15: random walk, trend base conditions -> expectancy near 0 ===")
    rw2 = _random_walk(11, "2016-01-01", "2023-12-31 23:55", 0.0001)
    opt = default_opts(oos_start="2021-01-01", min_trades=30, out=out_dir, spread=0.0, trend="ALL",
                       stops="S2", targets="T2,T3")
    res = run_all(opt, files={"RW": rw2}, quiet=True)
    cl = res["trades"][res["trades"]["result"] != "open"]
    f = pd.DataFrame(res["funnels"])
    print("  setups per N:", f["setups"].tolist(), " aligned:", {k: f[f"aligned_{k}"].tolist() for k in TRENDS})
    for name in ["NONE"] + TRENDS:
        g = cl if name == "NONE" else cl[cl[f"trend_{name}"] == 1]
        if len(g) < 2:
            ok = _check(ok, False, f"{name}: no trades on random walk")
            continue
        nset = g["setup_id"].nunique()
        se = g["R"].std(ddof=1) / np.sqrt(max(nset, 2))
        ok = _check(ok, abs(g["R"].mean()) < max(0.15, 3 * se),
                    f"{name:<7} rows {len(g):>5}, setups {nset:>4}, mean R {g['R'].mean():+.3f} (3*SE {3 * se:.3f})")
    tt = res["trends"]
    ok = _check(ok, {"NONE", *TRENDS} <= set(tt["trend"]), "trend table has NONE + all 5 definitions")
    txt = open(os.path.join(out_dir, "summary_c2required_trend.txt"), encoding="utf-8-sig").read()
    ok = _check(ok, txt.index("[T1]") < txt.index("[T2]") < txt.index("[셋업 깔때기]"),
                "summary starts with [T1] trend table then [T2] top 5")
    try:
        txt.encode("cp949")
        enc = True
    except UnicodeEncodeError as e:
        enc = False
        print("   cp949 problem:", e)
    ok = _check(ok, enc, "summary text encodable in cp949 (Windows console safe)")
    return ok


def _h4_hand(mirror=False):
    """손으로 만든 H4 봉 (o,h,l,c). SL = 봉2 저가 100, SH = 봉6 고가 120, H4 OB = 봉1(음봉 102~105).
    봉9 = 되돌림 중 작은 스윙 저점 110(뒤에 스윙 고점 없음). mirror=True 면 가격을 뒤집어 매도 시나리오."""
    bars = [(105, 106, 103, 104),     # 0
            (104, 105, 102, 102.5),   # 1 음봉 = H4 OB (SL 봉2는 양봉이라 한 칸 앞)
            (101, 103, 100, 102.5),   # 2 스윙 저점 100 (봉4 마감에 확정)
            (102.5, 104, 100.5, 103.5),
            (103.5, 108, 103, 107.5),
            (107.5, 112, 107, 111.5),
            (111.5, 120, 111, 119),   # 6 스윙 고점 120 (봉8 마감에 확정)
            (119, 119.5, 115, 116),
            (116, 117, 112, 113),
            (113, 114, 110, 111),     # 9 작은 스윙 저점 110 (봉11 마감에 확정)
            (111, 113, 111, 112.5),
            (112.5, 114, 112, 113),
            (113, 113, 111.5, 112),
            (112, 112, 111.5, 111.8)]
    o, h, l, c = (np.array(x, float) for x in zip(*bars))
    if mirror:
        o, h, l, c = -o, -l, -h, -c
    T4 = pd.Timestamp("2024-01-08").value + np.arange(len(bars)) * 4 * NS_H
    return dict(t=T4, o=o, h=h, l=l, c=c)


def _gbpusd_shape():
    """석준님 GBPUSD 4H 예시(2026-10-28) 모양. 앞 고점 1.3400 -> 하락 저점 1.3296(봉7, 음봉 = H4 OB 1.3296~1.3312)
    -> 상승해 봉11 종가 1.3405로 1.3400 위 BOS -> 고점 1.3419(봉12) -> 되돌림 중 내부 저점 1.3355(봉15)·1.3328(봉19)을
    종가로 깸(내부 CHoCH) -> 1.3303(봉23, OB 안). 봉24 = 1.3290까지 꼬리만, 봉25 = 1.3290 종가 마감."""
    bars = [(1.3360, 1.3370, 1.3350, 1.3365), (1.3365, 1.3385, 1.3360, 1.3380), (1.3380, 1.3400, 1.3375, 1.3390),
            (1.3390, 1.3392, 1.3370, 1.3372), (1.3372, 1.3375, 1.3345, 1.3350), (1.3350, 1.3355, 1.3320, 1.3325),
            (1.3325, 1.3330, 1.3305, 1.3310), (1.3310, 1.3312, 1.3296, 1.3300), (1.3300, 1.3330, 1.3298, 1.3328),
            (1.3328, 1.3360, 1.3325, 1.3355), (1.3355, 1.3385, 1.3350, 1.3380), (1.3380, 1.3410, 1.3375, 1.3405),
            (1.3405, 1.3419, 1.3400, 1.3415), (1.3415, 1.3416, 1.3390, 1.3395), (1.3395, 1.3400, 1.3370, 1.3375),
            (1.3375, 1.3380, 1.3355, 1.3360), (1.3360, 1.3378, 1.3358, 1.3372), (1.3372, 1.3376, 1.3360, 1.3365),
            (1.3365, 1.3366, 1.3335, 1.3340), (1.3340, 1.3345, 1.3328, 1.3332), (1.3332, 1.3342, 1.3330, 1.3338),
            (1.3338, 1.3340, 1.3331, 1.3335), (1.3335, 1.3336, 1.3305, 1.3308), (1.3308, 1.3312, 1.3299, 1.3303),
            (1.3303, 1.3306, 1.3290, 1.3301), (1.3301, 1.3302, 1.3285, 1.3290)]
    o, h, l, c = (np.array(v, float) for v in zip(*bars))
    T4 = pd.Timestamp("2026-10-15").value + np.arange(len(bars)) * 4 * NS_H
    return dict(t=T4, o=o, h=h, l=l, c=c)


def selftest_location(ok, out_dir):
    S = lambda s: pd.Timestamp(s).value   # noqa: E731
    print("=== Test 16: T_W1H4 = weekly AND H4 structure same direction ===")
    mk = lambda v: dict(close_t=np.array([0]), state=np.array([v], np.int8))   # noqa: E731
    cases = {(1, 1, 1): 1, (1, 1, -1): -1, (1, -1, 1): 0, (-1, 1, 1): 0, (-1, -1, 1): -1, (-1, -1, -1): 1,
             (0, 1, 1): 0, (1, 0, 1): 0, (0, 0, 1): 0}
    got = {}
    for (w, h4, d), want in cases.items():
        tc = dict(d1s=mk(0), w1s=mk(w), h4s=mk(h4), ema=mk(0))
        got[(w, h4, d)] = trend_align(tc, d, 1.0, 1)["T_W1H4"]
    ok = _check(ok, got == cases, "(W1, H4, setup dir) -> T_W1H4: both up & buy +1, both up & sell -1, mixed or none 0")
    ok = _check(ok, trend_list(default_opts(trend="T_D1S")) == ["T_W1H4EXT", "T_W1H4", "T_D1S"]
                and trend_list(default_opts(trend="ALL")) == TRENDS,
                "T_W1H4EXT (main verdict) and T_W1H4 (internal, comparison) always added in trend mode")
    gx = {}
    for (w, h4, d), want in cases.items():
        tc = dict(d1s=mk(0), w1s=mk(w), h4s=mk(-h4), h4x=mk(h4), ema=mk(0))   # 내부 구조는 일부러 반대로
        gx[(w, h4, d)] = trend_align(tc, d, 1.0, 1)["T_W1H4EXT"]
    ok = _check(ok, gx == cases, "T_W1H4EXT uses H4 EXTERNAL state (internal state set opposite on purpose, ignored)")
    tc = dict(d1s=mk(0), w1s=dict(close_t=np.array([0, 10]), state=np.array([1, -1], np.int8)), h4s=mk(1), ema=mk(0))
    ok = _check(ok, trend_align(tc, 1, 1.0, 9)["T_W1H4"] == 1 and trend_align(tc, 1, 1.0, 10)["T_W1H4"] == 0,
                "weekly flip counts only from the weekly close time (t=9 still +1, t=10 -> mixed 0)")

    print("=== Test 16b: H4 external structure, GBPUSD 10/28 shape (internal CHoCH down, protected low intact) ===")
    gb = _gbpusd_shape()
    x = ext_structure(gb, gb["t"] + 4 * NS_H, 2)
    ins = structure_states(gb["h"], gb["l"], gb["c"], gb["t"] + 4 * NS_H, 2)
    b23 = 23
    ok = _check(ok, int(x["state"][11]) == 1 and abs(x["prot"][11] - 1.3296) < 1e-9,
                f"bar 11 closes 1.3405 above swing high 1.3400 -> external UP, protected low {x['prot'][11]:.4f} (expect 1.3296)")
    ok = _check(ok, int(ins["state"][18]) == -1 and int(ins["state"][22]) == -1,
                "internal structure: close below 1.3355 (bar 18) and 1.3328 (bar 22) -> internal DOWN (CHoCH)")
    ok = _check(ok, all(int(v) == 1 for v in x["state"][11:b23 + 1]) and abs(x["prot"][b23] - 1.3296) < 1e-9
                and abs(x["lx"][b23] - 1.3419) < 1e-9,
                "external stays UP through the pullback to 1.3303; protected low 1.3296, swing high 1.3419")
    rgx = ext_range(x, 1, gb["t"][b23] + 4 * NS_H)
    dpx = depth_of(rgx, 1.3303)
    ok = _check(ok, rgx is not None and abs(rgx["ob_l"] - 1.3296) < 1e-9 and abs(rgx["ob_h"] - 1.3312) < 1e-9
                and abs(dpx - (1.3419 - 1.3303) / (1.3419 - 1.3296)) < 1e-9 and depth_bucket(dpx) == "75~100%"
                and ob_position(rgx, 1, 1.3303) == "OB안",
                f"external range 1.3296~1.3419, H4 OB 1.3296~1.3312, sweep 1.3303 -> depth {dpx:.3f} (75~100%), in OB")
    ok = _check(ok, ext_range(x, -1, gb["t"][b23] + 4 * NS_H) is None, "sell setup against external UP -> no range (bucket 없음)")
    ok = _check(ok, int(x["state"][24]) == 1, "bar 24 wick to 1.3290 but closes 1.3301 -> still UP (wick = sweep, not break)")
    ok = _check(ok, int(x["state"][25]) == -1 and abs(x["prot"][25] - 1.3419) < 1e-9,
                "bar 25 CLOSES 1.3290 below 1.3296 -> external DOWN, protected high 1.3419")
    t24 = gb["t"][25]   # 봉 25 진행 중
    ok = _check(ok, state_at(x, t24) == 1 and state_at(x, t24 + 4 * NS_H) == -1,
                "flip known only after bar 25 closes (during bar 25 still UP)")
    tb, pb = slb_break(1, 1.3296, gb["t"][23], gb["t"] + 4 * NS_H, gb["c"])
    ok = _check(ok, tb == gb["t"][25] + 4 * NS_H and abs(pb - 1.3290) < 1e-9, "F_SLB on this shape: break at bar 25 close 1.3290")

    print("=== Test 17: H4 dealing range depth by hand (boundaries, OB, no look-ahead, mirror) ===")
    h4 = _h4_hand()
    rc = h4_range_ctx(h4, 2)
    ok = _check(ok, rc["lo_idx"].tolist() == [2, 9] and rc["hi_idx"].tolist() == [6],
                f"swings: lows {rc['lo_idx'].tolist()} (expect [2, 9]), highs {rc['hi_idx'].tolist()} (expect [6])")
    T4 = h4["t"]
    t_end = T4[-1] + 4 * NS_H
    rg = dealing_range(rc, 1, t_end)
    ok = _check(ok, rg is not None and rg["origin"] == 100 and rg["far"] == 120 and rg["ob_l"] == 102 and rg["ob_h"] == 105,
                f"range SL 100 ~ SH 120, H4 OB 102~105 (bar 1, last bearish bar before rally) -> {rg and (rg['origin'], rg['far'], rg['ob_l'], rg['ob_h'])}")
    ok = _check(ok, rg is not None and rg["origin_i"] == 2,
                "minor pullback low 110 (no swing high after it) skipped -> SL stays the low that started the leg to SH")
    want = {121: "0%미만", 120: "0~25%", 116: "0~25%", 115: "25~50%", 110: "50~75%", 105: "75~100%",
            100: "75~100%", 99.99: "100%+"}
    got = {x: depth_bucket(depth_of(rg, x)) for x in want}
    ok = _check(ok, got == want, f"buckets: 120->0%, 115->25% (=25~50), 110->50%, 105->75%, 100(=SL)->75~100, 99.99->100%+ : {got}")
    ok = _check(ok, abs(depth_of(rg, 104) - 0.8) < 1e-12, "depth (120-104)/(120-100) = 0.80")
    pos = {x: ob_position(rg, 1, x) for x in (103, 105, 102, 106, 101.9)}
    ok = _check(ok, pos == {103: "OB안", 105: "OB안", 102: "OB안", 106: "OB전(안닿음)", 101.9: "OB관통"},
                f"H4 OB position (edges inclusive): {pos}")
    r7 = dealing_range(rc, 1, T4[8] + 4 * NS_H - 1)
    r8 = dealing_range(rc, 1, T4[8] + 4 * NS_H)
    ok = _check(ok, r7 is None and r8 is not None,
                "SH (bar 6) confirmed only when bar 8 closes: 1ns before -> no range ('없음'), at close -> range")
    ok = _check(ok, location_of(rc, 1, 110.0, T4[8] + 4 * NS_H - 1)["bucket"] == "없음", "no range -> bucket 없음")
    rs = dealing_range(rc, -1, t_end)
    ok = _check(ok, rs is not None and rs["origin"] == 120 and rs["far"] == 110 and abs(depth_of(rs, 115) - 0.5) < 1e-12,
                "sell view on same bars: SH 120 ~ later swing low 110, sweep 115 -> depth 50%")
    hm = _h4_hand(mirror=True)
    rcm = h4_range_ctx(hm, 2)
    rgm = dealing_range(rcm, -1, hm["t"][-1] + 4 * NS_H)
    gm = {x: depth_bucket(depth_of(rgm, -x)) for x in want}
    ok = _check(ok, rgm is not None and rgm["origin"] == -100 and rgm["far"] == -120 and gm == want
                and (rgm["ob_l"], rgm["ob_h"]) == (-105, -102) and ob_position(rgm, -1, -106) == "OB전(안닿음)"
                and ob_position(rgm, -1, -101.9) == "OB관통",
                "sell mirror: same depths/buckets/OB with prices flipped")

    print("=== Test 18: F_SLB (H4 body close beyond SL) cancel / exit ===")
    base = S("2024-01-08")
    t = base + np.arange(4 * 48) * 5 * NS_MIN                # M5 16시간
    CT4 = base + np.arange(1, 5) * 4 * NS_H                  # H4 마감 04,08,12,16시
    C4 = np.array([101.0, 99.5, 102.0, 103.0])               # 08시 마감 봉이 SL 100 아래 몸통 마감
    tb, pb = slb_break(1, 100.0, base, CT4, C4)
    ok = _check(ok, tb == CT4[1] and pb == 99.5, "first H4 close below SL -> 08:00, close 99.5")
    ok = _check(ok, slb_break(1, 100.0, CT4[1], CT4, C4)[0] == NS_INF, "closes at/before sweep start are ignored")
    ok = _check(ok, slb_break(1, 99.0, base, CT4, C4)[0] == NS_INF, "wick/close above SL 99 -> no break (body close needed)")
    ok = _check(ok, slb_break(1, 99.5, base, CT4, C4)[0] == NS_INF, "close exactly at SL is not a break (strict)")
    kx = int(np.searchsorted(t, CT4[1])) - 1
    fill, risk = 100.8, 1.0
    r = slb_apply(1, base + NS_H, "win", kx + 5, 102.8, tb, pb, t, 0.0)
    ok = _check(ok, r == ("slb", kx, 99.5) and t[kx] == CT4[1] - 5 * NS_MIN,
                f"holding, TP would come after the break -> exit at 08:00 H4 close 99.5 (M5 idx {kx}), R {(99.5 - fill) / risk:+.2f}")
    r = slb_apply(1, base + NS_H, "loss", kx - 3, 99.8, tb, pb, t, 0.0)
    ok = _check(ok, r == ("loss", kx - 3, 99.8), "stop hit before the break -> unchanged")
    r = slb_apply(1, base + NS_H, "win", kx, 102.8, tb, pb, t, 0.0)
    ok = _check(ok, r == ("win", kx, 102.8), "target hit inside the last M5 of the breaking H4 bar -> target kept (it came before the close)")
    r = slb_apply(1, base + NS_H, "open", len(t) - 1, np.nan, tb, pb, t, 0.0)
    ok = _check(ok, r == ("slb", kx, 99.5), "open trade + break -> exit at break")
    r = slb_apply(1, CT4[1], "win", kx + 5, 102.8, tb, pb, t, 0.0)
    ok = _check(ok, r[0] == "cancel", "fill at the same instant the breaking H4 closes -> setup cancelled (known before fill)")
    r = slb_apply(1, base + NS_H, "win", kx + 5, 102.8, NS_INF, np.nan, t, 0.0)
    ok = _check(ok, r == ("win", kx + 5, 102.8), "no break -> unchanged")
    tbs, pbs = slb_break(-1, 120.0, base, CT4, np.array([119.0, 120.5, 118.0, 117.0]))
    r = slb_apply(-1, base + NS_H, "open", len(t) - 1, np.nan, tbs, pbs, t, 0.3)
    ok = _check(ok, tbs == CT4[1] and r[0] == "slb" and abs(r[2] - 120.8) < 1e-12,
                "sell mirror: H4 close 120.5 above SH 120 -> exit at ask 120.5 + spread 0.3")

    print("=== Test 19: no look-ahead, whole pipeline (full data vs data cut at a date) ===")
    rw = _random_walk(5, "2019-01-01", "2021-06-30 23:55", 0.0001)
    cut = pd.Timestamp("2020-10-01")
    kw = dict(oos_start="2020-06-01", min_trades=1, out=out_dir, trend="ALL", stops="S2", targets="T2", mss_tf="M15,M5")
    full = run_all(default_opts(**kw), files={"RW": rw}, quiet=True)["trades"]
    part = run_all(default_opts(**kw), files={"RW": rw[rw.index < cut]}, quiet=True)["trades"]
    lim = (cut - pd.Timedelta(days=1)).strftime("%Y-%m-%d %H:%M")

    def done(x):
        e2 = x["exit_slb_server"].where(x["exit_slb_server"] != "", x["exit_server"])
        return x[(x["result"] != "open") & (x["exit_server"] < lim) & (e2 < lim)]
    cols = ["R", "R_slb", "depth", "depth_bucket", "ob_pos", "slb_cancel", "rng_origin", "rng_far"] + [f"trend_{k}" for k in TRENDS]
    a = done(full).set_index(["setup_id", "combo"])[cols].sort_index()
    b = done(part).set_index(["setup_id", "combo"])[cols].sort_index()
    same_keys = a.index.equals(b.index)
    same_vals = same_keys and all(((a[c] == b[c]) | (a[c].isna() & b[c].isna())).all() for c in cols)
    ok = _check(ok, len(a) > 50 and same_keys and same_vals,
                f"{len(a)} trades finished before the cut: identical keys and values (R, R_slb, depth, OB, trends) = {same_vals}")
    ok = _check(ok, set(a.reset_index()["combo"].str[:3]) >= {"N5-", "N3-", "M5-"}, "both MSS timeframes (M15, M5) present")

    print("=== Test 20: random walk -> new definitions near 0 (spread 0) ===")
    rw2 = _random_walk(11, "2016-01-01", "2023-12-31 23:55", 0.0001)
    res = run_all(default_opts(oos_start="2021-01-01", min_trades=30, out=out_dir, spread=0.0, trend="T_D1S",
                               stops="S2", targets="T2,T3", mss_tf="M15,M5"), files={"RW": rw2}, quiet=True)
    tr = res["trades"]
    cl = tr[tr["result"] != "open"]
    groups = [(f"{tf} {MAIN_TREND} with", cl[(cl["mss_tf"] == tf) & (cl[f"trend_{MAIN_TREND}"] == 1)]) for tf in MSS_TFS]
    groups += [(f"{tf} F_SLB on", cl[(cl["mss_tf"] == tf) & ~cl["slb_cancel"]].assign(R=lambda x: x["R_slb"])) for tf in MSS_TFS]
    for name, g in groups:
        g = g[g["R"].notna()]
        nset = g["setup_id"].nunique()
        if nset < 20:
            print(f"  {name:<22} only {nset} setups, skipped")
            continue
        se = g["R"].std(ddof=1) / np.sqrt(nset)
        ok = _check(ok, abs(g["R"].mean()) < max(0.15, 3 * se),
                    f"{name:<22} rows {len(g):>5}, setups {nset:>4}, mean R {g['R'].mean():+.3f} (3*SE {3 * se:.3f})")
    sl = tr[tr["result_slb"] == "slb"]
    okx = (sl["exit_slb_server"] <= sl["exit_server"].where(sl["result"] != "open", "9999")).all()
    cn = tr[tr["slb_cancel"]]
    okc = (cn["slb_break_server"] <= cn["fill_server"]).all() if len(cn) else True
    same = tr[~tr["result_slb"].isin(["slb", "cancel"])]
    oks = ((same["R"] == same["R_slb"]) | (same["R"].isna() & same["R_slb"].isna())).all()
    ok = _check(ok, len(sl) > 0 and len(cn) > 0 and okx and okc and oks,
                f"F_SLB consistency: {len(sl)} forced exits all earlier than normal exit, {len(cn)} cancels after a break, others unchanged")
    txt = open(os.path.join(out_dir, "summary_c2required_trend_m15m5.txt"), encoding="utf-8-sig").read()
    order = [txt.find("\n" + x) for x in (f"[주판정 {MAIN_TREND}]", "[위치 구간]", "[F_SLB 비교]", "[T1]", "[T2]", "[셋업 깔때기]")]
    ok = _check(ok, -1 not in order and order == sorted(order),
                f"summary order: [주판정 {MAIN_TREND}] -> [위치 구간] -> [F_SLB 비교] -> [T1] -> [T2] -> funnel")
    ok = _check(ok, "1분봉" in txt and "사전 지정" in txt and "과최적화" in txt, "summary says: no 1-min data, pre-specified, overfitting warning")
    try:
        txt.encode("cp949")
        enc = True
    except UnicodeEncodeError as e:
        enc = False
        print("   cp949 problem:", e)
    ok = _check(ok, enc, "new summary text encodable in cp949")
    lt = location_table(tr)
    ok = _check(ok, {"depth", "h4ob", "f_slb"} <= set(lt["kind"]), "location CSV has depth / h4ob / f_slb rows")
    # 구간별: 한 시드는 칸마다 표본이 작아 우연히 3SE를 넘을 수 있다(시드 11의 100%+ 가 그랬음) -> 시드 3개를 합쳐 본다
    files = {f"RW{sd}": _random_walk(sd, "2016-01-01", "2023-12-31 23:55", 0.0001) for sd in (11, 21, 22)}
    cl3 = run_all(default_opts(oos_start="2021-01-01", min_trades=30, out=out_dir, spread=0.0, trend="T_D1S",
                               stops="S2", targets="T2,T3", mss_tf="M15"), files=files, quiet=True)["trades"]
    cl3 = cl3[cl3["result"] != "open"]
    for kind, col in (("ext depth", "depth_bucket"), ("int depth", "depth_bucket_int")):
        for bk in DEPTH_BUCKETS[:-1]:
            g = cl3[cl3[col] == bk]
            nset = g["setup_id"].nunique()
            if nset < 30:
                print(f"  {kind} {bk:<8} only {nset} setups, skipped")
                continue
            se = g["R"].std(ddof=1) / np.sqrt(nset)
            ok = _check(ok, abs(g["R"].mean()) < max(0.15, 3 * se),
                        f"{kind} {bk:<8} (3 seeds pooled) setups {nset:>4}, mean R {g['R'].mean():+.3f} (3*SE {3 * se:.3f})")
    return ok


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace")   # cp949 콘솔에서 못 쓰는 글자는 ? 로 (오류로 멈추지 않게)
        except Exception:
            pass
    opt = build_parser().parse_args()
    if opt.selftest:
        sys.exit(0 if selftest() else 1)
    if not opt.data_dir or not opt.out:
        print("need --data-dir and --out. e.g. py -3.12 crt_backtest.py --data-dir C:\\...\\mt5_m5_data --out C:\\...\\crt_bt_out")
        sys.exit(2)
    run_all(opt)


if __name__ == "__main__":
    main()
