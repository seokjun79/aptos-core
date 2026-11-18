import json,io,pandas as pd,glob
D='/root/.claude/projects/-home-user-aptos-core/ef3271df-d73d-5f17-9a5a-ef310ec15f5a/tool-results/'
m={'yjclr6':'USDJPY','r3jncb':'USDCHF','54pg7r':'EURUSD','zidyil':'GBPUSD','rx9uux':'USDCAD','ame86f':'AUDUSD'}
s={}
for k,n in m.items():
    f=glob.glob(D+'*'+k+'.txt')[0]
    df=pd.read_csv(io.StringIO(json.load(open(f))['result']),parse_dates=['timestamp']).set_index('timestamp').sort_index()
    s[n]=df['close']
px=pd.DataFrame(s).dropna()
px.to_csv('px.csv')
print(px.index.min(),px.index.max(),len(px))
