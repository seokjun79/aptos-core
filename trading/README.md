# Venus 트레이딩

고객님 FTMO 진입 기록을 SMC·CRT로 분석해서 만든 자동매매 모델과 EA, 그리고 그걸 검증하는 도구가 들어 있어요.

## 들어 있는 것

| 파일 | 내용 |
|---|---|
| `analysis/smc_crt_entries.py` | FTMO 진입 29건을 SMC·CRT 기준으로 분석 |
| `strategy/venus_model_v1.md` | 모델 규칙서. EA와 백테스터 둘 다 이 규칙을 따름 |
| `mt5/VenusModelV1.mq5` | **MT5에 넣는 EA** (모델 A 모멘텀 / 모델 B CRT 선택) |
| `mt5/export_data.py` | MT5에서 가격 데이터와 거래 기록을 꺼냄 |
| `mt5/tester_*.ini` | MT5 전략 테스터를 명령 한 줄로 돌리는 설정 |
| `backtest/venus_backtest.py` | 파이썬 백테스터 (학습/검증 구간 자동 분리) |

## 고객님 컴퓨터에서 하는 순서

1. **EA 넣기:** `mt5/VenusModelV1.mq5`를 MT5의 `MQL5\Experts\Venus\` 폴더에 복사하고 MetaEditor에서 컴파일(F7)
2. **데이터 꺼내기:** MT5를 켠 채로 `pip install MetaTrader5 pandas matplotlib` 후 `python trading/mt5/export_data.py`
3. **백테스트 (두 가지 방법으로 교차 확인):**
   - 파이썬: `python trading/backtest/venus_backtest.py --data trading/data/EURUSD_M15_icmarkets.csv --model A --grid`
   - MT5 전략 테스터: `terminal64.exe /config:trading\mt5\tester_A_IS.ini` (그다음 `tester_A_OOS.ini`)
4. **합격 기준(검증 구간):** 거래 60건 이상, 프로핏 팩터 1.2 이상, 최대 낙폭 10R 이하
5. **합격하면:** 데모 계좌에 EA를 붙이고 4주 동안 그대로 둠 → 백테스트와 비교 → 실계좌

Claude Code를 이 컴퓨터에서 켜면 1~4번을 비너스가 대신 해요.
