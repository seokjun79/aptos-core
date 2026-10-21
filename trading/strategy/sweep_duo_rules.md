# Sweep Duo (EURUSD) — rule reconstruction from "Venus 트레이딩 관제실"

Source: artifact https://claude.ai/artifact/FG6czk3mTn7y12T6aUquGM (version 1792308679-9b74), read 2026-10-21.
The page is a dashboard, NOT a spec. It never states the EA's code-level rules. Everything below is either a
direct quote or explicitly marked **UNKNOWN** / **INFERRED**. Quotes are verbatim (Korean kept).

## 0. Identity / account
| Item | Value | Source quote |
|---|---|---|
| EA name, symbol | Sweep Duo, EURUSD | `● Sweep Duo 가동 · EURUSD` |
| Account | IC Markets live, $16.08, 1:1000 | `IC마켓 실계좌 · 잔고 $16.08 · 1:1000` |
| Size | fixed 0.01 lot | `0.01랏 고정` |
| "Duo" meaning | INFERRED: two models, "London model" and "NY model" | `'런던 모델 진입 마감'`, `'뉴욕 모델 진입 마감'` |

## 1. Session schedule (all hours defined in America/New_York time)
Source JS: `// 일정 (뉴욕 시각 기준 → 한국 시각)` and
```
const EV=[[19,'아시아 박스 만들기 시작'],[2,'런던 스윕 감시 · 런던 박스 시작'],[5,'런던 스윕 감시 끝 (진입은 계속)'],[7,'뉴욕 스윕 감시'],[8,'런던 모델 진입 마감'],[10,'뉴욕 스윕 감시 끝'],[11,'뉴욕 모델 진입 마감'],[12,'런던 포지션 정리'],[15,'뉴욕 포지션 정리']];
const rows=[[19,2,'아시아 박스 (보라)'],[2,5,'런던 스윕 감시'],[2,7,'런던 박스 (청록)'],[7,10,'뉴욕 스윕 감시'],[12,12,'런던 포지션 정리'],[15,15,'뉴욕 포지션 정리']];
```
DST: `// 시간 도우미 (뉴욕 서머타임 자동)`; `const shift=()=>9-nyOffsetH(new Date()); // KST - NY (13 또는 14)`.
So all windows are fixed in New York local time and float in KST/UTC with US DST (not EU DST).

| Window | NY time | UTC (US EDT / EST) | KST (US EDT / EST) |
|---|---|---|---|
| Asian box build | 19:00 → 02:00 | 23:00→06:00 / 00:00→07:00 | 08:00→15:00 / 09:00→16:00 |
| London sweep watch (sweep of Asian box) | 02:00 → 05:00 | 06:00→09:00 / 07:00→10:00 | 15:00→18:00 / 16:00→19:00 |
| London box build (for NY model) | 02:00 → 07:00 | 06:00→11:00 / 07:00→12:00 | 15:00→20:00 / 16:00→21:00 |
| London model: entries still allowed after sweep watch ends | 05:00 → 08:00 | — | — | 
| London model entry cutoff | 08:00 | 12:00 / 13:00 | 21:00 / 22:00 |
| NY sweep watch (INFERRED: sweep of London box) | 07:00 → 10:00 | 11:00→14:00 / 12:00→15:00 | 20:00→23:00 / 21:00→24:00 |
| NY model entry cutoff | 11:00 | 15:00 / 16:00 | 00:00 / 01:00 (+1d) |
| London positions flattened | 12:00 | 16:00 / 17:00 | 01:00 / 02:00 (+1d) |
| NY positions flattened | 15:00 | 19:00 / 20:00 | 04:00 / 05:00 (+1d) |

Quotes: `'런던 스윕 감시 끝 (진입은 계속)'` (London sweep watch ends, entries continue);
`'런던 포지션 정리'` / `'뉴욕 포지션 정리'` (time-based close).
- Mixed-DST weeks (EU vs US DST mismatch): handled only via US DST (`America/New_York`). Whether the EA itself
  uses broker server time / NY time is **UNKNOWN** (page code is display logic only).
- Asian box = high/low of NY 19:00–02:00: the page only says "아시아 박스 만들기"; that the box is the
  **high/low** of that window is INFERRED. Candle timeframe used to build it: **UNKNOWN** (data is "Dukascopy 5분봉", so likely M5 — INFERRED).
- Weekend: market considered closed Fri 17:00 NY → Sun 17:00 NY (`if(wd==='Fri'&&h>=17)return false;if(wd==='Sun'&&h<17)return false;`). Sunday 19:00 box start is shown.

## 2. Sweep definition — UNKNOWN
No text defines a sweep. Hints only:
- confluence factor `스윕 크기` (sweep size) exists → there is a minimum/qualifying sweep size threshold: value **UNKNOWN**.
- factor `전일 고저 스윕` (sweep of previous-day high/low).
- Wick-through vs close-through, minimum pips beyond box, max excursion: **UNKNOWN**.

## 3. Entry trigger — UNKNOWN
Not described. (Typical "sweep and reclaim" = close back inside box after sweep is a guess, not in source.)
Order type (market/limit/stop), confirmation timeframe: **UNKNOWN**.

## 4. Direction — INFERRED only
Sweep-reversal (fade the sweep: sweep of box high → sell, sweep of low → buy) is implied by the name and the
`4H 방향` factor, but never stated. **UNKNOWN** as a rule.

## 5. Stop loss / take profit
- EA SL: **UNKNOWN**. The "15핍" figure belongs to the *Risk Manager for manual trades*, not the EA:
  `리스크 매니저 규칙 ... 직접 매매` → `손절 없는 포지션 — 자동 SL 15핍 + TP 2.5배`.
  Risk manager also: `손절 범위 — 6 ~ 25핍` (allowed SL range).
- EA TP / R multiple: **UNKNOWN**. Consistency check: 169 trades, 34.9% win, +46.2R.
  If losers = −1R: 59 wins × W − 110 = 46.2 → W ≈ 2.65R per win, i.e. compatible with a ~2.5R TP plus
  time-exits (INFERRED; also costs). The 2.5× TP of the risk manager may mirror the EA, but this is not stated.
- Breakeven / trailing / partials: **UNKNOWN**. Time exit: London 12:00 NY, NY 15:00 NY (quoted above).

## 6. Confluence score (threshold 5)
Quote: `점수 5점부터 플러스로 바뀌어요. 그래서 EA는 5점 이상만 진입해요.`
Factors that are named (from `hbars('comps',...)`, panel `점수 항목별 효과 / 있을 때 / 없을 때 평균 R`):
| Factor | avg R with | avg R without |
|---|---|---|
| 4H 방향 (4H trend direction agrees) | +0.06 | −0.36 |
| 전일 고저 스윕 (previous-day high/low swept) | +0.07 | −0.20 |
| 스윕 크기 (sweep size qualifies) | −0.08 | −0.61 |

- Points per factor: **UNKNOWN**. Total factor list: **UNKNOWN** — observed scores reach 6 and start at 2,
  so with only 3 named factors there must be more factors and/or multi-point factors (≥6 max points).
- Definition of 4H direction (EMA? structure? candle colour?): **UNKNOWN**.
- Threshold definition `>= 5`: stated.

R by score (`hbars('scores',...)`, header `EURUSD 339건`):
| Score | n | avg R |
|---|---|---|
| 2 | 34 | −0.25 |
| 3 | 94 | −0.35 |
| 4 | 120 | −0.24 |
| 5 | 82 | +0.28 |
| 6 | 7 | +0.71 |
(n sums to 337, not 339 — 2 trades unaccounted, likely score 0/1 or 7: **UNKNOWN**.)
Note 5+6 = 89 trades, not 169 → the score table is a different sample (unfiltered London+NY? IS only? per-model?) — **UNKNOWN**.

## 7. Trade limits / risk
- Daily −3% lock: `하루 손실 한도 — −3% → 전부 청산·잠금`; max entries `하루 진입 — 최대 3회`;
  `동시 포지션 — 1개`; `거래 시간 — 18:00 ~ 23:30` (KST). **All of these are listed under the Risk Manager
  for manual trading (`직접 매매`)**, not as EA parameters. Whether the EA obeys them: **UNKNOWN**.
- EA max trades/day / one-per-session: **UNKNOWN** (169 trades / ~3.8 yrs = `연 45건` implies ≤ ~1 per week on average).
- Other filters (news, spread, day-of-week, min box size, max box size): **UNKNOWN**.

## 8. Backtest stats shown
| Metric | Value | Source quote |
|---|---|---|
| Symbol / period | EURUSD, 2023.01–2026.10 | `Sweep Duo 백테스트 ... EURUSD · 2023.01~2026.10` |
| Trades | 169 (45/yr) | `169건 (연 45건)` |
| Win rate | 34.9% | `승률 34.9%` |
| Total | +46.2R | `합계 +46.2R` |
| Max DD | −12.7R | `최대 낙폭 −12.7R` |
| OOS | 63 trades, +24.5R | `처음 보는 기간(OOS) 63건 · +24.5R` |
| $ projection | $16 → $53.8 at 0.01 lot | `16달러·0.01랏 환산 $16 → $53.8` |
| Max losing streak | 10 | `최대 연패 10연패` |
| Data | Dukascopy M5 | `데이터: Dukascopy 5분봉 2023.01~2026.10` |
| Costs | "included" | `비용 포함 백테스트` — spread/commission values **UNKNOWN** |
| IS/OOS split | **UNKNOWN** date. 169−63 = 106 IS trades, IS ≈ +21.7R (derived). | |

Half-year R (`런던 스윕 반기별 성적 — EURUSD · 점수 5+`):
`L=['23H1','23H2','24H1','24H2','25H1','25H2','26H1','26H2'], V=[-4.8,5.3,3.9,9.6,4.6,6.8,6.3,-3.4]`,
note `8개 반기 중 6번 플러스. 합계 +28.3R.` → this is **London model only** (+28.3R); so NY model ≈ +17.9R (derived: 46.2−28.3).
Note "26H2" only covers Jul–Oct 2026.

$ check: +46.2R → $37.8 gain at 0.01 lot ⇒ 1R ≈ $0.82 ≈ 8.2 pips at 0.01 lot ($0.10/pip) — implies
average risk ≈ 8 pips/trade (INFERRED; contradicts a fixed 15-pip SL unless R is cost-adjusted differently).

## 9. UNKNOWNs blocking an exact re-implementation
1. Sweep definition (wick vs close, min penetration, sweep-size threshold).
2. Entry trigger, order type, timeframe.
3. Direction rule (fade vs continuation) — inferred fade only.
4. SL placement (sweep extreme? fixed pips?) and TP/R target, BE/trailing.
5. Full confluence factor list and point weights; 4H-direction definition.
6. Max trades per day/session for the EA; whether risk-manager limits apply to EA.
7. Spread/commission/slippage values; IS/OOS split date; time zone of Dukascopy data handling.
8. Which sample the 339-trade score table comes from.
