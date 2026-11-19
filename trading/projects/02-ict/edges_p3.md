# 시간대·흐름 효과(우위) 후보 목록 — 백테스트용 (2026-10-31 조사)

## 먼저 알아 둘 점 (조사 한계)
- 이번 조사는 WebSearch만으로 했다. 논문 원문 사이트(bankofcanada.ca, nd.edu, newyorkfed.org, skidmore.edu, mql5.com, aut.ac.nz)는 이 세션 네트워크에서 막혀 WebFetch로 못 열었다.
  그래서 숫자는 "검색 결과에 나온 초록·요약" 기준이다. 요약 블로그(2차 출처)에서 온 숫자는 [2차]로 표시했다.
- "확인 못함" = 원문에서 숫자를 직접 못 봤다는 뜻.
- 시각은 모두 **뉴욕 시간(ET, 서머타임 반영)** 기준. 브로커 서버 시간(보통 GMT+2/+3)으로 바꿔서 시험해야 한다.
- "비용 판단"은 추정이다. CFD 스프레드는 브로커마다 다르므로, 백테스트 때 실제 스프레드를 넣고 다시 봐야 한다.

## 한눈에 보기

| # | 이름 | 대상 | 최근(2015년 이후) 유지? | 비용 대비 (추정) |
|---|---|---|---|---|
| 1 | 지수 장중 모멘텀(첫 30분→마지막 30분) | US500/USTEC/US30, UK100/DE40/JP225 | 엇갈림 | 작음~보통 |
| 2 | 하루 누적 → 마지막 30분 (헤지 수요) | 지수 + FX·금 | 2020년까지 표본, 유지 | 보통 |
| 3 | 노이즈 영역 돌파 장중 모멘텀 | US500 | 2007~2024 비용 뺀 뒤 유지(저자 주장) | 큼(저자 주장) |
| 4 | 개장 범위 돌파(5분 ORB) | USTEC | 재현 시 비용 빼면 0 [2차] | 작음 |
| 5 | 야간 드리프트(새벽 2~3시 ET) | US500 | 2021년 이후 거의 0 | 작음 |
| 6 | 유럽 개장 전후 4시간 상승 | US500 | 확인 못함 | 보통 |
| 7 | 야간 상승 vs 정규장 | US500 등 | 2000년 이후 유지 [arXiv 2025] | 작음(하루 2.75bp) |
| 8 | FOMC 전 상승(pre-FOMC) | US500 | 2015년 이후 사라짐(반론 있음) | 보통(있다면) |
| 9 | 월말·월초(TOM) | US500 등 | 2001년 이후 사라짐(2025 논문) | 보통 |
| 10 | FX 픽스 전 달러 강세→픽스 후 약세(W자) | EURUSD/GBPUSD/USDJPY 등 | 21년 표본, 2024 JF 게재 | 확인 못함 |
| 11 | 월말 4시 픽스 헤지 리밸런싱 | EURUSD/GBPUSD/USDJPY | 실무 노트만 | 작음~보통 |
| 12 | FX "자기 나라 장중엔 자기 통화 약세" | EURUSD | 1997~2007 표본, 이후는 블로그만 | 작음(EURUSD만 가능) |
| 13 | FX 장중 모멘텀 | (원 논문은 RUBUSD) | 금융위기 때만 | 작음 |
| 14 | 금: 아시아 시간 상승 / 런던·뉴욕 하락, PM 픽스 하락 | XAUUSD | 2001~2013 위주, 이후 논문 없음 | 확인 못함 |
| 15 | 시계열 모멘텀(12개월) | 전 종목 | 2009년 이후 약함 | 비용 영향 작음(드문 매매) |
| 16 | 변동성 축소(NR7) 뒤 돌파 | 선물 전반 | 학술 근거 거의 없음 | 작음 |

---

## 1. 지수 장중 모멘텀 (첫 30분 → 마지막 30분)
- **근거:** Gao, Han, Li, Zhou (2018) "Market Intraday Momentum", Journal of Financial Economics 129권 394-414쪽. https://ideas.repec.org/a/eee/jfinec/v129y2018i2p394-414.html
  - 해외 지수: Li, Sakkas, Urquhart (2022) "Intraday time series momentum: Global evidence and links to market characteristics", Journal of Financial Markets 57권. https://nottingham-repository.worktribe.com/OutputFile/5273196
- **효과 크기(원문/요약 숫자):** SPY 1993~2013. 첫 30분 수익률(전날 종가→10:00)이 마지막 30분(15:30→16:00)을 예측. 예측 R² 1.6%, 12번째 30분(15:00~15:30)을 더하면 2.6%, 표본 밖 R² 1.2%. 변동성·거래량 큰 날, 경기침체기, 일부 경제지표 발표일에 더 강함. 타이밍 전략 연 6.67%, 샤프 1.08(매수보유 0.29) [2차: Substack 요약], 다른 요약은 연 6.34%(작업논문) [2차: Alpha Architect]. 해외: 16개 선진 시장 중 12곳에서 유의. 원 논문에 FTSE 100, EuroStoxx 50 선물도 확인.
- **최근 유지?** 엇갈림. COVID 기간 연구: S&P 500 전체로는 여전히 예측하지만 팬데믹 충격 기간엔 유의하지 않음(https://dspace5old.zcu.cz/handle/11025/46501). QuantConnect 재현은 최근 기간 샤프 -0.628 [2차](https://www.quantconnect.com/research/15348/intraday-etf-momentum/). 2014~2024 깨끗한 재현은 확인 못함.
- **M5 규칙:**
  - 대상: US500, USTEC, US30 (현물 장 09:30~16:00 ET 기준). UK100(08:00~16:30 런던), DE40(09:00~17:30 프랑크푸르트), JP225(09:00~15:30 도쿄)도 같은 방식으로 해당 현물장 시간에 맞춰 시험.
  - 신호: r1 = (10:00 ET 봉 종가) / (전날 16:00 ET 종가) − 1.
  - 진입: 15:30 ET에 r1 > 0이면 매수, r1 < 0이면 매도(원 논문 변형: 매도 대신 쉬기).
  - 청산: 16:00 ET(15:55 봉 종가). 손절 없음.
  - 추가 변형: r1에 r12(15:00→15:30)를 더해 둘 다 같은 방향일 때만 진입.
- **비용 판단:** 마지막 30분 움직임 자체가 작아서 "가장 크게 움직인 날도 대부분 투자자가 먹기엔 작다"는 지적 있음(cxoadvisory). CFD 스프레드가 넓으면 남는 게 거의 없을 수 있다. → **작음~보통**. 변동성 큰 날만 고르면 나아질 수 있음(추정).

## 2. 하루 누적 수익 → 마지막 30분 (헤지 수요 모멘텀)
- **근거:** Baltussen, Da, Lammers, Martens (2021) "Hedging demand and market intraday momentum", Journal of Financial Economics 142권 1호 377-403쪽. https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html , https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum/
- **효과 크기:** 60개 넘는 선물(주가지수·채권·원자재·통화), 1974년 12월~2020년 5월. "마지막 30분 수익률은 그날 나머지 시간 수익률로 양(+)의 방향으로 예측된다", 경제적·통계적으로 매우 유의, 다음 며칠 동안 되돌림. 원인은 옵션 시장조성자·레버리지 ETF의 감마 헤지. 자산군별 샤프 0.87~1.73 [2차: Alpha Architect].
- **최근 유지?** 표본이 2020년까지라 2015~2020은 포함. 그 이후 확인 못함. (추정: 0DTE 옵션이 늘어 감마 헤지 흐름이 커졌다면 오히려 강해졌을 수 있음 — 확인 안 된 추정.)
- **M5 규칙:**
  - 대상: US500, USTEC, US30(장 종료 16:00 ET). DE40/UK100/JP225는 각 현물장 종료 30분 전. 원 논문이 통화·원자재 선물도 포함하므로 XAUUSD, EURUSD는 CME 선물 종료(17:00 ET) 기준으로 시험(추정 규칙, 원문에서 정확한 종료 시각 확인 못함).
  - 신호: r_rest = (15:30 ET 종가) / (전날 16:00 ET 종가) − 1.
  - 진입: 15:30 ET, r_rest 부호 방향.
  - 청산: 16:00 ET.
  - 변형: |r_rest|가 최근 20일 평균보다 큰 날만.
- **비용 판단:** 1번과 비슷하지만 샤프가 더 높게 보고됨 → **보통**.

## 3. 노이즈 영역 돌파 장중 모멘텀 (SPY)
- **근거:** Zarattini, Aziz, Barbon (2024) "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)", Swiss Finance Institute Research Paper 24-97. https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy , https://ideas.repec.org/p/chf/rpseri/rp2497.html
- **효과 크기:** 2007~2024년 초, 비용 뺀 총수익 1,985%, 연 19.6%, 샤프 1.33(초록).
- **최근 유지?** 표본이 2024년까지라 최근 포함. 다만 저자 측(Concretum, Bear Bull Traders)이 상업적 이해관계가 있고 동료심사 전 작업논문 → 과최적화 의심하고 시험 필요.
- **M5 규칙 (논문 개요 기준, 세부값 일부 확인 못함):**
  - 대상: US500 (USTEC, US30도 시험).
  - 노이즈 영역: 지난 14일 동안 "개장가 대비 같은 시각까지의 평균 절대 움직임"을 시각별로 구함 → 오늘 개장가 ± 그 값이 상단·하단.
  - 진입: 09:30 이후 정해진 체크 시각(논문은 30분 간격으로 알려짐 — 확인 못함)에 가격이 상단 위면 매수, 하단 아래면 매도.
  - 청산: 반대편 경계(또는 VWAP) 이탈 시, 아니면 16:00 ET 장 마감.
- **비용 판단:** 저자는 비용 뺀 뒤에도 크다고 함 → **큼(주장)**, 검증 우선순위 높음.

## 4. 개장 범위 돌파 (5분 ORB)
- **근거:** Zarattini, Aziz (2023) "Can Day Trading Really Be Profitable?", SSRN 4416622. 요약: https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy
- **효과 크기:** 원문 숫자 확인 못함. 규칙: 첫 5분 봉 방향으로 진입, 손절 = 첫 5분 봉 반대쪽 끝, 목표 = 진입~손절 거리 10배.
- **최근 유지?** 개인 재현(NQ, SPX, Dow, DAX, FTSE CFD, 2015~2026): "총수익은 재현됐으나 비용 빼면 0" [2차, mql5 블로그] https://www.mql5.com/en/blogs/post/776235
- **M5 규칙:** 대상 USTEC(원 논문 QQQ), US500, DE40, UK100. 09:30~09:35 ET 첫 M5 봉이 양봉이면 09:35에 매수(음봉이면 매도, 도지는 쉼). 손절 = 첫 봉 저가(매도는 고가). 목표 = 10R. 못 닿으면 16:00 ET 청산.
- **비용 판단:** **작음** (재현에서 비용 빼면 0).

## 5. 야간 드리프트 (새벽 2~3시 ET)
- **근거:** Boyarchenko, Larsen, Whelan "The Overnight Drift", Review of Financial Studies 36권 9호(2023) 3502-3547. https://ideas.repec.org/a/oup/rfinst/v36y2023i9p3502-3547..html , NY Fed Staff Report 917 https://www.newyorkfed.org/research/staff_reports/sr917
  - 후속: 같은 저자 "The Disappearing Overnight Drift", Liberty Street Economics, 2026-07-01. https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/
- **효과 크기:** 1998~2018 E-mini S&P 500. 미국 주식 프리미엄의 거의 100%가 02:00~03:00 ET 한 시간에 생김. 전날 장 마감 주문 불균형(매도 우위)이 클수록 더 큼. 이 한 시간이 예전엔 연 약 3.7%.
- **최근 유지?** **아니오.** 2021년 이후 평균 거의 0(저자 본인). 마감 주문 불균형의 흩어짐이 6.5%→2.9%로 줄어든 탓 [2차 숫자]. 불균형이 다시 커지면 돌아올 수 있다고 함. 또 2차 요약: 매수·매도 호가차 넣으면 평균 수익·샤프가 음수.
- **M5 규칙:** US500. 02:00 ET 봉 시가 매수 → 03:00 ET 청산. 변형: 전날 15:00~16:00 ET 하락폭이 큰 날(예: 하위 20%)만.
- **비용 판단:** 하루 1시간 수익이 매우 작음 → **작음**. 최근엔 효과도 없음.

## 6. 유럽 개장 전후 4시간 상승
- **근거:** Bondarenko, Muravyev (2023) "Market Return Around the Clock: A Puzzle", JFQA 58권 3호 939-967. https://ideas.repec.org/a/cup/jfinqa/v58y2023i3p939-967_1.html
- **효과 크기:** E-mini S&P 500에서 "유럽 개장 전후 4시간이 시장 평균 수익 전체를 차지". 아시아 마감~유럽 개장 4시간: 연 7.6%, 샤프 1.67, t=6.4 [2차: Alpha Architect]. 원인: 밤사이 쌓인 불확실성(VIX 선물)이 유럽 개장 때 풀림.
- **최근 유지?** 확인 못함. 5번과 같은 시간대라 2021년 이후 약해졌을 가능성(추정).
- **M5 규칙:** US500(USTEC도). 정확한 창은 원문 확인 못함 → 시험안: 00:00 ET 매수 → 04:00 ET 청산 (런던 개장 03:00 ET 전후). 서머타임 차이 주의.
- **비용 판단:** 하루 1번, 4시간 보유 → **보통**(효과가 아직 있다면).

## 7. 야간 상승 vs 정규장 (Overnight vs Intraday)
- **근거:** Lou, Polk, Skouras (2019) "A tug of war: Overnight versus intraday expected returns", JFE 134(1) 192-213. https://personal.lse.ac.uk/polk/research/TugOfWar.pdf ; Cooper, Cliff, Gulen (2008, 1993~2003 S&P 500에서 주식 프리미엄이 전부 야간에 생김 — 위 검색 요약 인용); Mamaysky (2025) arXiv https://arxiv.org/html/2507.04481v1
- **효과 크기:** 2000년 이후 야간이 장중보다 하루 평균 2.75bp, 연 약 7.2% 더 좋음(Mamaysky 2025 요약). Lou 등은 비용 때문에 실제 수익성은 "훨씬 덜 매력적"이라고 직접 씀.
- **최근 유지?** 2000년 이후 표본(2025 논문)에서 유지로 보고됨. 다만 5번의 2021년 이후 약화와 함께 볼 것.
- **M5 규칙:** US500/USTEC/US30. 15:55 ET 봉 종가 매수 → 다음 날 09:35 ET 봉 시가 청산(매일). 대조군: 09:30 매수→16:00 청산.
- **비용 판단:** 하루 2.75bp 차이는 CFD 스프레드+오버나이트 이자보다 작을 가능성 큼 → **작음**.

## 8. FOMC 전 상승 (pre-FOMC drift)
- **근거:** Lucca, Moench (2015) "The Pre-FOMC Announcement Drift", Journal of Finance 70권 329-371. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf ; 반박: Kurov, Wolfe, Gilbert (2021) "The Disappearing Pre-FOMC Announcement Drift", Finance Research Letters 40권. https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html
- **효과 크기:** 1994년 9월~2011년 3월, 발표 전 24시간 S&P 500 평균 +49bp(결과와 무관). 주식만, 국채는 없음.
- **최근 유지?** **의견 갈림.**
  - 사라졌다: Kurov 등 — 2015년 이후 기자회견 있든 없든 사실상 사라짐(2019년 12월까지). Ben Dor, Rosa (2019): 2011년 4월부터 없음.
  - 남아 있다: NY Fed 블로그(2018) — 2018년 6월까지 기자회견일 약 40bp. https://libertystreeteconomics.newyorkfed.org/2018/11/the-pre-fomc-announcement-drift-more-recent-evidence.html
  - 조건부: 내재변동성이 중앙값보다 높을 때 109bp, 낮을 때 9.7bp (Martello, Ribeiro, Quantpedia 요약 [2차]).
- **M5 규칙:** US500(USTEC, US30, DE40도). FOMC 발표 전날 14:00 ET 매수 → 발표 당일 13:45 ET(발표 14:00 ET 15분 전) 청산. 변형: 전날 VIX가 1년 중앙값보다 높을 때만. FOMC 날짜 목록 필요(연 8회).
- **비용 판단:** 효과가 있다면 40~49bp로 스프레드보다 훨씬 큼. 다만 1년 8번뿐이라 표본 작음 → **(있다면) 보통~큼, 최근엔 의심**.

## 9. 월말·월초 효과 (Turn-of-the-Month)
- **근거:** McConnell, Xu (2008) "Equity Returns at the Turn of the Month", Financial Analysts Journal 64(2) 49-64. https://ideas.repec.org/a/taf/ufajxx/v64y2008i2p49-64.html ; 반박: Han, Han, Tian (2025) "The disappearing turn-of-month effect", Finance Research Letters 71권. https://ideas.repec.org/a/eee/finlet/v71y2025ics1544612324014909.html ; ETF 시대: FPA Journal (2011) https://www.financialplanningassociation.org/article/journal/APR11-turn-month-anomaly-age-etfs-reexamination-return-enhancement-strategies
- **효과 크기:** 1926~2005 CRSP, 월 마지막 거래일~다음 달 3번째 거래일(4일) 하루 평균 0.15%(가치가중) / 0.22%(동일가중). 1987~2005에도 유지.
- **최근 유지?** **의견 갈림.** 2025 논문: 2001년 이후 완전히 사라짐. FPA(2011): ETF 이후 S&P 500에선 월 첫 거래일에 몰림. 또 다른 선물 연구: TOM "+1"(첫날)만 꾸준히 비용 뺀 이익(cxoadvisory 요약 [2차]).
- **M5 규칙:** US500/US30/USTEC/DE40/UK100. A안: 월 마지막 거래일 15:55 ET 매수 → 3번째 거래일 15:55 ET 청산. B안: 마지막 거래일 15:55 ET 매수 → 첫 거래일 15:55 ET 청산.
- **비용 판단:** 하루 0.15%면 스프레드보다 큼 → **보통**. 다만 최근엔 사라졌다는 논문 있음.

## 10. FX 픽스 전 달러 강세 → 픽스 후 약세 (W자 패턴)
- **근거:** Krohn, Mueller, Whelan (2024) "Foreign Exchange Fixings and Returns around the Clock", Journal of Finance 79(1) 541-578. https://ideas.repec.org/a/bla/jfinan/v79y2024i1p541-578.html , https://onlinelibrary.wiley.com/doi/10.1111/jofi.13306 , BoC 작업논문 21-48.
- **효과 크기:** 9개 주요 통화, 21년, 5분 수익률. "달러는 픽스 직전까지 오르고 그 뒤 내려 하루에 W자 모양". 되돌림은 넓게 나타나고 통계적으로 매우 유의. bp 크기·전략 샤프는 **확인 못함**(원문 열지 못함).
- **최근 유지?** 21년 표본이 2015년 이후 일부 포함(정확한 끝 연도 확인 못함). 2024년 최상위 저널 게재.
- **M5 규칙 (픽스 시각은 일반 지식, 논문 내 정확한 창은 확인 못함):**
  - 주요 픽스: 도쿄 09:55 JST, ECB 14:15 CET, WM/R 런던 16:00 런던시간.
  - 픽스 전: 픽스 2시간 전 달러 매수(EURUSD·GBPUSD 매도, USDJPY 매수) → 픽스 시각 청산.
  - 픽스 후: 픽스 시각 달러 매도 → 2시간 뒤 청산.
  - 대상: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF.
- **비용 판단:** 효과 크기 확인 못함. 주요 통화쌍은 스프레드가 작아 가능성 있음(추정). → **확인 못함, 1순위 시험 대상**.

## 11. 월말 4시 픽스 헤지 리밸런싱
- **근거:** Melvin, Prins (2015) "Equity hedging and exchange rates at the London 4 p.m. fix", Journal of Financial Markets 22권 50-72. https://ideas.repec.org/a/eee/finmar/v22y2015icp50-72.html ; 덴마크 중앙은행 메모(2024) https://nationalbanken.dk/en/news-and-knowledge/publications-and-speeches/economic-memo/2024/currency-hedging-and-the-danish-pension-sector
- **효과 크기:** "한 달 동안 주가가 오른 나라의 통화는 월말 픽스 전에 약해진다." 숫자 확인 못함. 덴마크: 미국 주가 10% 상승 ≈ FX 리밸런싱으로 크로네 약 280억 DKK 매수.
- **최근 유지?** 실무(BNY·RBC·골드만 월말 모델)는 계속 쓰지만 공개 검증 없음. SocGen 코멘트: "월말 픽스 직전 아주 짧은 시간 빼면 돈 벌기 어렵다".
- **M5 규칙:** 월 마지막 거래일. 그 달 US500 수익률 − (DE40 또는 UK100 수익률)이 양수(미국이 더 오름)면 → 12:00 런던시간에 달러 매도(EURUSD·GBPUSD 매수) → 16:00 런던시간 청산. 음수면 반대. USDJPY는 US500 − JP225로.
- **비용 판단:** 1년 12번, 크기 모름 → **작음~보통(추정)**.

## 12. FX "자기 나라 장중엔 자기 통화 약세"
- **근거:** Breedon, Ranaldo (2013) "Intraday patterns in FX returns and order flow" (SNB WP 2011-04, 1997~2007 EBS 자료) https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04 ; Ranaldo (2009) "Segmentation and time-of-day patterns in foreign exchange markets" (SNB WP 2007-03) https://www.snb.ch/en/publications/research/working-papers/2007/working_paper_2007_03
- **효과 크기:** 통화는 자기 나라 거래시간에 약해지는 경향이 유의. 주문흐름도 같은 패턴(자기 시간에 외화를 사는 쪽). 매수·매도 호가차 넣으면 대부분 통화쌍은 이익 안 남고 **EURUSD만 이익** (cxoadvisory 요약). 연수익 숫자 확인 못함.
- **최근 유지?** 학술 표본은 2007년까지. QuantRocket 블로그는 이후에도 유지됐다고 함 [2차] https://www.quantrocket.com/blog/business-day-forex-patterns
- **M5 규칙:** EURUSD. 03:00 ET(유럽 09:00) 매도 → 11:00 ET 청산하고 매수 → 16:00 ET 청산. (QuantRocket 재현 규칙) GBPUSD, USDJPY(도쿄 시간 엔 약세 → 19:00~03:00 ET USDJPY 매수)도 같은 생각으로 시험.
- **비용 판단:** 하루 2번 매매, EURUSD만 비용 넘었다는 결과 → **작음**(스프레드 0.1~0.2핍급 계좌에서만 가능성).

## 13. FX 장중 모멘텀
- **근거:** Elaut, Frömmel, Lampaert (2018) "Intraday momentum in FX markets: Disentangling informed trading from liquidity provision", Journal of Financial Markets 37권 35-51. https://ideas.repec.org/a/eee/finmar/v37y2018icp35-51.html
- **효과 크기:** RUB-USD에서 첫 30분이 마지막 30분 예측. 숫자 확인 못함. 금융위기 기간에 두드러짐(인용 논문 요약).
- **최근 유지?** 확인 못함. 주요 통화쌍(EURUSD 등) 근거는 2번(Baltussen) 논문의 통화 선물 쪽이 더 낫다.
- **M5 규칙:** EURUSD/GBPUSD/USDJPY. "하루"를 17:00 ET~다음 날 17:00 ET로 보고, 첫 30분 대신 런던 개장 30분(03:00~03:30 ET) 수익률 방향으로 16:30 ET 진입 → 17:00 ET 청산(추정 규칙).
- **비용 판단:** **작음**.

## 14. 금: 아시아 시간 상승 / 서구 시간 하락, PM 픽스 전후 하락
- **근거:**
  - Abrantes-Metz, Metz (2014) 금 픽스 분석(2001~2013): 2004년부터 오후 픽스 때 이상 움직임, 2010년엔 픽스 중 큰 움직임의 92%가 하락. https://www.bloomberg.com/news/articles/2014-02-28/gold-fix-study-shows-signs-of-decade-of-bank-manipulation
  - Caminschi, Heaney (2014) "Fixing a Leaky Fixing", Journal of Futures Markets 34(11): 픽스 초반 몇 분의 금 선물·GLD 거래가 픽스 방향을 맞힘(어떤 경우 90% 넘음). https://ideas.repec.org/a/wly/jfutmk/v34y2014i11p1003-1039.html
  - CBS 석사논문(동료심사 아님) "Gold Price Dynamics Around the Clock": 동양 시간엔 상승, 나머지 시간엔 하락하는 '모자 모양'. https://research.cbs.dk/en/studentProjects/gold-price-dynamics-around-the-clock/
  - 취리히대 석사논문: AM·PM 픽스 전후 평균 수익이 하루 중 가장 큰 음수. https://www.merlin.uzh.ch/publication/show/11299
  - Batten 외 (2017) PLOS ONE: 15년 5분 자료, 수익·변동성에 뚜렷한 주기성(세부 숫자 확인 못함).
- **최근 유지?** 2015년 3월 픽스가 ICE 전자 경매(LBMA Gold Price, 오후 3시 런던)로 바뀜. 그 뒤를 본 학술 논문은 확인 못함. 2026년 7월 Money Metals 기사는 "하락은 미국 시간, 반등은 아시아 시간"이라고 하지만 시장 논평.
- **M5 규칙:** XAUUSD.
  - A(세션): 19:00 ET(아시아 시작) 매수 → 03:00 ET(런던 개장) 청산. 대조: 03:00 매도 → 17:00 청산.
  - B(PM 경매): 15:00 런던시간 30분 전(14:30) 매도 → 15:30 청산.
  - C(AM 경매): 10:30 런던시간 경매 15분 전 매도 → 15분 뒤 청산.
- **비용 판단:** 크기 확인 못함. 금 스프레드가 지수보다 넓은 편이라 짧은 창(B·C)은 불리(추정). → **확인 못함**.

## 15. 시계열 모멘텀 (중기 추세 추종)
- **근거:** Moskowitz, Ooi, Pedersen (2012) "Time series momentum", JFE. 자료: https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data ; 반박: Kim, Tse, Wald (2016) 요약 https://quantpedia.com/deconstructing-the-time-series-momentum-strategy/
- **효과 크기:** 58개 선물·선도(지수·통화·원자재·국채), 1985년 1월~2009년 12월, 12개월 되돌아보기·1개월 보유. 모든 종목에서 수익이 양(+). 샤프 숫자 확인 못함.
- **최근 유지?** **약함.** Kim 등: 최근엔 매수보유보다 못하고, 좋은 성과는 2001년 이전에 몰림, 2009~2013엔 우위 사라짐. 변동성 조절을 빼면 알파가 0.41%/0.42%로 줄어듦.
- **M5 규칙:** (M5 자료를 일봉/월봉으로 묶어 시험) 대상 전부(US500…XAUUSD, EURUSD…). 매월 마지막 거래일 종가에 지난 12개월 수익률 > 0이면 매수, < 0이면 매도, 한 달 보유. 포지션 크기 = 목표 변동성(예: 연 40% ÷ 종목 변동성 — 원 논문 방식으로 알려짐, 수치 확인 못함). 단기 변형: 1개월·3개월 되돌아보기.
- **비용 판단:** 매매가 드물어 스프레드 부담은 작음. 단, CFD 오버나이트 이자가 큼 → **효과 약함, 비용 영향 보통**.

## 16. 변동성 축소(NR7) 뒤 돌파
- **근거:** 동료심사 학술 근거 **찾지 못함**. Crabel(1990, Technical Analysis of Stocks & Commodities, 실무 기사). 실무 백테스트 Oxfordstrat: 미국 선물 42개, 1980~2016 — 비용 넣으면 다른 규칙 없이는 거래 불가. https://oxfordstrat.com/?p=16086 ; Lundström(Umeå 작업논문): 개장 범위 돌파 수익이 변동성 상태에 따라 크게 다름(원유 약 200bp, S&P 500 약 150bp 차이). https://swopec.hhs.se/umnees/abs/umnees0861.htm
- **최근 유지?** 확인 못함.
- **M5 규칙:** 모든 대상. 전날 일봉 범위가 최근 7일 중 가장 좁으면(NR7) 다음 날 첫 1시간(지수는 현물 개장 후, FX·금은 런던 개장 03:00~04:00 ET) 고가 돌파 매수 / 저가 돌파 매도. 손절 반대편, 장 마감(지수 16:00 ET, FX·금 17:00 ET) 청산.
- **비용 판단:** **작음**.

---

## 가장 유망한 3개 (이유)
1. **2번 하루 누적→마지막 30분(헤지 수요)** — 60개 넘는 선물, 1974~2020년, JFE 게재. 원인(옵션 감마 헤지)이 지금도 존재. 지수·FX·금에 모두 같은 규칙 적용 가능. (1번 첫 30분 규칙과 같이 시험)
2. **3번 노이즈 영역 돌파(SPY)** — 2024년까지 표본, 비용 뺀 뒤 연 19.6%·샤프 1.33(저자 주장). 단 작업논문이고 저자 쪽 상업 이해관계 있음 → 엄격한 표본 밖 시험 필요.
3. **10번 FX 픽스 W자** — 2024 Journal of Finance, 21년·9개 통화, "넓고 매우 유의". 주요 통화쌍은 스프레드가 작아 비용 넘을 가능성. 크기 숫자는 원문 확인 필요.

## 사라졌다고 보고된 것 (시험은 하되 기대 낮춤)
- 5번 야간 드리프트(2021년 이후 ≈ 0, 저자 본인), 8번 pre-FOMC(2015년 이후 사라짐 — 반론 있음), 9번 월말·월초(2001년 이후 사라짐 — 2025 논문), 15번 시계열 모멘텀(2009년 이후 약함).
