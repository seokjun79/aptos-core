"""시간대 패턴 검증: "뉴욕 시각 A시 시가에 진입 → B시 시가에 청산"을 매일 반복했을 때의 성적.

데이터: venus_data.zip (export_basket.py 결과). H1 봉, time = 서버 시각(IC마켓 = 뉴욕 + 7시간).
비용: 진입 봉의 spread(포인트)를 매 거래에서 뺀다 (Standard 계좌, 수수료 없음).
결과는 핍(금은 달러) 단위 평균, 승률, t값, 연도별 합계. IS(~2023) / OOS(2024~)를 따로 보여 준다.

사용: python time_windows.py venus_data.zip
"""
import io
import sys
import zipfile

import numpy as np
import pandas as pd

SERVER_MINUS_NY = 7
PIP = {"USDJPY": 0.01, "XAUUSD": 0.1}  # 금은 0.1달러를 1 '핍'으로 본다

# (이름, 종목들, 진입 NY시, 청산 NY시, 방향 +1 매수/-1 매도) — 조사 결과 그대로, 우리 데이터로 고르지 않음
HYPOTHESES = [
    ("자국통화 약세: 유럽시간 EURUSD 매도 (NY 03→11)", ["EURUSD"], 3, 11, -1),
    ("자국통화 약세: 미국시간 EURUSD 매수 (NY 11→16)", ["EURUSD"], 11, 16, +1),
    ("픽스 전 달러 강세: 런던 12→16 달러 매수", ["EURUSD", "GBPUSD", "AUDUSD"], 7, 11, -1),
    ("픽스 후 달러 반전: 런던 16→20 달러 매도", ["EURUSD", "GBPUSD", "AUDUSD"], 11, 15, +1),
    ("금 야간 상승: NY 17(마감)→ 런던 08 금 매수", ["XAUUSD"], 18, 3, +1),
]


def load(zip_path, symbol, tf="H1"):
    with zipfile.ZipFile(zip_path) as z:
        df = pd.read_csv(io.BytesIO(z.read(f"{symbol}_{tf}.csv")))
    df["server"] = pd.to_datetime(df["time"], unit="s")
    df["ny"] = df["server"] - pd.Timedelta(hours=SERVER_MINUS_NY)
    return df


def point_of(symbol, price):
    # IC마켓 자릿수: JPY 3자리, 금 2자리, 나머지 5자리
    return 0.001 if symbol.endswith("JPY") else (0.01 if symbol == "XAUUSD" else 0.00001)


def run_window(df, symbol, h_in, h_out, direction):
    pip = PIP.get(symbol, 0.0001)
    pt = point_of(symbol, df.close.iloc[-1])
    d = df.set_index("ny")
    entries = d[d.index.hour == h_in]
    rows = []
    for t, e in entries.iterrows():
        # 청산 시각: 진입 이후 처음 오는 h_out시 봉 (자정을 넘기면 다음날)
        end = t.normalize() + pd.Timedelta(hours=h_out)
        if end <= t:
            end += pd.Timedelta(days=1)
        if end - t > pd.Timedelta(hours=20):
            continue
        try:
            x = d.loc[end]
        except KeyError:
            continue  # 주말·휴일로 청산 봉이 없으면 건너뜀
        if isinstance(x, pd.DataFrame):
            x = x.iloc[0]
        gross = direction * (x.open - e.open) / pip
        cost = e.spread * pt / pip
        rows.append((t, gross - cost, gross, cost))
    return pd.DataFrame(rows, columns=["t", "net", "gross", "cost"])


def summarize(r, label):
    if r.empty:
        return f"  {label}: 거래 없음"
    n = len(r)
    m, s = r.net.mean(), r.net.std(ddof=1)
    t = m / (s / np.sqrt(n)) if s > 0 else 0
    return (f"  {label:<6} {n:5d}건 평균 {m:+6.2f}핍(비용 전 {r.gross.mean():+.2f}, 비용 {r.cost.mean():.2f}) "
            f"승률 {100 * (r.net > 0).mean():4.1f}% 합계 {r.net.sum():+8.0f}핍 t={t:+.2f}")


def main(zip_path):
    for name, symbols, h_in, h_out, direction in HYPOTHESES:
        print(f"\n### {name}")
        allr = []
        for s in symbols:
            try:
                df = load(zip_path, s)
            except KeyError:
                print(f"  {s}: 데이터 없음")
                continue
            r = run_window(df, s, h_in, h_out, direction)
            r["sym"] = s
            allr.append(r)
            print(f"[{s}]")
            print(summarize(r[r.t < "2024-01-01"], "IS"))
            print(summarize(r[r.t >= "2024-01-01"], "OOS"))
            yearly = r.groupby(r.t.dt.year).net.sum()
            print("  연도별: " + " ".join(f"{y}:{v:+.0f}" for y, v in yearly.items()))


if __name__ == "__main__":
    main(sys.argv[1])
