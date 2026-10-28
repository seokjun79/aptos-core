"""프로젝트 2: ICT 모델 백테스트 (미리 정한 규칙, 정직하게). 읽기 전용 분석 스크립트, 주문 없음.

규칙 원문(사람용): trading/projects/02-ict/rules.md  — 이 docstring과 같은 내용이다.
규칙·숫자는 실제 데이터를 보기 전에(2026-10-29) 고정했다. 결과를 보고 바꾸지 않는다.
이미 불합격한 ICT ATM 48개 변형(ict_atm.py)은 다시 시험하지 않는다.

시간: 데이터는 MT5 서버시간(= 뉴욕 + 7시간, 서머타임도 서버가 같이 움직이므로 늘 7시간). 규칙의 시각은 모두 뉴욕(NY) 시각.
 일봉 = 서버 자정 기준 봉(= NY 17:00 ~ 다음날 17:00, MT5 D1과 같음). 주봉 = 서버 월요일 00:00 시작.
 '거래일 D' 의 시간창은 그 서버 날짜 안에 있다: NY h시 = 서버 (h+7)시. 예) NY 08:30 = 서버 15:30, NY 16:00 = 서버 23:00.
공통(모든 모델):
 - 매수 기준으로 정의, 매도는 가격을 뒤집어(−가격, 고가↔저가) 같은 코드로 처리한다(완전 대칭).
 - 미래 정보 금지: 레벨은 그 봉이 마감한 뒤에만 쓴다. 진입은 확인 봉 다음 봉 시가(시장가) 또는 그 뒤 지정가 터치.
 - 같은 봉에서 손절·목표 모두 닿으면 손절. 체결한 봉에서는 목표를 인정하지 않는다(손절만 본다).
   지정가 체결 전에 목표에 먼저 닿으면 주문 취소(같은 봉에 둘 다 닿아도 취소). 갭으로 손절을 건너뛰면 시가 청산.
 - 손절 버퍼 1핍. 손절폭이 max(4×스프레드, 2핍)보다 작으면 거래 안 함.
 - 비용 = 스프레드(핍) × 핍크기, 거래당 1번 뺀다. 결과는 R(= 진입~손절 거리). 기본 1핍, 금(XAUUSD) 핍 0.1 / 0.2달러(2핍).
   README 합격 기준에 따라 스프레드는 최소 1핍(금 0.2달러) 아래로 내려가지 않는다.
 - 시간 청산: 체결한 날 NY 16:00(서버 23:00) 직전 M5 봉 종가.
 - 같은 종목·같은 변형은 동시에 1포지션. 앞 거래가 청산된 봉 이후 체결만 인정.
 - '유동성 목표'(PDH, 반대편 범위 등)는 보상 ≥ 1.5R일 때만(M4 실버불릿은 2.0R).

바이어스 스위치 B (모든 모델에 켬/끔 두 가지로 시험): 거래일 D 기준
 주: 직전 완성 주봉 종가 > 그 전 주봉 범위 중간(고+저)/2 → 상승, < → 하락.
 일: 직전 일봉(D−1) 종가 > 그 전 일봉(D−2) 범위 중간(CE) → 상승, < → 하락.
 둘이 같은 방향일 때만 그 방향 거래 허용(다르면 그날 거래 없음).

M1 일봉 3봉 스윙 + 확인 (2026-10-28 NQ 영상 2번)
 스윙 저점: 일봉 k(2번 봉) 저가 < k−1 저가, k+1(3번 봉) 저가 > k 저가.
 키 레벨 스윕(둘 중 하나 이상): PWL = 직전 주 저가를 k가 이번 주 '처음' 깸.
   DSL = k−2일 이전에 확정된 일봉 스윙 저점(앞뒤 1봉보다 낮음) 중 아직 안 깨진 가장 최근 것(60일 안)을 k가 깸.
 확인: C4 = 4번 봉(k+2) 양봉 마감 → 5번 봉(k+3)이 거래일.  C45 = 4·5번 봉 모두 양봉 → 6번 봉(k+4)이 거래일.
 진입(거래일 NY 08:30~11:00):
   FVG = 창 안에서 처음 생긴 상승 M5 FVG(봉 i 저가 > 봉 i−2 고가, i가 창 안에서 마감)의 CE(중간)에 지정가, 11:00까지 유효.
         손절 = 봉 i−11~i 최저가 − 1핍.
   PDCE = 전일 범위 CE에 지정가(창 시작 시가가 CE 위일 때만), 손절 = 전일 25% 선(저가 + 0.25×범위) − 1핍. 11:00까지 유효.
 목표: PDH(전일 고가, ≥1.5R) / 2R.  → 2×2×2 = 8개
M2 딜링 레인지 표준편차 (영상 8번, ICT FX)
 범위: ASIA = NY 19:00~24:00, CBDR = NY 14:00~20:00(전날 오후~). 횡보 조건: 범위 ≤ 0.4 × ADR20(직전 20일 평균 일봉 범위).
 SD 선: 아래 L − k×범위, 위 H + k×범위 (k = 0.5, 1, 2, 2.5). 거래: 범위 끝 ~ NY 11:00.
 SD1 = −1에 매수 지정가, 손절 −2 − 1핍, 목표 범위 저가(1R).  SD2 = −2에 매수, 손절 −2.5 − 1핍, 목표 범위 저가(4R).
 바이어스 끔 = '먼저 닿은 쪽 되돌림'(단순판, 같은 봉에서 위·아래 둘 다 닿으면 그날 제외).
 바이어스 켬 = 바이어스 방향 쪽만 되돌림('바이어스 방향일 때 SD에서 되돌림').  → 2×2 = 4개
M3 주다스 스윙 / 런던
 아시아 범위(NY 19:00~24:00). NY 02:00~05:00에 처음으로 아시아 저가를 깸(그 전 00:00부터 그 봉까지 아시아 고가는 안 깨짐).
 MSS: 스윕 뒤 NY 06:00 전까지, 극값 이전의 가장 가까운 확정 M5 스윙 고점(앞뒤 5봉, 72봉 안, 오른쪽 5봉이 그 시점까지 마감)
      위로 양봉 몸통 마감 + 종가가 아시아 저가 위(범위 안 복귀). 극값이 새로 낮아지면 스윙 고점도 다시 찾음.
 진입: MKT = MSS 다음 봉 시가.  FVG = 극값~MSS 봉 사이 가장 최근 상승 FVG의 CE 지정가, NY 08:00까지 유효.
 손절 = 극값 − 1핍. 목표: OPP = 아시아 고가(≥1.5R) / 2R.  → 2×2 = 4개
M4 실버 불릿
 창: NY = NY 10:00~11:00, LDN = NY 03:00~04:00. 창 시작 시가 기준 '끌림(draw)' = 아직 안 깨진 유동성 중 가장 가까운 것.
 후보: 전일 고·저(그날 창 전까지 안 깨짐), 아시아 고·저(NY 24:00 이후 창 전까지 안 깨짐), (NY 창만) 런던 NY 02~05시 고·저(05시 이후 안 깨짐).
 위쪽이 더 가까우면 매수만. 창 안에서 처음 생긴 상승 M5 FVG: EDGE = FVG 위 끝(봉 i 저가) / CE = 중간에 지정가, 창 끝까지 유효.
 손절 = 봉 i−11~i 최저가 − 1핍. 목표 = draw 레벨, 2.0R 미만이면 제외.  → 2×2 = 4개
M5 IFVG CE 지키기 (영상 9번)
 H1 = H1 3봉 스윙 저점(일봉과 같은 정의, 키 레벨 = 48봉 안 안 깨진 가장 최근 H1 스윙 저점) + 4번 H1 봉 양봉 마감.
      직전 다리 = 스윙 저점 앞 24봉 중 최고가 봉부터 스윙 저점까지. 그 안의 하락 H1 FVG(봉 q 고가 < 봉 q−2 저가)가
      H1 종가로 위 끝을 넘으면 IFVG. 확인 후 24시간 동안 NY 02:00~12:00에 진입 가능.
 D1 = M1(C4) 일봉 셋업의 거래일. 직전 다리 = 2번 봉 앞 10일 중 최고가 일봉부터 2번 봉까지의 H1 하락 FVG. 거래일 NY 02:00~12:00.
 진입: M5 봉이 IFVG CE에 닿고(저가 ≤ CE) 종가가 CE 위 → 다음 봉 시가 매수. IFVG가 살아난 뒤 M5 종가가 CE 이하로
       마감하면 그 IFVG는 버림(몸통이 CE 아래로 닫히면 실패).
 손절 = IFVG 아래 끝 − 1핍. 목표: HIGH = 다리 시작 고가(≥1.5R) / 2R.  → 2×2 = 4개
M6 NDOG / NWOG
 NWOG = 금요일 마지막 M5 종가 ~ 다음 주 첫 M5 시가. NDOG = 월요일 NY 16:55봉 종가 ~ NY 18:00봉 시가(그 사이 1시간은 무시).
 CE = 갭 중간을 지지/저항으로: 생긴 뒤 그 주 안 NY 02:00~12:00 봉 중 가격이 CE에 처음 닿는 봉
      (직전 종가가 CE 위면 위에서 내려온 것 → 매수 지정가 CE, 아래면 매도). 갭 하나에 1번. 손절 = 갭 반대 끝 ∓ 1핍, 목표 2R.
 FILL = 갭 메우기: 갭이 그 뒤 첫 NY 02:00까지 안 메워졌으면 그 봉 시가에 갭 쪽으로 진입, 목표 = 갭 이전 종가, 손절 = 같은 거리(1R).
 → 2×2 = 4개
합계 기본 28개 × 바이어스 끔/켬 = 56개 변형 (이름 뒤 '+B' = 바이어스 켬).

판정(trading/projects/02-ict/README.md 합격 기준, 미리 정함):
 IS = 2019-01-01 ~ 2023-12-31, OOS = 2024-01-01 ~. 합격 = 아래 모두:
  OOS 60건 이상 / OOS 평균 R > 0 / OOS PF ≥ 1.2 / IS 평균 R > 0 / 종목 과반에서 IS·OOS 합계 둘 다 + /
  연도 과반 + / IS t ≥ Bonferroni 기준(한쪽 5%, 변형 56개 → 약 3.1) / 랜덤워크(스프레드 0) t < 2.
 하나라도 못 넘으면: IS·OOS 평균이 둘 다 + 면 '후보'(실전 권유 안 함), 아니면 '불합격'.

사용:
  py -3.12 ict_backtest.py --selftest
  py -3.12 ict_backtest.py --data-dir C:\\Users\\kun00\\venus\\mt5_m5_data --out C:\\Users\\kun00\\venus\\ict_bt_out
  옵션: --symbols EURUSD,GBPUSD  --models M1,M3  --spread-map EURUSD=1,XAUUSD=2  --pip-map XAUUSD=0.1  --rw 2
필요: Python 3.10+, pandas, numpy.
"""
import argparse
import math
import os
import sys
import time as _time
from collections import defaultdict

try:
    import numpy as np
    import pandas as pd
except ImportError:  # 설치 안내만
    print("pandas/numpy not found. Run:  py -3.12 -m pip install pandas numpy")
    sys.exit(1)

NS_MIN = 60 * 1_000_000_000
NS_H = 60 * NS_MIN
NS_D = 24 * NS_H
SERVER_MINUS_NY = 7
OOS_START = "2024-01-01"
SL_BUF_PIPS = 1.0
MIN_RISK_SPREADS, MIN_RISK_PIPS = 4.0, 2.0
MIN_RR_LIQ, MIN_RR_SB = 1.5, 2.0
CONSOL_X = 0.4            # M2 횡보: 범위 ≤ 0.4 × ADR20
SPREAD_FLOOR = {"XAUUSD": 2.0}   # 핍 단위 최소 스프레드(금 0.2달러). 나머지 1핍
DEFAULT_SPREAD = 1.0
MSS_N, MSS_LOOKBACK = 5, 72

# ---------------------------------------------------------------- 변형 목록 (미리 고정)
BASE_VARIANTS = (
    [("M1", f"M1-{c}-{e}-{t}") for c in ("C4", "C45") for e in ("FVG", "PDCE") for t in ("PDH", "2R")] +
    [("M2", f"M2-{r}-{s}") for r in ("ASIA", "CBDR") for s in ("SD1", "SD2")] +
    [("M3", f"M3-{e}-{t}") for e in ("MKT", "FVG") for t in ("OPP", "2R")] +
    [("M4", f"M4-{w}-{e}") for w in ("NY", "LDN") for e in ("EDGE", "CE")] +
    [("M5", f"M5-{c}-{t}") for c in ("H1", "D1") for t in ("HIGH", "2R")] +
    [("M6", f"M6-{g}-{m}") for g in ("NDOG", "NWOG") for m in ("CE", "FILL")]
)
VARIANTS = [v for _, b in BASE_VARIANTS for v in (b, b + "+B")]
MODEL_OF = {b: m for m, b in BASE_VARIANTS}
MODEL_DESC = {"M1": "일봉 3봉 스윙+확인", "M2": "딜링 레인지 SD 되돌림", "M3": "주다스 스윙(런던)",
              "M4": "실버 불릿", "M5": "IFVG CE 지키기", "M6": "NDOG/NWOG"}


# ---------------------------------------------------------------- 데이터 읽기 (crt_backtest.py 에서 복사)
def _norm(c):
    return str(c).strip().strip("<>").strip().lower().replace(" ", "_")


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
        ts = _parse_time(df[cdate].astype(str).str.strip() + " " + df[ctime].astype(str).str.strip())
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


def parse_map(s, cast=float):
    out = {}
    if s:
        for part in s.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip().upper()] = cast(v)
    return out


# ---------------------------------------------------------------- 시간 도구
def server_to_ny(ts):
    return pd.DatetimeIndex(ts) - pd.Timedelta(hours=SERVER_MINUS_NY)


def _us_dst_bounds(year):
    mar1 = pd.Timestamp(year=year, month=3, day=1)
    second_sun = mar1 + pd.Timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = pd.Timestamp(year=year, month=11, day=1)
    first_sun = nov1 + pd.Timedelta(days=(6 - nov1.weekday()) % 7)
    return second_sun + pd.Timedelta(hours=2), first_sun + pd.Timedelta(hours=2)


def server_to_kst(ts):
    """서버시간(뉴욕+7) -> 한국시간. 뉴욕 서머타임이면 +13, 아니면 +14."""
    ny = server_to_ny(ts)
    dst = np.zeros(len(ny), dtype=bool)
    for y in np.unique(ny.year):
        a, b = _us_dst_bounds(int(y))
        m = (ny.year == y)
        dst |= m & (ny >= a) & (ny < b)
    return ny + pd.to_timedelta(np.where(dst, 13, 14), unit="h")


def ny_to_server_hour(ny_hour):
    """NY 시각(시, 소수 가능) -> 그 거래일 서버 자정 기준 시(음수면 전날). NY 17시 = 0."""
    h = ny_hour + SERVER_MINUS_NY
    return h - 24 if h >= 24 else h


# ---------------------------------------------------------------- 작은 판정 함수 (자체 시험 대상)
def swing3_low(L, k):
    """3봉 스윙 저점: L[k] < L[k-1] and L[k+1] > L[k]."""
    return L[k] < L[k - 1] and L[k + 1] > L[k]


def untaken_swing_low(L, k, lookback):
    """k 시점 전에 확정된(j+1 <= k-1) 앞뒤 1봉 스윙 저점 중 아직 안 깨진 가장 최근 것의 인덱스. 없으면 -1."""
    for j in range(k - 2, max(0, k - lookback), -1):
        if L[j] < L[j - 1] and L[j] < L[j + 1]:
            if min(L[j + 1:k]) > L[j]:
                return j
    return -1


def fvg_bull(H, L, i):
    """봉 i(세 번째 봉)에서 상승 FVG: L[i] > H[i-2]. 돌려줌 (아래, 위) 또는 None."""
    return (H[i - 2], L[i]) if L[i] > H[i - 2] else None


def fvg_bear(H, L, i):
    """하락 FVG: H[i] < L[i-2]. 돌려줌 (아래, 위) 또는 None."""
    return (H[i], L[i - 2]) if H[i] < L[i - 2] else None


def ifvg_convert(C, q, top, lim):
    """하락 FVG(q에서 생김)가 IFVG가 되는 첫 봉: q+1 ~ lim-1 중 종가 > 위 끝. 없으면 -1."""
    if lim <= q + 1:
        return -1
    idx = np.flatnonzero(np.asarray(C[q + 1:lim]) > top)
    return int(q + 1 + idx[0]) if len(idx) else -1


def sd_levels(rh, rl):
    """딜링 레인지 표준편차 선. {k: (아래, 위)}"""
    rg = rh - rl
    return {k: (rl - k * rg, rh + k * rg) for k in (0.5, 1.0, 2.0, 2.5)}


def fractal_high(H, n):
    m = len(H)
    ok = np.zeros(m, bool)
    if m > 2 * n:
        ok[n:m - n] = True
        for j in range(1, n + 1):
            ok[n:m - n] &= (H[n:m - n] > H[n - j:m - n - j]) & (H[n:m - n] >= H[n + j:m - n + j])
    return ok


def first_true(mask):
    idx = np.flatnonzero(mask)
    return int(idx[0]) if len(idx) else -1


# ---------------------------------------------------------------- 종목 준비
class Ctx:
    """방향과 무관한 시간 구조(일·주·H1 인덱스, 바이어스 원재료)."""

    def __init__(self, df, pip, spread_pips):
        self.t = df.index.values.astype("datetime64[ns]").astype(np.int64)
        self.n = len(self.t)
        self.pip = pip
        self.cost = spread_pips * pip
        self.buf = SL_BUF_PIPS * pip
        self.min_risk = max(MIN_RISK_SPREADS * self.cost, MIN_RISK_PIPS * pip)
        t = self.t
        day = t // NS_D
        self.dstart = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
        self.dend = np.r_[self.dstart[1:], self.n]               # 끝(미포함)
        self.dkey = day[self.dstart]
        self.nd = len(self.dkey)
        self.bar_day = np.repeat(np.arange(self.nd), self.dend - self.dstart)
        self.hr = ((t // NS_H) % 24).astype(np.int64)            # 서버 시
        self.win_02_12 = (self.hr >= 9) & (self.hr < 19)          # NY 02:00~12:00
        self.exit_idx = np.searchsorted(t, self.dkey * NS_D + 23 * NS_H) - 1   # NY 16:00 직전 봉
        wk = (self.dkey + 3) // 7                                  # 월요일 시작 주
        self.wfirst_d = np.flatnonzero(np.r_[True, wk[1:] != wk[:-1]])
        self.dweek = np.repeat(np.arange(len(self.wfirst_d)), np.diff(np.r_[self.wfirst_d, self.nd]))
        self.nw = len(self.wfirst_d)
        hk = t // NS_H
        self.hstart = np.flatnonzero(np.r_[True, hk[1:] != hk[:-1]])
        self.hend = np.r_[self.hstart[1:], self.n]
        self.hT = hk[self.hstart] * NS_H
        self.h_close_m5 = np.searchsorted(t, self.hT + NS_H)     # H1 봉 마감 후 첫 M5
        self.d_h1_first = np.searchsorted(self.hT, self.dkey * NS_D)
        self.d_h1_end = np.searchsorted(self.hT, (self.dkey + 1) * NS_D)

    def idx(self, d, hour):
        """거래일 d(일봉 인덱스)의 서버 hour시(음수 = 전날) 이후 첫 M5 인덱스."""
        return int(np.searchsorted(self.t, self.dkey[d] * NS_D + int(round(hour * NS_H))))


class Space:
    """가격 공간. sd=+1 그대로, sd=-1 뒤집기(매도를 매수처럼 계산)."""

    def __init__(self, X, o, h, l, c, sd):
        if sd == -1:
            o, h, l, c = -o, -l, -h, -c
        self.sd = sd
        self.O, self.H, self.L, self.C = o, h, l, c
        self.Ol, self.Hl, self.Ll, self.Cl = o.tolist(), h.tolist(), l.tolist(), c.tolist()
        s, e = X.dstart, X.dend
        self.dO, self.dC = o[s], c[e - 1]
        self.dH, self.dL = np.maximum.reduceat(h, s), np.minimum.reduceat(l, s)
        self.dHl, self.dLl = self.dH.tolist(), self.dL.tolist()
        ws = X.wfirst_d
        self.wH, self.wL = np.maximum.reduceat(self.dH, ws), np.minimum.reduceat(self.dL, ws)
        self.wC = self.dC[np.r_[ws[1:], X.nd] - 1]
        hs, he = X.hstart, X.hend
        self.hO, self.hC = o[hs], c[he - 1]
        self.hH, self.hL = np.maximum.reduceat(h, hs), np.minimum.reduceat(l, hs)
        self.hHl, self.hLl = self.hH.tolist(), self.hL.tolist()
        self.frh = fractal_high(h, MSS_N).tolist()
        # 바이어스(이 공간 기준 +1 = 매수 허용)
        nd = X.nd
        b = np.zeros(nd, int)
        for i in range(2, nd):
            w = X.dweek[i]
            if w < 2:
                continue
            wb = np.sign(self.wC[w - 1] - (self.wH[w - 2] + self.wL[w - 2]) / 2)
            db = np.sign(self.dC[i - 1] - (self.dH[i - 2] + self.dL[i - 2]) / 2)
            b[i] = wb if wb == db else 0
        self.bias = b
        rng = self.dH - self.dL
        cs = np.r_[0, np.cumsum(rng)]
        self.adr20 = np.full(nd, np.nan)
        self.adr20[20:] = (cs[20:nd] - cs[0:nd - 20]) / 20


# ---------------------------------------------------------------- 체결·청산
def simulate(S, X, f, entry, sl, tp, limit):
    """봉 f에 entry로 진입(limit=True 지정가 체결 봉, False 시가 진입). 같은 날 NY16:00 직전 봉까지.
    돌려줌 (청산 인덱스, 청산가, 결과)."""
    iend = int(X.exit_idx[X.bar_day[f]])
    H, L, O, C = S.H, S.L, S.O, S.C
    if L[f] <= sl:                        # 체결 봉: 손절만 본다
        return f, sl, "loss"
    if f >= iend:
        return f, C[f], "time"
    a, b = f + 1, iend + 1
    s_hit = first_true(L[a:b] <= sl)
    t_hit = first_true(H[a:b] >= tp)
    if s_hit >= 0 and (t_hit < 0 or s_hit <= t_hit):
        k = a + s_hit
        return k, (O[k] if O[k] <= sl else sl), "loss"
    if t_hit >= 0:
        k = a + t_hit
        return k, tp, "win"                # 목표 갭 통과도 목표가로(보수적)
    return iend, C[iend], "time"


def limit_fill(S, j0, j1, entry, tp):
    """j0~j1-1 봉 동안 지정가 매수 entry. 목표 tp에 먼저 닿으면(같은 봉 포함) 취소. 체결 봉 인덱스 또는 -1."""
    if j1 <= j0:
        return -1
    fi = first_true(S.L[j0:j1] <= entry)
    ti = first_true(S.H[j0:j1] >= tp)
    if fi < 0 or (0 <= ti <= fi):
        return -1
    return j0 + fi


class Collector:
    def __init__(self, X):
        self.X = X
        self.rows = []
        self.fun = defaultdict(lambda: defaultdict(int))

    def count(self, base, stage, k=1):
        self.fun[base][stage] += k

    def trade(self, S, base, key, dec, f, entry, sl, tp, limit, struct, day):
        X = self.X
        risk = entry - sl
        if risk <= 0 or risk < X.min_risk or tp <= entry:
            self.count(base, "skip_risk")
            return
        xi, px, res = simulate(S, X, f, entry, sl, tp, limit)
        r = (px - entry - X.cost) / risk
        sd = S.sd
        self.rows.append((base, sd, key, dec, f, xi, sd * entry, sd * sl, sd * tp, r, res, risk / X.pip,
                          int(S.bias[day]) == 1, struct))
        self.count(base, "fill")


# ---------------------------------------------------------------- 모델
def daily_setups(S, X):
    """M1 일봉 스윙 저점 셋업: [(k, kinds)]."""
    dL = S.dLl
    out = []
    for k in range(2, X.nd - 2):
        if not swing3_low(dL, k):
            continue
        kinds = []
        w = X.dweek[k]
        if w >= 1:
            first = X.wfirst_d[w]
            pmin = min(dL[first:k]) if k > first else math.inf
            pwl = S.wL[w - 1]
            if dL[k] < pwl <= pmin:
                kinds.append("PWL")
        j = untaken_swing_low(dL, k, 60)
        if j >= 1 and dL[k] < dL[j]:
            kinds.append("DSL")
        if kinds:
            out.append((k, "+".join(kinds)))
    return out


def model_m1(S, X, col, dsetups):
    for k, kind in dsetups:
        for conf in ("C4", "C45"):
            T = k + 3 if conf == "C4" else k + 4
            if T >= X.nd:
                continue
            if not S.dC[k + 2] > S.dO[k + 2]:
                continue
            if conf == "C45" and not S.dC[k + 3] > S.dO[k + 3]:
                continue
            for e in ("FVG", "PDCE"):
                for tg in ("PDH", "2R"):
                    col.count(f"M1-{conf}-{e}-{tg}", "setup")
            s0, s1 = X.idx(T, 15.5), X.idx(T, 18)
            if s1 - s0 < 3:
                continue
            pdh, pdl = S.dH[T - 1], S.dL[T - 1]
            H, L = S.Hl, S.Ll
            orders = {}
            for i in range(max(s0, 11), s1):
                g = fvg_bull(H, L, i)
                if g:
                    orders["FVG"] = (i, (g[0] + g[1]) / 2, min(L[i - 11:i + 1]) - X.buf)
                    break
            ce = (pdh + pdl) / 2
            if S.O[s0] > ce:
                orders["PDCE"] = (s0 - 1, ce, pdl + 0.25 * (pdh - pdl) - X.buf)
            for e, (i, entry, sl) in orders.items():
                risk = entry - sl
                for tg in ("PDH", "2R"):
                    base = f"M1-{conf}-{e}-{tg}"
                    tp = pdh if tg == "PDH" else entry + 2 * risk
                    if risk <= 0 or (tg == "PDH" and tp - entry < MIN_RR_LIQ * risk):
                        col.count(base, "skip_rr")
                        continue
                    col.count(base, "order")
                    f = limit_fill(S, i + 1, s1, entry, tp)
                    if f >= 0:
                        col.trade(S, base, (k, S.sd, conf), f, f, entry, sl, tp, True, False, T)


def model_m2(S, X, col):
    for i in range(21, X.nd):
        adr = S.adr20[i]
        for rname, (ra, rb, need) in (("ASIA", (2, 7, 30)), ("CBDR", (-3, 3, 36))):
            a, b = X.idx(i, ra), X.idx(i, rb)
            if b - a < need:
                continue
            for s in ("SD1", "SD2"):
                col.count(f"M2-{rname}-{s}", "setup")
            rh, rl = S.H[a:b].max(), S.L[a:b].min()
            rg = rh - rl
            if not (0 < rg <= CONSOL_X * adr):
                continue
            we = X.idx(i, 18)
            lv = sd_levels(rh, rl)
            for s, k, ks in (("SD1", 1.0, 2.0), ("SD2", 2.0, 2.5)):
                base = f"M2-{rname}-{s}"
                col.count(base, "consol")
                entry, sl, tp = lv[k][0], lv[ks][0] - X.buf, rl
                f = first_true(S.L[b:we] <= entry)
                if f < 0:
                    continue
                f += b
                col.trade(S, base, (i, rname, s), f, f, entry, sl, tp, True, False, i)


def model_m3(S, X, col):
    H, L, C, O, frh = S.Hl, S.Ll, S.Cl, S.Ol, S.frh
    for i in range(1, X.nd):
        ra, rb = X.idx(i, 2), X.idx(i, 7)
        if rb - ra < 30:
            continue
        ah, al = S.H[ra:rb].max(), S.L[ra:rb].min()
        ws, we, me, oe = X.idx(i, 9), X.idx(i, 12), X.idx(i, 13), X.idx(i, 15)
        if we <= ws:
            continue
        s = first_true(S.L[rb:we] < al)
        if s < 0:
            continue
        s += rb
        if s < ws or S.H[rb:s + 1].max() > ah:
            continue
        for v in ("M3-MKT-OPP", "M3-MKT-2R", "M3-FVG-OPP", "M3-FVG-2R"):
            col.count(v, "setup")
        ext, k_mss = s, -1
        for k in range(s, me):
            if L[k] < L[ext]:
                ext = k
            lvl = None
            for m in range(ext - 1, max(ext - MSS_LOOKBACK, MSS_N) - 1, -1):
                if frh[m] and m + MSS_N <= k:
                    lvl = H[m]
                    break
            if lvl is not None and C[k] > lvl and C[k] > O[k] and C[k] > al:
                k_mss = k
                break
        if k_mss < 0:
            continue
        k = k_mss
        sl = L[ext] - X.buf
        for v in ("M3-MKT-OPP", "M3-MKT-2R", "M3-FVG-OPP", "M3-FVG-2R"):
            col.count(v, "mss")
        # MKT
        f = k + 1
        if f < X.n and X.bar_day[f] == i:
            entry = O[f]
            for tg in ("OPP", "2R"):
                base = f"M3-MKT-{tg}"
                risk = entry - sl
                tp = ah if tg == "OPP" else entry + 2 * risk
                if risk <= 0 or (tg == "OPP" and tp - entry < MIN_RR_LIQ * risk):
                    col.count(base, "skip_rr")
                    continue
                col.trade(S, base, i, k, f, entry, sl, tp, False, True, i)
        # FVG
        g = None
        for i3 in range(k, ext + 1, -1):
            if i3 - 2 >= ext:
                g = fvg_bull(H, L, i3)
                if g:
                    break
        if g is None:
            continue
        entry = (g[0] + g[1]) / 2
        risk = entry - sl
        for tg in ("OPP", "2R"):
            base = f"M3-FVG-{tg}"
            tp = ah if tg == "OPP" else entry + 2 * risk
            if risk <= 0 or entry >= C[k] or (tg == "OPP" and tp - entry < MIN_RR_LIQ * risk):
                col.count(base, "skip_rr")
                continue
            col.count(base, "order")
            f = limit_fill(S, k + 1, oe, entry, tp)
            if f >= 0:
                col.trade(S, base, i, k, f, entry, sl, tp, True, True, i)


def model_m4(S, X, col):
    H, L = S.Hl, S.Ll
    for i in range(1, X.nd):
        d0 = X.dstart[i]
        a_r, b_r = X.idx(i, 2), X.idx(i, 7)
        for wname, (wh0, wh1) in (("NY", (17, 18)), ("LDN", (10, 11))):
            ws, we = X.idx(i, wh0), X.idx(i, wh1)
            if we - ws < 3 or ws <= d0:
                continue
            o = S.O[ws]
            ups, dns = [], []
            if S.H[d0:ws].max() < S.dH[i - 1]:
                ups.append(S.dH[i - 1])
            if S.L[d0:ws].min() > S.dL[i - 1]:
                dns.append(S.dL[i - 1])
            if b_r - a_r >= 30 and ws > b_r:
                ah, al = S.H[a_r:b_r].max(), S.L[a_r:b_r].min()
                if S.H[b_r:ws].max() < ah:
                    ups.append(ah)
                if S.L[b_r:ws].min() > al:
                    dns.append(al)
            if wname == "NY":
                la, lb = X.idx(i, 9), X.idx(i, 12)
                if lb - la >= 18 and ws > lb:
                    lh, ll = S.H[la:lb].max(), S.L[la:lb].min()
                    if S.H[lb:ws].max() < lh:
                        ups.append(lh)
                    if S.L[lb:ws].min() > ll:
                        dns.append(ll)
            ups = [x for x in ups if x > o]
            dns = [x for x in dns if x < o]
            if not ups:
                continue
            up = min(ups)
            if dns and (o - max(dns)) <= (up - o):
                continue
            for e in ("EDGE", "CE"):
                col.count(f"M4-{wname}-{e}", "setup")
            g = None
            for i3 in range(max(ws, 11), we):
                g = fvg_bull(H, L, i3)
                if g:
                    break
            if g is None:
                continue
            sl = min(L[i3 - 11:i3 + 1]) - X.buf
            for e in ("EDGE", "CE"):
                base = f"M4-{wname}-{e}"
                entry = g[1] if e == "EDGE" else (g[0] + g[1]) / 2
                risk = entry - sl
                if risk <= 0 or up - entry < MIN_RR_SB * risk:
                    col.count(base, "skip_rr")
                    continue
                col.count(base, "order")
                f = limit_fill(S, i3 + 1, we, entry, up)
                if f >= 0:
                    col.trade(S, base, (i, wname), i3, f, entry, sl, up, True, True, i)


def ifvg_trigger(S, X, fvgs, j0, j1):
    """IFVG 목록 [(활성 M5 인덱스, 아래, 위)] 중 j0~j1-1, NY02~12시에 처음 'CE 터치 + 종가 CE 위'가 난 봉. (봉, 아래) 또는 None."""
    best = None
    for act, bot, top in fvgs:
        ce = (bot + top) / 2
        a = max(act, j0)
        if a >= j1:
            continue
        death = first_true(S.C[act:j1] <= ce)
        death = act + death if death >= 0 else j1
        trig = first_true((S.L[a:j1] <= ce) & (S.C[a:j1] > ce) & X.win_02_12[a:j1])
        if trig < 0:
            continue
        trig += a
        if trig < death and (best is None or trig < best[0]):
            best = (trig, bot)
    return best


def h1_bear_fvgs(S, X, q0, q1, conv_lim):
    """H1 q0~q1(포함) 하락 FVG 중 conv_lim(H1 인덱스, 미포함) 전에 IFVG로 바뀐 것: [(활성 M5, 아래, 위)]."""
    out = []
    for q in range(max(q0 + 2, 2), q1 + 1):
        g = fvg_bear(S.hHl, S.hLl, q)
        if g is None:
            continue
        cv = ifvg_convert(S.hC, q, g[1], conv_lim)
        if cv >= 0:
            out.append((int(X.h_close_m5[cv]), g[0], g[1]))
    return out


def m5_enter(S, X, col, ctx, key, fvgs, j0, j1, leg_hi):
    hit = ifvg_trigger(S, X, fvgs, j0, j1)
    if hit is None:
        return
    j, bot = hit
    f = j + 1
    if f >= X.n or X.bar_day[f] != X.bar_day[j]:
        return
    entry, sl = S.O[f], bot - X.buf
    risk = entry - sl
    for tg in ("HIGH", "2R"):
        base = f"M5-{ctx}-{tg}"
        col.count(base, "trigger")
        tp = leg_hi if tg == "HIGH" else entry + 2 * risk
        if risk <= 0 or (tg == "HIGH" and tp - entry < MIN_RR_LIQ * risk):
            col.count(base, "skip_rr")
            continue
        col.trade(S, base, key, j, f, entry, sl, tp, False, False, int(X.bar_day[f]))


def model_m5(S, X, col, dsetups):
    hL, hH = S.hLl, S.hHl
    nh = len(hL)
    for k in range(24, nh - 3):
        if not swing3_low(hL, k):
            continue
        j = untaken_swing_low(hL, k, 48)
        if j < 1 or not hL[k] < hL[j]:
            continue
        if not S.hC[k + 2] > S.hO[k + 2]:
            continue
        for tg in ("HIGH", "2R"):
            col.count(f"M5-H1-{tg}", "setup")
        ls = k - 24 + int(np.argmax(S.hH[k - 24:k + 1]))
        lim = min(k + 2 + 24, nh - 1)
        fvgs = h1_bear_fvgs(S, X, ls, k, lim)
        if not fvgs:
            continue
        j0, j1 = int(X.h_close_m5[k + 2]), int(X.h_close_m5[lim])
        m5_enter(S, X, col, "H1", ("H1", k, S.sd), fvgs, j0, j1, hH[ls])
    for k, _ in dsetups:
        T = k + 3
        if T >= X.nd or not S.dC[k + 2] > S.dO[k + 2]:
            continue
        for tg in ("HIGH", "2R"):
            col.count(f"M5-D1-{tg}", "setup")
        a = max(0, k - 10)
        ls = a + int(np.argmax(S.dH[a:k + 1]))
        j0, j1 = X.idx(T, 9), X.idx(T, 19)
        q0, q1 = int(X.d_h1_first[ls]), int(X.d_h1_end[k]) - 1
        lim = int(np.searchsorted(X.hT, X.t[j1 - 1] if j1 > 0 else 0, side="right")) - 1   # j1 직전 봉이 속한 H1(미포함) → 마감된 것만
        fvgs = h1_bear_fvgs(S, X, q0, q1, lim)
        if not fvgs or j1 <= j0:
            continue
        m5_enter(S, X, col, "D1", ("D1", k, S.sd), fvgs, j0, j1, S.dH[ls])


def gaps(X, S_plus):
    """[(종류, 키, 형성 M5 인덱스, 갭 전 종가, 갭 후 시가, 진입 검색 끝(미포함), FILL 진입 인덱스)] (원래 가격)."""
    out = []
    t = X.t
    C, O = S_plus.C, S_plus.O
    for w in range(1, X.nw):
        d = X.wfirst_d[w]
        f = int(X.dstart[d])
        wend_d = (X.wfirst_d[w + 1] if w + 1 < X.nw else X.nd) - 1
        out.append(("NWOG", ("NWOG", w), f, C[f - 1], O[f], int(X.exit_idx[wend_d]) + 1, X.idx(d, 9), d, wend_d))
    for d in range(1, X.nd):
        if pd.Timestamp(int(X.dkey[d] * NS_D)).dayofweek != 1:      # 서버 화요일 = NY 월요일 17:00 이후
            continue
        f = X.idx(d, 1)
        pre = int(X.dstart[d]) - 1
        if f >= X.dend[d] or t[f] - X.dkey[d] * NS_D >= 2 * NS_H or pre < 0 or X.dkey[d] * NS_D - t[pre] > NS_H:
            continue
        w = X.dweek[d]
        wend_d = (X.wfirst_d[w + 1] if w + 1 < X.nw else X.nd) - 1
        out.append(("NDOG", ("NDOG", d), f, C[pre], O[f], int(X.exit_idx[wend_d]) + 1, X.idx(d, 9), d, wend_d))
    return out


def model_m6(S, X, col, glist):
    sd = S.sd
    for kind, key, f, pc, po, jend, efill, d, _ in glist:
        pc, po = sd * pc, sd * po
        if pc == po:
            continue
        lo, hi = min(pc, po), max(pc, po)
        ce = (lo + hi) / 2
        # CE: 첫 터치(어느 쪽이든), 이 공간에서는 위에서 내려온 경우만 매수
        base = f"M6-{kind}-CE"
        if sd == 1:
            col.count(base, "setup")
        if jend > f + 1:
            prev = S.C[f:jend - 1]
            win = X.win_02_12[f + 1:jend]
            lt = (prev > ce) & (S.L[f + 1:jend] <= ce) & win
            st = (prev < ce) & (S.H[f + 1:jend] >= ce) & win
            j = first_true(lt | st)
            if j >= 0:
                j += f + 1
                if S.C[j - 1] > ce:
                    col.trade(S, base, key, j, j, ce, lo - X.buf, ce + 2 * (ce - lo + X.buf), True, True, int(X.bar_day[j]))
        # FILL: 갭 아래로 열렸고(po < pc) 첫 NY 02:00까지 안 메워짐 → 매수, 목표 pc
        base = f"M6-{kind}-FILL"
        if sd == 1:
            col.count(base, "setup")
        if po < pc and efill > f and efill < X.n and X.bar_day[efill] == d and S.H[f:efill].max() < pc:
            entry = S.O[efill]
            if entry < pc:
                col.trade(S, base, key, efill, efill, entry, entry - (pc - entry), pc, False, True, d)


# ---------------------------------------------------------------- 종목 실행
COLS = ["variant_base", "dir", "key", "dec_i", "fill_i", "exit_i", "entry", "sl", "tp", "R", "result", "risk_pips",
        "bias_ok", "struct"]


def run_symbol(sym, df, pip, spread_pips, models=None):
    models = models or ["M1", "M2", "M3", "M4", "M5", "M6"]
    X = Ctx(df, pip, spread_pips)
    o, h, l, c = (df[x].values.astype(float) for x in ("o", "h", "l", "c"))
    col = Collector(X)
    sp = {sd: Space(X, o, h, l, c, sd) for sd in (1, -1)}
    glist = gaps(X, sp[1]) if "M6" in models else []
    for sd in (1, -1):
        S = sp[sd]
        dsetups = daily_setups(S, X) if ("M1" in models or "M5" in models) else []
        if "M1" in models:
            model_m1(S, X, col, dsetups)
        if "M2" in models:
            model_m2(S, X, col)
        if "M3" in models:
            model_m3(S, X, col)
        if "M4" in models:
            model_m4(S, X, col)
        if "M5" in models:
            model_m5(S, X, col, dsetups)
        if "M6" in models:
            model_m6(S, X, col, glist)
    raw = pd.DataFrame(col.rows, columns=COLS)
    trades, funnel = finalize(raw, X, sym, col.fun, models)
    return trades, funnel, (int(X.t[0]), int(X.t[-1]))


def _dedupe(df):
    """같은 키에서 결정 봉이 가장 빠른 것 하나. 같은 봉에서 둘이면 둘 다 버림."""
    if df.empty:
        return df
    df = df.copy()
    df["_k"] = df["key"].astype(str)
    first = df.groupby("_k")["dec_i"].transform("min")
    df = df[df["dec_i"] == first]
    cnt = df.groupby("_k")["dec_i"].transform("size")
    return df[cnt == 1].drop(columns="_k")


def _one_position(df):
    df = df.sort_values(["fill_i", "exit_i"])
    keep, last = [], -1
    for fi, xi in zip(df["fill_i"].values, df["exit_i"].values):
        ok = fi > last
        keep.append(ok)
        if ok:
            last = xi
    return df[np.array(keep, bool)] if len(df) else df


def finalize(raw, X, sym, fun, models):
    out, funnel = [], []
    for base in [b for m, b in BASE_VARIANTS if m in models]:
        g = raw[raw["variant_base"] == base]
        for bias_on in (False, True):
            v = base + ("+B" if bias_on else "")
            a, b = g[g["struct"]], g[~g["struct"]]
            a = _dedupe(a)
            if bias_on:
                a, b = a[a["bias_ok"]], b[b["bias_ok"]]
            b = _dedupe(b)
            gg = pd.concat([a, b])
            n_c = len(gg)
            gg = _one_position(gg)
            fr = dict(symbol=sym, variant=v, model=MODEL_OF[base])
            fr.update({k: int(x) for k, x in fun[base].items()})
            fr.update(after_bias_dedupe=n_c, trades=len(gg))
            funnel.append(fr)
            if len(gg):
                gg = gg.copy()
                gg["variant"] = v
                out.append(gg)
    tr = pd.concat(out) if out else pd.DataFrame(columns=COLS + ["variant"])
    if len(tr):
        t = X.t
        tr["symbol"] = sym
        tr["model"] = tr["variant_base"].map(MODEL_OF)
        tr["t_fill_ns"] = t[tr["fill_i"].values]
        tr["fill_server"] = pd.DatetimeIndex(pd.to_datetime(tr["t_fill_ns"])).strftime("%Y-%m-%d %H:%M")
        tr["fill_ny"] = server_to_ny(pd.to_datetime(tr["t_fill_ns"])).strftime("%Y-%m-%d %H:%M")
        tr["fill_kst"] = server_to_kst(pd.to_datetime(tr["t_fill_ns"])).strftime("%Y-%m-%d %H:%M")
        tr["setup_server"] = pd.DatetimeIndex(t[tr["dec_i"].values]).strftime("%Y-%m-%d %H:%M")
        tr["exit_server"] = pd.DatetimeIndex(t[tr["exit_i"].values]).strftime("%Y-%m-%d %H:%M")
        tr["exit_kst"] = server_to_kst(pd.to_datetime(t[tr["exit_i"].values])).strftime("%Y-%m-%d %H:%M")
        tr["period"] = np.where(tr["t_fill_ns"] < pd.Timestamp(OOS_START).value, "IS", "OOS")
        tr["year"] = pd.DatetimeIndex(pd.to_datetime(tr["t_fill_ns"])).year
        tr["dir"] = np.where(tr["dir"] == 1, "BUY", "SELL")
    return tr, funnel


# ---------------------------------------------------------------- 통계·판정
def stats(r):
    r = np.asarray(r, float)
    n = len(r)
    if n == 0:
        return dict(n=0, avg=np.nan, pf=np.nan, t=np.nan, dd=np.nan, win=np.nan, sum=0.0)
    cum = np.cumsum(r)
    dd = np.max(np.maximum.accumulate(np.r_[0, cum]) - np.r_[0, cum])
    gp, gl = r[r > 0].sum(), -r[r < 0].sum()
    se = r.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return dict(n=n, avg=r.mean(), pf=(gp / gl) if gl > 0 else np.inf,
                t=(r.mean() / se) if (se and se > 0) else np.nan, dd=dd, win=100 * (r > 0).mean(), sum=r.sum())


def norm_ppf(p):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if 0.5 * math.erfc(-mid / math.sqrt(2)) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def judge(tr, symbols, variants, rw=None):
    """변형마다 README 기준 판정. rw = 랜덤워크 거래표(없으면 그 기준은 '미시험')."""
    crit = norm_ppf(1 - 0.05 / max(1, len(variants)))
    rows = []
    for v in variants:
        g = tr[tr["variant"] == v].sort_values("t_fill_ns") if len(tr) else tr
        si = stats(g[g["period"] == "IS"]["R"].values) if len(g) else stats([])
        so = stats(g[g["period"] == "OOS"]["R"].values) if len(g) else stats([])
        sa = stats(g["R"].values) if len(g) else stats([])
        both = 0
        for s in symbols:
            gs = g[g["symbol"] == s] if len(g) else g
            if len(gs) and gs[gs["period"] == "IS"]["R"].sum() > 0 and gs[gs["period"] == "OOS"]["R"].sum() > 0:
                both += 1
        yr = g.groupby("year")["R"].sum() if len(g) else pd.Series(dtype=float)
        ypos, ny = int((yr > 0).sum()), len(yr)
        rws = stats(rw[rw["variant"] == v]["R"].values) if rw is not None and len(rw) else None
        checks = {
            "OOS≥60건": so["n"] >= 60,
            "OOS평균>0": so["n"] > 0 and so["avg"] > 0,
            "OOS PF≥1.2": so["n"] > 0 and so["pf"] >= 1.2,
            "IS평균>0": si["n"] > 0 and si["avg"] > 0,
            "종목과반 둘다+": both > len(symbols) / 2,
            "연도과반+": ny > 0 and ypos > ny / 2,
            f"IS t≥{crit:.2f}": si["n"] > 1 and si["t"] >= crit,
            "랜덤워크 t<2": (rws is not None and (rws["n"] < 2 or not (rws["t"] >= 2.0))),
        }
        fails = [k for k, ok in checks.items() if not ok]
        if not fails:
            verdict = "합격"
        elif si["n"] and so["n"] and si["avg"] > 0 and so["avg"] > 0:
            verdict = "후보"
        else:
            verdict = "불합격"
        rows.append(dict(variant=v, model=MODEL_OF[v.replace("+B", "")], bias=v.endswith("+B"),
                         IS_n=si["n"], IS_avgR=si["avg"], IS_PF=si["pf"], IS_t=si["t"], IS_dd=si["dd"],
                         OOS_n=so["n"], OOS_avgR=so["avg"], OOS_PF=so["pf"], OOS_t=so["t"], OOS_dd=so["dd"],
                         ALL_n=sa["n"], ALL_avgR=sa["avg"], ALL_dd=sa["dd"],
                         sym_both_pos=both, n_sym=len(symbols), years_pos=ypos, n_years=ny,
                         RW_n=(rws["n"] if rws else np.nan), RW_avgR=(rws["avg"] if rws else np.nan),
                         RW_t=(rws["t"] if rws else np.nan), bonf_t=crit, verdict=verdict, fails=", ".join(fails)))
    return pd.DataFrame(rows)


def f2(x, nd=2):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "-"
    if np.isinf(x):
        return "inf"
    return f"{x:+.{nd}f}" if nd == 3 else f"{x:.{nd}f}"


def write_text(path, jd, tr, funnel, meta, symbols):
    L = ["프로젝트 2: ICT 모델 백테스트 요약 (정보 제공용. 매매 결정은 석준님)", "=" * 78]
    for k, v in meta.items():
        L.append(f"{k}: {v}")
    L.append("")
    n_ok = int((jd["verdict"] == "합격").sum())
    n_c = int((jd["verdict"] == "후보").sum())
    L.append(f"[한 줄 결론] 변형 {len(jd)}개 중 합격 {n_ok}개, 후보 {n_c}개, 불합격 {len(jd) - n_ok - n_c}개.")
    L.append(f"  Bonferroni 기준 IS t ≥ {jd['bonf_t'].iloc[0]:.2f} (한쪽 5%, 변형 {len(jd)}개).")
    L.append("")
    L.append("[변형별 판정]  IS/OOS = 건수 · 평균R · PF · t,  DD = OOS 최대 낙폭(R),  종목 = IS·OOS 둘 다 + 종목 수,  연도 = + 연도 수")
    for m in ["M1", "M2", "M3", "M4", "M5", "M6"]:
        g = jd[jd["model"] == m]
        if g.empty:
            continue
        L.append(f"-- {m} {MODEL_DESC[m]}")
        for _, r in g.iterrows():
            L.append(f"  {r['variant']:<22} IS {r['IS_n']:5d}·{f2(r['IS_avgR'], 3):>6}·{f2(r['IS_PF'])}·{f2(r['IS_t'])}"
                     f" | OOS {r['OOS_n']:4d}·{f2(r['OOS_avgR'], 3):>6}·{f2(r['OOS_PF'])}·{f2(r['OOS_t'])} DD {f2(r['OOS_dd'], 1)}"
                     f" | 종목 {r['sym_both_pos']}/{r['n_sym']} 연도 {r['years_pos']}/{r['n_years']}"
                     f" | RW {f2(r['RW_avgR'], 3)} t{f2(r['RW_t'])} → {r['verdict']}")
            if r["fails"]:
                L.append(f"      못 넘은 기준: {r['fails']}")
    L.append("")
    L.append("[모델별 IS 최선 변형] (IS 100건 이상 중 IS 평균 R 1위. OOS는 고른 뒤 확인만)")
    for m in ["M1", "M2", "M3", "M4", "M5", "M6"]:
        g = jd[(jd["model"] == m) & (jd["IS_n"] >= 100)]
        if g.empty:
            L.append(f"  {m}: IS 100건 이상 변형 없음")
            continue
        r = g.sort_values("IS_avgR", ascending=False).iloc[0]
        L.append(f"  {m}: {r['variant']}  IS {f2(r['IS_avgR'], 3)}R (t {f2(r['IS_t'])}) → OOS {f2(r['OOS_avgR'], 3)}R PF {f2(r['OOS_PF'])} ({r['OOS_n']}건) → {r['verdict']}")
        if len(tr):
            gt = tr[tr["variant"] == r["variant"]]
            parts = []
            for s in symbols:
                gs = gt[gt["symbol"] == s]
                parts.append(f"{s} {gs[gs['period'] == 'IS']['R'].sum():+.1f}/{gs[gs['period'] == 'OOS']['R'].sum():+.1f}")
            L.append("     종목별 합계R IS/OOS: " + ", ".join(parts))
            yr = gt.groupby("year")["R"].sum()
            L.append("     연도별 합계R: " + " ".join(f"{y}:{x:+.1f}" for y, x in yr.items()))
    L.append("")
    L.append("[깔때기] 종목 합계 (setup = 조건 성립, order = 주문, fill = 체결, after_bias_dedupe = 바이어스·중복 정리 후, trades = 1포지션 규칙 후)")
    fd = pd.DataFrame(funnel)
    if len(fd):
        num = [c for c in fd.columns if c not in ("symbol", "variant", "model")]
        agg = fd.groupby("variant", sort=False)[num].sum()
        for v, r in agg.iterrows():
            L.append(f"  {v:<22} " + ", ".join(f"{c} {int(r[c])}" for c in num if r[c] > 0))
    L.append("")
    L.append("용어: R = 손절폭 1개. 평균R +0.10 = 거래마다 손절폭의 10%를 번다는 뜻. PF = 번 R 합 ÷ 잃은 R 합.")
    L.append("      IS = 2023년까지(고르는 기간), OOS = 2024년부터(확인 기간). t가 2보다 작으면 운과 구분이 안 됨.")
    L.append("      RW = 방향 없는 가짜 시세(스프레드 0)에서의 평균R·t. 여기서 +가 크게 나오면 규칙이 미래를 엿본다는 뜻.")
    txt = "\n".join(L)
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    return txt


# ---------------------------------------------------------------- 랜덤워크
def random_walk(seed, start, end, pip, price=1.1):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, end, freq="5min")
    idx = idx[idx.dayofweek < 5]
    m = len(idx)
    sub = 20                                                                       # 15초 20걸음(넘침 오차 줄임)
    steps = rng.normal(0, 2.5 * pip / np.sqrt(sub), size=(m, sub)).astype(np.float64).cumsum(axis=1)
    wk = (idx.dayofweek == 0) & (idx.hour == 0) & (idx.minute == 0)               # 주말 갭(평균 0, 표준편차 10핍)
    jump = np.where(wk, rng.normal(0, 10 * pip, size=m), 0.0)
    st = price + np.r_[0, steps[:-1, -1]].cumsum() + jump.cumsum()
    path = st[:, None] + steps
    return pd.DataFrame({"o": st, "c": path[:, -1], "h": np.maximum(path.max(axis=1), st),
                         "l": np.minimum(path.min(axis=1), st)}, index=idx)[["o", "h", "l", "c"]]


def run_rw(count, start, end, models, quiet=True):
    out = []
    for s in range(count):
        df = random_walk(1000 + s, start, end, 0.0001)
        tr, _, _ = run_symbol(f"RW{s}", df, 0.0001, 0.0, models)
        out.append(tr)
        if not quiet:
            print(f"  RW{s}: {len(tr):,} trade rows")
    return pd.concat(out) if out else pd.DataFrame()


# ---------------------------------------------------------------- 실행
def build_parser():
    p = argparse.ArgumentParser(description="ICT models M1-M6 backtest, pre-registered (read-only)")
    p.add_argument("--data-dir", help="folder with {SYMBOL}_M5.csv")
    p.add_argument("--out", help="output folder (created if missing)")
    p.add_argument("--symbols", default="", help="comma list. empty = all *_M5.csv in folder")
    p.add_argument("--models", default="M1,M2,M3,M4,M5,M6", help="models to run (default all)")
    p.add_argument("--spread", type=float, default=DEFAULT_SPREAD, help="default spread pips (default 1.0, floor 1)")
    p.add_argument("--spread-map", default="", help="per-symbol spread pips, e.g. GBPJPY=2.5 (XAUUSD default 2 = $0.20)")
    p.add_argument("--pip-map", default="", help="per-symbol pip size, e.g. XAUUSD=0.1")
    p.add_argument("--start", default="", help="use data from this date (server time)")
    p.add_argument("--rw", type=int, default=2, help="random-walk series for the RW criterion (default 2, 0 = skip)")
    p.add_argument("--selftest", action="store_true", help="run self tests on synthetic data only")
    return p


def run_all(opt, files=None, quiet=False):
    t0 = _time.time()
    models = [m.strip().upper() for m in opt.models.split(",") if m.strip()]
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
    all_tr, all_fun, rng = [], [], {}
    sp_used = {}
    for sym, path in files.items():
        print(f"\n== {sym} ==")
        df = path if isinstance(path, pd.DataFrame) else load_m5(path, verbose=not quiet)
        if opt.start:
            df = df[df.index >= pd.Timestamp(opt.start)]
        pip = pipmap.get(sym, default_pip(sym, float(df["c"].iloc[-1])))
        floor = SPREAD_FLOOR.get(sym, 1.0)
        sp = spmap.get(sym, max(opt.spread, floor))
        if sp < floor:
            print(f"  ! spread {sp} below README floor {floor} pips -> {floor}")
            sp = floor
        sp_used[sym] = sp
        print(f"  pip = {pip}, spread = {sp} pips")
        tr, fun, r = run_symbol(sym, df, pip, sp, models)
        rng[sym] = r
        all_tr.append(tr)
        all_fun += fun
        print(f"  trades {len(tr):,} (all variants), {(_time.time() - t0):.0f}s")
    tr = pd.concat(all_tr) if all_tr else pd.DataFrame()
    symbols = list(files.keys())
    variants = [v for v in VARIANTS if MODEL_OF[v.replace("+B", "")] in models]
    rw = None
    if opt.rw > 0:
        lo, hi = min(a for a, _ in rng.values()), max(b for _, b in rng.values())
        print(f"\n== random walk x{opt.rw} (spread 0) ==")
        rw = run_rw(opt.rw, pd.Timestamp(lo).floor("D"), pd.Timestamp(hi), models, quiet=False)
    jd = judge(tr, symbols, variants, rw)
    lo, hi = min(a for a, _ in rng.values()), max(b for _, b in rng.values())
    meta = {"데이터": f"MT5 M5 CSV ({opt.data_dir or '메모리'}), 종목 {', '.join(symbols)}",
            "기간(서버시간)": "; ".join(f"{s} {pd.Timestamp(a):%Y-%m-%d %H:%M}~{pd.Timestamp(b):%Y-%m-%d %H:%M}" for s, (a, b) in rng.items()),
            "기간(한국시간)": f"{server_to_kst([pd.Timestamp(lo)])[0]:%Y-%m-%d %H:%M} ~ {server_to_kst([pd.Timestamp(hi)])[0]:%Y-%m-%d %H:%M} KST",
            "시간 기준": "규칙 시각 = 뉴욕(NY = 서버 - 7h). 거래 목록에 서버·NY·한국시간(KST) 열",
            "IS / OOS": f"IS = {OOS_START} 이전 체결, OOS = 이후",
            "비용": "스프레드 " + ", ".join(f"{s} {v}핍" for s, v in sp_used.items()) + " (거래당 1번 차감), 손절 버퍼 1핍, 같은 봉 손절 우선",
            "랜덤워크": f"{opt.rw}개 (스프레드 0, 같은 기간)" if opt.rw > 0 else "건너뜀(--rw 0) → 랜덤워크 기준 불합격 처리",
            "규칙": "trading/projects/02-ict/rules.md (2026-10-29 고정)",
            "만든 시각": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M") + " (실행 PC 시각)"}
    out_cols = ["model", "variant", "symbol", "dir", "period", "year", "setup_server", "fill_server", "fill_ny", "fill_kst",
                "exit_server", "exit_kst", "entry", "sl", "tp", "risk_pips", "result", "R", "bias_ok", "key"]
    if len(tr):
        tr[out_cols].to_csv(os.path.join(opt.out, "trades_ict.csv"), index=False, encoding="utf-8-sig", float_format="%.10g")
    jd.to_csv(os.path.join(opt.out, "summary_ict.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    # 종목별 표
    rows = []
    if len(tr):
        for (v, s), g in tr.groupby(["variant", "symbol"]):
            for per in ("IS", "OOS"):
                st = stats(g[g["period"] == per]["R"].values)
                rows.append(dict(variant=v, symbol=s, period=per, **st))
    pd.DataFrame(rows).to_csv(os.path.join(opt.out, "by_symbol_ict.csv"), index=False, encoding="utf-8-sig", float_format="%.4f")
    pd.DataFrame(all_fun).to_csv(os.path.join(opt.out, "funnel_ict.csv"), index=False, encoding="utf-8-sig")
    txt = write_text(os.path.join(opt.out, "summary_ict.txt"), jd, tr, all_fun, meta, symbols)
    if not quiet:
        print("\n" + txt)
    print(f"\ndone {(_time.time() - t0):.0f}s. output folder: {opt.out}  (summary_ict.txt is UTF-8)")
    return dict(trades=tr, judge=jd, funnel=all_fun, rw=rw)


# ---------------------------------------------------------------- 자체 시험
def _check(ok, cond, msg):
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    return ok and bool(cond)


def _mini_space(o, h, l, c, start="2024-01-02 15:30"):
    idx = pd.date_range(start, periods=len(o), freq="5min")
    df = pd.DataFrame({"o": o, "h": h, "l": l, "c": c}, index=idx)
    X = Ctx(df, 0.0001, 0.0)
    return X, Space(X, *(np.asarray(v, float) for v in (o, h, l, c)), 1)


def selftest():
    ok = True
    t_start = _time.time()
    print("=== 1. 시간 변환 ===")
    s = pd.Timestamp("2026-07-01 15:30")
    ok = _check(ok, server_to_ny([s])[0] == pd.Timestamp("2026-07-01 08:30"), "서버 15:30 -> NY 08:30")
    ok = _check(ok, server_to_kst([s])[0] == pd.Timestamp("2026-07-01 21:30"), "여름 서버 15:30 -> KST 21:30 (NY+13)")
    w = pd.Timestamp("2026-01-15 15:30")
    ok = _check(ok, server_to_kst([w])[0] == pd.Timestamp("2026-01-15 22:30"), "겨울 서버 15:30 -> KST 22:30 (NY+14)")
    ok = _check(ok, ny_to_server_hour(8.5) == 15.5 and ny_to_server_hour(19) == 2 and ny_to_server_hour(14) == 21,
                "NY 08:30=서버 15:30, NY 19=서버 2(다음날), NY 14=서버 21(CBDR은 전날 21시 = -3)")

    print("=== 2. 3봉 스윙·키 레벨 ===")
    L = [10, 9, 8, 9, 10, 9.5, 7.5, 8.5, 9]
    ok = _check(ok, swing3_low(L, 2) and not swing3_low(L, 3) and swing3_low(L, 6), "스윙 저점 인덱스 2·6")
    ok = _check(ok, untaken_swing_low(L, 6, 60) == 2, "k=6 기준 안 깨진 최근 스윙 저점 = 2")
    L2 = [10, 9, 8, 9, 7.9, 9, 7, 8]
    ok = _check(ok, untaken_swing_low(L2, 6, 60) == 4, "2는 4에서 깨짐 -> 최근 안 깨진 것 = 4")
    ok = _check(ok, untaken_swing_low(L2, 5, 60) == -1, "k=5: 2는 봉4가 이미 깼고 4는 아직 미확정 -> 없음(-1)")
    print("=== 3. FVG / IFVG ===")
    H = [1.0, 1.1, 1.3, 1.25]
    Lb = [0.9, 1.0, 1.15, 1.1]
    ok = _check(ok, fvg_bull(H, Lb, 2) == (1.0, 1.15), "상승 FVG (봉0 고가 1.0 < 봉2 저가 1.15)")
    ok = _check(ok, fvg_bull(H, Lb, 3) is None, "봉3은 FVG 아님(1.1 > 1.1 아님)")
    Hd = [2.0, 1.9, 1.7, 1.75]
    Ld = [1.9, 1.8, 1.6, 1.65]
    ok = _check(ok, fvg_bear(Hd, Ld, 2) == (1.7, 1.9), "하락 FVG (봉2 고가 1.7 < 봉0 저가 1.9)")
    Cs = [1.8, 1.75, 1.65, 1.85, 1.95, 2.0]
    ok = _check(ok, ifvg_convert(Cs, 2, 1.9, 6) == 4, "종가 1.95 > 위 끝 1.9 인 첫 봉 = 4 -> IFVG")
    ok = _check(ok, ifvg_convert(Cs, 2, 1.9, 4) == -1, "lim=4면 아직 IFVG 아님(미래 안 봄)")
    print("=== 4. 표준편차 선 ===")
    lv = sd_levels(1.1020, 1.1000)
    ok = _check(ok, abs(lv[1.0][0] - 1.0980) < 1e-12 and abs(lv[2.0][1] - 1.1060) < 1e-12 and abs(lv[2.5][0] - 1.0950) < 1e-12,
                "범위 20핍: -1 = 1.0980, +2 = 1.1060, -2.5 = 1.0950")

    print("=== 5. 청산 규칙 ===")
    # 봉0 체결(지정가 1.1000, 손절 1.0990, 목표 1.1020). 봉0 고가가 목표 넘어도 무시, 봉1 둘 다 -> 손절
    o = [1.1005, 1.1000, 1.1000]
    h = [1.1030, 1.1025, 1.1005]
    l_ = [1.0995, 1.0985, 1.0995]
    c = [1.1000, 1.1000, 1.1000]
    X, S = _mini_space(o, h, l_, c)
    xi, px, res = simulate(S, X, 0, 1.1000, 1.0990, 1.1020, True)
    ok = _check(ok, (xi, res) == (1, "loss") and abs(px - 1.0990) < 1e-12, f"체결 봉 목표 무시 + 같은 봉 손절 우선 -> {res} @{xi}")
    o = [1.1005, 1.0980, 1.1000]
    h = [1.1010, 1.0990, 1.1005]
    l_ = [1.1000, 1.0975, 1.0995]
    X, S = _mini_space(o, h, l_, c)
    xi, px, res = simulate(S, X, 0, 1.1000, 1.0990, 1.1020, True)
    ok = _check(ok, res == "loss" and abs(px - 1.0980) < 1e-12, "갭으로 손절 건너뜀 -> 시가 1.0980 청산")
    o = [1.1005, 1.1005, 1.1015]
    h = [1.1010, 1.1015, 1.1025]
    l_ = [1.1000, 1.1001, 1.1010]
    X, S = _mini_space(o, h, l_, c)
    ok = _check(ok, limit_fill(S, 0, 3, 1.0999, 1.1020) == -1, "지정가 안 닿고 목표 먼저 -> 취소")
    xi, px, res = simulate(S, X, 0, 1.1000, 1.0990, 1.1020, True)
    ok = _check(ok, res == "win" and xi == 2, "봉2 목표 -> win")
    # 시간 청산: NY 16:00(서버 23:00) 직전 봉
    X, S = _mini_space([1.1] * 120, [1.1001] * 120, [1.0999] * 120, [1.1] * 120, start="2024-01-02 22:00")
    xi, px, res = simulate(S, X, 0, 1.1, 1.09, 1.12, False)
    ok = _check(ok, res == "time" and pd.Timestamp(int(X.t[xi])) == pd.Timestamp("2024-01-02 22:55"), "시간 청산 = 서버 22:55 봉")

    print("=== 6. 랜덤워크: 모든 변형 엣지 ≈ 0 (스프레드 0, 4개 x 8년, 주말 갭 포함) ===")
    rw = []
    for sd in (11, 12, 13, 14):
        df = random_walk(sd, "2017-01-01", "2024-12-31 23:55", 0.0001)
        tr, fun, _ = run_symbol(f"RW{sd}", df, 0.0001, 0.0)
        rw.append(tr)
    rw = pd.concat(rw)
    print(f"  ({_time.time() - t_start:.0f}s, 거래 {len(rw):,}행)")
    bad, few, worst = [], [], (None, -9)
    for v in VARIANTS:
        st = stats(rw[rw["variant"] == v]["R"].values)
        if st["n"] < 30:
            few.append(f"{v}({st['n']})")
            continue
        if st["t"] > worst[1]:
            worst = (v, st["t"])
        if st["t"] >= 3.0:
            bad.append(f"{v}: 평균 {st['avg']:+.3f}R t {st['t']:+.2f}")
    ok = _check(ok, not bad, f"변형별 t < 3 (30건 이상 {len(VARIANTS) - len(few)}개, 가장 높은 t: {worst[0]} {worst[1]:+.2f})"
                + ("" if not bad else f" -> {bad}"))
    if few:
        print(f"  (참고) 랜덤워크에서 30건 미만이라 변형별 판정 생략: {', '.join(few)}")
    for m in ["M1", "M2", "M3", "M4", "M5", "M6"]:
        st = stats(rw[rw["model"] == m]["R"].values)
        ok = _check(ok, st["t"] < 2.5 and -0.20 < st["avg"] < 0.10,
                    f"{m} 전체 {st['n']:6d}행 평균 {st['avg']:+.3f}R t {st['t']:+.2f} (기준 t<2.5, -0.20<평균<+0.10)")
    allr = rw["R"].values
    ok = _check(ok, -0.10 < allr.mean() < 0.03, f"전체 평균 {allr.mean():+.3f}R (보수적 체결 규칙 때문에 약간 음수가 정상)")
    print("  (참고) 손절이 M5 봉 1~2개 크기로 좁은 변형은 '같은 봉 손절 우선·체결 봉 목표 무시' 때문에 랜덤워크에서도"
          " -0.05~-0.15R이 나와요. 실제 결과도 그만큼 보수적(불리하게) 계산된다는 뜻이에요.")

    print("=== 7. 미래 엿보기 검사: 데이터를 중간에 잘라도 그 전 거래는 똑같아야 함 ===")
    df = random_walk(21, "2019-01-01", "2021-12-31 23:55", 0.0001)
    full, _, _ = run_symbol("RWF", df, 0.0001, 0.5)
    cut = pd.Timestamp("2020-08-12 13:37")
    part, _, _ = run_symbol("RWF", df[df.index < cut], 0.0001, 0.5)
    lim = (cut - pd.Timedelta(days=8)).strftime("%Y-%m-%d %H:%M")

    def sig(x):
        x = x[x["exit_server"] < lim]
        return set(zip(x["variant"], x["dir"], x["fill_server"], x["exit_server"], np.round(x["R"].values, 9)))
    a, b = sig(full), sig(part)
    ok = _check(ok, len(a) > 100 and a == b, f"잘린 시점 8일 전까지 거래 {len(a)}건 = {len(b)}건, 차이 {len(a ^ b)}")
    print(f"\n자체 시험 {'모두 통과' if ok else '실패 있음'} ({_time.time() - t_start:.0f}s)")
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
