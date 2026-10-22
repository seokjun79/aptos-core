//+------------------------------------------------------------------+
//|  Venus CRT 비서 (MT5) — 자동매매가 아닌 '감시·알림·위험관리' EA   |
//|  규칙서: trading/strategy/user_smc_crt_rules.md                  |
//|   ① 4H CRT 기준봉(직전 마감 4H)의 CRH/CRL 너머로 스윕 → 알림     |
//|   ② 1분봉(InpLTF)이 '진짜 MSS 선'(마지막 하락이 시작된 고점)을  |
//|      몸통 마감으로 돌파 → 확정 알림 + OB·FVG·손절·목표·추천 랏    |
//|   ③ 확정 후 가격이 OB(M)로 되돌아오면 알림, 확인 캔들 마감 알림  |
//|   ④ 아시아장에는 알림 없음                                       |
//|   ⑤ 고객님 수동 주문: 손절 없으면 자동 손절, 위험 과다면 랏 축소,  |
//|      하루 손실 한도면 잠금                                       |
//|  진입은 고객님이 결정한다. 이 EA는 신규 주문을 넣지 않는다.       |
//+------------------------------------------------------------------+
#property copyright "Venus"
#property version   "1.43"
#property description "SMC+CRT 감시·확정 알림·위험관리 비서. 신규 주문은 넣지 않음."
#include <Trade\Trade.mqh>

input group "=== 감시 종목 ==="
input string InpSymbols        = "GBPUSD,GBPJPY,EURUSD,EURJPY"; // 감시할 종목 (쉼표로 구분)
input string InpSuffix         = "";      // 브로커 종목 접미사
input group "=== 시간 (뉴욕 시각) ==="
input int    InpServerMinusNY  = 7;       // 서버시간 - 뉴욕시간 (IC마켓 = 7)
input int    InpAsiaStartNY    = 19;      // 아시아장 시작 (알림 없음)
input int    InpAsiaEndNY      = 2;       // 아시아장 끝
input group "=== 규칙 ==="
input ENUM_TIMEFRAMES InpLTF  = PERIOD_M1; // MSS·OB를 보는 시간봉 (석준님은 1분봉)
input int    InpLegBars        = 240;     // C 시각을 모를 때 MSS를 찾을 범위 (봉 개수)
input int    InpSwingBars      = 5;       // MSS 스윙 판단: 앞뒤 몇 봉보다 높아야(낮아야) 스윙으로 볼지
input double InpSLBufferPips   = 1.0;     // 손절 버퍼 (핍)
input double InpRiskPct        = 1.0;     // 추천 랏 계산용 1회 위험 (잔고 %)
input bool   InpPush           = true;    // 휴대폰 알림
input bool   InpDraw           = true;    // 이 차트 종목에 선·박스 그리기
input group "=== 텔레그램 ==="
input string InpTgToken        = "";      // 텔레그램 봇 토큰 (@BotFather 에서 받은 것)
input string InpTgChatId       = "";      // 채팅 ID (비워 두면 봇에게 보낸 첫 메시지에서 자동으로 찾음)
input bool   InpTgChart        = true;    // 알림 때 차트 사진도 보내기
input group "=== 위험 관리 (고객님 수동 주문) ==="
input bool   InpGuard          = true;    // 위험 관리 켜기
input double InpGuardMaxRisk   = 2.0;     // 1회 손실 한도 (잔고 %), 넘으면 랏을 줄임
input double InpGuardDefaultSL = 15.0;    // 손절이 없을 때 자동으로 거는 손절 (핍)
input double InpDailyLossPct   = 3.0;     // 하루 손실 한도 (%), 넘으면 잠금

struct Watch
  {
   string   sym;
   double   pip;
   datetime h4;          // 현재 4H 봉 시작
   datetime lastM5;
   double   crh, crl;
   int      dir;          // 0 없음, +1 매수 셋업(CRL 스윕), -1 매도 셋업(CRH 스윕)
   double   ext;          // 스윕 극값
   datetime extT;
   double   mss;          // 진짜 MSS 선
   bool     done;         // 이번 4H 봉에서 확정 알림 보냄
   double   sugSL;        // 최근 셋업의 추천 손절 (위험 관리에 사용)
   int      sugDir;
   datetime crhT, crlT;   // CRH·CRL을 만든 봉 시각 (그림의 C)
   int      stage;        // 0 대기, 1 확정 후 OB 되돌림 대기, 2 OB 도달 후 확인 캔들 대기
   int      tdir;         // 추적 중인 셋업 방향 (새 4H가 시작돼도 유지)
   double   obH, obL, tp;
   datetime confT;
   bool     rebuilt;      // 붙인 직후 지난 봉으로 상태를 복원했는지
   string   snap;         // 이번 봉 처리 뒤 텔레그램으로 보낼 차트 사진 설명 (빈칸이면 안 보냄)
  };

CTrade   trade;
Watch    W[];
datetime g_day = 0;
double   g_dayStart = 0;
bool     g_locked = false;

//--- 도우미 ---------------------------------------------------------
// 휴대폰 알림은 255자 제한이 있어 줄 단위로 나눠 보낸다
//--- 텔레그램 --------------------------------------------------------
string g_tgChat = "";
void   TgSend(string s);
bool   g_tgWarned = false;

string UrlEncode(string s)
  {
   uchar b[];
   int n = StringToCharArray(s, b, 0, WHOLE_ARRAY, CP_UTF8) - 1;   // 마지막 0 제외
   string out = "";
   for(int i = 0; i < n; i++)
     {
      uchar c = b[i];
      if((c >= '0' && c <= '9') || (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || c == '-' || c == '_' || c == '.')
         out += CharToString(c);
      else
         out += StringFormat("%%%02X", c);
     }
   return out;
  }

// 성공하면 응답 본문, 실패하면 ""
string TgCall(string method, string body)
  {
   if(InpTgToken == "" || MQLInfoInteger(MQL_TESTER)) return "";
   char data[], res[];
   string resHdr;
   StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   ArrayResize(data, ArraySize(data) - 1);
   ResetLastError();
   int code = WebRequest("POST", "https://api.telegram.org/bot" + InpTgToken + "/" + method,
                         "Content-Type: application/x-www-form-urlencoded\r\n", 3000, data, res, resHdr);
   if(code == -1)
     {
      if(!g_tgWarned)
        {
         g_tgWarned = true;
         string m = StringFormat("[CRT 비서] 텔레그램 연결 실패 (오류 %d). 도구 → 옵션 → 전문가 조언자 → 'WebRequest 허용 URL'에 https://api.telegram.org 를 넣어 주세요.", GetLastError());
         Print(m);
         if(InpPush) SendNotification(m);
        }
      return "";
     }
   string r = CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8);
   if(code != 200) { PrintFormat("[CRT 비서] 텔레그램 응답 %d: %s", code, r); return ""; }
   return r;
  }

// 봇에게 보낸 메시지에서 채팅 ID를 찾아 저장
void TgFindChat()
  {
   if(g_tgChat != "" || InpTgToken == "") return;
   string r = TgCall("getUpdates", "limit=20");
   int p = StringFind(r, "\"chat\":{\"id\":");
   int last = -1;
   while(p >= 0) { last = p; p = StringFind(r, "\"chat\":{\"id\":", p + 1); }
   if(last < 0) return;
   int a = last + 13, e = a;   // "chat":{"id": 는 13글자
   while(e < StringLen(r) && (StringGetCharacter(r, e) == '-' || (StringGetCharacter(r, e) >= '0' && StringGetCharacter(r, e) <= '9'))) e++;
   g_tgChat = StringSubstr(r, a, e - a);
   if(g_tgChat == "") return;
   GlobalVariableSet("VCRT_TGCHAT", StringToDouble(g_tgChat));
   TgSend("[CRT 비서] 텔레그램 연결됐어요! 이제 여기로 알림을 보내 드려요.");
  }

void TgSend(string s)
  {
   if(InpTgToken == "" || g_tgChat == "") return;
   TgCall("sendMessage", "chat_id=" + g_tgChat + "&text=" + UrlEncode(s));
  }

// 텔레그램으로 사진 보내기 (MQL5\Files 안의 파일)
void TgPhoto(string file, string caption)
  {
   if(InpTgToken == "" || g_tgChat == "" || MQLInfoInteger(MQL_TESTER)) return;
   int fh = FileOpen(file, FILE_READ | FILE_BIN);
   if(fh == INVALID_HANDLE) { PrintFormat("[CRT 비서] 차트 사진 파일을 못 열었어요 (%d)", GetLastError()); return; }
   char img[];
   FileReadArray(fh, img);
   FileClose(fh);
   string bd = "----VenusCRTBoundary7MA4YWxk";
   string head = "--" + bd + "\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n" + g_tgChat + "\r\n"
               + "--" + bd + "\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n" + caption + "\r\n"
               + "--" + bd + "\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"chart.png\"\r\nContent-Type: image/png\r\n\r\n";
   string tail = "\r\n--" + bd + "--\r\n";
   char a[], t[], data[], res[];
   StringToCharArray(head, a, 0, WHOLE_ARRAY, CP_UTF8); ArrayResize(a, ArraySize(a) - 1);
   StringToCharArray(tail, t, 0, WHOLE_ARRAY, CP_UTF8); ArrayResize(t, ArraySize(t) - 1);
   ArrayCopy(data, a);
   ArrayCopy(data, img, ArraySize(data));
   ArrayCopy(data, t, ArraySize(data));
   string resHdr;
   int code = WebRequest("POST", "https://api.telegram.org/bot" + InpTgToken + "/sendPhoto",
                         "Content-Type: multipart/form-data; boundary=" + bd + "\r\n", 10000, data, res, resHdr);
   if(code != 200) PrintFormat("[CRT 비서] 차트 사진 전송 실패 (%d): %s", code, CharArrayToString(res, 0, WHOLE_ARRAY, CP_UTF8));
  }

void Notify(string s)
  {
   Print(s);
   if(MQLInfoInteger(MQL_TESTER)) return;
   TgSend(s);
   if(!InpPush) return;
   string lines[];
   int n = StringSplit(s, '\n', lines);
   string chunk = "";
   for(int i = 0; i < n; i++)
     {
      if(StringLen(chunk) + StringLen(lines[i]) + 1 > 240)
        { SendNotification(chunk); chunk = ""; }
      chunk += (chunk == "" ? "" : "\n") + lines[i];
     }
   if(chunk != "") SendNotification(chunk);
  }

int NyHour(datetime t)
  {
   MqlDateTime d;
   TimeToStruct((datetime)((long)t - InpServerMinusNY * 3600), d);
   return d.hour;
  }

bool InAsia(datetime t)
  {
   int h = NyHour(t);
   return (InpAsiaStartNY > InpAsiaEndNY) ? (h >= InpAsiaStartNY || h < InpAsiaEndNY)
                                          : (h >= InpAsiaStartNY && h < InpAsiaEndNY);
  }

// 추세: 마지막으로 '몸통 마감'으로 깬 스윙(앞뒤 2봉) 방향. 고점 라인을 몸통 마감으로 넘으면 상승,
// 저점 라인을 몸통 마감으로 깨면 하락 (공부 노트 규칙). +1 상승, -1 하락, 0 모름
int Bias(string sym, ENUM_TIMEFRAMES tf)
  {
   int n = 150;
   if(Bars(sym, tf) < n + 10) return 0;
   double lastHi = 0, lastLo = 0;
   int bias = 0;
   for(int k = n; k >= 1; k--)
     {
      int j = k + 2;   // k봉이 마감될 때 확정되는 스윙
      double hj = iHigh(sym, tf, j), lj = iLow(sym, tf, j);
      if(hj > iHigh(sym, tf, j + 1) && hj > iHigh(sym, tf, j + 2) && hj >= iHigh(sym, tf, j - 1) && hj >= iHigh(sym, tf, j - 2)) lastHi = hj;
      if(lj < iLow(sym, tf, j + 1) && lj < iLow(sym, tf, j + 2) && lj <= iLow(sym, tf, j - 1) && lj <= iLow(sym, tf, j - 2)) lastLo = lj;
      double c = iClose(sym, tf, k);
      if(lastHi > 0 && c > lastHi) { bias = 1;  lastHi = 0; }
      if(lastLo > 0 && c < lastLo) { bias = -1; lastLo = 0; }
     }
   return bias;
  }

string Arrow(int b) { return b > 0 ? "상승↑" : (b < 0 ? "하락↓" : "횡보"); }

// 셋업 방향과 일봉·4H 추세 비교 문구
string TrendLine(string sym, int dir)
  {
   int d1 = Bias(sym, PERIOD_D1), h4 = Bias(sym, PERIOD_H4);
   int agree = (d1 == dir ? 1 : 0) + (h4 == dir ? 1 : 0);
   string verdict = (agree == 2) ? "✅ 추세와 같은 방향 (좋은 자리)"
                  : (agree == 1) ? "🟡 추세 하나만 같은 방향 (조심)"
                                 : "⚠ 추세 반대 방향 (역추세, 랏 줄이거나 패스)";
   return StringFormat("추세: 일봉 %s · 4H %s → %s", Arrow(d1), Arrow(h4), verdict);
  }

string Px(string s, double v) { return DoubleToString(v, (int)SymbolInfoInteger(s, SYMBOL_DIGITS)); }

int FindWatch(string s)
  {
   for(int i = 0; i < ArraySize(W); i++)
      if(W[i].sym == s) return i;
   return -1;
  }

double LossPerLot(string s, double dist)
  {
   double tv = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE_LOSS);
   if(tv <= 0) tv = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(s, SYMBOL_TRADE_TICK_SIZE);
   if(tv <= 0 || ts <= 0) return 0;
   return dist / ts * tv;
  }

double SuggestLots(string s, double dist)
  {
   double lpl = LossPerLot(s, dist);
   double step = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP);
   if(lpl <= 0 || step <= 0) return 0;
   double lots = MathFloor(AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPct / 100.0 / lpl / step + 1e-9) * step;
   return NormalizeDouble(lots, 2);
  }

//--- 그리기 (차트 종목만) --------------------------------------------
void HLine(string name, double price, color col, ENUM_LINE_STYLE st, string tip)
  {
   if(!InpDraw) return;
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_HLINE, 0, 0, price);
   ObjectSetDouble(0, name, OBJPROP_PRICE, price);
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
   ObjectSetString(0, name, OBJPROP_TEXT, tip);
  }

void Box(string name, datetime t1, double p1, datetime t2, double p2, color col, string tip)
  {
   if(!InpDraw) return;
   if(ObjectFind(0, name) < 0) ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, col);
   ObjectSetInteger(0, name, OBJPROP_FILL, true);
   ObjectSetInteger(0, name, OBJPROP_BACK, true);
   ObjectSetString(0, name, OBJPROP_TOOLTIP, tip);
  }

// 선 하나 (차트 id 지정)
void SnapLine(long cid, string name, double price, color col, ENUM_LINE_STYLE st)
  {
   if(price <= 0) return;
   ObjectCreate(cid, name, OBJ_HLINE, 0, 0, price);
   ObjectSetInteger(cid, name, OBJPROP_COLOR, col);
   ObjectSetInteger(cid, name, OBJPROP_STYLE, st);
  }

// 차트 차트를 사진으로 찍어 텔레그램으로 보낸다. 감시 종목이 이 차트가 아니면 잠깐 열었다 닫는다.
void Snap(Watch &w)
  {
   if(!InpTgChart || InpTgToken == "" || g_tgChat == "" || MQLInfoInteger(MQL_TESTER)) return;
   long cid = ChartID();
   bool temp = (w.sym != _Symbol || Period() != InpLTF);
   if(temp)
     {
      cid = ChartOpen(w.sym, InpLTF);
      if(cid == 0) { PrintFormat("[CRT 비서] %s 차트를 열지 못했어요 (%d)", w.sym, GetLastError()); return; }
      ChartSetInteger(cid, CHART_SHOW_GRID, false);
      ChartSetInteger(cid, CHART_AUTOSCROLL, true);
      ChartSetInteger(cid, CHART_SHIFT, true);
      SnapLine(cid, "S_CRH", w.crh, clrDodgerBlue, STYLE_SOLID);
      SnapLine(cid, "S_CRL", w.crl, clrDodgerBlue, STYLE_SOLID);
      SnapLine(cid, "S_MSS", w.mss, clrRed, STYLE_DASH);
      if(w.stage > 0)
        {
         ObjectCreate(cid, "S_OB", OBJ_RECTANGLE, 0, w.confT - 3600, w.obH, TimeCurrent() + 3600, w.obL);
         ObjectSetInteger(cid, "S_OB", OBJPROP_COLOR, clrDarkKhaki);
         ObjectSetInteger(cid, "S_OB", OBJPROP_FILL, true);
         ObjectSetInteger(cid, "S_OB", OBJPROP_BACK, true);
         SnapLine(cid, "S_TP", w.tp, clrLimeGreen, STYLE_DOT);
        }
      if(w.sugDir != 0) SnapLine(cid, "S_SL", w.sugSL, clrOrangeRed, STYLE_DOT);
      ChartRedraw(cid);
      Sleep(1500);   // 새 차트가 그려질 시간
     }
   ChartRedraw(cid);
   string f = "VCRT_" + w.sym + ".png";
   if(ChartScreenShot(cid, f, 1100, 650, ALIGN_RIGHT))
      TgPhoto(f, w.sym + " " + StringSubstr(EnumToString(InpLTF), 7) + " · " + w.snap);
   else
      PrintFormat("[CRT 비서] %s 차트 사진 실패 (%d)", w.sym, GetLastError());
   if(temp) ChartClose(cid);
  }

// 같은 4H 봉에서 이미 보낸 알림인지 (EA를 다시 붙여도 중복 알림이 안 가게 터미널에 기록)
bool AlreadySent(string sym, string kind, datetime h4)
  {
   string k = "VCRT_" + kind + "_" + sym;
   if(GlobalVariableCheck(k) && (datetime)GlobalVariableGet(k) == h4) return true;
   GlobalVariableSet(k, (double)h4);
   return false;
  }

//--- 감시 로직 -------------------------------------------------------
void ResetCycle(Watch &w)
  {
   w.h4  = iTime(w.sym, PERIOD_H4, 0);
   w.crh = iHigh(w.sym, PERIOD_H4, 1);   // 직전 마감 4H = CRT 기준봉(1번 캔들)
   w.crl = iLow(w.sym, PERIOD_H4, 1);
   w.dir = 0; w.ext = 0; w.extT = 0; w.mss = 0; w.done = false;
   if(w.stage == 0) { w.sugSL = 0; w.sugDir = 0; }   // OB 추적 중이면 추천 손절 유지
   Anchors(w);
   if(w.sym == _Symbol)
     {
      HLine("VCRT_CRH", w.crh, clrDodgerBlue, STYLE_SOLID, "4H CRH");
      HLine("VCRT_CRL", w.crl, clrDodgerBlue, STYLE_SOLID, "4H CRL");
      ObjectDelete(0, "VCRT_MSS");
      if(w.stage == 0)
        {
         ObjectDelete(0, "VCRT_OB"); ObjectDelete(0, "VCRT_FVG");
         ObjectDelete(0, "VCRT_SL"); ObjectDelete(0, "VCRT_TP");
        }
     }
  }

// C1(직전 4H) 안에서 CRH·CRL을 만든 봉(그림의 C) 찾기
void Anchors(Watch &w)
  {
   w.crhT = 0; w.crlT = 0;
   int sEnd = iBarShift(w.sym, InpLTF, iTime(w.sym, PERIOD_H4, 1), false);
   int sBeg = iBarShift(w.sym, InpLTF, w.h4, false) + 1;
   if(sEnd >= sBeg && sBeg > 0)
     {
      int hi = iHighest(w.sym, InpLTF, MODE_HIGH, sEnd - sBeg + 1, sBeg);
      int lo = iLowest(w.sym, InpLTF, MODE_LOW, sEnd - sBeg + 1, sBeg);
      if(hi >= 0) w.crhT = iTime(w.sym, InpLTF, hi);
      if(lo >= 0) w.crlT = iTime(w.sym, InpLTF, lo);
     }
  }

// 진짜 MSS 선 (석준님 그림, 매수 기준): 스윕 최저점(극값)으로 내려오기 직전의 스윙 고점
// = 마지막 하락이 시작된 고점. 극값에서 거꾸로 가며 처음 만나는 스윙 고점(앞뒤 InpSwingBars봉보다 높음).
// 가격이 더 낮은 저점을 새로 만들면 그 직전 스윙 고점으로 선이 내려온다. 매도는 대칭.
// 작은 흔들림은 InpSwingBars(기본 5)로 거른다. C(CRH/CRL을 만든 봉) 이전까지는 찾지 않는다.
double TrueMssLevel(const Watch &w)
  {
   int es = iBarShift(w.sym, InpLTF, w.extT, false);
   if(es < 0) return 0;
   int n = (int)MathMax(1, InpSwingBars);
   datetime anchor = (w.dir == 1) ? w.crlT : w.crhT;
   int last = es + InpLegBars;
   if(anchor > 0)
     {
      int as = iBarShift(w.sym, InpLTF, anchor, false);
      if(as > es) last = (int)MathMin(as - 1, es + 600);
     }
   for(int k = (int)MathMax(es + 1, n + 1); k <= last; k++)
     {
      double v  = (w.dir == 1) ? iHigh(w.sym, InpLTF, k) : iLow(w.sym, InpLTF, k);
      if(v <= 0) break;
      if(w.dir == 1 && v >= w.crh) continue;
      if(w.dir == -1 && v <= w.crl) continue;
      bool sw = true;
      for(int j = 1; j <= n && sw; j++)
        {
         double a = (w.dir == 1) ? iHigh(w.sym, InpLTF, k + j) : iLow(w.sym, InpLTF, k + j);
         double b = (w.dir == 1) ? iHigh(w.sym, InpLTF, k - j) : iLow(w.sym, InpLTF, k - j);
         if(w.dir == 1)  sw = (v > a && v >= b);
         else            sw = (v < a && v <= b);
        }
      if(sw) return v;   // 극값에 가장 가까운 스윙 = 마지막 하락(상승)의 시작점
     }
   return 0;
  }

// 확정 후: 가격이 OB(그림의 D)로 되돌아오는지, 그다음 확인 캔들이 마감하는지 지켜본다
void Track(Watch &w)
  {
   datetime t1 = iTime(w.sym, InpLTF, 1);
   double o = iOpen(w.sym, InpLTF, 1), h = iHigh(w.sym, InpLTF, 1);
   double l = iLow(w.sym, InpLTF, 1),  c = iClose(w.sym, InpLTF, 1);
   if(o <= 0) return;
   bool asia = InAsia(t1 + PeriodSeconds(InpLTF));
   string side = (w.tdir == 1) ? "매수" : "매도";
   double edge = (w.tdir == 1) ? w.obH : w.obL;   // 가격이 먼저 닿는 OB 끝
   double far  = (w.tdir == 1) ? w.obL : w.obH;   // 이 너머로 마감하면 무효
   if(t1 - w.confT > 8 * 3600)
     {
      Notify(StringFormat("[CRT 비서] %s %s 셋업: 8시간 동안 진입 자리가 안 나와서 감시를 끝내요.", w.sym, side));
      w.stage = 0; return;
     }
   if(w.tdir * (c - far) < 0)
     {
      Notify(StringFormat("[CRT 비서] %s %s 셋업 무효: OB를 몸통으로 뚫고 마감 (%s). 진입하지 마세요.", w.sym, side, Px(w.sym, c)));
      w.stage = 0; return;
     }
   if((w.tdir == 1 && h >= w.tp) || (w.tdir == -1 && l <= w.tp))
     {
      Notify(StringFormat("[CRT 비서] %s 진입 전에 목표 %s 도달 → 이번 셋업은 끝. 쫓아가지 마세요.", w.sym, Px(w.sym, w.tp)));
      w.stage = 0; return;
     }
   if(asia) return;   // 아시아장: 진입 단계로 넘어가지 않음 (거래 금지)
   if(w.stage == 1)
     {
      if((w.tdir == 1 && l <= edge) || (w.tdir == -1 && h >= edge))
        {
         w.stage = 2;
         w.snap = "OB 도달";
         Notify(StringFormat("[CRT 비서] %s OB(M) %s~%s 도달! 지정가 자리예요.\n더 확실하게: %s 쪽 몸통 마감 캔들을 기다려요.",
                                       w.sym, Px(w.sym, w.obL), Px(w.sym, w.obH), w.tdir == 1 ? "양봉" : "음봉"));
        }
      else return;   // 닿은 봉이 곧바로 확인 캔들일 수도 있어 아래로 이어서 본다
     }
   // stage 2: OB에서 반대로 몸통 마감 = 확인 캔들 (반성 원칙: 마감 확인 후 진입)
   bool conf = (w.tdir == 1) ? (c > o && c > w.obH) : (c < o && c < w.obL);
   if(conf)
     {
      w.snap = "확인 캔들 마감";
      Notify(StringFormat("[CRT 비서] %s %s 확인 캔들 마감 (%s). 다음 봉 시가가 진입 자리예요. 결정은 고객님!", w.sym, side, Px(w.sym, c)));
      w.stage = 0;
     }
  }

// 비서를 붙이거나 차트 시간봉을 바꾸면 처음부터 시작한다. 이번 4H 봉의 지난 봉들을 조용히 다시 보며
// 스윕·극값·MSS 선·확정 여부를 복원한다 (알림은 보내지 않음).
void Rebuild(Watch &w)
  {
   w.rebuilt = true;
   int first = iBarShift(w.sym, InpLTF, w.h4, false);
   if(first < 1 || w.crh <= w.crl) return;
   for(int sh = first; sh >= 1; sh--)
     {
      datetime t = iTime(w.sym, InpLTF, sh);
      double o = iOpen(w.sym, InpLTF, sh), h = iHigh(w.sym, InpLTF, sh);
      double l = iLow(w.sym, InpLTF, sh),  c = iClose(w.sym, InpLTF, sh);
      if(t < w.h4 || o <= 0) continue;
      if(w.dir == 0)
        {
         if(l < w.crl)      { w.dir = 1;  w.ext = l; w.extT = t; }
         else if(h > w.crh) { w.dir = -1; w.ext = h; w.extT = t; }
         else continue;
         w.mss = TrueMssLevel(w);
         continue;
        }
      if((w.dir == 1 && l < w.ext) || (w.dir == -1 && h > w.ext))
        { w.ext = (w.dir == 1) ? l : h; w.extT = t; w.mss = TrueMssLevel(w); continue; }
      if(w.mss > 0)
        {
         bool body = (w.dir == 1) ? (c > w.mss && c > o) : (c < w.mss && c < o);
         if(body && c > w.crl && c < w.crh) { w.done = true; break; }
        }
     }
   if(w.dir != 0)
      PrintFormat("[CRT 비서] %s 복원: %s 스윕 극값 %s, MSS 선 %s%s", w.sym, w.dir == 1 ? "CRL" : "CRH",
                  Px(w.sym, w.ext), Px(w.sym, w.mss), w.done ? " (이미 확정됨)" : "");
   if(w.sym == _Symbol && w.mss > 0)
      HLine("VCRT_MSS", w.mss, clrRed, STYLE_DASH, "진짜 MSS 선 (몸통 마감 돌파 대기)");
  }

void OnNewM5(Watch &w)
  {
   if(!w.rebuilt && iTime(w.sym, PERIOD_H4, 0) == w.h4) Rebuild(w);
   if(w.stage > 0) Track(w);   // 이전 셋업의 OB 추적은 따로, 새 4H 셋업 감지는 계속
   if(iTime(w.sym, PERIOD_H4, 0) != w.h4)
     {
      ResetCycle(w);
      w.rebuilt = true;
     }
   else if(w.crhT == 0 && w.crlT == 0)
      Anchors(w);              // 시작 직후 봉 데이터가 늦게 오면 다시 계산
   if(w.done) return;
   datetime t1 = iTime(w.sym, InpLTF, 1);
   double o = iOpen(w.sym, InpLTF, 1), h = iHigh(w.sym, InpLTF, 1);
   double l = iLow(w.sym, InpLTF, 1),  c = iClose(w.sym, InpLTF, 1);
   if(o <= 0 || w.crh <= w.crl) return;
   bool asia = InAsia(t1 + PeriodSeconds(InpLTF));

   // ① 스윕 감지 / 극값 갱신
   if(w.dir == 0)
     {
      if(l < w.crl) { w.dir = 1;  w.ext = l; w.extT = t1; }
      else if(h > w.crh) { w.dir = -1; w.ext = h; w.extT = t1; }
      else return;
      w.mss = TrueMssLevel(w);
      bool dup = AlreadySent(w.sym, "SW", w.h4);
      if(!asia && !dup) w.snap = "스윕 (파란 선 = 4H CRH/CRL, 빨간 점선 = 진짜 MSS 선)";
      if(!asia && !dup)
         Notify(StringFormat("[CRT 비서] %s 4H %s 스윕 (%s) → %s 셋업 감시 시작. 진짜 MSS 선 %s\n%s",
                             w.sym, w.dir == 1 ? "CRL" : "CRH", Px(w.sym, w.ext), w.dir == 1 ? "매수" : "매도", Px(w.sym, w.mss),
                             TrendLine(w.sym, w.dir)));
     }
   else if((w.dir == 1 && l < w.ext) || (w.dir == -1 && h > w.ext))
     {
      w.ext = (w.dir == 1) ? l : h; w.extT = t1;
      w.mss = TrueMssLevel(w);
     }
   if(w.sym == _Symbol && w.mss > 0)
      HLine("VCRT_MSS", w.mss, clrRed, STYLE_DASH, "진짜 MSS 선 (몸통 마감 돌파 대기)");

   // ② 확정: 진짜 MSS 선을 몸통 마감으로 돌파, 종가는 CRT 범위 안
   if(w.mss <= 0) return;
   bool body = (w.dir == 1) ? (c > w.mss && c > o) : (c < w.mss && c < o);
   bool inside = c > w.crl && c < w.crh;
   if(!(body && inside)) return;
   w.done = true;
   if(AlreadySent(w.sym, "CF", w.h4)) return;   // 다시 붙이기 전에 이미 알린 확정
   if(asia)
     {
      Print(w.sym, " MSS 확정됐지만 아시아장이라 알림 생략");
      return;
     }
   // OB: 극값~확정 봉 사이 마지막 반대색 봉, FVG: 같은 구간 가장 최근 갭
   int es = iBarShift(w.sym, InpLTF, w.extT, false);
   double obH = 0, obL = 0, fvB = 0, fvT = 0;
   datetime obT = 0, fvTm = 0;
   // OB = MSS를 깬 하락(매수는 상승) 직전의 마지막 반대색 봉 = 그림의 M (B에서 4로 내려오는 중간)
   for(int k = 2; k <= es && obT == 0; k++)
     {
      double ok = iOpen(w.sym, InpLTF, k), ck = iClose(w.sym, InpLTF, k);
      if(!((w.dir == 1 && ck < ok) || (w.dir == -1 && ck > ok))) continue;
      obH = iHigh(w.sym, InpLTF, k); obL = iLow(w.sym, InpLTF, k); obT = iTime(w.sym, InpLTF, k);
     }
   for(int k = 1; k + 2 <= es && fvTm == 0; k++)
     {
      double hk2 = iHigh(w.sym, InpLTF, k + 2), lk2 = iLow(w.sym, InpLTF, k + 2);
      double hk = iHigh(w.sym, InpLTF, k), lk = iLow(w.sym, InpLTF, k);
      if(w.dir == 1 && hk2 < lk)  { fvB = hk2; fvT = lk; fvTm = iTime(w.sym, InpLTF, k + 2); }
      if(w.dir == -1 && lk2 > hk) { fvB = hk; fvT = lk2; fvTm = iTime(w.sym, InpLTF, k + 2); }
     }
   double sl = w.ext - w.dir * InpSLBufferPips * w.pip;                       // 안전: A(스윕 극값) 너머
   double slT = (obT > 0) ? ((w.dir == 1) ? obL : obH) - w.dir * InpSLBufferPips * w.pip : sl;  // 타이트: OB 너머
   double tp = (w.dir == 1) ? w.crh : w.crl;
   double entry = (obT > 0) ? ((w.dir == 1) ? obH : obL) : c;
   double risk = MathAbs(entry - sl);
   double rr = (risk > 0) ? w.dir * (tp - entry) / risk : 0;
   double lots = SuggestLots(w.sym, risk);
   w.sugSL = sl; w.sugDir = w.dir;
   string msg = StringFormat("[CRT 비서] %s %s 확정! 몸통 마감으로 MSS %s 돌파\n"
                             "OB(M) %s~%s / FVG %s\n지정가 %s · 손절 %s (%.1f핍, 타이트 %s) · 목표 %s (손익비 %.1f)\n추천 랏 %.2f (잔고 %.1f%% 위험)\n%s\n%s",
                             w.sym, w.dir == 1 ? "매수" : "매도", Px(w.sym, w.mss),
                             obT > 0 ? Px(w.sym, obL) : "-", obT > 0 ? Px(w.sym, obH) : "-",
                             fvTm > 0 ? (Px(w.sym, fvB) + "~" + Px(w.sym, fvT)) : "없음",
                             Px(w.sym, entry), Px(w.sym, sl), risk / w.pip, Px(w.sym, slT), Px(w.sym, tp), rr, lots, InpRiskPct,
                             TrendLine(w.sym, w.dir),
                             obT > 0 ? "OB로 되돌아오면 다시 알려 드려요" : "OB를 못 찾았어요. 차트에서 직접 확인해 주세요");
   w.snap = "확정 (노란 박스 = OB, 주황 = 손절, 초록 = 목표)";
   Notify(msg);
   if(obT > 0) { w.stage = 1; w.tdir = w.dir; w.obH = obH; w.obL = obL; w.tp = tp; w.confT = t1; }
   if(w.sym == _Symbol)
     {
      datetime tEnd = TimeCurrent() + 4 * 3600;
      if(obT > 0)  Box("VCRT_OB", obT, obH, tEnd, obL, clrDarkKhaki, "5M OB");
      if(fvTm > 0) Box("VCRT_FVG", fvTm, fvT, tEnd, fvB, clrPlum, "5M FVG");
      HLine("VCRT_SL", sl, clrOrangeRed, STYLE_DOT, "추천 손절");
      HLine("VCRT_TP", tp, clrLimeGreen, STYLE_DOT, "목표 (CRT 반대편)");
     }
  }

//--- 위험 관리 -------------------------------------------------------
ulong    g_failTk[];
datetime g_failT[];

// 같은 티켓의 실패는 처음 한 번만 알리고, 60초 간격으로만 다시 시도
bool CanTry(ulong tk)
  {
   for(int i = 0; i < ArraySize(g_failTk); i++)
      if(g_failTk[i] == tk) return TimeCurrent() - g_failT[i] >= 60;
   return true;
  }
void Failed(ulong tk, string what)
  {
   for(int i = 0; i < ArraySize(g_failTk); i++)
      if(g_failTk[i] == tk) { g_failT[i] = TimeCurrent(); return; }
   int n = ArraySize(g_failTk);
   ArrayResize(g_failTk, n + 1); ArrayResize(g_failT, n + 1);
   g_failTk[n] = tk; g_failT[n] = TimeCurrent();
   Notify(StringFormat("[CRT 비서] ⚠ #%I64u %s 실패 (%u %s). 직접 확인해 주세요!", tk, what, trade.ResultRetcode(), trade.ResultRetcodeDescription()));
  }

string GKey(string k) { return "VCRT_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + k; }

void Guard()
  {
   if(!InpGuard) return;
   datetime now = TimeCurrent();
   datetime day = now - (now % 86400);
   if(day != g_day)
     {
      g_day = day;
      // 재시작해도 같은 날이면 저장된 시작 잔고·잠금을 이어받는다
      if(GlobalVariableCheck(GKey("day")) && (datetime)GlobalVariableGet(GKey("day")) == day)
        {
         g_dayStart = GlobalVariableGet(GKey("start"));
         g_locked   = GlobalVariableGet(GKey("lock")) > 0;
        }
      else
        {
         g_dayStart = AccountInfoDouble(ACCOUNT_BALANCE);
         g_locked   = false;
         GlobalVariableSet(GKey("day"), (double)day);
         GlobalVariableSet(GKey("start"), g_dayStart);
         GlobalVariableSet(GKey("lock"), 0);
        }
     }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(!g_locked && g_dayStart > 0 && eq <= g_dayStart * (1.0 - InpDailyLossPct / 100.0))
     {
      g_locked = true;
      GlobalVariableSet(GKey("lock"), 1);
      Notify(StringFormat("[CRT 비서] 하루 손실 %.1f%% 도달 → 오늘은 잠금. 수동 포지션을 정리해요.", InpDailyLossPct));
     }
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0 || PositionGetInteger(POSITION_MAGIC) != 0) continue;   // 고객님 수동 주문만
      string s = PositionGetString(POSITION_SYMBOL);
      int wi = FindWatch(s);
      if(wi < 0) continue;
      if(g_locked)
        {
         if(CanTry(tk) && !trade.PositionClose(tk)) Failed(tk, "잠금 청산");
         continue;
        }
      int dir = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 1 : -1;
      double open = PositionGetDouble(POSITION_PRICE_OPEN), sl = PositionGetDouble(POSITION_SL);
      double vol = PositionGetDouble(POSITION_VOLUME);
      if(sl == 0)
        {
         double ns = (W[wi].sugDir == dir && W[wi].sugSL > 0 && dir * (open - W[wi].sugSL) > 0)
                     ? W[wi].sugSL : open - dir * InpGuardDefaultSL * W[wi].pip;
         ns = NormalizeDouble(ns, (int)SymbolInfoInteger(s, SYMBOL_DIGITS));
         double px = (dir == 1) ? SymbolInfoDouble(s, SYMBOL_BID) : SymbolInfoDouble(s, SYMBOL_ASK);
         double minDist = (SymbolInfoInteger(s, SYMBOL_TRADE_STOPS_LEVEL) + 2) * SymbolInfoDouble(s, SYMBOL_POINT);
         if(dir * (px - ns) <= minDist)
           {
            // 이미 손절 자리보다 불리하게 움직임 → 걸 수 없으니 알림
            if(CanTry(tk)) Failed(tk, StringFormat("자동 손절 %s (현재가가 이미 넘어감)", Px(s, ns)));
            continue;
           }
         if(!CanTry(tk)) continue;
         if(trade.PositionModify(tk, ns, PositionGetDouble(POSITION_TP)))
            Notify(StringFormat("[CRT 비서] %s 손절이 없어서 %s 에 자동으로 걸었어요", s, Px(s, ns)));
         else
            Failed(tk, "자동 손절");
         continue;   // 다음 틱에 손절 기준으로 랏 점검
        }
      if(dir * (open - sl) <= 0) continue;   // 손절이 본전 이상이면 위험 없음
      double lpl = LossPerLot(s, MathAbs(open - sl));
      if(lpl <= 0 || bal <= 0) continue;
      double riskPct = vol * lpl / bal * 100.0;
      if(riskPct > InpGuardMaxRisk + 0.05)
        {
         double step = SymbolInfoDouble(s, SYMBOL_VOLUME_STEP), mn = SymbolInfoDouble(s, SYMBOL_VOLUME_MIN);
         double keep = MathMax(mn, MathFloor(bal * InpGuardMaxRisk / 100.0 / lpl / step + 1e-9) * step);
         double cut = NormalizeDouble(vol - keep, 2);
         if(cut >= mn && CanTry(tk))
           {
            if(trade.PositionClosePartial(tk, cut))
               Notify(StringFormat("[CRT 비서] %s 위험 %.1f%% > 한도 %.1f%% → %.2f랏 줄여서 %.2f랏만 남겼어요", s, riskPct, InpGuardMaxRisk, cut, keep));
            else
               Failed(tk, "랏 줄이기");
           }
        }
     }
  }

//--- 이벤트 ----------------------------------------------------------
int OnInit()
  {
   string parts[];
   int n = StringSplit(InpSymbols, ',', parts);
   ArrayResize(W, 0);
   for(int i = 0; i < n; i++)
     {
      string s = parts[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(s == "") continue;
      s += InpSuffix;
      if(!SymbolSelect(s, true)) { PrintFormat("[CRT 비서] %s 종목을 찾을 수 없어 건너뜀", s); continue; }
      Watch w;
      w.sym = s;
      int dg = (int)SymbolInfoInteger(s, SYMBOL_DIGITS);
      w.pip = (dg == 3 || dg == 5) ? SymbolInfoDouble(s, SYMBOL_POINT) * 10 : SymbolInfoDouble(s, SYMBOL_POINT);
      w.lastM5 = 0; w.sugSL = 0; w.sugDir = 0; w.stage = 0; w.snap = ""; w.rebuilt = false;
      ResetCycle(w);
      int k = ArraySize(W);
      ArrayResize(W, k + 1);
      W[k] = w;
     }
   if(ArraySize(W) == 0) return INIT_FAILED;
   trade.SetDeviationInPoints(30);
   g_tgChat = InpTgChatId;
   if(g_tgChat == "" && GlobalVariableCheck("VCRT_TGCHAT"))
      g_tgChat = StringFormat("%.0f", GlobalVariableGet("VCRT_TGCHAT"));
   EventSetTimer(10);   // 차트 종목에 틱이 없어도 다른 종목을 감시
   PrintFormat("Venus CRT 비서 시작: %d개 종목 감시, 아시아장(NY %02d~%02d시) 알림 없음", ArraySize(W), InpAsiaStartNY, InpAsiaEndNY);
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, "VCRT_");
  }

// 붙인 직후 한 번: 종목별 지금 상태를 텔레그램으로 보고 (연결 확인 겸)
bool g_hello = false;
void Hello()
  {
   if(g_hello || g_tgChat == "" || InpTgToken == "") return;
   for(int i = 0; i < ArraySize(W); i++)
      if(!W[i].rebuilt) return;
   g_hello = true;
   string m = StringFormat("[CRT 비서] 시작했어요 (v1.43, %s봉). 지금 상태:", StringSubstr(EnumToString(InpLTF), 7));
   for(int i = 0; i < ArraySize(W); i++)
     {
      string st;
      if(W[i].dir == 0)   st = "스윕 없음, 대기";
      else if(W[i].done)  st = StringFormat("%s 셋업 이미 확정됨", W[i].dir == 1 ? "매수" : "매도");
      else                st = StringFormat("%s 셋업, MSS 선 %s 몸통 마감 대기", W[i].dir == 1 ? "매수" : "매도", Px(W[i].sym, W[i].mss));
      m += StringFormat("\n• %s: CRH %s / CRL %s → %s", W[i].sym, Px(W[i].sym, W[i].crh), Px(W[i].sym, W[i].crl), st);
     }
   Print(m);
   TgSend(m);
  }

void Scan()
  {
   for(int i = 0; i < ArraySize(W); i++)
     {
      datetime b = iTime(W[i].sym, InpLTF, 0);
      if(b == 0 || b == W[i].lastM5) continue;
      W[i].lastM5 = b;
      W[i].snap = "";
      OnNewM5(W[i]);
      if(W[i].snap != "") Snap(W[i]);
     }
   Hello();
   Guard();
  }

void OnTick()  { Scan(); }
void OnTimer()
  {
   static datetime lastTry = 0;
   if(g_tgChat == "" && InpTgToken != "" && TimeLocal() - lastTry >= 30) { lastTry = TimeLocal(); TgFindChat(); }
   Scan();
  }
//+------------------------------------------------------------------+
