//+------------------------------------------------------------------+
//|  Venus Gold Night EA (MT5)                                        |
//|  근거: 금은 밤(아시아 시간)에 오르고 낮에 내린다                  |
//|        (Blose·Gondhalekar·Kort, J. Econ. Finance 2018)            |
//|  우리 데이터(2019~2026 H1): 밤 18→03시 +$2,556/oz, 낮 −$379/oz     |
//|  규칙: 뉴욕 18시(재개장) 매수 → 뉴욕 03시(런던 오픈 전) 청산      |
//|        비상 손절만 두고 이익 목표 없음. 하룻밤 1회.               |
//|  명세·결과: trading/research/README.md                           |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "1.00"
#property description "금 야간 매수: 뉴욕 18시 매수, 뉴욕 03시 청산. 실제 틱 테스트로 재개장 스프레드 비용 확인용."
#include <Trade\Trade.mqh>

input group "=== 시간 (뉴욕 시각) ==="
input int    InpServerMinusNY = 7;      // 서버시간 - 뉴욕시간 (IC마켓 = 7)
input int    InpOpenHourNY    = 18;     // 매수 시각 (뉴욕)
input int    InpEntryDelayMin = 0;      // 재개장 후 기다릴 분 (스프레드 안정)
input int    InpCloseHourNY   = 3;      // 청산 시각 (뉴욕, 다음날)
input int    InpMaxSpreadPts  = 60;     // 이보다 스프레드가 크면 진입 미룸 (포인트, 60 = $0.60)
input group "=== 위험 ==="
input double InpStopPct       = 2.0;    // 비상 손절 (가격의 %)
input double InpRiskPct       = 1.0;    // 비상 손절까지 위험 (잔고 %)
input double InpMaxRiskPct    = 2.0;    // 이 %를 넘으면 진입 안 함
input double InpMaxLots       = 0.01;   // 최대 랏 (안전장치)
input long   InpMagic         = 20261103;
input bool   InpPush          = true;

CTrade trade;
int    lastCycle = -1;   // 진입한 밤 (뉴욕 날짜 키)

void Notify(string s)
  {
   Print(s);
   if(InpPush && !MQLInfoInteger(MQL_TESTER))
      SendNotification(s);
  }

void NyTime(datetime t, MqlDateTime &d)
  {
   TimeToStruct((datetime)((long)t - InpServerMinusNY * 3600), d);
  }

ulong MyPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk > 0 && PositionGetString(POSITION_SYMBOL) == _Symbol && PositionGetInteger(POSITION_MAGIC) == InpMagic)
         return tk;
     }
   return 0;
  }

double CalcLots(double riskPrice)
  {
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(tv <= 0 || ts <= 0 || riskPrice <= 0 || bal <= 0 || step <= 0) return 0.0;
   double lossPerLot = riskPrice / ts * tv;
   double lots = MathFloor(bal * InpRiskPct / 100.0 / lossPerLot / step + 1e-9) * step;
   lots = MathMin(lots, MathMin(mx, InpMaxLots));
   if(lots < mn) lots = mn;
   double riskPct = lots * lossPerLot / bal * 100.0;
   if(riskPct > InpMaxRiskPct)
     {
      PrintFormat("[GoldNight] 진입 안 함: %.2f랏 비상손절 위험 %.1f%% > 한도 %.1f%%", lots, riskPct, InpMaxRiskPct);
      return 0.0;
     }
   return NormalizeDouble(lots, 2);
  }

int OnInit()
  {
   trade.SetExpertMagicNumber(InpMagic);
   trade.SetDeviationInPoints(50);
   trade.SetTypeFillingBySymbol(_Symbol);
   PrintFormat("Venus Gold Night 시작: %s 뉴욕 %02d:%02d 매수 → %02d:00 청산", _Symbol, InpOpenHourNY, InpEntryDelayMin, InpCloseHourNY);
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   datetime now = TimeCurrent();
   MqlDateTime d;
   NyTime(now, d);
   int cycle = d.year * 10000 + d.mon * 100 + d.day;

   // 1) 청산: 뉴욕 청산 시각이 되었거나, 너무 오래 들고 있으면
   ulong tk = MyPosition();
   if(tk > 0 && PositionSelectByTicket(tk))
     {
      long held = (long)now - (long)PositionGetInteger(POSITION_TIME);
      bool timeUp = (d.hour >= InpCloseHourNY && d.hour < InpOpenHourNY) || held > 14 * 3600;
      double pr = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      if(timeUp && trade.PositionClose(tk))
         Notify(StringFormat("[Venus Gold] %s 청산 (손익 약 %+.2f)", _Symbol, pr));
      return;
     }

   // 2) 진입: 뉴욕 매수 시각 대, 그날 밤 아직 안 샀고, 스프레드가 정상일 때
   if(d.hour != InpOpenHourNY || d.min < InpEntryDelayMin || cycle == lastCycle)
      return;
   if((int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
      return;   // 재개장 직후 스프레드가 넓으면 다음 틱에 다시 확인
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double risk = ask * InpStopPct / 100.0;
   double lots = CalcLots(risk);
   lastCycle = cycle;   // 랏이 0이어도 그날 밤은 한 번만 판단
   if(lots <= 0)
      return;
   double sl = NormalizeDouble(ask - risk, _Digits);
   bool ok = trade.Buy(lots, _Symbol, 0, sl, 0, "GoldNight");
   Notify(StringFormat("[Venus Gold] %s 야간 매수 %.2f랏 @ %.2f → %s", _Symbol, lots, ask, ok ? "체결" : trade.ResultRetcodeDescription()));
  }
//+------------------------------------------------------------------+
