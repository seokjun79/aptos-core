import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fs=['/tmp/claude-0/-home-user-aptos-core/ef3271df-d73d-5f17-9a5a-ef310ec15f5a/scratchpad/maxfx/NanumGothic.ttf']
if fs: fm.fontManager.addfont(fs[0]); plt.rcParams['font.family']=fm.FontProperties(fname=fs[0]).get_name()
plt.rcParams['axes.unicode_minus']=False
R=pd.read_csv('events.csv',index_col=0,parse_dates=True)
def boot(x,n=4000):
    r=np.random.default_rng(1);x=np.asarray(x);m=[r.choice(x,len(x)).mean() for _ in range(n)];return np.percentile(m,[2.5,97.5])
grps=['USD넓게끝','EUR넓게끝','섞임']; lab={'USD넓게끝':'달러 쪽이\n넓게 끝','EUR넓게끝':'유로 쪽이\n넓게 끝','섞임':'섞임'}
fig,ax=plt.subplots(figsize=(9,4.6),facecolor='#2b2f38');ax.set_facecolor('#2b2f38')
cols={'개발 2007~2017':'#5aa0ff','검증 2018~2026':'#f5c518'}
for j,(nm,sub) in enumerate([('개발 2007~2017',R[:'2017']),('검증 2018~2026',R['2018':])]):
    for i,g in enumerate(grps):
        x=sub[sub.grp==g].rev; m=x.mean(); lo,hi=boot(x); xpos=i+(j-0.5)*0.35
        ax.bar(xpos,m,0.33,color=cols[nm],label=nm if i==0 else None)
        ax.errorbar(xpos,m,yerr=[[m-lo],[hi-m]],color='white',capsize=4,lw=1)
        ax.text(xpos,hi+3,f'{len(x)}번',ha='center',color='#ccc',fontsize=9)
ax.axhline(0,color='#aaa',lw=1)
ax.set_xticks(range(3));ax.set_xticklabels([lab[g] for g in grps],color='white')
ax.set_ylabel('5일 뒤 되돌아온 크기 (bp, 0.01%)',color='white');ax.tick_params(colors='white')
for s in ax.spines.values(): s.set_color('#555')
ax.set_title('EURUSD가 20일 끝(최고/최저)에 닿은 날 → 5일 뒤 되돌아왔나?  막대가 0 위 = 되돌아옴, 흰 선 = 95% 범위',color='white',fontsize=11)
ax.legend(facecolor='#2b2f38',labelcolor='white',edgecolor='#555')
plt.tight_layout();plt.savefig('zone_reversion.png',dpi=110,facecolor='#2b2f38')
