"""IC마켓 MT5에서 가격 데이터와 내 거래 기록을 꺼내 CSV로 저장한다.

준비:
  1. MT5를 켜고 IC마켓 계좌에 로그인해 둔다.
  2. 도구 > 옵션 > 차트 > "차트의 최대 바 수"를 Unlimited로 바꾼다.
  3. pip install MetaTrader5 pandas

실행:
  python trading/mt5/export_data.py            # 2019-01-01부터 지금까지
  python trading/mt5/export_data.py 2023-01-01 # 시작일 지정
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

SYMBOL = "EURUSD"
OUT = Path(__file__).resolve().parent.parent / "data"
TIMEFRAMES = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}


def month_starts(start, end):
    cur = start.replace(day=1)
    while cur < end:
        nxt = (cur + timedelta(days=32)).replace(day=1)
        yield cur, min(nxt, end)
        cur = nxt


def export_rates(start, end):
    for name, tf in TIMEFRAMES.items():
        parts = []
        for a, b in month_starts(start, end):
            r = mt5.copy_rates_range(SYMBOL, tf, a, b)
            if r is not None and len(r):
                parts.append(pd.DataFrame(r))
        if not parts:
            print(f"[{name}] 데이터 없음: {mt5.last_error()}")
            continue
        df = pd.concat(parts).drop_duplicates("time").sort_values("time")
        # MT5 time은 브로커 서버 시각(IC마켓은 GMT+2, 미국 서머타임 중 GMT+3)
        df["server_time"] = pd.to_datetime(df["time"], unit="s")
        path = OUT / f"{SYMBOL}_{name}_icmarkets.csv"
        df.to_csv(path, index=False)
        print(f"[{name}] {len(df):,}개 봉 저장 → {path.name} ({df.server_time.iloc[0]} ~ {df.server_time.iloc[-1]})")


def export_deals(start, end):
    deals = mt5.history_deals_get(start, end)
    if deals is None or len(deals) == 0:
        print(f"[거래 기록] 없음: {mt5.last_error()}")
        return
    df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    df["server_time"] = pd.to_datetime(df["time"], unit="s")
    path = OUT / "my_deals_icmarkets.csv"
    df.to_csv(path, index=False)
    print(f"[거래 기록] {len(df)}건 저장 → {path.name}")


def export_symbol_info():
    info = mt5.symbol_info(SYMBOL)
    acc = mt5.account_info()
    lines = [
        f"server={acc.server} currency={acc.currency} leverage=1:{acc.leverage} balance={acc.balance}",
        f"symbol={SYMBOL} digits={info.digits} point={info.point} spread_now={info.spread}pt "
        f"contract_size={info.trade_contract_size} volume_min={info.volume_min} volume_step={info.volume_step}",
        "주의: 수수료(commission)는 MT5 API로 나오지 않는다. IC마켓 Raw 계좌는 보통 랏당 왕복 $7 — 계좌 종류를 확인할 것.",
    ]
    (OUT / "account_symbol_info.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


def main():
    start = datetime.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime(2019, 1, 1)
    start = start.replace(tzinfo=timezone.utc)
    end = datetime.now(timezone.utc)
    if not mt5.initialize():
        sys.exit(f"MT5 연결 실패: {mt5.last_error()} — MT5가 켜져 있고 로그인돼 있는지 확인하세요.")
    try:
        if not mt5.symbol_select(SYMBOL, True):
            sys.exit(f"{SYMBOL} 심볼을 찾을 수 없습니다(IC마켓은 접미사가 붙을 수 있음).")
        OUT.mkdir(parents=True, exist_ok=True)
        export_symbol_info()
        export_rates(start, end)
        export_deals(start, end)
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
