//+------------------------------------------------------------------+
//|  Venus SMC EA (MT5)                                              |
//|  ① H4 시장 구조로 방향(바이어스)                                  |
//|  ② H1 BOS + FVG(변위)를 만든 움직임의 오더블록, 디스카운트/프리미엄|
//|  ③ 가격이 OB에 들어오면 M1 CHoCH로 진입                          |
//|  ④ 손절: OB 진입 후 최저(최고)점 너머, 목표: H1 외부 유동성(고/저점)|
//|  규칙 명세: trading/strategy/venus_smc_v1.md                     |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "1.00"
#property description "SMC: H4 바이어스 + H1 오더블록 + M1 CHoCH 진입. 1회 위험 % 랏, 위험 한도 초과 시 진입 안 함."
#include <Trade\Trade.mqh>

input group "=== 주문 / 위험 ==="
input bool   InpUseRiskLot     = true;     // true: 잔고 % 위험으로 랏 계산
input double InpLots           = 0.01;     // 고정 랏 (위 옵션 false일 때)
input double InpRiskPct        = 1.0;      // 1회 위험 %
input double InpMaxLots        = 0.01;     // 최대 랏 (안전장치)
input double InpMaxRiskPct     = 2.0;      // 1회 손실이 잔고의 이 %를 넘으면 진입 안 함
input long   InpMagic          = 20261022; // 매직 넘버
input int    InpMaxSpreadPts   = 20;       // 최대 스프레드(포인트)
input group "=== H4 바이어스 ==="
input int    InpH4SwingLen     = 5;        // H4 스윙 길이
input group "=== H1 오더블록 ==="
input int    InpH1SwingLen     = 3;        // H1 스윙 길이
input int    InpH1Lookback     = 60;       // 스윙 고점/저점 찾는 범위 (H1 봉)
input bool   InpRequireFvg     = true;     // BOS 움직임에 FVG(변위) 필수
input bool   InpRequireDiscount = true;    // 롱은 디스카운트, 숏은 프리미엄 OB만
input int    InpPoiMaxHours    = 120;      // OB 유효 시간 (시간)
input group "=== M1 진입 ==="
input int    InpM1SwingLen     = 2;        // M1 CHoCH 스윙 길이
input int    InpM1Lookback     = 60;       // CHoCH 기준 스윙 찾는 범위 (M1 봉)
input double InpSLBufferPips   = 1.0;      // 손절 버퍼 (핍)
input double InpMinSLPips      = 3.0;      // 최소 손절 (핍)
input double InpMaxSLPips      = 30.0;     // 최대 손절 (핍, 넘으면 진입 안 함)
input double InpMinRR          = 2.0;      // 최소 손익비
input double InpMaxRR          = 6.0;      // 최대 손익비 (넘으면 TP를 이 값으로)
input group "=== 시간 / 하루 한도 (뉴욕 시각) ==="
input int    InpServerMinusNY  = 7;        // 서버시간 - 뉴욕시간 (IC마켓 = 7)
input int    InpEntryStartNY   = 2;        // 진입 시작 (런던 오픈)
input int    InpEntryEndNY     = 11;       // 진입 끝 (뉴욕 오전)
input int    InpMaxTradesDay   = 2;        // 하루 최대 진입
input int    InpMaxLossesDay   = 2;        // 하루 손실 거래 한도
input int    InpMaxHoldHours   = 72;       // 최대 보유 시간
input bool   InpPush           = true;     // 휴대폰 푸시 알림

struct Poi
  {
   bool     active;
   int      dir;        // +1 롱(수요 OB), -1 숏(공급 OB)
   double   obHigh, obLow;
   double   target;     // 외부 유동성 (H1 레그 끝 고점/저점)
   datetime created;
   bool     touched;
   datetime touchT;
   double   ext;        // OB 진입 후 최저(롱)/최고(숏)
  };

CTrade   trade;
Poi      poi[2];        // [0] 롱, [1] 숏
datetime lastM1 = 0, lastH1 = 0;
double   g_pip = 0.0001;

//--- 공통 도우미 ----------------------------------------------------
int NyHour(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t - InpServerMinusNY * 3600, d);
   return d.hour;
  }
datetime NyDayStart(datetime t)   // 뉴욕 17:00 기준 거래일 시작 (서버 시각)
  {
   long ny = (long)t - InpServerMinusNY * 3600;
   long mid = ny - (ny % 86400);
   long s = mid + 17 * 3600;
   if(ny < s) s -= 86400;
   return (datetime)(s + InpServerMinusNY * 3600);
  }
void Notify(string s)
  {
   Print(s);
   if(InpPush && !MQLInfoInteger(MQL_TESTER))
      SendNotification(s);
  }

bool IsSwingHigh(ENUM_TIMEFRAMES tf, int p, int len)
  {
   double hp = iHigh(_Symbol, tf, p);
   for(int j = 1; j <= len; j++)
      if(iHigh(_Symbol, tf, p + j) > hp || iHigh(_Symbol, tf, p - j) >= hp)
         return false;
   return true;
  }
bool IsSwingLow(ENUM_TIMEFRAMES tf, int p, int len)
  {
   double lp = iLow(_Symbol, tf, p);
   for(int j = 1; j <= len; j++)
      if(iLow(_Symbol, tf, p + j) < lp || iLow(_Symbol, tf, p - j) <= lp)
         return false;
   return true;
  }
// from 이후(오래된 쪽)로 가장 가까운 확정 스윙 (없으면 -1). 확정되려면 p >= from + len 이상이어야 함
int LastSwing(ENUM_TIMEFRAMES tf, int from, int len, int lookback, bool high)
  {
   int bars = iBars(_Symbol, tf);
   for(int p = from + len; p <= from + lookback && p + len < bars; p++)
      if(high ? IsSwingHigh(tf, p, len) : IsSwingLow(tf, p, len))
         return p;
   return -1;
  }

//--- ① H4 바이어스: 마지막 구조 돌파 방향 --------------------------
int BiasH4()
  {
   int len = InpH4SwingLen;
   int bars = iBars(_Symbol, PERIOD_H4);
   int start = MathMin(300, bars - 2 * len - 2);
   int tr = 0;
   double sh = 0, sl = 0;
   bool hsh = false, hsl = false;
   for(int j = start; j >= 1; j--)
     {
      int p = j + len;
      if(IsSwingHigh(PERIOD_H4, p, len)) { sh = iHigh(_Symbol, PERIOD_H4, p); hsh = true; }
      if(IsSwingLow(PERIOD_H4, p, len))  { sl = iLow(_Symbol, PERIOD_H4, p);  hsl = true; }
      double c = iClose(_Symbol, PERIOD_H4, j);
      if(hsh && c > sh) { tr = 1;  hsh = false; }
      if(hsl && c < sl) { tr = -1; hsl = false; }
     }
   return tr;
  }

// H4 봉이 바뀔 때만 다시 계산 (테스터 속도)
int GetBias()
  {
   static datetime lastCalc = 0;
   static int b = 0;
   datetime h4 = iTime(_Symbol, PERIOD_H4, 0);
   if(h4 != lastCalc) { lastCalc = h4; b = BiasH4(); }
   return b;
  }

//--- ② 새 H1 봉: BOS가 났으면 오더블록 등록 -------------------------
void OnNewH1()
  {
   int len = InpH1SwingLen;
   double c1 = iClose(_Symbol, PERIOD_H1, 1), c2 = iClose(_Symbol, PERIOD_H1, 2);

   // 기존 POI 무효화: 종가가 OB를 반대로 뚫거나 유효 시간이 지나면 삭제
   for(int k = 0; k < 2; k++)
     {
      if(!poi[k].active) continue;
      bool broken = (poi[k].dir == 1) ? (c1 < poi[k].obLow) : (c1 > poi[k].obHigh);
      bool old = (TimeCurrent() - poi[k].created) > InpPoiMaxHours * 3600;
      if(broken || old) poi[k].active = false;
     }

   for(int dir = 1; dir >= -1; dir -= 2)
     {
      // 직전 확정 스윙 고점(롱)/저점(숏)을 종가로 처음 돌파했는가
      int sp = LastSwing(PERIOD_H1, 2, len, InpH1Lookback, dir == 1);
      if(sp < 0) continue;
      double lvl = (dir == 1) ? iHigh(_Symbol, PERIOD_H1, sp) : iLow(_Symbol, PERIOD_H1, sp);
      bool bos = (dir == 1) ? (c1 > lvl && c2 <= lvl) : (c1 < lvl && c2 >= lvl);
      if(!bos) continue;

      // 레그 시작: 스윙 이후 ~ 돌파봉 사이 최저점(롱)/최고점(숏)
      int legStart = 1;
      double ext = (dir == 1) ? iLow(_Symbol, PERIOD_H1, 1) : iHigh(_Symbol, PERIOD_H1, 1);
      for(int j = 1; j <= sp; j++)
        {
         double v = (dir == 1) ? iLow(_Symbol, PERIOD_H1, j) : iHigh(_Symbol, PERIOD_H1, j);
         if((dir == 1 && v < ext) || (dir == -1 && v > ext)) { ext = v; legStart = j; }
        }
      if(legStart <= 1) continue;

      // 변위: 레그 안에 같은 방향 FVG
      bool fvg = false;
      for(int j = 1; j + 2 <= legStart && !fvg; j++)
         fvg = (dir == 1) ? (iLow(_Symbol, PERIOD_H1, j) > iHigh(_Symbol, PERIOD_H1, j + 2))
                          : (iHigh(_Symbol, PERIOD_H1, j) < iLow(_Symbol, PERIOD_H1, j + 2));
      if(InpRequireFvg && !fvg) continue;

      // 오더블록: 레그 시작 근처의 마지막 반대색 캔들 (롱=음봉, 숏=양봉)
      int ob = legStart;
      for(int j = legStart; j <= legStart + 3; j++)
        {
         double o = iOpen(_Symbol, PERIOD_H1, j), c = iClose(_Symbol, PERIOD_H1, j);
         if((dir == 1 && c < o) || (dir == -1 && c > o)) { ob = j; break; }
        }
      double obH = iHigh(_Symbol, PERIOD_H1, ob), obL = iLow(_Symbol, PERIOD_H1, ob);

      // 레그 끝(외부 유동성) = 돌파 이후 최고점(롱)/최저점(숏)
      double tgt = (dir == 1) ? iHigh(_Symbol, PERIOD_H1, 1) : iLow(_Symbol, PERIOD_H1, 1);
      for(int j = 1; j < legStart; j++)
         tgt = (dir == 1) ? MathMax(tgt, iHigh(_Symbol, PERIOD_H1, j)) : MathMin(tgt, iLow(_Symbol, PERIOD_H1, j));

      // 디스카운트(롱: OB 위쪽이 레그 50% 아래) / 프리미엄(숏)
      double mid = (ext + tgt) / 2.0;
      if(InpRequireDiscount && ((dir == 1 && obH > mid) || (dir == -1 && obL < mid))) continue;

      int k = (dir == 1) ? 0 : 1;
      poi[k].active = true;  poi[k].dir = dir;
      poi[k].obHigh = obH;   poi[k].obLow = obL;  poi[k].target = tgt;
      poi[k].created = iTime(_Symbol, PERIOD_H1, 1);
      poi[k].touched = false; poi[k].touchT = 0;  poi[k].ext = 0;
      PrintFormat("[SMC] %s OB 등록 %.5f~%.5f 목표 %.5f", dir == 1 ? "수요" : "공급", obL, obH, tgt);
     }
  }

//--- 계좌 / 주문 도우미 ---------------------------------------------
bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk > 0 && PositionGetInteger(POSITION_MAGIC) == InpMagic && PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
     }
   return false;
  }

void ManagePositions()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME) > InpMaxHoldHours * 3600)
        {
         if(trade.PositionClose(tk))
            Notify(StringFormat("[Venus SMC] %s 최대 보유 시간 초과로 청산", _Symbol));
        }
     }
  }

// 오늘(뉴욕 거래일) 진입 수, 손실 수
void TodayStats(int &entries, int &losses)
  {
   entries = 0; losses = 0;
   if(!HistorySelect(NyDayStart(TimeCurrent()), TimeCurrent() + 60))
      return;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0 || HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic || HistoryDealGetString(tk, DEAL_SYMBOL) != _Symbol)
         continue;
      long en = HistoryDealGetInteger(tk, DEAL_ENTRY);
      if(en == DEAL_ENTRY_IN)
         entries++;
      else if(en == DEAL_ENTRY_OUT || en == DEAL_ENTRY_OUT_BY)
        {
         double pr = HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_COMMISSION) + HistoryDealGetDouble(tk, DEAL_SWAP);
         if(pr < 0) losses++;
        }
     }
  }

// 0이면 진입 안 함 (위험 한도 초과)
double CalcLots(double risk)
  {
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   if(tv <= 0 || ts <= 0 || risk <= 0 || bal <= 0) return 0.0;
   double lossPerLot = risk / ts * tv;
   double lots = InpUseRiskLot ? bal * InpRiskPct / 100.0 / lossPerLot : InpLots;
   lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMin(lots, MathMin(mx, InpMaxLots));
   if(lots < mn) lots = mn;
   double riskPct = lots * lossPerLot / bal * 100.0;
   if(riskPct > InpMaxRiskPct)
     {
      PrintFormat("[SMC] 진입 안 함: %.2f랏 손실 위험 %.1f%% > 한도 %.1f%%", lots, riskPct, InpMaxRiskPct);
      return 0.0;
     }
   return NormalizeDouble(lots, 2);
  }

//--- ③ 새 M1 봉: OB 진입 확인 → CHoCH면 진입 -----------------------
void OnNewM1()
  {
   double h1 = iHigh(_Symbol, PERIOD_M1, 1), l1 = iLow(_Symbol, PERIOD_M1, 1);
   double c1 = iClose(_Symbol, PERIOD_M1, 1), c2 = iClose(_Symbol, PERIOD_M1, 2);
   datetime t1 = iTime(_Symbol, PERIOD_M1, 1);

   // OB 터치·극값 갱신, 진입 전 OB를 종가로 뚫으면 무효
   for(int k = 0; k < 2; k++)
     {
      if(!poi[k].active) continue;
      int d = poi[k].dir;
      if((d == 1 && c1 < poi[k].obLow) || (d == -1 && c1 > poi[k].obHigh)) { poi[k].active = false; continue; }
      bool inZone = (d == 1) ? (l1 <= poi[k].obHigh) : (h1 >= poi[k].obLow);
      if(inZone && !poi[k].touched) { poi[k].touched = true; poi[k].touchT = t1; poi[k].ext = (d == 1) ? l1 : h1; }
      if(poi[k].touched) poi[k].ext = (d == 1) ? MathMin(poi[k].ext, l1) : MathMax(poi[k].ext, h1);
     }

   if(!((poi[0].active && poi[0].touched) || (poi[1].active && poi[1].touched))) return;
   if(HasPosition()) return;
   int nyh = NyHour(t1 + 60);
   if(nyh < InpEntryStartNY || nyh >= InpEntryEndNY) return;
   int entries, losses;
   TodayStats(entries, losses);
   if(entries >= InpMaxTradesDay || losses >= InpMaxLossesDay) return;
   if((int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts) return;

   int bias = GetBias();
   for(int k = 0; k < 2; k++)
     {
      if(!poi[k].active || !poi[k].touched || poi[k].dir != bias) continue;
      int d = poi[k].dir;
      // M1 CHoCH: OB 진입 이후 생긴 마지막 확정 스윙 고점(롱)/저점(숏)을 종가로 처음 돌파
      int sp = LastSwing(PERIOD_M1, 1, InpM1SwingLen, InpM1Lookback, d == 1);
      if(sp < 0 || iTime(_Symbol, PERIOD_M1, sp) < poi[k].touchT) continue;
      double lvl = (d == 1) ? iHigh(_Symbol, PERIOD_M1, sp) : iLow(_Symbol, PERIOD_M1, sp);
      bool choch = (d == 1) ? (c1 > lvl && c2 <= lvl) : (c1 < lvl && c2 >= lvl);
      if(!choch) continue;

      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK), bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double e = (d == 1) ? ask : bid;
      double stp = poi[k].ext - d * InpSLBufferPips * g_pip;
      double risk = d * (e - stp);
      if(risk <= 0) continue;
      if(risk < InpMinSLPips * g_pip) { risk = InpMinSLPips * g_pip; stp = e - d * risk; }
      if(risk > InpMaxSLPips * g_pip) { PrintFormat("[SMC] 손절 %.1f핍이 너무 넓어 패스", risk / g_pip); poi[k].active = false; continue; }
      double tp = poi[k].target;
      double rr = d * (tp - e) / risk;
      if(rr < InpMinRR) { PrintFormat("[SMC] 손익비 %.1f 부족으로 패스", rr); poi[k].active = false; continue; }
      if(rr > InpMaxRR) { tp = e + d * InpMaxRR * risk; rr = InpMaxRR; }
      double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 2) * _Point;
      if(risk <= minDist) continue;

      double lots = CalcLots(risk);
      poi[k].active = false;   // OB는 한 번만 사용
      if(lots <= 0) return;
      stp = NormalizeDouble(stp, _Digits);
      tp  = NormalizeDouble(tp, _Digits);
      string cmt = StringFormat("SMC %s RR%.1f", d == 1 ? "L" : "S", rr);
      bool ok = (d == 1) ? trade.Buy(lots, _Symbol, 0, stp, tp, cmt) : trade.Sell(lots, _Symbol, 0, stp, tp, cmt);
      Notify(StringFormat("[Venus SMC] %s %s %.2f랏 SL %.1f핍 RR %.1f → %s", _Symbol, d == 1 ? "매수" : "매도",
                          lots, risk / g_pip, rr, ok ? "체결" : trade.ResultRetcodeDescription()));
      return;
     }
  }

//--- 이벤트 ----------------------------------------------------------
int OnInit()
  {
   g_pip = (_Digits == 3 || _Digits == 5) ? _Point * 10 : _Point;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(20);
   trade.SetTypeFillingBySymbol(_Symbol);
   for(int k = 0; k < 2; k++) poi[k].active = false;
   lastM1 = iTime(_Symbol, PERIOD_M1, 0);
   lastH1 = 0;
   PrintFormat("Venus SMC 시작: %s / 위험 %.1f%% / 한도 %.1f%% / 최대 %.2f랏", _Symbol, InpRiskPct, InpMaxRiskPct, InpMaxLots);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   ManagePositions();
   datetime h1 = iTime(_Symbol, PERIOD_H1, 0);
   if(h1 != lastH1) { lastH1 = h1; OnNewH1(); }
   datetime m1 = iTime(_Symbol, PERIOD_M1, 0);
   if(m1 != lastM1) { lastM1 = m1; OnNewM1(); }
   if(MQLInfoInteger(MQL_TESTER)) return;   // 테스터에서는 화면 표시 생략 (속도)
   string s = StringFormat("Venus SMC | H4 방향 %s\n", BiasLabel());
   for(int k = 0; k < 2; k++)
      s += StringFormat("%s OB: %s\n", k == 0 ? "수요" : "공급",
                        poi[k].active ? StringFormat("%.5f~%.5f %s", poi[k].obLow, poi[k].obHigh, poi[k].touched ? "(진입 구역 도달)" : "")
                                      : "-");
   Comment(s);
  }

string BiasLabel()
  {
   int b = GetBias();
   return b == 1 ? "상승" : (b == -1 ? "하락" : "없음");
  }

void OnDeinit(const int reason) { Comment(""); }
//+------------------------------------------------------------------+
