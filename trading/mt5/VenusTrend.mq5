//+------------------------------------------------------------------+
//|  Venus Trend EA (MT5) — 일봉 추세추종, 여러 종목 바스켓           |
//|  규칙 (Andreas Clenow식, 숫자는 공개 규칙 그대로):               |
//|   진입: 일봉 종가가 50일 최고 종가 이상 + EMA50 > EMA100 → 매수   |
//|         일봉 종가가 50일 최저 종가 이하 + EMA50 < EMA100 → 매도   |
//|   청산: 진입 후 최고(최저) 종가에서 3 × ATR(100) 추적 손절        |
//|   크기: 1 ATR 움직임 = 잔고의 0.2% (손절까지 약 0.6% 위험)        |
//|   이익 목표 없음, 종목당 포지션 1개                               |
//|  근거·명세: trading/strategy/venus_trend_v1.md                   |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "1.00"
#property description "일봉 추세추종 (50일 돌파 + EMA50/100 필터, 3ATR 추적 손절). 한 차트에 붙이면 여러 종목을 같이 거래."
#include <Trade\Trade.mqh>

input group "=== 종목 ==="
input string InpSymbols      = "EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD,USDCHF,XAUUSD"; // 거래할 종목 (쉼표로 구분)
input string InpSuffix       = "";        // 브로커 종목 접미사 (예: .a)
input group "=== 규칙 (공개 규칙 기본값) ==="
input int    InpBreakoutDays = 50;        // 돌파 기간 (일)
input int    InpFastEMA      = 50;        // 빠른 EMA
input int    InpSlowEMA      = 100;       // 느린 EMA
input int    InpATRPeriod    = 100;       // ATR 기간
input double InpStopATR      = 3.0;       // 추적 손절 ATR 배수
input group "=== 위험 ==="
input double InpRiskPerATR   = 0.2;       // 1 ATR 움직임 = 잔고의 몇 % (0.2 → 손절까지 약 0.6%)
input double InpMaxRiskPct   = 2.0;       // 손절까지 손실이 잔고의 이 %를 넘으면 진입 안 함
input double InpMaxLots      = 0.01;      // 종목당 최대 랏 (안전장치)
input long   InpMagic        = 20261101;  // 매직 넘버
input bool   InpPush         = true;      // 휴대폰 푸시 알림

struct Sym
  {
   string   name;
   int      hFast, hSlow, hATR;
   datetime lastBar;
  };

CTrade trade;
Sym    syms[];

void Notify(string s)
  {
   Print(s);
   if(InpPush && !MQLInfoInteger(MQL_TESTER))
      SendNotification(s);
  }

double Buf(int h, int shift)
  {
   double v[1];
   if(CopyBuffer(h, 0, shift, 1, v) != 1)
      return EMPTY_VALUE;
   return v[0];
  }

// 이 EA의 해당 종목 포지션 티켓 (없으면 0)
ulong PositionOf(string s)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk > 0 && PositionGetString(POSITION_SYMBOL) == s && PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return tk;
     }
   return 0;
  }

// 1 ATR = 잔고의 InpRiskPerATR% 가 되도록 랏 계산. 0이면 진입 안 함
double CalcLots(string s, double atr)
  {
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double tv   = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(s, SYMBOL_VOLUME_MAX);
   if(tv <= 0 || ts <= 0 || atr <= 0 || bal <= 0 || step <= 0)
      return 0.0;
   double perLotPerATR = atr / ts * tv;
   double lots = MathFloor(bal * InpRiskPerATR / 100.0 / perLotPerATR / step + 1e-9) * step;
   lots = MathMin(lots, MathMin(mx, InpMaxLots));
   if(lots < mn) lots = mn;
   double riskPct = lots * perLotPerATR * InpStopATR / bal * 100.0;
   if(riskPct > InpMaxRiskPct)
     {
      PrintFormat("[Trend] %s 진입 안 함: %.2f랏 손절 위험 %.1f%% > 한도 %.1f%%", s, lots, riskPct, InpMaxRiskPct);
      return 0.0;
     }
   return NormalizeDouble(lots, 2);
  }

// 진입 후 최고(롱)/최저(숏) 일봉 종가
double ExtremeCloseSince(string s, datetime opened, int dir)
  {
   int n = iBarShift(s, PERIOD_D1, opened, false);
   if(n < 1) n = 1;
   double ext = iClose(s, PERIOD_D1, 1);
   for(int j = 1; j <= n; j++)
     {
      double c = iClose(s, PERIOD_D1, j);
      ext = (dir == 1) ? MathMax(ext, c) : MathMin(ext, c);
     }
   return ext;
  }

void ProcessSymbol(Sym &x)
  {
   string s = x.name;
   double atr = Buf(x.hATR, 1), fast = Buf(x.hFast, 1), slow = Buf(x.hSlow, 1);
   if(atr == EMPTY_VALUE || fast == EMPTY_VALUE || slow == EMPTY_VALUE || atr <= 0)
      return;
   int digits = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
   double c1 = iClose(s, PERIOD_D1, 1);

   // 1) 보유 중이면 추적 손절만 올림(내림)
   ulong tk = PositionOf(s);
   if(tk > 0 && PositionSelectByTicket(tk))
     {
      int dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      double ext = ExtremeCloseSince(s, (datetime)PositionGetInteger(POSITION_TIME), dir);
      double ns = NormalizeDouble(ext - dir * InpStopATR * atr, digits);
      double cur = PositionGetDouble(POSITION_SL);
      bool better = (cur == 0) || (dir == 1 ? ns > cur : ns < cur);
      double px = (dir == 1) ? SymbolInfoDouble(s, SYMBOL_BID) : SymbolInfoDouble(s, SYMBOL_ASK);
      double minDist = (SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL) + 2) * SymbolInfoDouble(s, SYMBOL_POINT);
      if(dir * (px - ns) <= minDist)
        {
         // 이미 손절선을 넘었으면 바로 청산
         if(trade.PositionClose(tk))
            Notify(StringFormat("[Venus Trend] %s 추적 손절 도달로 청산", s));
         return;
        }
      if(better && trade.PositionModify(tk, ns, 0))
         PrintFormat("[Trend] %s 추적 손절 %s", s, DoubleToString(ns, digits));
      return;
     }

   // 2) 진입: 50일 최고(최저) 종가 돌파 + EMA 방향
   double hi = c1, lo = c1;
   for(int j = 1; j <= InpBreakoutDays; j++)
     {
      double c = iClose(s, PERIOD_D1, j);
      hi = MathMax(hi, c);
      lo = MathMin(lo, c);
     }
   int dir = 0;
   if(fast > slow && c1 >= hi) dir = 1;
   if(fast < slow && c1 <= lo) dir = -1;
   if(dir == 0)
      return;

   double lots = CalcLots(s, atr);
   if(lots <= 0)
      return;
   double e = (dir == 1) ? SymbolInfoDouble(s, SYMBOL_ASK) : SymbolInfoDouble(s, SYMBOL_BID);
   double sl = NormalizeDouble(c1 - dir * InpStopATR * atr, digits);
   if(dir * (e - sl) <= 0)
      return;
   string cmt = StringFormat("VT %s", dir == 1 ? "L" : "S");
   bool ok = (dir == 1) ? trade.Buy(lots, s, 0, sl, 0, cmt) : trade.Sell(lots, s, 0, sl, 0, cmt);
   Notify(StringFormat("[Venus Trend] %s %s %.2f랏 손절 %s → %s", s, dir == 1 ? "매수" : "매도", lots,
                       DoubleToString(sl, digits), ok ? "체결" : trade.ResultRetcodeDescription()));
  }

int OnInit()
  {
   string parts[];
   int n = StringSplit(InpSymbols, ',', parts);
   ArrayResize(syms, 0);
   for(int i = 0; i < n; i++)
     {
      string s = parts[i];
      StringTrimLeft(s);
      StringTrimRight(s);
      if(s == "") continue;
      s += InpSuffix;
      if(!SymbolSelect(s, true))
        {
         PrintFormat("[Trend] 종목 %s 를 찾을 수 없어 건너뜀", s);
         continue;
        }
      Sym x;
      x.name    = s;
      x.hFast   = iMA(s, PERIOD_D1, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
      x.hSlow   = iMA(s, PERIOD_D1, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
      x.hATR    = iATR(s, PERIOD_D1, InpATRPeriod);
      x.lastBar = 0;
      if(x.hFast == INVALID_HANDLE || x.hSlow == INVALID_HANDLE || x.hATR == INVALID_HANDLE)
        {
         PrintFormat("[Trend] %s 지표 생성 실패", s);
         continue;
        }
      int k = ArraySize(syms);
      ArrayResize(syms, k + 1);
      syms[k] = x;
     }
   if(ArraySize(syms) == 0)
      return INIT_FAILED;
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(30);
   PrintFormat("Venus Trend 시작: 종목 %d개, 1ATR=%.2f%%, 손절 %.1fATR", ArraySize(syms), InpRiskPerATR, InpStopATR);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   for(int i = 0; i < ArraySize(syms); i++)
     {
      IndicatorRelease(syms[i].hFast);
      IndicatorRelease(syms[i].hSlow);
      IndicatorRelease(syms[i].hATR);
     }
  }

void OnTick()
  {
   // 종목마다 새 일봉이 열리면 한 번 처리
   for(int i = 0; i < ArraySize(syms); i++)
     {
      datetime b = iTime(syms[i].name, PERIOD_D1, 0);
      if(b == 0 || b == syms[i].lastBar)
         continue;
      // 틱이 들어온 종목만 처리 (가격이 유효해야 주문 가능)
      if(SymbolInfoDouble(syms[i].name, SYMBOL_BID) <= 0)
         continue;
      syms[i].lastBar = b;
      ProcessSymbol(syms[i]);
     }
  }
//+------------------------------------------------------------------+
