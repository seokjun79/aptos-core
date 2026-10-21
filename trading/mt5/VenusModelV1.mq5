//+------------------------------------------------------------------+
//| VenusModelV1.mq5                                                 |
//| 규칙 명세: trading/strategy/venus_model_v1.md                    |
//|  모델 A: 모멘텀 지속 (흐름 + BOS + 4시간 범위 위쪽 절반)          |
//|  모델 B: H4 CRT + M15 BOS                                        |
//| 시간은 모두 브로커 서버 시각(IC마켓 = 뉴욕 + 7시간)              |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "1.00"

#include <Trade/Trade.mqh>

enum ENUM_VENUS_MODEL
  {
   MODEL_A_MOMENTUM = 0, // A: 모멘텀 지속
   MODEL_B_CRT      = 1  // B: H4 CRT + M15 BOS
  };

input ENUM_VENUS_MODEL InpModel          = MODEL_A_MOMENTUM; // 모델
input double           InpFlowMinPips    = 5.0;   // A: 최근 1시간 최소 흐름(핍)
input double           InpRR             = 2.0;   // A: 손익비(TP = RR x SL)
input double           InpMinRR_B        = 1.5;   // B: 최소 손익비(미만이면 진입 안 함)
input double           InpRiskPct        = 0.5;   // 거래당 위험(잔고 %)
input double           InpMaxRiskPct     = 1.0;   // 최소 랏 때문에 이 %를 넘으면 진입 안 함
input double           InpDailyLossPct   = 3.0;   // 하루 손실 잠금(%)
input int              InpMaxTradesDay   = 2;     // 하루 최대 진입
input double           InpSLMinPips      = 6.0;   // SL 최소(핍)
input double           InpSLMaxPipsA     = 25.0;  // A: SL 최대(핍, 넘으면 진입 안 함)
input double           InpSLMaxPipsB     = 30.0;  // B: SL 최대(핍, 넘으면 진입 안 함)
input int              InpLondonStartMin = 600;   // 런던 시작(서버 분, 10:00)
input int              InpLondonEndMin   = 780;   // 런던 끝(서버 분, 13:00)
input int              InpNYStartMin     = 900;   // 뉴욕 시작(서버 분, 15:00)
input int              InpNYEndMin       = 1050;  // 뉴욕 끝(서버 분, 17:30)
input int              InpForceExitMin   = 1140;  // 강제 청산(서버 분, 19:00)
input long             InpMagic          = 520311;// 매직 넘버

CTrade   trade;
datetime g_lastBar      = 0;
datetime g_day          = 0;
double   g_dayStartBal  = 0.0;
bool     g_dayLocked    = false;
double   g_pip          = 0.0001;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(_Digits == 3 || _Digits == 5)
      g_pip = _Point * 10.0;
   else
      g_pip = _Point;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(20);
   ResetDay(DayStart(TimeCurrent()));
   PrintFormat("Venus v1 시작: 모델=%s 위험=%.2f%% 잠금=-%.1f%%",
               InpModel == MODEL_A_MOMENTUM ? "A 모멘텀" : "B CRT", InpRiskPct, InpDailyLossPct);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
datetime DayStart(datetime t)
  {
   return t - (t % 86400);
  }

int MinuteOfDay(datetime t)
  {
   return (int)((t % 86400) / 60);
  }

void ResetDay(datetime day)
  {
   g_day         = day;
   g_dayStartBal = AccountInfoDouble(ACCOUNT_BALANCE);
   g_dayLocked   = false;
  }

//+------------------------------------------------------------------+
bool HasPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return true;
     }
   return false;
  }

void CloseAll(string why)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == InpMagic)
        {
         if(trade.PositionClose(ticket))
            PrintFormat("청산(%s): #%I64u", why, ticket);
         else
            PrintFormat("청산 실패(%s): #%I64u 오류 %d", why, ticket, GetLastError());
        }
     }
  }

int EntriesToday()
  {
   if(!HistorySelect(g_day, TimeCurrent() + 60))
      return 0;
   int n = 0;
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d > 0 && HistoryDealGetString(d, DEAL_SYMBOL) == _Symbol &&
         HistoryDealGetInteger(d, DEAL_MAGIC) == InpMagic &&
         HistoryDealGetInteger(d, DEAL_ENTRY) == DEAL_ENTRY_IN)
         n++;
     }
   return n;
  }

bool InEntryWindow(datetime signalClose)
  {
   int m = MinuteOfDay(signalClose);
   return (m >= InpLondonStartMin && m < InpLondonEndMin) ||
          (m >= InpNYStartMin && m < InpNYEndMin);
  }

//+------------------------------------------------------------------+
// 랏 계산: 위험금액 / (SL가격거리 x 1랏당 가격단위 가치). 최소 랏이 위험 한도를 넘으면 0.
double LotsForRisk(double slDistPrice)
  {
   double bal      = AccountInfoDouble(ACCOUNT_BALANCE);
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double vmin     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tickVal <= 0 || tickSize <= 0 || slDistPrice <= 0 || step <= 0)
      return 0.0;
   double lossPerLot = slDistPrice / tickSize * tickVal;
   double lots = MathFloor((bal * InpRiskPct / 100.0) / lossPerLot / step) * step;
   if(lots < vmin)
     {
      double riskAtMin = vmin * lossPerLot / bal * 100.0;
      if(riskAtMin > InpMaxRiskPct)
        {
         PrintFormat("진입 안 함: 최소 랏 %.2f의 위험이 %.2f%% (한도 %.2f%%)", vmin, riskAtMin, InpMaxRiskPct);
         return 0.0;
        }
      lots = vmin;
     }
   return MathMin(lots, vmax);
  }

//+------------------------------------------------------------------+
// 스윙 고점: i-16..i-1 범위에서 high[k] > high[k-1] && high[k] >= high[k+1] 인 가장 최근 k
int LastSwingHigh(const MqlRates &r[], int i)
  {
   for(int k = i - 1; k >= i - 16 && k >= 1; k--)
      if(r[k].high > r[k - 1].high && r[k].high >= r[k + 1].high)
         return k;
   return -1;
  }

int LastSwingLow(const MqlRates &r[], int i)
  {
   for(int k = i - 1; k >= i - 16 && k >= 1; k--)
      if(r[k].low < r[k - 1].low && r[k].low <= r[k + 1].low)
         return k;
   return -1;
  }

bool BosLong(const MqlRates &r[], int i)
  {
   int k = LastSwingHigh(r, i);
   return k >= 0 && r[i].close > r[k].high;
  }

bool BosShort(const MqlRates &r[], int i)
  {
   int k = LastSwingLow(r, i);
   return k >= 0 && r[i].close < r[k].low;
  }

//+------------------------------------------------------------------+
// 모델 A: dir = +1 롱, -1 숏, 0 신호 없음. sl/tp는 가격.
int SignalA(const MqlRates &r[], int i, double &sl, double &tp)
  {
   double hi = r[i].high, lo = r[i].low;
   for(int k = i - 15; k < i; k++)
     {
      hi = MathMax(hi, r[k].high);
      lo = MathMin(lo, r[k].low);
     }
   if(hi <= lo)
      return 0;
   double pos  = (r[i].close - lo) / (hi - lo);
   double flow = (r[i].close - r[i - 4].close) / g_pip;

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(flow >= InpFlowMinPips && BosLong(r, i) && pos >= 0.5)
     {
      double low4 = MathMin(MathMin(r[i].low, r[i - 1].low), MathMin(r[i - 2].low, r[i - 3].low));
      double dist = ask - (low4 - g_pip);
      if(dist < InpSLMinPips * g_pip)
         dist = InpSLMinPips * g_pip;
      if(dist > InpSLMaxPipsA * g_pip)
        {
         PrintFormat("A 롱 신호 무시: SL %.1f핍 > %.1f", dist / g_pip, InpSLMaxPipsA);
         return 0;
        }
      sl = ask - dist;
      tp = ask + InpRR * dist;
      return 1;
     }
   if(-flow >= InpFlowMinPips && BosShort(r, i) && (1.0 - pos) >= 0.5)
     {
      double high4 = MathMax(MathMax(r[i].high, r[i - 1].high), MathMax(r[i - 2].high, r[i - 3].high));
      double dist = (high4 + g_pip) - bid;
      if(dist < InpSLMinPips * g_pip)
         dist = InpSLMinPips * g_pip;
      if(dist > InpSLMaxPipsA * g_pip)
        {
         PrintFormat("A 숏 신호 무시: SL %.1f핍 > %.1f", dist / g_pip, InpSLMaxPipsA);
         return 0;
        }
      sl = bid + dist;
      tp = bid - InpRR * dist;
      return -1;
     }
   return 0;
  }

//+------------------------------------------------------------------+
// 모델 B: 마감된 H4 두 개(C1, C2)로 CRT 셋업, 현재 H4(C3) 안에서 M15 BOS로 진입.
int SignalB(const MqlRates &r[], int i, double &sl, double &tp)
  {
   MqlRates h4[];
   ArraySetAsSeries(h4, false);
   if(CopyRates(_Symbol, PERIOD_H4, 1, 2, h4) != 2)
      return 0;
   datetime c3Open = iTime(_Symbol, PERIOD_H4, 0);
   if(r[i].time < c3Open)
      return 0; // 신호 봉이 아직 C2에 속함
   MqlRates c1 = h4[0], c2 = h4[1];

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   bool longSetup  = c2.low < c1.low && c2.close > c1.low && c2.close < c1.high;
   bool shortSetup = c2.high > c1.high && c2.close > c1.low && c2.close < c1.high;

   if(longSetup && BosLong(r, i))
     {
      double dist = ask - (c2.low - g_pip);
      if(dist < InpSLMinPips * g_pip)
         dist = InpSLMinPips * g_pip;
      if(dist > InpSLMaxPipsB * g_pip)
         return 0;
      double reward = c1.high - ask;
      if(reward / dist < InpMinRR_B)
         return 0;
      sl = ask - dist;
      tp = c1.high;
      return 1;
     }
   if(shortSetup && BosShort(r, i))
     {
      double dist = (c2.high + g_pip) - bid;
      if(dist < InpSLMinPips * g_pip)
         dist = InpSLMinPips * g_pip;
      if(dist > InpSLMaxPipsB * g_pip)
         return 0;
      double reward = bid - c1.low;
      if(reward / dist < InpMinRR_B)
         return 0;
      sl = bid + dist;
      tp = c1.low;
      return -1;
     }
   return 0;
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   datetime now = TimeCurrent();
   datetime day = DayStart(now);
   if(day != g_day)
      ResetDay(day);

   // 1) 하루 손실 잠금 (실현 + 평가)
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!g_dayLocked && equity <= g_dayStartBal * (1.0 - InpDailyLossPct / 100.0))
     {
      g_dayLocked = true;
      PrintFormat("하루 손실 잠금: 시작 %.2f → 현재 %.2f", g_dayStartBal, equity);
      CloseAll("하루 손실 잠금");
     }

   // 2) 강제 청산 시각
   if(MinuteOfDay(now) >= InpForceExitMin && HasPosition())
      CloseAll("강제 청산 시각");

   // 3) 새 M15 봉에서만 신호 판단
   datetime barTime = iTime(_Symbol, PERIOD_M15, 0);
   if(barTime == g_lastBar)
      return;
   g_lastBar = barTime;

   if(g_dayLocked || HasPosition() || EntriesToday() >= InpMaxTradesDay)
      return;

   datetime signalClose = barTime; // 직전 봉(신호 봉)의 마감 = 현재 봉 시작
   if(!InEntryWindow(signalClose))
      return;

   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, PERIOD_M15, 1, 40, r);
   if(n < 40)
      return;
   int i = n - 1; // 마지막으로 마감된 봉

   double sl = 0, tp = 0;
   int dir = (InpModel == MODEL_A_MOMENTUM) ? SignalA(r, i, sl, tp) : SignalB(r, i, sl, tp);
   if(dir == 0)
      return;

   double price = (dir > 0) ? SymbolInfoDouble(_Symbol, SYMBOL_ASK) : SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double lots  = LotsForRisk(MathAbs(price - sl));
   if(lots <= 0)
      return;

   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);
   bool ok = (dir > 0) ? trade.Buy(lots, _Symbol, 0.0, sl, tp, "Venus v1")
                       : trade.Sell(lots, _Symbol, 0.0, sl, tp, "Venus v1");
   PrintFormat("%s %s %.2f랏 SL %.5f TP %.5f (SL %.1f핍) → %s",
               InpModel == MODEL_A_MOMENTUM ? "A" : "B", dir > 0 ? "매수" : "매도", lots, sl, tp,
               MathAbs(price - sl) / g_pip, ok ? "체결" : "실패 " + IntegerToString(trade.ResultRetcode()));
  }
//+------------------------------------------------------------------+
