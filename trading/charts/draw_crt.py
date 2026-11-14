"""CRT A+ 예시 차트 그리기: python draw_crt.py <zip> <C2 서버시각> <방향 1/-1> <출력.png>"""
import sys, logging
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from zoneinfo import ZoneInfo
sys.path.insert(0, "../research")
from crt_examples import load, trace, P
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
plt.rcParams["font.family"] = "WenQuanYi Zen Hei"; plt.rcParams["axes.unicode_minus"] = False

zp, t2s, d, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
m = load(zp)
t2 = pd.Timestamp(t2s); t1 = t2 - pd.Timedelta(hours=4)
c1w = m.loc[t1:t2 - pd.Timedelta(minutes=15)]
c1 = pd.Series(dict(high=c1w.high.max(), low=c1w.low.min()))
s = trace(m, t1, t2, d, c1)
w = m.loc[t1:t2 + pd.Timedelta(hours=8) - pd.Timedelta(minutes=15)]
ny = (w.index - pd.Timedelta(hours=7)).tz_localize(ZoneInfo("America/New_York"))
kst = ny.tz_convert(ZoneInfo("Asia/Seoul")).tz_localize(None)
o, h, l, c = w.open.values, w.high.values, w.low.values, w.close.values
fig, ax = plt.subplots(figsize=(10, 7.4), dpi=130)
for i in range(len(w)):
    col = "#16a34a" if c[i] >= o[i] else "#dc2626"
    ax.vlines(i, l[i], h[i], color=col, lw=1)
    ax.add_patch(plt.Rectangle((i - 0.32, min(o[i], c[i])), 0.64, max(abs(c[i] - o[i]), P * 0.15), color=col))
n1, n2 = s["n1"], s["n2"]
ax.axvspan(-0.5, n1 - 0.5, color="#93c5fd", alpha=0.18)
ax.axvspan(n1 - 0.5, n2 - 0.5, color="#fde68a", alpha=0.25)
H, L = c1.high, c1.low
top = max(h.max(), s["tp"]) + 8 * P; bot = min(l.min(), s["sl"]) - 6 * P
ax.text(0.5, top - 2 * P, "① C1 (기준 4시간봉)", color="#1d4ed8", fontsize=11, va="top")
ax.text(n1 + 0.5, top - 2 * P, "② C2 (다음 4시간봉, 런던 킬존)", color="#a16207", fontsize=11, va="top")
ax.text(n2 + 0.5, top - 2 * P, "C3", color="#555", fontsize=11, va="top")
for y, n in [(H, "C1 고점"), (L, "C1 저점")]:
    ax.hlines(y, -0.5, len(w) - 0.5, colors="#1d4ed8", linestyles="--", lw=1.3)
    ax.text(len(w) - 0.3, y, f" {n} {y:.4f}", color="#1d4ed8", va="center", fontsize=9)
ws, sh, mss, ei = s["ws"], s["sh"], s["mss"], s["ei"]
ext = l[ws] if d == 1 else h[ws]
ax.annotate(f"③ 스윕: C1 {'저점' if d == 1 else '고점'}을 찌르고\n   범위 안으로 마감", xy=(ws, ext),
            xytext=(ws + 3, ext - d * 9 * P), fontsize=10, color="#b91c1c", arrowprops=dict(arrowstyle="->", color="#b91c1c", lw=1.5))
lvl = h[sh] if d == 1 else l[sh]
ax.hlines(lvl, sh - 0.5, mss + 0.5, colors="#9333ea", lw=1.6)
ax.annotate("④ MSS: 직전 고점을 종가로 돌파" if d == 1 else "④ MSS: 직전 저점을 종가로 돌파", xy=(mss, c[mss]),
            xytext=(max(mss - 16, 1), c[mss] + d * 8 * P), fontsize=10, color="#9333ea", arrowprops=dict(arrowstyle="->", color="#9333ea", lw=1.5))
fk, f1, f2 = s["fvg"]
ax.add_patch(plt.Rectangle((fk - 2.5, min(f1, f2)), ei - fk + 4, abs(f2 - f1), color="#a855f7", alpha=0.25))
ax.text(fk - 9, (f1 + f2) / 2, "⑤ FVG →", color="#7e22ce", fontsize=10, va="center")
ax.scatter([ei], [s["entry"]], s=140, marker="^" if d == 1 else "v", color="black", zorder=5)
ax.annotate(f"⑥ FVG 되돌림 {'매수' if d == 1 else '매도'} {s['entry']:.4f}", xy=(ei, s["entry"]),
            xytext=(ei - 22, s["entry"] - d * 8 * P), fontsize=10.5, fontweight="bold", arrowprops=dict(arrowstyle="-", lw=0.8))
risk = abs(s["entry"] - s["sl"])
ax.hlines(s["sl"], ei - 0.5, len(w) - 0.5, colors="#dc2626", lw=1.3)
ax.text(len(w) - 12, s["sl"], f"손절 {s['sl']:.4f} ({risk / P:.1f}핍)", color="#dc2626", fontsize=9, va="top" if d == 1 else "bottom")
ax.text(ei - 12, s["tp"] + d * 1 * P, f"⑦ 목표 = C1 {'고점' if d == 1 else '저점'} ({abs(s['tp'] - s['entry']) / P:.1f}핍, 손익비 {s['rr']:.1f})",
        color="#15803d", fontsize=9.5, fontweight="bold", va="bottom" if d == 1 else "top")
ticks = [i for i, k in enumerate(kst) if k.minute == 0 and k.hour % 2 == 0]
ax.set_xticks(ticks); ax.set_xticklabels([kst[i].strftime("%H:%M") for i in ticks], fontsize=9)
ax.set_xlim(-1, len(w) + 10); ax.set_ylim(bot, top); ax.grid(alpha=0.2)
ax.set_title(f"[SMC+CRT A+ 예시] {kst[0]:%Y년 %m월 %d일} EURUSD · 4시간봉 CRT + 15분봉 MSS·FVG", fontsize=12, fontweight="bold", loc="left")
ax.text(0.99, 0.03, "A+ 체크리스트\n① C1 범위\n② C2가 킬존에서 스윕\n③ 범위 안으로 마감\n④ 15분봉 MSS\n⑤ FVG 생성\n⑥ FVG 되돌림 진입\n⑦ 목표 C1 반대편\n" + f"결과: {s['res']} 도달",
        transform=ax.transAxes, fontsize=9.5, ha="right", va="bottom", bbox=dict(boxstyle="round", fc="white", ec="#999", alpha=0.95))
ax.set_xlabel("한국 시간 · EURUSD 15분봉 · IC마켓 실제 가격")
fig.tight_layout(); fig.savefig(out); plt.close(fig)
print(s["res"], round(s["rr"], 2), kst[ei], round(s["entry"], 5), round(s["sl"], 5), round(s["tp"], 5))
