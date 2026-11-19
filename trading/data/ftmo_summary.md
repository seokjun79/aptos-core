# FTMO Challenge #520311388 (2nd attempt) — trade data & stated patterns

Source: artifact https://claude.ai/artifact/GY2JdmAvfWNh88C7ThgV3A (version 1792145670-9b59), read 2026-10-21;
plus FTMO panel in https://claude.ai/artifact/FG6czk3mTn7y12T6aUquGM.
Header: `FTMO Challenge #520311388 · 10K · 2025.08.05 – 09.04`; `시각은 모두 한국 시간이에요` (all times KST, UTC+9).

## Files
- `ftmo_trades.csv` — 29 rows, from the page's `META` array
  (`[KST 날짜·시각, 종목, 방향, 랏, 결과핍, MAE, MFE, 보유분, 직전1h흐름핍, 돌파여부, 메모]`).
  - Year 2025 assumed from header. `close_time_kst_derived` = open + hold minutes.
  - `pattern` computed exactly as the page's `cls()`: A if prior-1h flow ≥ 5 pips (A+ if breakout flag = 1), else B;
    `late_night` = entry hour < 3 or ≥ 23:30.
  - **Not in source (blank):** entry/exit price, SL, TP, $ profit, seconds. `est_profit_usd_pips_x_lots_x10`
    = pips × lots × $10 for *USD-quoted pairs only* (estimate, no commission).
  - `pre_fail_challenge_trade` = trades 1–4 (8/5–8/7); `8/7 이후 거래는 탈락이 확정된 뒤 자유롭게 한 거래예요`.
- `ftmo_trade_context_15m_bars.csv` — 720 rows: per-trade 15-minute OHLC from ~4 h before entry through exit,
  **in pips relative to the entry price** (price − entry, not direction-adjusted), Dukascopy **bid**
  (`가격은 Dukascopy 매도호가(bid) 기준이라 FTMO 체결가와 0.1~0.3핍 정도 차이`). Bar start times derived from
  the page's entry offset (`진입오프셋(분)|보유분|15분봉 o,h,l,c (진입가 대비 핍)`), KST. Values are integers (rounded).
  Absolute prices are not embedded.

## Stated summary (quotes)
- `29건 거래 (EURUSD 22 · 기타 7)`; `+108.7핍 전체 결과 (5랏 기준 약 +5,100달러)`
- `21:00–23:00 진입이 가장 많은 시간 (뉴욕 개장 전후)`; `−29.5핍 가장 깊은 역행 (9/3 매도, SL 없음)`
- Venus page: `1차 수익 / 하루 최대 손실 +28.4% / −32.1%`, `2차 +50.9% / −29.0%`, `2차 승률 · 프로핏 팩터 65.5% · 3.63`,
  `거래당 랏 5랏 (적정 0.5~2랏)`, `SL을 건 거래 29건 중 5건`, `탈락 순간 8/7 · 14핍 역행 = −$715`,
  `하루 한도(−500달러)`.

## Patterns (stated vs recomputed from CSV)
| Pattern | Stated | Recomputed |
|---|---|---|
| A 흐름 따라가기 (prior 1h ≥5 pips my way) | 12건, 11승 1패, +94.9핍, 평균 역행 −7.0 | 12, 11W 1L, +94.9, −7.0 ✔ |
| A+ 세션 고·저점 돌파 (subset of A; broke prior 4h high/low) | 7건 7승 0패 +65.2핍 | 7, 7W, +65.2 ✔ |
| B 되돌림 | 17건 10승 5패 2본전 +13.8핍, 평균 역행 −10.6 | 17, 10W **6L 1BE**, +13.8, −10.6 (W/L split differs) |
| 늦은 밤 (≥23:30 KST) | 8건 3승 −18.4핍 | 8, **4** wins by pips (two +0.2 trades), −18.4 |
| All | win 65.5% (=19/29), PF 3.63 | 21 positive-pip trades; 65.5% implies FTMO counted 2 small trades as losses (likely commission) |

Exit: `이긴 거래는 최대 유리 구간(MFE)의 85% 안팎에서 청산`. Stops: `SL은 29건 중 5건만` — which 5: **UNKNOWN**.

## Inferred trading rules (page's own list, `기록으로 본 내 매매 규칙 (추정)`)
1. 시간: KST 18:40 ~ 23:30, core 21:00–23:00 (NY open).
2. 종목: mainly EURUSD; EURJPY early London (18–20 KST).
3. 잘된 진입: join an existing move, esp. on break of Asian/London range or day high/low.
4. 익절: 5–25 pips, exit when momentum stalls.
5. 약점: counter-trend reversal entries, entries after 23:30, two same-direction positions at once, holding without SL.

Risk-manager rules derived (Venus page, for manual trading): auto SL 15 pips + TP 2.5× when none set; 1 concurrent
position; max 3 entries/day; daily loss −3% → flatten & lock; SL range 6–25 pips; trading hours 18:00–23:30 KST.
