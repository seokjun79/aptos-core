exec(open('data.py',encoding='utf-8').read())
notes={("15-02",26):"끝에 점(.)",("15-06",17):"끝자리 5/4",("15-06",21):"옆에 작은 글씨 '12'",("15-06",25):"앞에 작은 표시",
("15-04",38):"앞 글자 고쳐 씀",("15-07",35):"앞 번호 지우고 고쳐 씀",("15-09",4):"앞 번호 지우고 고쳐 씀",("15-13",28):"앞 번호 지우고 고쳐 씀",
("15-15",22):"앞 번호 지우고 고쳐 씀",("15-08",11):"옆에 (S2008) 다시 적음",("15-08",25):"옆에 S2663 다시 적음",("15-14",15):"옆에 점(•)",("15-02",7):"옆에 작은 표시"}
for (p,seq),t in notes.items():
    P[p]["rows"]=[(r[0],r[1],r[2],r[3],r[4],r[5],(r[6]+"; " if r[6] else "")+t) if r[0]==seq else r for r in P[p]["rows"]]
from openpyxl import Workbook
from openpyxl.styles import Font,Alignment,Border,Side,PatternFill
from collections import Counter,defaultdict
thin=Side(style="thin",color="999999");B=Border(left=thin,right=thin,top=thin,bottom=thin)
H=PatternFill("solid",fgColor="DDE7F0");Y=PatternFill("solid",fgColor="FFF2CC");G=PatternFill("solid",fgColor="EEEEEE")
isno=lambda s: len(s)==5 and s[0] in "SEJMQR" and s[1:].isdigit()
key=lambda x:int(x.split("-")[1])
wb=Workbook();ws=wb.active;ws.title="전체"
ws.append(["장","장 메모","순번","구분","NO","메모(PLATE 칸)","위치","← 표시","확인 필요"])
for c in ws[1]: c.font=Font(bold=True);c.fill=H;c.border=B;c.alignment=Alignment(horizontal="center")
allno=defaultdict(list)
for p in sorted(P,key=key):
    for r in sorted(P[p]["rows"],key=lambda r:r[0]):
        ws.append([p,P[p]["head"],*r]);row=ws.max_row
        for c in ws[row]:
            c.border=B
            if not isno(r[2]): c.fill=G
        if r[6]: ws.cell(row,9).fill=Y
        if isno(r[2]): allno[r[2]].append(f"{p} {r[0]}번")
for col,w in zip("ABCDEFGHI",(7,14,6,6,26,16,7,7,34)): ws.column_dimensions[col].width=w
ws.freeze_panes="A2"; ws.auto_filter.ref=f"A1:I{ws.max_row}"
s=wb.create_sheet("장별 요약")
s.append(["장","장 메모","동그라미 숫자","옮긴 NO 개수","일치","적치","수압"])
for c in s[1]: c.font=Font(bold=True);c.fill=H;c.border=B
tot=Counter()
for p in sorted(P,key=key):
    rs=[r for r in P[p]["rows"] if isno(r[2])];n=len(rs);j=sum(r[1]=="적" for r in rs);su=sum(r[1]=="수" for r in rs);ci=P[p]["circle"]
    s.append([p,P[p]["head"],ci if ci else "-",n,("O" if ci==n else "확인") if ci else "-",j,su])
    for c in s[s.max_row]: c.border=B
    tot.update(n=n,j=j,s=su)
s.append(["합계","","",tot["n"],"",tot["j"],tot["s"]])
for c in s[s.max_row]: c.font=Font(bold=True);c.border=B
for col,w in zip("ABCDEFG",(8,16,14,14,8,8,8)): s.column_dimensions[col].width=w
d=wb.create_sheet("중복 NO");d.append(["NO","나온 곳"])
for c in d[1]: c.font=Font(bold=True);c.fill=H
dups={k:v for k,v in allno.items() if len(v)>1}
for k,v in sorted(dups.items()): d.append([k,", ".join(v)])
if not dups: d.append(["중복 없음",""])
d.column_dimensions["A"].width=10;d.column_dimensions["B"].width=40
for p in sorted(P,key=key):
    t=wb.create_sheet(p);t["A1"]=f"배관 PALLET 기록대장  {p}  {P[p]['head']}";t["A1"].font=Font(bold=True,size=13)
    t.append([]);t.append(["순번","구분","NO","메모","위치","←","확인 필요"])
    for c in t[3]: c.font=Font(bold=True);c.fill=H;c.border=B
    rows={r[0]:r for r in P[p]["rows"]}
    for i in range(1,51):
        r=rows.get(i,(i,"","","","","",""));t.append(list(r))
        for c in t[t.max_row]: c.border=B
        if r[6]: t.cell(t.max_row,7).fill=Y
    for col,w in zip("ABCDEFG",(6,6,26,14,7,5,30)): t.column_dimensions[col].width=w
    t.freeze_panes="A4"
wb.save("/home/user/aptos-core/docs/pallet/배관_PALLET_기록대장_15-01~15.xlsx")
print(dict(tot),"dups",dups)
for p in sorted(P,key=key):
    print(p,len([r for r in P[p]["rows"] if isno(r[2])]),P[p]["circle"])
