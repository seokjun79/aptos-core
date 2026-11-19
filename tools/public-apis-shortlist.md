# 우리 일에 바로 쓸 공개 API (public-apis-4Kr에서 고름, 2026-11-07)

전체 목록: `tools/vendor/public-apis-4Kr/README.md` (한국), `GLOBAL_PUBLIC_APIS_KR.md` (글로벌).
키가 필요한 API는 석준님 계정으로 발급해야 하고, 키는 화면·메시지에 쓰지 않는다.

## 주식·매크로 (JC비너스)
| API | 쓸 곳 | 키 |
|---|---|---|
| [Open DART](https://opendart.fss.or.kr/) | 국내 상장사 공시·재무, 실적 발표 확인, 보유 ETF 구성 종목 공시 | 무료 발급 |
| [한국은행 ECOS](https://ecos.bok.or.kr/api/) | 기준금리·환율·물가 등 매크로 재료(qlib B 재료 보강) | 무료 발급 |
| [한국수출입은행 환율](https://www.koreaexim.go.kr/ir/HPHKIR019M01) | 원/달러 등 매일 환율 | 무료 발급 |
| [금융위원회 금융공공데이터](https://www.fsc.go.kr/in060301) | 주식 시세·기업 기본정보(공공데이터포털) | 무료 발급 |
| [한국투자증권 KIS](https://apiportal.koreainvestment.com/intro) | 이미 사용 중(조회만) | 사용 중 |

## 경매·부동산 (auction-analyst, data-collector)
| API | 쓸 곳 | 키 |
|---|---|---|
| [아파트 매매 실거래가](https://www.data.go.kr/data/15126469/openapi.do) | 부산·경남 아파트 경매 시세 비교 | 공공데이터포털 |
| [아파트 전월세 실거래가](https://www.data.go.kr/data/15126474/openapi.do) | 임차인·전세가율 확인 | 공공데이터포털 |
| [한국부동산원 R-ONE](https://www.reb.or.kr/r-one/portal/openapi/openApiIntroPage.do) | 지역 시세 흐름 통계 | 무료 발급 |

## 물류·통관 (석준님 회사 일: 팔레트·용기 관리)
| API | 쓸 곳 | 키 |
|---|---|---|
| [관세청 화물통관정보](https://www.data.go.kr/data/15126268/openapi.do) | 수입 화물 통관 진행 조회 | 공공데이터포털 |
| [KOMSA MTIS](https://mtisopenapi.komsa.or.kr/) | 선박·해운 안전 정보 | 무료 발급 |
| [관세청 수출입 무역통계](https://tradedata.go.kr/cts/index.do) | 품목별 수출입 통계 | 웹 |
| [Delivery Tracker](https://tracker.delivery/) | 택배 배송 조회(쇼핑·개인비서) | 무료 |

## 생활·일정 (personal-assistant)
| API | 쓸 곳 | 키 |
|---|---|---|
| 한국천문연구원 특일 정보 | 공휴일·대체휴일(장 쉬는 날 계산) | 공공데이터포털 |
| 기상청 단기예보 | 출퇴근·현장 날씨 | 공공데이터포털 |

## 바로 할 일
1. 석준님이 공공데이터포털(data.go.kr)에 가입하면 키 하나로 실거래가·통관·특일·날씨를 모두 신청할 수 있다. 안내는 처음 쓸 때 공식 문서를 확인하고 전체 순서를 한 번에 드린다.
2. DART·ECOS 키는 무료라서 발급되면 JC가 공시 알림·매크로 재료에 붙인다.
