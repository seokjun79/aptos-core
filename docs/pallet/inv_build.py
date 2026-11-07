exec(open('inv_data.py',encoding='utf-8').read())
exec(open('data.py',encoding='utf-8').read())
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment,Border,Side,PatternFill
from collections import defaultdict,Counter
thin=Side(style="thin",color="999999");B=Border(left=thin,right=thin,top=thin,bottom=thin)
H=PatternFill("solid",fgColor="DDE7F0");Y=PatternFill("solid",fgColor="FFF2CC")
GM={"S":"스풀","O":"공"};UM={"1":"입고","J":"적치","-":""}
wb=Workbook();ws=wb.active;ws.title="전체"
hd=["장","칸","NO","용기번호","구분","구분 뜻","용도","용도 뜻","조사위치(적힌 값)","위치(이어서 채움)","비고","확인 필요"]
ws.append(hd)
for c in ws[1]: c.font=Font(bold=True);c.fill=H;c.border=B;c.alignment=Alignment(horizontal="center",wrap_text=True)
cur="";where=defaultdict(list);rows_all=[]
for p in ["4-1","4-2","4-3","4-4"]:
    for side,lab in (("left","왼쪽"),("right","오른쪽")):
        for (i,no,g,u,loc,memo,q) in D[p][side]:
            if loc and loc!="사무실 옆": cur=loc
            fill = loc if loc=="사무실 옆" else cur
            r=[p,lab,i,no,g,GM.get(g,g),u,UM.get(u,u),loc,fill,memo,q]
            ws.append(r);rows_all.append(r);where[no].append(f"{p} {lab} {i}번")
            for c in ws[ws.max_row]: c.border=B
            if q: ws.cell(ws.max_row,12).fill=Y
for col,w in zip("ABCDEFGHIJKL",(6,7,5,11,5,7,5,7,11,11,8,30)): ws.column_dimensions[col].width=w
ws.freeze_panes="A2";ws.auto_filter.ref=f"A1:L{ws.max_row}"
s=wb.create_sheet("요약")
s.append(["장","개수","스풀(S)","공(O)","입고(1)","적치(J)"])
for c in s[1]: c.font=Font(bold=True);c.fill=H;c.border=B
T=Counter()
for p in ["4-1","4-2","4-3","4-4"]:
    rr=[r for r in rows_all if r[0]==p]
    v=[len(rr),sum(r[4]=="S" for r in rr),sum(r[4]=="O" for r in rr),sum(r[6]=="1" for r in rr),sum(r[6]=="J" for r in rr)]
    s.append([p,*v]);T.update(dict(zip("abcde",v)))
    for c in s[s.max_row]: c.border=B
s.append(["합계",T["a"],T["b"],T["c"],T["d"],T["e"]])
for c in s[s.max_row]: c.font=Font(bold=True);c.border=B
s.append([]);s.append(["위치별","개수"])
for c in s[s.max_row]: c.font=Font(bold=True);c.fill=H
lc=Counter(r[9] for r in rows_all)
for k in lc: s.append([k,lc[k]])
d=wb.create_sheet("중복 NO");d.append(["용기번호","나온 곳"])
for c in d[1]: c.font=Font(bold=True);c.fill=H
dups={k:v for k,v in where.items() if len(v)>1}
for k,v in dups.items(): d.append([k,", ".join(v)])
if not dups: d.append(["중복 없음",""])
x=wb.create_sheet("15번 대장과 겹침");x.append(["용기번호","2단지 재고(4-x)","15번 기록대장"])
for c in x[1]: c.font=Font(bold=True);c.fill=H
p15=defaultdict(list)
for p in P:
    for r in P[p]["rows"]: p15[r[2]].append(f"{p} {r[0]}번 ({r[4] or P[p]['head']})")
ov=[(k,", ".join(where[k]),", ".join(p15[k])) for k in where if k in p15]
for o in ov: x.append(list(o))
if not ov: x.append(["겹침 없음","",""])
for sh in (d,x):
    sh.column_dimensions["A"].width=11;sh.column_dimensions["B"].width=30;sh.column_dimensions["C"].width=40
s.column_dimensions["A"].width=12
info=wb.create_sheet("메모",0) if False else None
ws.insert_rows(1);ws["A1"]="26년 11월 2단지 삼성팔레트 재고파악 (4-1~4-4) · 범례: 스풀(S)/공(O)/입고(1)/적치(J) · "+HEAD["4-1"]
ws["A1"].font=Font(bold=True)
ws.freeze_panes="A3";ws.auto_filter.ref=f"A2:L{ws.max_row}"
wb.save("/home/user/aptos-core/docs/pallet/2단지_삼성팔레트_재고파악_4-1~4.xlsx")
print(dict(T),"dups",dups,"overlap",len(ov),ov[:10])
