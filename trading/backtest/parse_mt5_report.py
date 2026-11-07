"""MT5 전략 테스터 보고서(.htm)를 읽어 거래별 R, IS/OOS 성적, 합격 여부를 계산한다.

사용: python parse_mt5_report.py <보고서.htm> [--risk-pct 1.0] [--oos-start 2024-01-01]

- 보고서의 '거래(Deals)' 표에서 종목이 있는 행만 쓴다(입금 행 제외).
- 진입 거래의 수수료는 다음 청산 거래에 합친다.
- R = 거래 손익 ÷ (진입 직전 잔고 × risk_pct%). EA를 잔고 % 위험으로 돌렸을 때 의미가 있다.
- 보고서에 수수료가 하나도 없으면 IC마켓 Raw 기준 랏당 왕복 $7을 직접 빼고 그 사실을 표시한다.
"""
import argparse
import html
import re
import sys
from datetime import datetime

DT = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}(:\d{2})?$")


def read_text(path):
    raw = open(path, "rb").read()
    for enc in ("utf-16", "utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue
    return raw.decode("latin-1")


def num(s):
    s = s.replace("\xa0", "").replace(" ", "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def deal_rows(text):
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S | re.I):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)]
        if len(cells) >= 13 and DT.match(cells[0]):
            rows.append(cells)
    return rows


def parse_trades(rows):
    """[time, deal, symbol, type, direction, volume, price, order, commission, swap, profit, balance, comment]"""
    trades, pend_comm, pend_vol, any_comm = [], 0.0, 0.0, False
    for c in rows:
        if not c[2]:
            continue  # 입금 등 종목 없는 행
        direction = c[4].lower()
        comm, swap, profit = num(c[8]) or 0.0, num(c[9]) or 0.0, num(c[10]) or 0.0
        vol, bal = num(c[5]) or 0.0, num(c[11])
        any_comm |= comm != 0
        is_out = "out" in direction or "청산" in direction or "아웃" in direction
        is_in = not is_out and ("in" in direction or "진입" in direction or profit == 0)
        if is_in:
            pend_comm += comm
            pend_vol += vol
            continue
        pnl = profit + swap + comm + pend_comm
        trades.append(dict(time=datetime.strptime(c[0][:16], "%Y.%m.%d %H:%M"), pnl=pnl,
                           balance_after=bal, volume=pend_vol or vol))
        pend_comm, pend_vol = 0.0, 0.0
    return trades, any_comm


def stats(ts, label, risk_pct):
    if not ts:
        return {"label": label, "trades": 0}
    rs = [t["r"] for t in ts]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    eq, peak, dd, streak, worst = 0.0, 0.0, 0.0, 0, 0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
        streak = streak + 1 if r <= 0 else 0
        worst = max(worst, streak)
    halves = {}
    for t in ts:
        k = f"{t['time'].year}H{1 if t['time'].month <= 6 else 2}"
        halves[k] = halves.get(k, 0.0) + t["r"]
    gross_loss = -sum(losses)
    return {
        "label": label, "trades": len(rs), "win_rate": round(100 * len(wins) / len(rs), 1),
        "total_R": round(sum(rs), 2), "PF": round(sum(wins) / gross_loss, 3) if gross_loss else float("inf"),
        "avg_R": round(sum(rs) / len(rs), 3), "max_dd_R": round(dd, 2), "longest_losing_streak": worst,
        "net_usd": round(sum(t["pnl"] for t in ts), 2),
        "per_half_year_R": {k: round(v, 2) for k, v in sorted(halves.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--risk-pct", type=float, default=1.0)
    ap.add_argument("--oos-start", default="2024-01-01")
    ap.add_argument("--commission-per-lot", type=float, default=7.0,
                    help="보고서에 수수료가 없을 때 뺄 랏당 왕복 수수료. Standard 계좌(수수료 없음)는 0")
    a = ap.parse_args()

    trades, any_comm = parse_trades(deal_rows(read_text(a.report)))
    if not trades:
        sys.exit("보고서에서 거래를 찾지 못했어요. 보고서 파일을 비너스에게 보내 주세요.")
    if not any_comm and a.commission_per_lot > 0:
        print(f"주의: 보고서에 수수료가 없어서 랏당 왕복 ${a.commission_per_lot:g}을 직접 뺐어요.")
        for t in trades:
            t["pnl"] -= a.commission_per_lot * t["volume"]
            t["balance_after"] = None
    bal = None
    for t in trades:
        # 진입 직전 잔고 = 청산 후 잔고 - 이번 손익 (수수료를 직접 뺀 경우는 누적으로 계산)
        before = (t["balance_after"] - t["pnl"]) if t["balance_after"] is not None else bal
        if before is None:
            before = 10000.0
        t["r"] = t["pnl"] / (before * a.risk_pct / 100.0)
        bal = before + t["pnl"]

    oos = datetime.fromisoformat(a.oos_start)
    groups = [("전체", trades), ("IS (~2023)", [t for t in trades if t["time"] < oos]),
              ("OOS (2024~)", [t for t in trades if t["time"] >= oos])]
    for label, ts in groups:
        s = stats(ts, label, a.risk_pct)
        print(f"\n=== {label} ===")
        for k, v in s.items():
            if k == "per_half_year_R":
                print("  per_half_year_R: " + ", ".join(f"{h} {r:+.1f}" for h, r in v.items()))
            elif k != "label":
                print(f"  {k}: {v}")
    so = stats(groups[2][1], "OOS", a.risk_pct)
    so.setdefault("PF", 0.0)
    so.setdefault("max_dd_R", 0.0)
    ok = so["trades"] >= 60 and so["PF"] >= 1.2 and so["max_dd_R"] <= 10
    why = [] if ok else [m for m, bad in [
        (f"거래 {so['trades']} < 60", so["trades"] < 60),
        (f"PF {so.get('PF')} < 1.2", so["trades"] and so["PF"] < 1.2),
        (f"최대낙폭 {so.get('max_dd_R')}R > 10R", so["trades"] and so["max_dd_R"] > 10)] if bad]
    print(f"\nOOS 판정: {'합격' if ok else '불합격'} " + ("" if ok else "-- " + "; ".join(why)))


if __name__ == "__main__":
    main()
