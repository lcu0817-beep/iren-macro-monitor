from datetime import datetime, timezone
from pathlib import Path
import io,json,pandas as pd,requests,yfinance as yf
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data.json';S=requests.Session();S.headers.update({'User-Agent':'Mozilla/5.0 IREN-Macro-Monitor/1.0'})
FRED={'us2y':'DGS2','us10y':'DGS10','us30y':'DGS30','real10y':'DFII10'}
YF={'iren':'IREN','move':'^MOVE','ndx':'^NDX','sox':'^SOX','wti':'CL=F','gold':'GC=F','copper':'HG=F','dxy':'DX-Y.NYB','btc':'BTC-USD'}
def fred(s):
 r=S.get(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}',timeout=20);r.raise_for_status();df=pd.read_csv(io.StringIO(r.text));x=pd.to_numeric(df.iloc[:,1],errors='coerce').dropna();return float(x.iloc[-1])
def yh(t):
 df=yf.download(t,period='1y',interval='1d',auto_adjust=True,progress=False,threads=False)
 if df.empty: raise RuntimeError(t)
 c=df['Close'];c=c.iloc[:,0] if hasattr(c,'columns') else c;return c.dropna().astype(float)
def pct(s,n): return float((s.iloc[-1]/s.iloc[-n-1]-1)*100) if len(s)>n else None
def vs50(s): return float((s.iloc[-1]/s.iloc[-50:].mean()-1)*100) if len(s)>=50 else None
values={};warn=[]
for k,s in FRED.items():
 try: values[k]=fred(s)
 except Exception: warn.append(k+' unavailable')
series={}
for k,t in YF.items():
 try: series[k]=yh(t);values[k]=float(series[k].iloc[-1])
 except Exception: warn.append(k+' unavailable')
mom={k:{'m1':pct(s,21),'m3':pct(s,63),'m6':pct(s,126),'vs50d':vs50(s)} for k,s in series.items() if k in ['ndx','sox','wti','gold','copper','dxy','btc']}
payload={'updated_at':datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),'values':values,'momentum':mom,'macro_lab_url':'','source_note':'FRED + Yahoo Finance Â· GitHub Actions refresh','warnings':warn}
OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print('wrote',OUT)
