import json,sys
X=float(sys.argv[1]) if len(sys.argv)>1 else 0.07   # 부분 매도 % (고점 대비)
TR=json.loads(sys.argv[2]) if len(sys.argv)>2 else None  # 시험 결과 행
d=json.load(open("qqq.json"))
CUR,BUY,SELL,QLD0=656.10,687.07,673.50,74.11
DATE="2026-11-06(목) 미국 정규장 종가"
QLDB=QLD0*(1+2*(BUY/CUR-1)); qb=lambda p:QLDB*(1+2*(p/BUY-1)); QLDS=qb(SELL)
pcts=[20,15,12.5,10,7.5,5,"B",None,0,-5,-10,-15]
lv=[]
for s in pcts:
    if s=="B": p,lab=BUY,f"+{(BUY/CUR-1)*100:.1f}%"
    elif s is None: p,lab=SELL,f"+{(SELL/CUR-1)*100:.1f}%"
    else: p,lab=CUR*(1+s/100),("+" if s>0 else "")+(f"{s:g}%" if s else "0%")
    lv.append((lab,round(p,2)))
def man(v,sign=True): return ("+" if v>0 and sign else ("−" if v<0 else ""))+f"{abs(v):,.0f}만원"
def table(A):
    out=[];prev=None
    for i,(lab,p) in enumerate(lv):
        nxt=lv[i+1][1] if i+1<len(lv) else None
        dcur=p-CUR; dstep=(p-nxt) if nxt else None
        held=p>=BUY-0.01
        if held:
            q=qb(p);val=A*q/QLDB;pl=val-A;rt=pl/A*100
            act="QLD 사기" if abs(p-BUY)<0.01 else "QLD 들고 있기"
            ps=p*(1-X)
            if ps>SELL+0.01:
                qh=qb(ps);plh=A/2*(qh/QLDB-1)
                part=f"QQQ {ps:.2f} 밑 마감 → 절반({A/2:,.0f}만원어치) 매도 · 그 절반 손익 {man(plh)}"
            else: part="부분 매도 없이 아래 전량 매도선"
            full=f"QQQ {SELL:.2f} 밑 마감 → 전량 매도 · 손익 {man(A*(QLDS/QLDB-1))}" if not (ps>SELL+0.01) else f"QQQ {SELL:.2f} 밑 마감 → 나머지 전량 매도 · 그 절반 손익 {man(A/2*(QLDS/QLDB-1))}"
            out.append(dict(lab=lab,p=p,dcur=dcur,dstep=dstep,act=act,q=q,val=val,pl=pl,rt=rt,part=part,full=full,cls="hit" if act=="QLD 사기" else ""))
        else:
            q=QLD0*(1+2*(p/CUR-1))
            out.append(dict(lab=lab,p=p,dcur=dcur,dstep=dstep,act="기다리기",q=q,val=A,pl=0,rt=0,part="—",full="—",cls="now" if abs(p-CUR)<0.01 else ""))
    return out

def pc(p): return f"{(p/CUR-1)*100:+.1f}%"
def rows_html(t,A):
    h=""
    for r in t:
        p=r["p"]
        if r["act"]=="기다리기":
            h+=f'<div class="lv wait {r["cls"]}"><div class="lvh"><b>QQQ {p:.2f}</b><span>{pc(p)} · 지금보다 {r["dcur"]:+.2f}달러</span><em>기다리기 · 현금 1,000만원</em></div></div>'
            continue
        ps=p*(1-X); half=ps>SELL+0.01
        buy=f'QQQ {BUY:.2f} <small>({pc(BUY)})</small><br>QLD {QLDB:.2f}에 {A:,.0f}만원'
        if half:
            keep=f'QQQ {ps:.2f} ~ {p:.2f} <small>({pc(ps)} ~ {pc(p)})</small><br>QLD 평가 {r["val"]:,.0f}만원 · 손익 {man(r["pl"])} ({r["rt"]:+.1f}%)'
            plh=A/2*(qb(ps)/QLDB-1); plf=A/2*(QLDS/QLDB-1)
            sell=f'① QQQ {ps:.2f} 밑 <small>({pc(ps)}, 고점 −{X*100:g}%)</small> → 절반 매도 {man(plh)}<br>② QQQ {SELL:.2f} 밑 <small>({pc(SELL)})</small> → 나머지 매도 {man(plf)}'
        else:
            keep=f'QQQ {SELL:.2f} ~ {p:.2f} <small>({pc(SELL)} ~ {pc(p)})</small><br>QLD 평가 {r["val"]:,.0f}만원 · 손익 {man(r["pl"])} ({r["rt"]:+.1f}%)'
            sell=f'QQQ {SELL:.2f} 밑 <small>({pc(SELL)})</small> → 전량 매도 {man(A*(QLDS/QLDB-1))}'
        h+=f'<div class="lv {r["cls"]}"><div class="lvh"><b>QQQ {p:.2f}</b><span>{pc(p)} · 지금보다 {r["dcur"]:+.2f}달러 · QLD 약 {r["q"]:.2f}</span><em>{r["act"]}</em></div><div class="lvb"><div class="bx b"><i>매수</i>{buy}</div><div class="bx k"><i>유지</i>{keep}</div><div class="bx s"><i>매도</i>{sell}</div></div></div>'
    return h
t5,t10=table(500),table(1000)
head='<thead><tr><th>QQQ 변동<br>(종가 대비)</th><th>QQQ 가격</th><th>지금보다<br>(달러)</th><th>아래 칸보다<br>(달러)</th><th>할 일</th><th>QLD 예상가</th><th>QLD 평가금액</th><th>손익</th><th>수익률</th><th>여기서 꺾이면 ① 부분 매도</th><th>② 전량 매도</th></tr></thead>'
# chart data
xs=[round(CUR*(1+k/1000),2) for k in range(-150,201,5)]
def acct(A,p): return A if p<BUY else round(A*qb(p)/QLDB,1)
data=dict(x=xs,a500=[acct(500,p)+500 if False else (500+ (acct(500,p)-500)) for p in xs],a1000=[acct(1000,p) for p in xs])
data["a500"]=[ (1000 if p<BUY else 500+acct(500,p)) for p in xs]   # 1,000만원 중 500만원 투자 시 계좌 총액
data["a1000"]=[ (1000 if p<BUY else acct(1000,p)) for p in xs]
QLDD=json.load(open("qld.json"))
qqq=dict(d=[x[0][5:] for x in d],c=[x[1] for x in d],q=[QLDD.get(x[0][5:]) for x in d])
tr_rows=""
if TR:
    for r in TR: tr_rows+="<tr>"+"".join(f"<td>{c}</td>" for c in r)+"</tr>"
norm=json.load(open('norm.json'))
blend=json.load(open('blend.json'))
J=json.dumps(dict(blend=blend,norm=norm,daily=json.load(open('daily2.json')),chart=data,qqq=qqq,BUY=BUY,SELL=SELL,CUR=CUR,X=X,QLDB=QLDB,QLD0=QLD0))
tpl=open("tpl2.html",encoding="utf-8").read()
out=(tpl.replace("%%DATE%%",DATE).replace("%%HEAD%%",head).replace("%%T5%%",rows_html(t5,500)).replace("%%T10%%",rows_html(t10,1000))
 .replace("%%J%%",J).replace("%%XP%%",f"{X*100:g}").replace("%%QLDB%%",f"{QLDB:.2f}").replace("%%QLDS%%",f"{QLDS:.2f}")
 .replace("%%L5%%",man(500*(QLDS/QLDB-1))).replace("%%L10%%",man(1000*(QLDS/QLDB-1))).replace("%%TR%%",tr_rows))
open("index.html","w",encoding="utf-8").write(out);print("ok")
