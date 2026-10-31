# 프로젝트 1: SMC+CRT (석준님 방식)

2026-10-29 석준님 지시로 "프로젝트 1번"으로 저장. 파일은 원래 자리에 두고 여기서 목록으로 묶는다(다른 문서 링크가 깨지지 않게).

## 규칙
- `trading/rules/smc-crt-analysis.md` — 차트 분석 기준(4H CRT → 스윕 → HTF 위치 → MSS = 마지막 다리 시작 스윙, 몸통 마감 → OB 진입), 진입 전 반대 점검 5개
- `trading/rules/seokjun-method-v1.md` — 석준님 방식(주봉+4H 외부 구조 일치, 보호 저점, 위치, 4H → 15/5분 → 1분)
- `trading/strategy/user_smc_crt_rules.md`, `venus_smc_v1.md`, `venus_model_v1.md`, `venus_model_v2.md` — 이전 버전 규칙

## 백테스트
- 코드: `trading/research/crt_backtest.py`(v4, 9종목 M5), `crt_mss_ob.py`, `crt_cisd.py`, `crt_scorecard.py`
- 결과: `trading/research/results/2026-10-28_crt_variants.md`, `trading/research/README.md`의 CRT 절
- 결론(2026-10-28): 비용 후 기계적 엣지 없음. 일관된 것은 "4H OB까지 안 내려온 스윕은 나쁨" 하나.

## 실전 기록
- `trading/learning/README.md`(거래 카드 양식), `trading/learning/trades/20261027-GBPUSD-01.md`(손절 복기)

## 다음 할 일
- 석준님 재량 거래 30~50건을 체크리스트와 함께 기록해 실제 엣지 확인.
