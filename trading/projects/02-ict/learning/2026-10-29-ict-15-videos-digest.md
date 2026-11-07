# ICT 영상 15개 학습 요약 (2026-10-29, RC비너스 자막 추출 → 매니저 정리)

- 원문 자막: PC `C:\Users\kun00\venus\learning\ict\<영상ID>.txt`
- 영상별 상세 메모(규칙·강도·예시·애매한 점·의사코드): PC `C:\Users\kun00\venus\learning\ict\notes\<영상ID>.md`
- 모두 ICT 본인 채널(The Inner Circle Trader). 자막 없는 실시간 매매 영상 3개(f6KC4m4zNgc, KhnKA8Uu0n8, sUGuNE31lG0)는 규칙을 뽑을 수 없었음.

## 영상 목록
| ID | 제목 | 날짜 | 핵심 |
|---|---|---|---|
| 9YS41OoxbX4 | Market Review On NQ December Price Delivery | 2026-10-19 | TGIF 되돌림 20~30%(최대 40%), Macro 09:50~10:10, 첫 FVG(09:38) |
| 59Elm8myGEc | NonFarm Payroll October 2026 Lecture | 2026-10-02 | 뉴스 뒤 반대 되돌림, 7:00~8:30 박스 -2.5 SD와 Event Horizon 겹침 |
| kRShZKZlvJ4 | NQ AM Session Review 09/30/2026 | 2026-09-30 | 월요일 RTH 시작 갭 CE → 갭 전체 메우기 |
| 7M56e9O06Ko | NQ December Asian Session Execution | 2026-09-29 | IFVG 롱, 나눠서 청산, 방어선 3개 |
| I7fIf1eEz0w | NQ December Commentary 09/29/2026 | 2026-09-29 | 09:30 시가 = 자석, 런던 02:00~05:00, 점심 11:30~13:30 |
| UVVmS0de0g0 | NQ AM Session Low Of Day Long Review | 2026-09-28 | RTH 갭 1/8·1/4·-2 SD + 이전 저점 겹침, Macro 10:50~11:10 |
| 50VbES10ULs | NQ Dec Futures September FOMC Trade Review | 2026-09-17 | 연속 inside day 2개 → 큰 움직임, FOMC 진입 14:40~14:50 |
| tRq1hyGGtl4 | ICT Silver Bullet (2023 Mentorship) | 2023-05-14 | 03~04 / 10~11 / 14~15시 창, FX 최소 15핍 |
| iKsIbUblSWM | Market Maker Models (2023 Mentorship) | 2023-11-01 | GBPUSD, 1H SIBI CE에서 저위험 매도 |
| xJMbva8SjzE | ICT Judas Swing | 2017-12-10 | 00:00~05:00, 아시아 박스 위→자정 시가 아래→박스 아래 10~20핍 |
| dIT4HTFYGGo | Accumulation-Manipulation-Distribution (Power of 3) | 2017-12-09 | 강세일은 시가 아래에서 사고 고점 위에서 판다 |
| JA0mLNJeytY | Implementing The Asian Range | 2017-12-09 | 아시아 박스 19:00~00:00, 손절 최소 10핍, 목표 50~80핍 |

## FX(석준님 GBPUSD)에 바로 쓸 수 있는 규칙 — 모두 뉴욕 시간 (MT5 서버 = 뉴욕 + 7, 한국 = 뉴욕 + 13/14)
1. **아시아 박스** = 19:00~00:00 고점·저점. **자정 시가(00:00)** 선을 11:00까지 그어 둔다.
2. **바이어스 먼저.** 일봉·주봉으로 오늘 오를지 내릴지 정한다. 없으면 거래 안 함.
3. **강세일 매수:** 00:00 뒤 아시아 저점이 **먼저** 깨진 다음 가격이 아시아 고점으로 돌아오면 매수. 저점이 안 깨졌는데 고점 돌파 매수하면 "털린다".
4. **Judas Swing(00:00~05:00):** 강세일이면 아시아 고점 위로 살짝 → 자정 시가 아래 → 아시아 저점 아래 10~20핍 → 그 아래서 매수. 하나라도 빠지면 거래 안 함. 일주일에 몇 번만 나옴.
5. **Silver Bullet:** 03~04시, 10~11시, 14~15시 창 안에서만 진입. 목표(전날 고저·직전 세션 고저·전주 고저)까지 **15핍 이상** 남아 있어야 함. 창 안에서 구조 전환 뒤 처음 생긴 FVG에 진입.
6. **손절은 10핍 이상**, 거래당 위험 1~1.5%, 주간 목표 50~75핍 달성하면 그 주는 끝.
7. **몸통이 말해 준다:** FVG 안·CE 위(아래)에 몸통이 머물면 그 방향이 진짜. 꼬리는 무시.

## ICT가 스스로 인정한 한계
- 손절 위치를 대부분 영상에서 말하지 않음 → 백테스트에서는 가정으로 정함.
- 바이어스 정하는 법은 "다른 강의"라며 거의 설명 안 함 → 기계 규칙으로 바꿔 시험.
- "매일 나오지 않는다", "손실 거래도 있다", "따라 하라는 것 아님"이라고 반복함.
- 최근 영상은 대부분 NQ(나스닥 선물) 정규장 갭·뉴스 기준이라 FX에는 그대로 못 씀.

## 백테스트 연결
- fx-trader가 만드는 `trading/research/ict_backtest.py`에 위 숫자(시간창, 10~20핍, 15핍, 10핍 손절, 50/80핍 목표)를 그대로 넣도록 전달함(2026-10-29).
