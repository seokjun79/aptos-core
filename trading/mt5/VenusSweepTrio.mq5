//+------------------------------------------------------------------+
//|  Venus Sweep Trio EA (MT5) — Sweep Duo v2.10 + 아시아 스윕      |
//|  모델 1: 런던 스윕 – 아시아 레인지를 런던 킬존에서 스윕          |
//|  모델 2: 뉴욕 스윕 – 런던 레인지를 뉴욕 킬존에서 스윕            |
//|  스윕 → 5분 MSS → FVG 진입, SL/TP 자동, 한 번에 한 포지션       |
//+------------------------------------------------------------------+
//| Trio 1.00: 모델 3 아시아 스윕 추가 (뉴욕 오후 레인지를 도쿄      |
//|   오픈에서 스윕). 모델마다 자기 레인지 시작 시각에 상태 초기화.  |
//| v2.10 변경 (검수 결과 반영, 전략 규칙은 그대로)                  |
//|  1. 랏: 1회 손실이 잔고의 InpMaxRiskPct를 넘으면 진입 안 함      |
//|  2. 포지션 보유 중에도 다른 모델의 스윕 극값·무효 판정 갱신      |
//|  3. 지정가에 만료 시각 지정, 재시작 시 대기 주문 복원,          |
//|     체결 전 TP 먼저 닿으면 취소                                  |
//|  4. 강제 청산: 청산 시각이 지난 포지션은 언제든 청산             |
//|  5. 연속 손실을 여러 날에 걸쳐 집계 (오늘 손실로 한도 도달 시 중단)|
//|  6. FVG는 스윕 이후 봉에서만, 손절 반대편이면 시장가로 대체       |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "3.00"
#property description "아시아 스윕 + 런던 스윕 + 뉴욕 스윕 자동매매 (EURUSD 권장). 랏수 지정, SL/TP 자동, 푸시 알림."
#include <Trade\Trade.mqh>

input group "=== 주문 ==="
input double InpLots          = 0.01;     // 랏수 (고정)
input bool   InpUseRiskLot    = false;    // true: 잔고 % 리스크로 랏 자동 계산
input double InpRiskPct       = 1.0;      // 1회 리스크 % (위 옵션 true일 때만)
input double InpMaxLots       = 0.01;     // 최대 랏 (안전장치)
input double InpMaxRiskPct    = 2.0;      // 1회 손실이 잔고의 이 %를 넘으면 진입 안 함
input bool   InpEnforceMaxRisk = true;    // 위 한도 적용 (고정 랏일 때도)
input long   InpMagic         = 20261015; // 매직 넘버 (런던 = 이 값, 뉴욕 = 이 값 + 1)
input int    InpMaxSpreadPts  = 25;       // 최대 스프레드(포인트), 넘으면 진입 안 함
input group "=== 모델 공통 ==="
input int    InpMinScore      = 5;        // 최소 컨플루언스 점수 (0~6)
input double InpMinRR         = 2.0;      // 최소 손익비
input double InpMaxRR         = 8.0;      // 최대 손익비 (넘으면 TP를 이 값으로)
input double InpBufAtr        = 0.2;      // SL 버퍼 (5분 ATR 배수)
input int    InpLenC          = 2;        // MSS 내부 스윙 길이
input bool   InpFvgLimit      = true;     // true: FVG 지정가 / false: 시장가
input int    InpFvgWaitBars   = 12;       // 지정가 대기 시간 (5분봉 개수)
input int    InpServerMinusNY = 7;        // 서버시간 - 뉴욕시간 (IC마켓 = 7)
input group "=== 모델 1: 런던 스윕 (뉴욕 시각) ==="
input bool   InpUseLondon     = true;     // 런던 스윕 사용
input int    InpL_RangeStart  = 19;       // 레인지 시작 (아시아)
input int    InpL_RangeEnd    = 2;        // 레인지 끝
input int    InpL_KzStart     = 2;        // 스윕 킬존 시작
input int    InpL_KzEnd       = 5;        // 스윕 킬존 끝
input int    InpL_EntryEnd    = 8;        // 진입 마감
input int    InpL_Exit        = 12;       // 남은 포지션 청산 시각
input group "=== 모델 2: 뉴욕 스윕 (뉴욕 시각) ==="
input bool   InpUseNY         = true;     // 뉴욕 스윕 사용
input int    InpN_RangeStart  = 2;        // 레인지 시작 (런던)
input int    InpN_RangeEnd    = 7;        // 레인지 끝
input int    InpN_KzStart     = 7;        // 스윕 킬존 시작
input int    InpN_KzEnd       = 10;       // 스윕 킬존 끝
input int    InpN_EntryEnd    = 11;       // 진입 마감
input int    InpN_Exit        = 15;       // 남은 포지션 청산 시각
input group "=== 모델 3: 아시아 스윕 (뉴욕 시각) ==="
input bool   InpUseAsia       = true;     // 아시아 스윕 사용
input int    InpA_RangeStart  = 12;       // 레인지 시작 (뉴욕 오후)
input int    InpA_RangeEnd    = 17;       // 레인지 끝 (뉴욕 마감)
input int    InpA_KzStart     = 19;       // 스윕 킬존 시작 (도쿄 오픈)
input int    InpA_KzEnd       = 23;       // 스윕 킬존 끝
input int    InpA_EntryEnd    = 0;        // 진입 마감 (0 = 자정)
input int    InpA_Exit        = 2;        // 남은 포지션 청산 시각 (다음날 런던 오픈 전)
input group "=== 리스크 / 알림 ==="
input int    InpMaxDailyLoss  = 2;        // 하루 손실 거래 수 한도
input int    InpMaxConsecLoss = 3;        // 연속 손실 한도 (그날 중단)
input bool   InpOneAtATime    = true;     // 다른 종목에 이 EA 포지션 있으면 진입 안 함
input bool   InpPush          = true;     // 휴대폰 푸시 알림 (MT5 옵션에 MetaQuotes ID 필요)
input bool   InpDrawBoxes     = true;     // 레인지 박스 그리기

struct MState
  {
   bool     hasA;
   double   aH, aL;
   datetime aT0;
   int      swept;
   double   swExt;
   datetime swT;
   bool     swPD;
   bool     done;
   string   msg;
  };

CTrade   trade;
int      atrH = INVALID_HANDLE;
datetime lastBar = 0;
int      cyc[3] = {-1, -1, -1};   // 모델별 레인지 주기 키
double   lastPH = 0, lastPL = 0;
bool     hasPH = false, hasPL = false;
ulong    pendTicket = 0;
datetime pendT = 0;
double   pendStp = 0;
double   pendTp = 0;
int      pendSide = 0;

MState   st[3];
bool     ON[3];
int      RS[3], RE[3], KS[3], KE[3], EE[3], XE[3];
long     MG[3];
string   NM[3] = {"런던", "뉴욕", "아시아"};
color    BC[3] = {clrMediumPurple, clrDarkCyan, clrGoldenrod};

//--- 시간 도우미 -----------------------------------------------------
int NyMin(datetime t)
  {
   MqlDateTime d;
   TimeToStruct(t - InpServerMinusNY * 3600, d);
   return d.hour * 60 + d.min;
  }
int NyDayKey(datetime t)
  {
   datetime ny = t - InpServerMinusNY * 3600;
   MqlDateTime d;
   TimeToStruct(ny, d);
   if(d.hour * 60 + d.min >= 17 * 60)
     {
      ny += 86400;
      TimeToStruct(ny, d);
     }
   return d.year * 10000 + d.mon * 100 + d.day;
  }
datetime DayStartServer(datetime t)
  {
   datetime ny = t - InpServerMinusNY * 3600;
   MqlDateTime d;
   TimeToStruct(ny, d);
   datetime nyMid = ny - (d.hour * 3600 + d.min * 60 + d.sec);
   datetime s = nyMid + 17 * 3600;
   if(d.hour < 17)
      s -= 86400;
   return s + InpServerMinusNY * 3600;
  }
bool InWin(int m, int a, int b)   // a, b = 분 단위
  {
   return a <= b ? (m >= a && m < b) : (m >= a || m < b);
  }
void Notify(string s)
  {
   Print(s);
   if(InpPush)
      SendNotification(s);
  }
bool IsOurMagic(long mg) { return mg == MG[0] || mg == MG[1] || mg == MG[2]; }

//--- 구조 ------------------------------------------------------------
void UpdateSwings(int sh)
  {
   int p = sh + InpLenC;
   if(iBars(_Symbol, PERIOD_M5) <= p + InpLenC + 1)
      return;
   double hp = iHigh(_Symbol, PERIOD_M5, p), lp = iLow(_Symbol, PERIOD_M5, p);
   bool isH = true, isL = true;
   for(int j = 1; j <= InpLenC; j++)
     {
      if(iHigh(_Symbol, PERIOD_M5, p + j) > hp || iHigh(_Symbol, PERIOD_M5, p - j) >= hp)
         isH = false;
      if(iLow(_Symbol, PERIOD_M5, p + j) < lp || iLow(_Symbol, PERIOD_M5, p - j) <= lp)
         isL = false;
     }
   if(isH) { lastPH = hp; hasPH = true; }
   if(isL) { lastPL = lp; hasPL = true; }
  }

int Trend4H(datetime t)
  {
   int len = 5;
   int last = iBarShift(_Symbol, PERIOD_H4, t, false) + 1;
   int bars = iBars(_Symbol, PERIOD_H4);
   int start = MathMin(last + 300, bars - 2 * len - 2);
   int tr = 0;
   double sh = 0, sl = 0;
   bool hsh = false, hsl = false;
   for(int j = start; j >= last; j--)
     {
      int p = j + len;
      double hp = iHigh(_Symbol, PERIOD_H4, p), lp = iLow(_Symbol, PERIOD_H4, p);
      bool isH = true, isL = true;
      for(int k = 1; k <= len; k++)
        {
         if(iHigh(_Symbol, PERIOD_H4, p + k) > hp || iHigh(_Symbol, PERIOD_H4, p - k) >= hp)
            isH = false;
         if(iLow(_Symbol, PERIOD_H4, p + k) < lp || iLow(_Symbol, PERIOD_H4, p - k) <= lp)
            isL = false;
        }
      if(isH) { sh = hp; hsh = true; }
      if(isL) { sl = lp; hsl = true; }
      double c = iClose(_Symbol, PERIOD_H4, j);
      if(hsh && c > sh) { tr = 1;  hsh = false; }
      if(hsl && c < sl) { tr = -1; hsl = false; }
     }
   return tr;
  }

//--- 계좌 / 주문 도우미 ---------------------------------------------
// 오늘 손실 거래 수 한도, 또는 (여러 날에 걸친) 연속 손실 한도에 오늘 도달했으면 오늘은 중단
bool DayStopped()
  {
   datetime ds = DayStartServer(TimeCurrent());
   if(!HistorySelect(ds - 30 * 86400, TimeCurrent() + 60))
      return false;
   int lossesToday = 0, consec = 0;
   datetime lastLoss = 0;
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
     {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0 || !IsOurMagic(HistoryDealGetInteger(tk, DEAL_MAGIC)))
         continue;
      long en = HistoryDealGetInteger(tk, DEAL_ENTRY);
      if(en != DEAL_ENTRY_OUT && en != DEAL_ENTRY_OUT_BY)
         continue;
      double pr = HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_COMMISSION) + HistoryDealGetDouble(tk, DEAL_SWAP);
      datetime dt = (datetime)HistoryDealGetInteger(tk, DEAL_TIME);
      if(pr < 0)
        {
         consec++;
         lastLoss = dt;
         if(dt >= ds)
            lossesToday++;
        }
      else
         consec = 0;
     }
   return (lossesToday >= InpMaxDailyLoss || (consec >= InpMaxConsecLoss && lastLoss >= ds));
  }

// 서버 시각 t가 속한 뉴욕 날짜의 hhmm(분) 시각을 서버 시각으로 돌려준다
datetime NyClockOfDay(datetime t, int minutes)
  {
   long ny = (long)t - InpServerMinusNY * 3600;
   long nyMid = ny - (ny % 86400);
   return (datetime)(nyMid + minutes * 60 + InpServerMinusNY * 3600);
  }

// 진입 시각 이후 처음 오는 청산 시각 (아시아처럼 자정을 넘기면 다음날)
datetime ExitTime(datetime opened, int minutes)
  {
   datetime x = NyClockOfDay(opened, minutes);
   if(x <= opened)
      x += 86400;
   return x;
  }

// 모델 k의 주기 키: 레인지 시작 시각을 하루의 시작으로 본 뉴욕 날짜
int CycleKey(int k, datetime t)
  {
   MqlDateTime d;
   TimeToStruct((datetime)((long)t - InpServerMinusNY * 3600 - RS[k] * 60), d);
   return d.year * 10000 + d.mon * 100 + d.day;
  }

// 청산 시각이 지난 이 모델의 포지션·대기 주문 정리 (틱이 늦게 와도 동작)
void ExpireModel(int k)
  {
   datetime now = TimeCurrent();
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetInteger(POSITION_MAGIC) != MG[k] || PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if(now >= ExitTime((datetime)PositionGetInteger(POSITION_TIME), XE[k]))
         trade.PositionClose(tk);
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0 || OrderGetInteger(ORDER_MAGIC) != MG[k] || OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if(now >= ExitTime((datetime)OrderGetInteger(ORDER_TIME_SETUP), XE[k]))
        {
         trade.OrderDelete(tk);
         if(tk == pendTicket) pendTicket = 0;
        }
     }
  }

// 재시작 시 남아 있는 이 EA의 지정가 주문을 다시 관리 대상으로
void RestorePending()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0 || !IsOurMagic(OrderGetInteger(ORDER_MAGIC)) || OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      long type = OrderGetInteger(ORDER_TYPE);
      pendTicket = tk;
      pendT      = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      pendStp    = OrderGetDouble(ORDER_SL);
      pendTp     = OrderGetDouble(ORDER_TP);
      pendSide   = (type == ORDER_TYPE_BUY_LIMIT) ? 1 : -1;
      PrintFormat("대기 주문 복원: #%I64u", tk);
      return;
     }
  }

bool HasExposure(bool anySym)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || !IsOurMagic(PositionGetInteger(POSITION_MAGIC)))
         continue;
      if(anySym || PositionGetString(POSITION_SYMBOL) == _Symbol)
         return true;
     }
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0 || !IsOurMagic(OrderGetInteger(ORDER_MAGIC)))
         continue;
      if(anySym || OrderGetString(ORDER_SYMBOL) == _Symbol)
         return true;
     }
   return false;
  }

void CancelPending(long magic)   // magic = -1 이면 두 모델 모두
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0 || OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      long mg = OrderGetInteger(ORDER_MAGIC);
      if((magic < 0 && IsOurMagic(mg)) || mg == magic)
        {
         trade.OrderDelete(tk);
         if(tk == pendTicket) pendTicket = 0;
        }
     }
  }

void CloseModel(long magic)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) == magic && PositionGetString(POSITION_SYMBOL) == _Symbol)
         trade.PositionClose(tk);
     }
  }

// 0을 돌려주면 진입하지 않는다 (위험 한도 초과)
double CalcLots(double risk)
  {
   double bal  = AccountInfoDouble(ACCOUNT_BALANCE);
   double tv   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0)
      tv = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double ts   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double mn   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   if(step <= 0) step = 0.01;
   if(tv <= 0 || ts <= 0 || risk <= 0 || bal <= 0)
      return 0.0;
   double lossPerLot = risk / ts * tv;
   double lots = InpLots;
   if(InpUseRiskLot)
      lots = bal * InpRiskPct / 100.0 / lossPerLot;
   lots = MathFloor(lots / step + 1e-9) * step;
   lots = MathMin(lots, MathMin(mx, InpMaxLots));
   if(lots < mn)
      lots = mn;   // 최소 랏으로 올리되, 아래 위험 검사를 통과해야만 진입
   double riskPct = lots * lossPerLot / bal * 100.0;
   if(InpEnforceMaxRisk && riskPct > InpMaxRiskPct)
     {
      PrintFormat("진입 안 함: %.2f랏의 손실 위험 %.1f%% > 한도 %.1f%% (손절 %.1f핍)",
                  lots, riskPct, InpMaxRiskPct, risk / (_Point * 10));
      return 0.0;
     }
   return NormalizeDouble(lots, 2);
  }

void PlaceTrade(int k, int s, double entry, bool useLimit, double stp, double tp, int score, double rr)
  {
   if((int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD) > InpMaxSpreadPts)
     {
      st[k].msg = "스프레드가 커서 진입 건너뜀";
      Print(st[k].msg);
      return;
     }
   int    dg = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double minDist = (SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL) + 2) * pt;
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   stp = NormalizeDouble(stp, dg);
   tp  = NormalizeDouble(tp, dg);
   string cmt = StringFormat("VS-%s sc%d RR%.1f", k == 0 ? "L" : (k == 1 ? "N" : "A"), score, rr);
   trade.SetExpertMagicNumber(MG[k]);
   bool ok = false;
   double lots = 0;
   if(useLimit && ((s == 1 && entry < ask - minDist) || (s == -1 && entry > bid + minDist)))
     {
      double e = NormalizeDouble(entry, dg);
      if(MathAbs(e - stp) < minDist || MathAbs(tp - e) < minDist)
         return;
      lots = CalcLots(MathAbs(e - stp));
      if(lots <= 0) { st[k].msg = "위험 한도 초과로 진입 안 함"; return; }
      // 브로커가 허용하면 만료 시각을 지정 (재시작해도 늦게 체결되지 않게)
      datetime expiry = TimeCurrent() + InpFvgWaitBars * 300;
      bool canSpecified = (SymbolInfoInteger(_Symbol, SYMBOL_EXPIRATION_MODE) & SYMBOL_EXPIRATION_SPECIFIED) != 0;
      ENUM_ORDER_TYPE_TIME tt = canSpecified ? ORDER_TIME_SPECIFIED : ORDER_TIME_GTC;
      datetime ex = canSpecified ? expiry : 0;
      ok = (s == 1) ? trade.BuyLimit(lots, e, _Symbol, stp, tp, tt, ex, cmt)
                    : trade.SellLimit(lots, e, _Symbol, stp, tp, tt, ex, cmt);
      if(ok)
        {
         pendTicket = trade.ResultOrder();
         pendT = TimeCurrent();
         pendStp = stp;
         pendTp = tp;
         pendSide = s;
        }
     }
   else
     {
      double e = (s == 1) ? ask : bid;
      if(s * (tp - e) <= minDist || s * (e - stp) <= minDist)
        {
         st[k].msg = "현재가가 SL/TP 범위 밖이라 진입 안 함";
         Print(st[k].msg);
         return;
        }
      lots = CalcLots(MathAbs(e - stp));
      if(lots <= 0) { st[k].msg = "위험 한도 초과로 진입 안 함"; return; }
      ok = (s == 1) ? trade.Buy(lots, _Symbol, 0, stp, tp, cmt)
                    : trade.Sell(lots, _Symbol, 0, stp, tp, cmt);
     }
   st[k].msg = (ok ? "주문 완료: " : "주문 실패: ") + cmt + " / " + trade.ResultRetcodeDescription();
   if(ok)
      Notify(StringFormat("[Venus] %s %s %s 주문 %.2f랏 (%s)\nSL %s  TP %s  점수 %d  RR %.1f",
                          _Symbol, NM[k], s == 1 ? "매수" : "매도", lots, useLimit ? "지정가" : "시장가",
                          DoubleToString(stp, dg), DoubleToString(tp, dg), score, rr));
   else
      Notify("[Venus] 주문 실패: " + trade.ResultRetcodeDescription());
  }

void ManagePending()
  {
   if(pendTicket == 0)
      return;
   if(!OrderSelect(pendTicket)) { pendTicket = 0; return; }   // 체결되었거나 취소됨
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID), ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   bool expired = (TimeCurrent() - pendT) > InpFvgWaitBars * 300;
   bool stopHit = (pendSide == 1) ? (bid <= pendStp) : (ask >= pendStp);
   // 체결되기 전에 가격이 목표가에 먼저 닿으면 셋업이 끝난 것
   bool tpHit = pendTp > 0 && ((pendSide == 1) ? (bid >= pendTp) : (ask <= pendTp));
   if(expired || stopHit || tpHit)
     {
      trade.OrderDelete(pendTicket);
      pendTicket = 0;
      Notify(StringFormat("[Venus] %s 지정가 취소 (%s)", _Symbol,
                          expired ? "시간 초과" : (tpHit ? "체결 전 목표가 도달" : "체결 전 SL 도달")));
     }
  }

void DrawBox(int k, datetime t)
  {
   string nm = "VS_BOX" + IntegerToString(k) + "_" + IntegerToString(cyc[k]);
   if(ObjectFind(0, nm) < 0)
     {
      ObjectCreate(0, nm, OBJ_RECTANGLE, 0, st[k].aT0, st[k].aH, t + 300, st[k].aL);
      ObjectSetInteger(0, nm, OBJPROP_COLOR, BC[k]);
      ObjectSetInteger(0, nm, OBJPROP_STYLE, STYLE_DASH);
      ObjectSetInteger(0, nm, OBJPROP_FILL, false);
      ObjectSetInteger(0, nm, OBJPROP_BACK, true);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, nm, OBJPROP_TOOLTIP, k == 0 ? "아시아 레인지 (런던 스윕용)" : "런던 레인지 (뉴욕 스윕용)");
     }
   else
     {
      ObjectSetDouble(0, nm, OBJPROP_PRICE, 0, st[k].aH);
      ObjectSetDouble(0, nm, OBJPROP_PRICE, 1, st[k].aL);
      ObjectSetInteger(0, nm, OBJPROP_TIME, 1, t + 300);
     }
  }

//--- 모델 하나에 대해 확정된 5분봉 처리 ------------------------------
void ProcessModel(int k, int sh, bool live)
  {
   datetime t = iTime(_Symbol, PERIOD_M5, sh);
   double h  = iHigh(_Symbol, PERIOD_M5, sh);
   double l  = iLow(_Symbol, PERIOD_M5, sh);
   double c  = iClose(_Symbol, PERIOD_M5, sh);
   double cp = iClose(_Symbol, PERIOD_M5, sh + 1);
   int m = NyMin(t);

   // 1) 레인지
   if(InWin(m, RS[k], RE[k]))
     {
      if(!st[k].hasA) { st[k].hasA = true; st[k].aH = h; st[k].aL = l; st[k].aT0 = t; }
      else            { st[k].aH = MathMax(st[k].aH, h); st[k].aL = MathMin(st[k].aL, l); }
      if(InpDrawBoxes) DrawBox(k, t);
      return;
     }
   if(!st[k].hasA || st[k].done)
      return;

   // 2) 킬존 스윕
   if(InWin(m, KS[k], KE[k]) && st[k].swept == 0)
     {
      int d1 = iBarShift(_Symbol, PERIOD_D1, t, false);
      double pdH = iHigh(_Symbol, PERIOD_D1, d1 + 1), pdL = iLow(_Symbol, PERIOD_D1, d1 + 1);
      if(h > st[k].aH)      { st[k].swept = -1; st[k].swExt = h; st[k].swT = t; st[k].swPD = (h > pdH); }
      else if(l < st[k].aL) { st[k].swept = 1;  st[k].swExt = l; st[k].swT = t; st[k].swPD = (l < pdL); }
      if(st[k].swept != 0 && live)
         st[k].msg = (st[k].swept == -1) ? "레인지 고점 스윕 → 매도 MSS 대기" : "레인지 저점 스윕 → 매수 MSS 대기";
     }
   if(st[k].swept == 0 || !InWin(m, KS[k], EE[k]))
      return;

   st[k].swExt = (st[k].swept == -1) ? MathMax(st[k].swExt, h) : MathMin(st[k].swExt, l);
   if((st[k].swept == -1 && c < st[k].aL) || (st[k].swept == 1 && c > st[k].aH))
     {
      st[k].done = true;
      if(live) st[k].msg = "반대편까지 가버림 → 오늘 셋업 없음";
      return;
     }
   // 포지션 보유 중에도 위의 극값·무효 판정은 계속 갱신하고, 진입 판단만 건너뜀
   if(live && HasExposure(false))
      return;

   // 3) MSS
   double mss  = (st[k].swept == -1) ? lastPL : lastPH;
   bool   hasM = (st[k].swept == -1) ? hasPL : hasPH;
   bool crossed = (st[k].swept == -1) ? (c < mss && cp >= mss) : (c > mss && cp <= mss);
   if(!hasM || t <= st[k].swT || !crossed)
      return;

   int s = st[k].swept;
   double atr[1];
   if(CopyBuffer(atrH, 0, sh, 1, atr) != 1)
      return;
   double stp = st[k].swExt - s * InpBufAtr * atr[0];

   // 4) 변위 FVG
   bool hasF = false;
   double fvg = 0;
   for(int j = sh; j <= sh + 2 && !hasF; j++)
     {
      if(iTime(_Symbol, PERIOD_M5, j + 2) < st[k].swT)
         break;   // 스윕 이전 봉으로 만든 갭은 쓰지 않음
      if(s == -1 && iHigh(_Symbol, PERIOD_M5, j) < iLow(_Symbol, PERIOD_M5, j + 2))  { fvg = iHigh(_Symbol, PERIOD_M5, j); hasF = true; }
      if(s == 1  && iLow(_Symbol, PERIOD_M5, j)  > iHigh(_Symbol, PERIOD_M5, j + 2)) { fvg = iLow(_Symbol, PERIOD_M5, j);  hasF = true; }
     }
   double tp = (s == 1) ? st[k].aH : st[k].aL;
   bool useLimit = InpFvgLimit && hasF;
   double e = useLimit ? fvg : c;
   if(useLimit && s * (e - stp) <= 0)
     {
      useLimit = false;   // 갭 가격이 손절 반대편이면 시장가로
      e = c;
     }
   double risk = MathAbs(e - stp);
   double rr = (risk > 0) ? s * (tp - e) / risk : 0;

   // 5) 컨플루언스 점수
   int t4 = Trend4H(t);
   double mid = (st[k].aH + st[k].aL) / 2;
   int score = (t4 == s ? 1 : 0) + (hasF ? 1 : 0) + (st[k].swPD ? 1 : 0)
             + ((s == 1 ? e < mid : e > mid) ? 1 : 0) + (rr >= 3 ? 1 : 0)
             + (MathAbs(st[k].swExt - (s == 1 ? st[k].aL : st[k].aH)) >= 0.5 * atr[0] ? 1 : 0);
   st[k].done = true;
   string tag = StringFormat("%s 신호 점수 %d RR %.1f", s == 1 ? "매수" : "매도", score, rr);
   if(rr < InpMinRR || score < InpMinScore)
     {
      if(live) { st[k].msg = tag + " → 조건 미달 패스"; Print(NM[k], " ", st[k].msg); }
      return;
     }
   if(rr > InpMaxRR)
      tp = e + s * InpMaxRR * risk;
   if(!live)
      return;
   if(DayStopped())                       { st[k].msg = tag + " → 일일 손실 한도로 패스";   Notify("[Venus] " + _Symbol + " " + NM[k] + " " + st[k].msg); return; }
   if(InpOneAtATime && HasExposure(true)) { st[k].msg = tag + " → 다른 종목 포지션 보유 중"; Print(st[k].msg); return; }
   PlaceTrade(k, s, e, useLimit, stp, tp, score, rr);
  }

void ProcessBar(int sh, bool live)
  {
   datetime t = iTime(_Symbol, PERIOD_M5, sh);
   // 모델마다 자기 레인지 시작 시각에 새 주기를 시작 (아시아 레인지가 뉴욕 17시를 넘나들어도 안전)
   for(int k = 0; k < 3; k++)
     {
      int ck = CycleKey(k, t);
      if(ck == cyc[k])
         continue;
      cyc[k] = ck;
      st[k].hasA = false;
      st[k].swept = 0;
      st[k].done = false;
      st[k].msg = "대기 중";
      if(live) CancelPending(MG[k]);
     }
   UpdateSwings(sh);
   for(int k = 0; k < 3; k++)
      if(ON[k])
         ProcessModel(k, sh, live);
  }

//--- 이벤트 ----------------------------------------------------------
int OnInit()
  {
   ON[0] = InpUseLondon; ON[1] = InpUseNY; ON[2] = InpUseAsia;
   RS[0] = InpL_RangeStart * 60; RE[0] = InpL_RangeEnd * 60; KS[0] = InpL_KzStart * 60; KE[0] = InpL_KzEnd * 60; EE[0] = InpL_EntryEnd * 60; XE[0] = InpL_Exit * 60;
   RS[1] = InpN_RangeStart * 60; RE[1] = InpN_RangeEnd * 60; KS[1] = InpN_KzStart * 60; KE[1] = InpN_KzEnd * 60; EE[1] = InpN_EntryEnd * 60; XE[1] = InpN_Exit * 60;
   RS[2] = InpA_RangeStart * 60; RE[2] = InpA_RangeEnd * 60; KS[2] = InpA_KzStart * 60; KE[2] = InpA_KzEnd * 60; EE[2] = InpA_EntryEnd * 60; XE[2] = InpA_Exit * 60;
   MG[0] = InpMagic; MG[1] = InpMagic + 1; MG[2] = InpMagic + 2;
   for(int k = 0; k < 3; k++)
     {
      st[k].hasA = false; st[k].swept = 0; st[k].done = false; st[k].msg = "대기 중";
     }
   trade.SetDeviationInPoints(20);
   atrH = iATR(_Symbol, PERIOD_M5, 14);
   if(atrH == INVALID_HANDLE)
      return INIT_FAILED;
   for(int k = 0; k < 3; k++) cyc[k] = -1;
   int warm = MathMin(600, iBars(_Symbol, PERIOD_M5) - 10);
   for(int sh = warm; sh >= 1; sh--)
      ProcessBar(sh, false);          // 오늘 레인지/스윕 상태 복원 (주문 없음)
   lastBar = iTime(_Symbol, PERIOD_M5, 0);
   RestorePending();
   PrintFormat("Venus Sweep Trio 시작: %s / %s / 랏 %.2f / 런던 %s · 뉴욕 %s",
               _Symbol, AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL ? "실계좌" : "데모",
               InpLots, ON[0] ? "ON" : "OFF", ON[1] ? "ON" : "OFF");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   Comment("");
   if(atrH != INVALID_HANDLE)
      IndicatorRelease(atrH);
  }

void OnTick()
  {
   ManagePending();
   for(int k = 0; k < 3; k++)
      ExpireModel(k);
   datetime bt = iTime(_Symbol, PERIOD_M5, 0);
   if(bt != lastBar)
     {
      lastBar = bt;
      ProcessBar(1, true);
     }
   string acc = AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL ? "실계좌" : "데모";
   string lot = InpUseRiskLot ? StringFormat("%.1f%% 리스크", InpRiskPct) : DoubleToString(InpLots, 2) + "랏";
   string s = StringFormat("Venus Sweep Trio | %s | %s\n", acc, lot);
   for(int k = 0; k < 3; k++)
     {
      if(!ON[k]) { s += NM[k] + " 스윕: OFF\n"; continue; }
      s += StringFormat("%s 스윕  레인지 %s ~ %s | %s\n", NM[k],
                        st[k].hasA ? DoubleToString(st[k].aL, _Digits) : "-",
                        st[k].hasA ? DoubleToString(st[k].aH, _Digits) : "-", st[k].msg);
     }
   Comment(s);
  }

void OnTradeTransaction(const MqlTradeTransaction &tr, const MqlTradeRequest &rq, const MqlTradeResult &rs)
  {
   if(tr.type != TRADE_TRANSACTION_DEAL_ADD)
      return;
   if(!HistoryDealSelect(tr.deal))
      return;
   long mg = HistoryDealGetInteger(tr.deal, DEAL_MAGIC);
   if(!IsOurMagic(mg) || HistoryDealGetString(tr.deal, DEAL_SYMBOL) != _Symbol)
      return;
   string mdl = (mg == MG[0]) ? "런던" : (mg == MG[1] ? "뉴욕" : "아시아");
   long en = HistoryDealGetInteger(tr.deal, DEAL_ENTRY);
   double px = HistoryDealGetDouble(tr.deal, DEAL_PRICE);
   if(en == DEAL_ENTRY_IN)
      Notify(StringFormat("[Venus] %s %s 진입 체결 @ %s", _Symbol, mdl, DoubleToString(px, _Digits)));
   else if(en == DEAL_ENTRY_OUT || en == DEAL_ENTRY_OUT_BY)
     {
      double pr = HistoryDealGetDouble(tr.deal, DEAL_PROFIT) + HistoryDealGetDouble(tr.deal, DEAL_COMMISSION) + HistoryDealGetDouble(tr.deal, DEAL_SWAP);
      Notify(StringFormat("[Venus] %s %s 청산 @ %s  손익 %+.2f %s  잔고 %.2f", _Symbol, mdl, DoubleToString(px, _Digits),
                          pr, AccountInfoString(ACCOUNT_CURRENCY), AccountInfoDouble(ACCOUNT_BALANCE)));
     }
  }
//+------------------------------------------------------------------+
