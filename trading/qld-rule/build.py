import json
d=json.load(open("qqq.json"))
CUR,BUY,SELL,QLD0=656.10,687.07,673.50,74.11
QLDB=QLD0*(1+2*(BUY/CUR-1))
qb=lambda p:QLDB*(1+2*(p/BUY-1))
QLDS=qb(SELL); L50=500*(QLDS/QLDB-1); L100=1000*(QLDS/QLDB-1)
steps=[-15,-10,-5,0,None,"B",5,7.5,10,12.5,15,20]
rows=[]
for s in steps:
    if s is None: p=SELL;lab=f"+{(SELL/CUR-1)*100:.1f}%"
    elif s=="B": p=BUY;lab=f"+{(BUY/CUR-1)*100:.1f}%"
    else: p=CUR*(1+s/100);lab=("+" if s>0 else "")+f"{s:g}%" if s else "0% (지금)"
    if p<BUY-0.01:
        q=QLD0*(1+2*(p/CUR-1));act="기다리기";buy="0 (현금)";a50=a100=None
    else:
        q=qb(p);a50=500*(q/QLDB-1);a100=1000*(q/QLDB-1)
        act="QLD 사기" if s=="B" else "QLD 들고 있기";buy="500 / 1,000만원"
    rows.append((lab,p,act,q,buy,a50,a100))
def won(v):
    if v is None: return "—"
    return ("+" if v>0 else ("−" if v<0 else ""))+f"{abs(v):,.0f}만원"
trs="".join(f'<tr class="{"hit" if r[2]=="QLD 사기" else ("now" if "지금" in r[0] else "")}"><td>{r[0]}</td><td>{r[1]:.2f}</td><td class="act">{r[2]}</td><td>{r[3]:.2f}</td><td>{r[4]}</td><td>{won(r[5])}</td><td>{won(r[6])}</td></tr>' for r in rows[::-1])
# chart1: x=QQQ price, y=계좌 손익(만원)
W,H,Lm,Rm,T,B=720,320,56,20,16,40
xs=[r[1] for r in rows];x0,x1=min(xs)-5,max(xs)+5
y0,y1=-60,300
X=lambda v:Lm+(v-x0)/(x1-x0)*(W-Lm-Rm);Y=lambda v:T+(y1-v)/(y1-y0)*(H-T-B)
held=[r for r in rows if r[5] is not None]
l50=" ".join(f"{X(r[1]):.1f},{Y(r[5]):.1f}" for r in held);l100=" ".join(f"{X(r[1]):.1f},{Y(r[6]):.1f}" for r in held)
grid="".join(f'<line x1="{Lm}" x2="{W-Rm}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="g"/><text x="{Lm-6}" y="{Y(v)+4:.1f}" class="ax" text-anchor="end">{v:+d}</text>' for v in range(-50,301,50))
xt="".join(f'<line x1="{X(p):.1f}" x2="{X(p):.1f}" y1="{T}" y2="{H-B}" class="g"/><text x="{X(p):.1f}" y="{H-B+16}" class="ax" text-anchor="middle">{p}</text>' for p in range(560,801,40))
c1=f'''<svg viewBox="0 0 {W} {H}" role="img" aria-label="QQQ 가격별 계좌 손익">{grid}{xt}
<line x1="{X(CUR):.1f}" x2="{X(CUR):.1f}" y1="{T}" y2="{H-B}" class="cur"/><text x="{X(CUR)-4:.1f}" y="{H-B-6}" class="lb curt" text-anchor="end">지금 656</text>
<line x1="{X(SELL):.1f}" x2="{X(SELL):.1f}" y1="{T}" y2="{H-B}" class="sell"/><text x="{X(SELL)-4:.1f}" y="{T+12}" class="lb sellt" text-anchor="end">팔기 674</text>
<line x1="{X(BUY):.1f}" x2="{X(BUY):.1f}" y1="{T}" y2="{H-B}" class="buy"/><text x="{X(BUY)+4:.1f}" y="{T+12}" class="lb buyt">사기 687</text>
<line x1="{X(x0):.1f}" x2="{X(BUY):.1f}" y1="{Y(0):.1f}" y2="{Y(0):.1f}" class="flat"/>
<polyline points="{l100}" class="p100"/><polyline points="{l50}" class="p50"/>
<circle cx="{X(SELL):.1f}" cy="{Y(L100):.1f}" r="4" class="lossdot"/><circle cx="{X(SELL):.1f}" cy="{Y(L50):.1f}" r="4" class="lossdot"/>
<text x="{X(SELL)+6:.1f}" y="{Y(L100)+14:.1f}" class="lb sellt">손절 시 −{abs(L50):.0f}만원 / −{abs(L100):.0f}만원</text>
<text x="{W/2:.0f}" y="{H-4}" class="ax" text-anchor="middle">QQQ 종가(달러)</text>
</svg>'''
# chart2: 10년 뒤 1,000만원
res=[("이 규칙 (QLD만)",5506,1424),("나스닥100만",3675,444),("QLD 그냥 들고 있기",4450,42)]
W2,H2,L2=720,230,150;mx=6000
bw=lambda v:(W2-L2-60)*v/mx
bars=""
for i,(n,med,worst) in enumerate(res):
    y=20+i*68
    bars+=f'<text x="{L2-8}" y="{y+22}" class="lbl" text-anchor="end">{n}</text>'
    bars+=f'<rect x="{L2}" y="{y}" width="{bw(med):.1f}" height="22" class="bmed"/><text x="{L2+bw(med)+6:.1f}" y="{y+16}" class="lb">중간 {med:,}만원</text>'
    bars+=f'<rect x="{L2}" y="{y+26}" width="{max(2,bw(worst)):.1f}" height="22" class="bwor"/><text x="{L2+max(2,bw(worst))+6:.1f}" y="{y+42}" class="lb">최악 {worst:,}만원</text>'
bars+=f'<line x1="{L2+bw(1000):.1f}" x2="{L2+bw(1000):.1f}" y1="10" y2="{H2-10}" class="base"/><text x="{L2+bw(1000)+4:.1f}" y="{H2-6}" class="ax">원금 1,000만원</text>'
c2=f'<svg viewBox="0 0 {W2} {H2}" role="img" aria-label="10년 뒤 1,000만원이 얼마가 되었나">{bars}</svg>'
# chart3: 3개월 QQQ
W3,H3,L3,R3,T3,B3=720,260,44,96,14,28
vals=[c for _,c in d]+[BUY,SELL];lo,hi=min(vals)-6,max(vals)+6
X3=lambda i:L3+i*(W3-L3-R3)/(len(d)-1);Y3=lambda v:T3+(hi-v)/(hi-lo)*(H3-T3-B3)
pts=" ".join(f"{X3(i):.1f},{Y3(c):.1f}" for i,(_,c) in enumerate(d))
g3="".join(f'<line x1="{L3}" x2="{W3-R3}" y1="{Y3(v):.1f}" y2="{Y3(v):.1f}" class="g"/><text x="{L3-6}" y="{Y3(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>' for v in range(660,761,20))
t3="".join(f'<text x="{X3(i):.1f}" y="{H3-8}" class="ax" text-anchor="middle">{d[i][0][5:].replace("-","/")}</text>' for i in range(0,len(d),15))
c3=f'''<svg viewBox="0 0 {W3} {H3}" role="img" aria-label="QQQ 최근 3개월 종가">{g3}{t3}
<line x1="{L3}" x2="{W3-R3}" y1="{Y3(BUY):.1f}" y2="{Y3(BUY):.1f}" class="buy"/><text x="{W3-R3+6}" y="{Y3(BUY)+4:.1f}" class="lb buyt">사기 687</text>
<line x1="{L3}" x2="{W3-R3}" y1="{Y3(SELL):.1f}" y2="{Y3(SELL):.1f}" class="sell"/><text x="{W3-R3+6}" y="{Y3(SELL)+4:.1f}" class="lb sellt">팔기 674</text>
<polyline points="{pts}" class="px"/><circle cx="{X3(len(d)-1):.1f}" cy="{Y3(CUR):.1f}" r="5" class="dot"/><text x="{W3-R3+6}" y="{Y3(CUR)+4:.1f}" class="lb curt">지금 656</text></svg>'''
page=f'''<title>QLD 매수 판정</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap">
<style>
/* 방향: 가격표(시나리오) 중심 판정서. 1,000만원 기준, 11/6 종가 */
:root{{--bg:#f4f5f2;--paper:#fff;--ink:#1b211d;--muted:#5f6a63;--rule:#d8ddd6;--buy:#1f7a4d;--sell:#b3322a;--wait:#8a6a12;--line:#2e5aa8;--hl:#e6f3ec;--now:#f6eed4;
--sans:"IBM Plex Sans KR",system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#121614;--paper:#1a1f1c;--ink:#e6ebe7;--muted:#9ba69f;--rule:#2d3530;--buy:#6fd39c;--sell:#f2877d;--wait:#e3c062;--line:#8fb3ff;--hl:#173021;--now:#33290f;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#121614;--paper:#1a1f1c;--ink:#e6ebe7;--muted:#9ba69f;--rule:#2d3530;--buy:#6fd39c;--sell:#f2877d;--wait:#e3c062;--line:#8fb3ff;--hl:#173021;--now:#33290f;color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.6}}
.wrap{{max-width:820px;margin:0 auto;padding-block:20px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:22px}}
.wrap>*{{min-width:0}} .kicker{{font-size:.8rem;color:var(--muted)}} h2{{font-size:1.02rem;margin:0 0 8px}}
.verdict{{background:var(--paper);border:1px solid var(--rule);border-radius:8px;padding:18px;display:grid;gap:4px}}
.verdict .big{{font-size:2.2rem;font-weight:700;color:var(--wait);line-height:1.15}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}}
.card{{background:var(--paper);border:1px solid var(--rule);border-radius:8px;padding:12px}} .card b{{display:block;font-family:var(--mono);font-size:1.25rem}}
.card.buy b{{color:var(--buy)}} .card.sell b{{color:var(--sell)}}
.tbl{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:.88rem;background:var(--paper);min-width:640px}}
td,th{{border:1px solid var(--rule);padding:7px 8px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}} td:nth-child(3),td:nth-child(5),th:nth-child(3),th:nth-child(5){{text-align:left;white-space:normal}}
th{{color:var(--muted);font-weight:600;font-size:.8rem}} tr.hit td{{background:var(--hl);font-weight:700}} tr.now td{{background:var(--now)}}
td.act{{font-weight:600}}
.chart{{background:var(--paper);border:1px solid var(--rule);border-radius:8px;padding:8px;overflow-x:auto}} svg{{width:100%;min-width:560px;height:auto;display:block}}
.g{{stroke:var(--rule)}} .ax{{fill:var(--muted);font-size:11px;font-family:var(--mono)}} .lb{{font-size:12px;font-weight:600;font-family:var(--mono);fill:var(--ink)}} .lbl{{font-size:13px;fill:var(--ink)}}
.buy{{stroke:var(--buy);stroke-width:1.6;stroke-dasharray:6 4}} .sell{{stroke:var(--sell);stroke-width:1.6;stroke-dasharray:6 4}} .cur{{stroke:var(--wait);stroke-width:1.4}}
.buyt{{fill:var(--buy)}} .sellt{{fill:var(--sell)}} .curt{{fill:var(--wait)}}
.p100{{fill:none;stroke:var(--buy);stroke-width:2.6}} .p50{{fill:none;stroke:var(--line);stroke-width:2.6}} .flat{{stroke:var(--muted);stroke-width:2}} .lossdot{{fill:var(--sell)}}
.px{{fill:none;stroke:var(--line);stroke-width:2}} .dot{{fill:var(--wait)}}
.bmed{{fill:var(--buy)}} .bwor{{fill:var(--sell);opacity:.8}} .base{{stroke:var(--muted);stroke-dasharray:3 3}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:.82rem;color:var(--muted)}} .legend i{{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:6px}}
.neg{{color:var(--sell)}} .foot{{font-size:.8rem;color:var(--muted)}}
</style>
<div class="wrap">
  <div class="kicker">QLD 매수 판정 · 11월 6일(목) QQQ 종가 656.10달러 기준 · 전체 금액 1,000만원</div>
  <section class="verdict"><div class="kicker">지금 할 일</div><div class="big">기다리기 · 현금 1,000만원</div>
    <div>QQQ가 <b>687.07달러</b>(지금보다 +4.7%) 넘게 끝난 다음 날 QLD를 사요.</div></section>
  <div class="cards">
    <div class="card buy"><span class="kicker">QLD 사기</span><b>QQQ 687.07</b>QLD 약 {QLDB:.2f}</div>
    <div class="card sell"><span class="kicker">QLD 팔기 (산 뒤)</span><b>QQQ 673.50</b>QLD 약 {QLDS:.2f}</div>
    <div class="card"><span class="kicker">살 금액</span><b>500만원</b>최근 20일 QQQ 하루 평균 움직임 9.9달러 넘으면 50% · 이하면 1,000만원(100%) · 11/6 기준 10.5달러 → 50%</div>
    <div class="card"><span class="kicker">한 번 사서 손절하면</span><b class="neg">−{abs(L50):.0f}만원</b>500만원 샀을 때 (1,000만원이면 −{abs(L100):.0f}만원)</div>
  </div>
  <section><h2>QQQ 오르내림별 할 일과 손익 (1,000만원 기준)</h2>
    <div class="tbl"><table><thead><tr><th>QQQ 변동</th><th>QQQ 가격</th><th>할 일</th><th>QLD 예상가</th><th>QLD에 넣는 돈</th><th>손익 (500만원 샀을 때)</th><th>손익 (1,000만원 샀을 때)</th></tr></thead><tbody>{trs}</tbody></table></div>
    <p class="foot">위로 갈수록 QQQ가 올랐을 때예요. 손익은 687.07달러에서 산 뒤 그 가격이 되었을 때 기준이에요. QLD 예상가는 "QQQ 변동의 2배" 근사치라 실제와 조금 다를 수 있어요.</p></section>
  <section><h2>QQQ 가격별 계좌 손익 그래프</h2>
    <div class="chart">{c1}</div>
    <div class="legend"><span><i style="background:var(--line)"></i>500만원 샀을 때</span><span><i style="background:var(--buy)"></i>1,000만원 샀을 때</span><span><i style="background:var(--muted)"></i>사기 전(현금, 손익 0)</span></div></section>
  <section><h2>10년 동안 했다면 1,000만원이 얼마가 되었나 (과거 1986~2026)</h2>
    <div class="chart">{c2}</div>
    <p class="foot">시작 날짜를 바꿔 가며 10년씩 362번 계산한 중간값과 가장 나빴던 경우예요. QLD가 생기기 전 기간은 나스닥100 자료로 2배를 계산했어요(배당 제외). 이 규칙도 중간에 계좌가 가장 크게 줄어든 폭은 −52%였어요.</p></section>
  <section><h2>QQQ 최근 3개월과 사기·팔기 가격</h2><div class="chart">{c3}</div>
    <p class="foot">자료: Alpha Vantage QQQ 일별 종가. 사기·팔기 가격은 나스닥100 200일선에서 나와서 매일 조금씩 바뀌어요. 차트 페이지 QLD 탭에 매일 새 값이 나와요.</p></section>
</div>'''
open("index.html","w",encoding="utf-8").write(page)
