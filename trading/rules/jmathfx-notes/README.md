# 석준님 jMathFx 공부 노트 정리 (사진 13장, 2026-11-18 받음)

원본 사진: note_01.jpg ~ note_13.jpg (석준님 필기). 아래는 매니저가 읽어 정리한 것.

## 1. 기본 공식 (Basic base)
- **Cross A ÷ Cross B = Cross C**
  - EURJPY ÷ USDJPY = EURUSD, EURCAD ÷ USDCAD = EURUSD, EURCHF ÷ USDCHF = EURUSD (JPY·CAD·CHF는 **나누기**)
  - EURGBP × GBPUSD = EURUSD, EURAUD × AUDUSD = EURUSD, EURNZD × NZDUSD = EURUSD (AUD·GBP·NZD는 **곱하기**)
- 변화율로 보면 C 변화 ≈ A 변화 − B 변화 (곱하기 쌍은 A 변화 + B 변화).
- 규칙(5줄 표): A+ > B+ = C+ (C < A) / A+ > B− = C+ (C > A) / A− < B+ = C− / A− < B− = C− / A− > B− = C+.
  → **A가 B보다 크면 C는 오르고, 작으면 내린다.**
- "이 4개 환율의 변동 차이는 EURUSD 변동과 같다." "시장의 변동 논리를 이해해야 한다."

## 2. 평면(Plane) 읽기
- 가로 X = Cross B(USD 쪽, 독립변수), 세로 Y = Cross A(EUR 쪽, 종속변수), 공식 Y = X(45°선).
- 45°선 위 = EURUSD 상승(C+), 아래 = 하락(C−). 사분면 ①(A+·B+)·④(A−·B+)에서 크기 비교가 중요.
- Plane A의 X·Y를 Plane B의 축으로 옮겨 Z축(세 번째 통화)을 본다.

## 3. 교차 통화 유도
- CHFJPY = EURJPY / EURCHF, CADJPY = EURJPY / EURCAD, CADCHF = EURCAD / EURCHF.
- EURJPY 매수 + EURCHF 매도 = CHFJPY 매수.
- 통화별 강약 순위로 교차쌍 방향을 정한다(예: CAD·CHF 강세, JPY 약세 → CADJPY·CHFJPY 매수). AUD/GBP/NZD 쪽은 GBPNZD·AUDNZD·GBPAUD.
- EUR·USD와 나머지 6개 통화(AUD·CAD·CHF·GBP·JPY·NZD)로 만드는 교차쌍 15개(+EURUSD).

## 4. 시장 상호연결 해석
- "환율 간 상호관계는 상관관계가 아니라 서로 걸려 있는 관계."
- EURUSD 추세를 알려면 세 번째 통화의 움직임을 봐야 한다(EURJPY·USDJPY 관찰).
- EURJPY가 옆으로 머무는데 USDJPY가 오르면 EURUSD는 내려간다(EURUSD 약세 시나리오).
- USDJPY가 높은 자리에서 머물면 EURJPY는 더 아래로 떨어지지 않는다(옆걸음).
- 순환 추세를 가진 통화가 특정 가격 범위에서 움직임을 수렴한다 → 가격대 머묾(히트맵)이 의미.

## 5. 손익분기(BEP)
- BEP = (P1·수량1 + P2·수량2) ÷ (수량1 + 수량2). 예: EURJPY 129.600·129.924 각 100K → 129.762.

## 시스템 적용 (매니저 결정)
- 통화 평면판(https://claude.ai/artifact/UPrgkWm9HqFMryWif75gwj)에 노트 공식 그대로의 '사분면 판'과 '교차쌍 강약 지도'를 추가한다. 참고 그림이며 예측·주문 신호가 아니다.
