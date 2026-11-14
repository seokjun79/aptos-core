"""MT5에서 여러 종목의 가격 데이터를 꺼내 압축 파일 하나로 만든다 (비너스에게 올리기용).

종목: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, XAUUSD
시간봉: M15, H1, D1 (+ EURUSD는 M5도)
열: time(서버 시각 epoch 초), open, high, low, close, spread(포인트) — 크기를 줄이려고 나머지 열은 뺀다.
결과: 바탕화면의 venus_data.zip

실행: MT5를 켜고 로그인한 상태에서 python export_basket.py [시작일, 기본 2019-01-01]
"""
import io
import os
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "XAUUSD"]
TIMEFRAMES = {"M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1, "D1": mt5.TIMEFRAME_D1}
EXTRA = {("EURUSD", "M5"): mt5.TIMEFRAME_M5}
COLS = ["time", "open", "high", "low", "close", "spread"]


def month_starts(start, end):
    cur = start.replace(day=1)
    while cur < end:
        nxt = (cur + timedelta(days=32)).replace(day=1)
        yield cur, min(nxt, end)
        cur = nxt


def rates(symbol, tf, start, end):
    parts = []
    for a, b in month_starts(start, end):
        r = mt5.copy_rates_range(symbol, tf, a, b)
        if r is not None and len(r):
            parts.append(pd.DataFrame(r)[COLS])
    if not parts:
        return None
    return pd.concat(parts).drop_duplicates("time").sort_values("time")


def main():
    start = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime(2019, 1, 1)
    start = start.replace(tzinfo=timezone.utc)
    end = datetime.now(timezone.utc)
    path = os.environ.get("MT5_PATH")
    if not (mt5.initialize(path=path) if path else mt5.initialize()):
        sys.exit(f"MT5 연결 실패: {mt5.last_error()} — MT5가 켜져 있고 로그인돼 있는지 확인하세요.")
    out = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop" / "venus_data.zip"
    jobs = [(s, n, tf) for s in SYMBOLS for n, tf in TIMEFRAMES.items()] + [(s, n, tf) for (s, n), tf in EXTRA.items()]
    info_lines = []
    try:
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for s, n, tf in jobs:
                if not mt5.symbol_select(s, True):
                    print(f"[{s}] 종목을 찾을 수 없어 건너뜀")
                    continue
                df = rates(s, tf, start, end)
                if df is None:
                    print(f"[{s} {n}] 데이터 없음: {mt5.last_error()}")
                    continue
                buf = io.StringIO()
                df.to_csv(buf, index=False, float_format="%.6g")
                z.writestr(f"{s}_{n}.csv", buf.getvalue())
                print(f"[{s} {n}] {len(df):,}봉 ({pd.to_datetime(df.time.iloc[0], unit='s')} ~ {pd.to_datetime(df.time.iloc[-1], unit='s')})")
            for s in SYMBOLS:
                i = mt5.symbol_info(s)
                if i:
                    info_lines.append(f"{s} digits={i.digits} point={i.point} spread_now={i.spread} "
                                      f"contract={i.trade_contract_size} swap_long={i.swap_long} swap_short={i.swap_short} "
                                      f"tick_value={i.trade_tick_value} tick_size={i.trade_tick_size}")
            acc = mt5.account_info()
            info_lines.insert(0, f"server={acc.server} leverage=1:{acc.leverage} currency={acc.currency}")
            z.writestr("symbols_info.txt", "\n".join(info_lines))
    finally:
        mt5.shutdown()
    print(f"\n완성: {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
