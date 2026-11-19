import json
SP='/tmp/claude-0/-home-user-aptos-core/ef3271df-d73d-5f17-9a5a-ef310ec15f5a/scratchpad/q2/charts/'
def svg(sym,L):
    b=json.load(open(SP+sym+".json"))["h4"][-90:]
    b=[[x[0][:10]]+[float(v) for v in x[1:5]] for x in b];n=len(b)
    W,H,Lm,Rm,T,Bm=760,420,8,150,14,26
    lo=min(min(x[3] for x in b),L["low"])*0.985;hi=max(max(x[2] for x in b),L["sh"])*1.005
    X=lambda i:Lm+(i+.5)*(W-Lm-Rm)/n;cw=(W-Lm-Rm)/n
    Y=lambda v:T+(hi-v)/(hi-lo)*(H-T-Bm)
    idx=lambda d:next((i for i,x in enumerate(b) if x[0]>=d),n-1)
    g=""
    eq=(L["sh"]+L["low"])/2
    g+=f'<rect x="{Lm}" y="{Y(L["sh"]):.1f}" width="{W-Rm-Lm}" height="{Y(eq)-Y(L["sh"]):.1f}" class="prem"/>'
    g+=f'<rect x="{Lm}" y="{Y(eq):.1f}" width="{W-Rm-Lm}" height="{Y(L["low"])-Y(eq):.1f}" class="disc"/>'
    def box(t0,top,bot,cls,lab):
        x0=X(idx(t0))-cw/2;return f'<rect x="{x0:.1f}" y="{Y(top):.1f}" width="{W-Rm-x0:.1f}" height="{Y(bot)-Y(top):.1f}" class="{cls}"/><text x="{W-Rm+4}" y="{(Y(top)+Y(bot))/2+4:.1f}" class="lab {cls}t">{lab}</text>'
    for t0,top,bot,cls,lab in L["boxes"]: g+=box(t0,top,bot,cls,lab)
    for i,x in enumerate(b):
        d,o,h,l,c=x;col="up" if c>=o else "dn"
        g+=f'<line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h):.1f}" y2="{Y(l):.1f}" class="{col}w"/><rect x="{X(i)-cw*.32:.1f}" y="{Y(max(o,c)):.1f}" width="{cw*.64:.1f}" height="{max(1,abs(Y(o)-Y(c))):.1f}" class="{col}"/>'
    def hline(t0,t1,v,cls,lab,right=True):
        x0=X(idx(t0));x1=X(idx(t1)) if t1 else W-Rm
        s=f'<line x1="{x0:.1f}" x2="{x1:.1f}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{cls}"/>'
        if right=="A": s+=f'<text x="{x0+4:.1f}" y="{Y(v)-5:.1f}" class="lab {cls}t">{lab}</text>'
        elif right=="L": s+=f'<text x="{x0-4:.1f}" y="{Y(v)+4:.1f}" class="lab {cls}t" text-anchor="end">{lab}</text>'
        elif right: s+=f'<text x="{W-Rm+4}" y="{Y(v)+4:.1f}" class="lab {cls}t">{lab}</text>'
        else: s+=f'<text x="{x1+3:.1f}" y="{Y(v)-4:.1f}" class="lab {cls}t">{lab}</text>'
        return s
    for a in L["lines"]: g+=hline(*a)
    g+=f'<text x="{Lm+4}" y="{Y(L["sh"])+14:.1f}" class="lab mt">프리미엄</text><text x="{Lm+4}" y="{Y(L["low"])-6:.1f}" class="lab mt">할인</text>'
    i=idx(L["sh_d"]);g+=f'<text x="{X(i):.1f}" y="{Y(L["sh"])-4:.1f}" class="lab dnt" text-anchor="middle">고점 {L["sh"]}</text>'
    for k in range(0,n,15): g+=f'<text x="{X(k):.1f}" y="{H-8}" class="ax" text-anchor="middle">{b[k][0][5:]}</text>'
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{sym} SMC 일봉">{g}</svg>'
Q=dict(low=647.05,sh=762.86,sh_d="2026-10-06",
 boxes=[("2026-11-05",687.87,664.52,"fvg","FVG 664.52~687.87"),("2026-11-04",701.45,687.87,"ob","약세 OB 687.87~701.45"),("2026-10-29",720.30,698.63,"fvg2","FVG 698.63~720.30")],
 lines=[("2026-09-16","2026-10-30",699.27,"choch","CHoCH 699.27 (10/30 깸)","L"),("2026-07-29","2026-11-05",660.45,"bos","BOS 660.45 (11/5 깸)","A"),
        ("2026-11-05",None,647.05,"liq","유동성 647.05"),("2026-11-06",None,664.52,"crt","CRH 664.52","L"),("2026-11-06",None,653.99,"crt","CRL 653.99","L"),
        ("2026-08-10",None,704.96,"eq","중간 704.96"),("2026-10-06",None,762.86,"mss","MSS 762.86"),("2026-08-10",None,687.07,"buy","규칙 사기 687.07")])
L=dict(low=72.13,sh=101.62,sh_d="2026-10-06",
 boxes=[("2026-11-05",81.88,75.95,"fvg","FVG 75.95~81.88"),("2026-11-04",85.09,81.88,"ob","약세 OB 81.88~85.09"),("2026-10-29",90.04,84.57,"fvg2","FVG 84.57~90.04")],
 lines=[("2026-09-16","2026-10-30",85.79,"choch","CHoCH 85.79 (10/30 깸)","L"),("2026-07-29","2026-11-05",77.43,"bos","BOS 77.43 (11/5 깸)","A"),
        ("2026-11-05",None,72.13,"liq","유동성 72.13"),("2026-11-06",None,75.95,"crt","CRH 75.95","L"),("2026-11-06",None,73.61,"crt","CRL 73.61","L"),
        ("2026-08-10",None,86.88,"eq","중간 86.88"),("2026-10-06",None,101.62,"mss","MSS 101.62"),("2026-08-10",None,81.11,"buy","규칙 사기 81.11")])
open("smc_svg.json","w").write(json.dumps(dict(QQQ=svg("QQQ",Q),QLD=svg("QLD",L))))
print("ok")
