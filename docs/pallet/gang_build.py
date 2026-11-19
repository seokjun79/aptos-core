exec(open('gang_data.py',encoding='utf-8').read())
exec(open('data.py',encoding='utf-8').read())
exec(open('inv_data.py',encoding='utf-8').read())
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment,Border,Side,PatternFill
from collections import defaultdict
thin=Side(style="thin",color="999999");B=Border(left=thin,right=thin,top=thin,bottom=thin)
H=PatternFill("solid",fgColor="DDE7F0");Y=PatternFill("solid",fgColor="FFF2CC");GR=PatternFill("solid",fgColor="EEEEEE")
def k(n): a,b=n.replace("강","").split("-"); return (int(a),int(b))
order=sorted(G,key=k)
rows=defaultdict(list);where=defaultdict(list)
for s in order:
    v=G[s];cur=""
    for i,n in enumerate(v["nos"],1):
        if v["loc"].get(i): cur=v["loc"][i]
        r=[i,v["g"].get(i,""),n or "(지움)",v["memo"].get(i,""),v["loc"].get(i,""),cur if n else "",v["q"].get(i,"")]
        rows[s].append(r)
        if n: where[n].append(f"{s} {i}번")
    for e in v["extra"]:
        rows[s].append([e[0],"",e[1],e[2],"",cur,"칸 밖에 적음"]);where[e[1]].append(f"{s} {e[0]}")
wb=Workbook();ws=wb.active;ws.title="전체"
hd=["장","순번","구분","NO","메모","위치(적힌 값)","위치(이어서 채움)","확인 필요"]
ws.append(hd)
for c in ws[1]: c.font=Font(bold=True);c.fill=H;c.border=B
for s in order:
    for r in rows[s]:
        ws.append([s,*r])
        for c in ws[ws.max_row]: c.border=B
        if r[6]: ws.cell(ws.max_row,8).fill=Y
        if r[2]=="(지움)":
            for c in ws[ws.max_row]: c.fill=GR
for col,w in zip("ABCDEFGH",(9,8,14,9,26,11,11,30)): ws.column_dimensions[col].width=w
ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:H{ws.max_row}"
sm=wb.create_sheet("장별 요약");sm.append(["장","동그라미 번호","제목","NO 개수","위치"])
for c in sm[1]: c.font=Font(bold=True);c.fill=H;c.border=B
tot=0
for s in order:
    n=len([r for r in rows[s] if r[2]!="(지움)"]);tot+=n
    locs=" ".join(dict.fromkeys(x for x in G[s]["loc"].values()))
    sm.append([s,G[s]["page"],G[s]["title"],n,locs])
    for c in sm[sm.max_row]: c.border=B
sm.append(["합계","","",tot,""])
for c in sm[sm.max_row]: c.font=Font(bold=True)
for col,w in zip("ABCDE",(9,12,26,9,40)): sm.column_dimensions[col].width=w
d=wb.create_sheet("중복 NO");d.append(["NO","나온 곳"])
for c in d[1]: c.font=Font(bold=True);c.fill=H
dups={a:b for a,b in where.items() if len(b)>1}
for a,b in sorted(dups.items()): d.append([a,", ".join(b)])
if not dups: d.append(["중복 없음",""])
x=wb.create_sheet("다른 대장과 겹침");x.append(["NO","강9·강14","다른 대장"])
for c in x[1]: c.font=Font(bold=True);c.fill=H
other=defaultdict(list)
for p,v in P.items():
    for r in v["rows"]: other[r[2]].append(f"기록대장 {p} {r[0]}번")
for p,v in D.items():
    for side,lab in (("left","왼"),("right","오")):
        for r in v[side]: other[r[1]].append(f"재고파악 {p} {lab}{r[0]}번")
ov=[(a,", ".join(where[a]),", ".join(other[a])) for a in sorted(where) if a in other]
for o in ov: x.append(list(o))
if not ov: x.append(["겹침 없음","",""])
for sh in (d,x):
    for col,w in zip("ABC",(10,30,36)): sh.column_dimensions[col].width=w
for s in order:
    t=wb.create_sheet(s);t["A1"]=f"배관 PALLET 기록대장  {G[s]['title']}  (동그라미 {G[s]['page']})";t["A1"].font=Font(bold=True,size=13)
    t.append([]);t.append(["순번","구분","NO","메모","위치(적힌 값)","위치(이어서)","확인 필요"])
    for c in t[3]: c.font=Font(bold=True);c.fill=H;c.border=B
    have={r[0]:r for r in rows[s]}
    for i in range(1,51):
        r=have.get(i,[i,"","","","","",""]);t.append(r)
        for c in t[t.max_row]: c.border=B
        if r[6]: t.cell(t.max_row,7).fill=Y
    for r in rows[s]:
        if not isinstance(r[0],int):
            t.append(r)
            for c in t[t.max_row]: c.border=B
            t.cell(t.max_row,7).fill=Y
    for col,w in zip("ABCDEFG",(9,14,9,26,11,11,30)): t.column_dimensions[col].width=w
    t.freeze_panes="A4"
wb.save("/home/user/aptos-core/docs/pallet/배관_PALLET_기록대장_강9_강14.xlsx")
print("total",tot);print("dups",dups);print("overlap",ov)
