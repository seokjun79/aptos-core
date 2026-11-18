import pandas as pd,numpy as np
px=pd.read_csv('px.csv',index_col=0,parse_dates=True)
L=np.log(px)
usd=pd.DataFrame({'JPY':L.USDJPY,'CHF':L.USDCHF,'CAD':L.USDCAD,'GBP':-L.GBPUSD,'AUD':-L.AUDUSD})
eur=usd.add(L.EURUSD,axis=0)  # EUR/X
N=20
def pos(s): 
    hi=s.rolling(N).max(); lo=s.rolling(N).min(); return (s-lo)/(hi-lo)
up=usd.apply(pos); ep=eur.apply(pos); e=L.EURUSD; epos=pos(e)
H=5
fwd=e.shift(-H)-e
rows=[]
i=N; idx=e.index; last=-999
for t in range(N,len(e)-H):
    if t-last<H: continue
    if epos.iloc[t]<=0.0 or epos.iloc[t]>=1.0:
        d=-1 if epos.iloc[t]<=0 else 1   # -1 = EURUSD 20일 최저(하락 끝), +1 = 최고
        # USD 넓게 끝: 하락 끝이면 USD legs가 고점 근처(>=0.9), 상승 끝이면 저점 근처(<=0.1)
        if d==-1: usd_ext=(up.iloc[t]>=0.9).sum(); eur_ext=(ep.iloc[t]<=0.1).sum()
        else: usd_ext=(up.iloc[t]<=0.1).sum(); eur_ext=(ep.iloc[t]>=0.9).sum()
        rev=-d*fwd.iloc[t]*1e4  # 되돌림 방향 수익(핍 아닌 bp)
        rows.append(dict(date=idx[t],d=d,usd=usd_ext,eur=eur_ext,rev=rev)); last=t
R=pd.DataFrame(rows).set_index('date')
R['grp']=np.where(R.usd>=3,'USD넓게끝',np.where(R.eur>=3,'EUR넓게끝','섞임'))
def boot(x,n=5000,seed=1):
    r=np.random.default_rng(seed); x=np.asarray(x)
    if len(x)<5: return (np.nan,np.nan)
    m=[r.choice(x,len(x)).mean() for _ in range(n)]; return np.percentile(m,[2.5,97.5])
# 기준선: 모든 날 5일 수익(방향 무작위 아님) -> 같은 날짜 무작위 방향 대신, 모든 날의 |수익| 부호 랜덤 평균 = 0
for name,sub in [('개발 2007-2017',R[:'2017']),('검증 2018-2026',R['2018':])]:
    print('==',name,'사건',len(sub))
    for g in ['USD넓게끝','EUR넓게끝','섞임']:
        x=sub[sub.grp==g].rev
        lo,hi=boot(x); print(f'{g:8s} n={len(x):3d} 평균 {x.mean():6.1f}bp 승률 {(x>0).mean():.2f} 95% [{lo:6.1f},{hi:6.1f}]')
    x=sub.rev; lo,hi=boot(x); print(f'전체      n={len(x):3d} 평균 {x.mean():6.1f}bp 95% [{lo:6.1f},{hi:6.1f}]')
R.to_csv('events.csv')
