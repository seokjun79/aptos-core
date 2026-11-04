# 외부에서 가져온 도구 목록 (매니저 비너스 관리)

새로 설치하거나 가져올 때마다 여기에 한 줄 추가한다. 출처·버전(커밋)·위치·안전 확인 결과를 같이 적는다.

| 이름 | 무엇 | 출처 · 버전 | 어디에 있나 | 안전 확인 | 날짜 |
|---|---|---|---|---|---|
| qlib (pyqlib) | 마이크로소프트 AI 퀀트 연구 도구 | github.com/microsoft/qlib · pyqlib 0.9.7, lightgbm 4.7.0 | RC PC `C:\Users\kun00\venus\qlib_env` (가상환경 안에만) | 코드 검사 후 설치, 석준님 승인 | 2026-11-03 |
| xgboost, torch (CPU) | qlib 딥러닝 모델용 | pip · xgboost 3.4.1, torch 2.15.0+cpu | RC PC `qlib_env` 안 | 석준님이 RC 창에서 직접 승인 | 2026-11-04 |
| oil-ui | 화면 디자인 스킬(설명서+보조 스크립트) | github.com/oil-oil/oil-ui · 커밋 5b03da0 · MIT | 이 저장소 `.claude/skills/oil-ui/` (SOURCE.txt) | 코드 검사: 악성 없음. 자동 업데이트·버전 확인 끔(settings.json env) | 2026-11-04 |

규칙
- 출처를 모르는 pickle·모델 파일은 열지 않는다.
- 자동 업데이트는 끈다. 업데이트는 다시 검사한 뒤에만 한다.
- PC에 설치(pip 등)는 석준님이 그 PC 창에서 직접 허락할 때만 한다.
