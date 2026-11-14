for f in ('data.py','inv_data.py','gang_data.py','jang_data.py'): exec(open(f,encoding='utf-8').read())
from openpyxl import Workbook
from openpyxl.styles import Font,Border,Side,PatternFill
from collections import defaultdict
thin=Side(style="thin",color="999999");B=Border(left=thin,right=thin,top=thin,bottom=thin)
H=PatternFill("solid",fgColor="DDE7F0");Y=PatternFill("solid",fgColor="FFF2CC")
where=defaultdict(list);allrows=[]
for p in J:
    for side,lab in (("left","왼"),("right","오")):
        for i,r in enumerate(J[p][side],1):
            allrows.append([p,lab,i,*r]);where[r[0]].append(f"{p} {lab}{i}")
wb=Workbook();ws=wb.active;ws.title="전체"
ws.append(["장","칸","줄","용기번호","용도","위치","확인 필요"])
for c in ws[1]: c.font=Font(bold=True);c.fill=H;c.border=B
for r in allrows:
    ws.append(r)
    for c in ws[ws.max_row]: c.border=B
    if r[6]: ws.cell(ws.max_row,7).fill=Y
for col,w in zip("ABCDEFG",(6,5,5,11,11,10,34)): ws.column_dimensions[col].width=w
ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:G{ws.max_row}"
s=wb.create_sheet("장별 요약");s.append(["장","왼쪽","오른쪽","합계"])
for c in s[1]: c.font=Font(bold=True);c.fill=H
for p in J: s.append([p,len(J[p]["left"]),len(J[p]["right"]),len(J[p]["left"])+len(J[p]["right"])])
s.append(["합계","","",len(allrows)])
d=wb.create_sheet("중복 NO");d.append(["용기번호","나온 곳"])
for c in d[1]: c.font=Font(bold=True);c.fill=H
dups={a:b for a,b in where.items() if len(b)>1}
for a,b in dups.items(): d.append([a,", ".join(b)])
if not dups: d.append(["중복 없음",""])
other=defaultdict(list)
for p,v in P.items():
    for r in v["rows"]: other[r[2]].append(f"기록대장 {p}")
for p,v in D.items():
    for side in ("left","right"):
        for r in v[side]: other[r[1]].append(f"재고파악 {p}")
for k,v in G.items():
    for i,n in enumerate(v["nos"],1):
        if n: other[n].append(f"{k} {i}번")
    for e in v["extra"]: other[e[1]].append(f"{k}")
x=wb.create_sheet("다른 대장과 겹침");x.append(["용기번호","이번 장","다른 대장"])
for c in x[1]: c.font=Font(bold=True);c.fill=H
ov=[(a,", ".join(where[a]),", ".join(other[a])) for a in where if a in other]
for o in ov: x.append(list(o))
if not ov: x.append(["겹침 없음","",""])
Q="J0508 S2439 J0367 J0658 J0811 S1053 M0507 J0033 M0531 Q0217 S1060 S0451 S1266 Q0358 Q0222 J0621 Q0443 M0358 Q0200 Q0077 S0540 Q0136 Q0300 J0525 Q0416 Q0098 S2350".split()
m=wb.create_sheet("미확인 27개 확인");m.append(["번호","이번 장(1~7)","앞서 받은 대장","결과","비슷한 번호(글씨 오인 가능)"])
for c in m[1]: c.font=Font(bold=True);c.fill=H
allidx=defaultdict(list)
for a,b in where.items(): allidx[a]+=b
for a,b in other.items(): allidx[a]+=b
res=[]
for q in Q:
    a=", ".join(where.get(q,[]));b=", ".join(other.get(q,[]))
    near=[f"{k}({allidx[k][0]})" for k in allidx if len(k)==5 and k!=q and k[0]==q[0] and sum(u!=v for u,v in zip(k,q))==1]
    r=[q,a,b,"있음" if (a or b) else "없음",", ".join(near[:4])];m.append(r);res.append(r)
for sh,ws_ in ((d,(10,30)),(x,(10,24,40)),(m,(9,18,22,7,60))):
    for col,w in zip("ABCDE",ws_): sh.column_dimensions[col].width=w
for p in J:
    t=wb.create_sheet(p);t["A1"]=J[p]["title"];t["A1"].font=Font(bold=True,size=13)
    t.append([]);t.append(["줄","용기번호","용도","위치","확인 필요","","줄","용기번호","용도","위치","확인 필요"])
    for c in t[3]:
        if c.value: c.font=Font(bold=True);c.fill=H;c.border=B
    n=max(len(J[p]["left"]),len(J[p]["right"]),30)
    for i in range(n):
        l=J[p]["left"][i] if i<len(J[p]["left"]) else ["","","",""]
        rr=J[p]["right"][i] if i<len(J[p]["right"]) else ["","","",""]
        t.append([i+1,*l,"",i+1,*rr])
        for c in t[t.max_row]:
            if c.column!=6: c.border=B
        if l[3]: t.cell(t.max_row,5).fill=Y
        if rr[3]: t.cell(t.max_row,11).fill=Y
    for col,w in zip("ABCDEFGHIJK",(5,11,10,9,28,2,5,11,10,9,28)): t.column_dimensions[col].width=w
wb.save("/home/user/aptos-core/docs/pallet/용기번호_장1~7.xlsx")
print(len(allrows),dups);print(ov)
for r in res:
    if r[3]=="있음" or any(x in r[4] for x in ("장",)): print(r)
