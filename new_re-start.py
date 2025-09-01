#!/usr/bin/env python
# coding: utf-8

# In[1]:


import mplfinance as mpf
import sys
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath("C:\\temp\\temp\\a1\\tehcbot\\api_helper.py"))))
from NorenRestApiPy.NorenApi import  NorenApi
from threading import Timer
import pandas as pd
import time
import concurrent.futures
from threading import Timer
import pandas as pd
import numpy as np
import time
import yaml
import concurrent.futures
import math
import logging
from datetime import datetime,timedelta
import plotly.graph_objects as go
from pytz import timezone
from IPython.display import clear_output
class ShoonyaApiPy(NorenApi):
    def __init__(self):
        NorenApi.__init__(self, host='https://api.shoonya.com/NorenWClientTP/',websocket='wss://api.shoonya.com/NorenWSTP/')
api = ShoonyaApiPy()


# In[174]:


#supress debug messages for prod/tests
logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)


# In[3]:


def auth_module(api):
    with open('C:\\temp\\temp\\a1\\tehcbot\\creds.yml') as f:
        cred = yaml.load(f, Loader=yaml.FullLoader)
    TOTP= input('enter 2FA: '),
    cred['factor2']=TOTP[0]
    ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=cred['factor2'], vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])
    return ret
#auth_module(api)


# In[43]:


def get_itm(spot_price,idx_search):
  base= 100
  spot_price = float(spot_price)
  print('LAST TRADING PRICE',idx_search,'-',spot_price)
  put = spot_price+(spot_price*0.0035)
  call = spot_price-(spot_price*0.0035)
  put_str = round(base * round((put)/base),2)
  call_str = round(base * round(call/base),2)
  print(idx_search,'- call side',call_str,' - put side',put_str)
  call_scrip = api.searchscrip('NFO',idx_search+str(" ")+str(call_str))
  put_scrip = api.searchscrip('NFO',idx_search+str(" ")+str(put_str))
  return [call_scrip['values'][3],put_scrip['values'][2]]


# In[100]:


def myround(x, prec=2, base=.05):
  return round(base * round(float(x)/base),prec)


# In[102]:


def calculate_macd(data):
    short_ema = data['close'].ewm(span=12, adjust=False).mean()
    long_ema = data['close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=9, adjust=False).mean()+ 0.01
    return macd, signal_line


# In[104]:


def atr(sub_df, n=14):
    data = sub_df.copy()
    high = data['high']
    low = data['low']
    close = data['close']
    data['tr0'] = abs(high - low)
    data['tr1'] = abs(high - close.shift())
    data['tr2'] = abs(low - close.shift())
    tr = data[['tr0', 'tr1', 'tr2']].max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False).mean()
    return atr


# In[106]:


def hull_moving_average(s, period):
  HMA = s.rolling(period//2).apply(lambda x: ((np.arange(period//2) + 1)*x).sum()/(np.arange(period//2) + 1).sum(), raw=True).multiply(2).sub(s.rolling(period).apply(lambda x: ((np.arange(period) + 1)*x).sum()/(np.arange(period) + 1).sum(), raw=True)).rolling(int(np.sqrt(period))).apply(lambda x: ((np.arange(int(np.sqrt(period))) + 1)*x).sum()/(np.arange(int(np.sqrt(period))) + 1).sum(), raw=True)
  return HMA


# In[226]:


def vwma(data, period=17):
    volume = data['volume']
    close = data['close']
    vol_close = volume * close
    vwma = vol_close.rolling(period).sum() / volume.rolling(period).sum()
    return vwma

def detect_crossovers(df,column1, column2):
    df['Signal'] = 0
    df['Signal'][1:] = np.where(df[column1][1:] > df[column2][1:], 1, 0)
    df['crossover'] = df['Signal'].diff()
    return  df['crossover']

def calculate_rsi(df, candle_lengths):

    def compute_rsi(series, period):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    for length in candle_lengths:
        column_name = f'rsi_{length}'
        df[column_name] = compute_rsi(df['close'], length)

    return df

import pandas as pd

def calculate_ema(df, ema_lengths):
    def compute_ema(series, span):
        return series.ewm(span=span, adjust=False).mean()

    for length in ema_lengths:
        column_name = f'ema_{length}'
        df[column_name] = compute_ema(df['close'], length)

    return df

def ret_grooming(ret_df):
  df= pd.DataFrame(data=ret_df)
  print(df)
  df = df.filter(["time","into","inth","intl","intc","intv"],axis=1)
  df.columns = ["time","open","high","low","close","volume"]
  df["time"] = df["time"].apply(pd.to_datetime,format="%d-%m-%Y %H:%M:%S")
  df.sort_values(by="time",inplace=True,ignore_index=True)
  df = df.astype( {"open":float,"high":float,"low":float,"close":float,"volume":int})
  df['HMA']= hull_moving_average(df['close'], 15)
  df['ATR'] = atr(df)
  df['entry'] =df['close']+df['ATR']
  df['SL'] = df['high']-df['ATR']
  df['MACD'], df['Signal Line'] = calculate_macd(df)
  df['MACD_Crossover'] = detect_crossovers(df,'MACD','Signal Line')
  return df


# In[190]:


delta = timedelta(days=-10) #set to zero for today
lastBusDay = datetime.today() + delta
tf = 60
pd.options.mode.chained_assignment = None
last_candles = 10
lastBusDay = lastBusDay.replace(hour=0, minute=0, second=0, microsecond=0)
lots = 1


# In[192]:


api = ShoonyaApiPy()
#for first time login, else refer ret as logged in
if ret == None:
    ret = auth_module(api)


# In[220]:


def get_option_chart(api,details):
    endtime   =  datetime.today()
    timeseries=api.get_time_price_series(exchange=details['exch'], token=details['token'] , starttime=lastBusDay.timestamp(),endtime=endtime.timestamp(), interval=tf)
    print(timeseries)
    #groomed_df=pd.DataFrame()
    groomed_df=ret_grooming(timeseries)
    return groomed_df


# In[230]:


print(datetime.now(timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S.%f'))
instruments=[['RELIANCE-EQ','RELIANCE']]
for i in instruments:
   print(i[0])
   qResnf = api.get_quotes('NSE', i[0])
   last_price = float(qResnf['lp'])
   put_details,call_details = get_itm(last_price,i[1])
   #print(put_details,call_details)
   call_chart=get_option_chart(api,call_details)
   put_chart=get_option_chart(api,put_details)
   if (bool(call_chart['Crossover'].tail(1).item() == 1) & (call_chart['close'].tail(1).item() > call_chart['HMA'].tail(1).item())):
       print(api.place_order(buy_or_sell='B', product_type='M',exchange=exch, tradingsymbol=bnf_put_sym,quantity=bnf_qty, discloseqty=0,price_type='SL-LMT', price=myround(bnf_put_signal['entry']), trigger_price=myround(bnf_put_signal['entry']-1),retention='DAY', remarks=bnf_put_sym))
   #print(bnf_put_order_ret)
   if (bool(put_chart['Crossover'].tail(1).item() == 1) & (put_chart['close'].tail(1).item() > put_chart['HMA'].tail(1).item())):
       print(api.place_order(buy_or_sell='B', product_type='M',exchange=exch, tradingsymbol=bnf_put_sym,quantity=bnf_qty, discloseqty=0,price_type='SL-LMT', price=myround(bnf_put_signal['entry']), trigger_price=myround(bnf_put_signal['entry']-1),retention='DAY', remarks=bnf_put_sym))
   #print(bnf_put_order_ret)
   bnf_put_sub_df['Date'] =pd.to_datetime(bnf_put_sub_df['time'].tail(last_candles))
   df.set_index('Date', inplace=True)
   bnf_put_macd_plot = mpf.make_addplot(df['Crossover'].tail(last_candles), panel=1, color='orange', markersize=1, secondary_y=True)
   bnf_put_entry_plot = mpf.make_addplot(df['entry'].tail(last_candles), panel=0, color='red', scatter=True, marker='|', markersize=2, secondary_y=False)
   bnf_put_hma_plot = mpf.make_addplot(df['HMA'].tail(last_candles), panel=0, color='blue', scatter=True, marker='x', markersize=1, secondary_y=False)
   mpf.plot(df.tail(last_candles), type='candle', title=exch+' '+bnf_put_sym, style='yahoo', addplot=[bnf_put_hma_plot,bnf_put_macd_plot,bnf_put_entry_plot], figsize=(17, 8), ylim=(min(bnf_put_sub_df['sl'].tail(last_candles)), max(bnf_put_sub_df['entry'].tail(last_candles))))


# In[224]:





# In[178]:


instruments = [['360ONE-EQ','360ONE'],
['ABB-EQ','ABB'],
['ABCAPITAL-EQ','ABCAPITAL'],
['ADANIENSOL-EQ','ADANIENSOL'],
['ADANIENT-EQ','ADANIENT'],
['ADANIGREEN-EQ','ADANIGREEN'],
['ADANIPORTS-EQ','ADANIPORTS'],
['ALKEM-EQ','ALKEM'],
['AMBER-EQ','AMBER'],
['AMBUJACEM-EQ','AMBUJACEM'],
['ANGELONE-EQ','ANGELONE'],
['APLAPOLLO-EQ','APLAPOLLO'],
['APOLLOHOSP-EQ','APOLLOHOSP'],
['ASHOKLEY-EQ','ASHOKLEY'],
['ASIANPAINT-EQ','ASIANPAINT'],
['ASTRAL-EQ','ASTRAL'],
['AUBANK-EQ','AUBANK'],
['AUROPHARMA-EQ','AUROPHARMA'],
['AXISBANK-EQ','AXISBANK'],
['BAJAJ-AUTO-EQ','BAJAJ-AUTO'],
['BAJAJFINSV-EQ','BAJAJFINSV'],
['BAJFINANCE-EQ','BAJFINANCE'],
['BANDHANBNK-EQ','BANDHANBNK'],
['BANKBARODA-EQ','BANKBARODA'],
['BANKINDIA-EQ','BANKINDIA'],
['BDL-EQ','BDL'],
['BEL-EQ','BEL'],
['BHARATFORG-EQ','BHARATFORG'],
['BHARTIARTL-EQ','BHARTIARTL'],
['BHEL-EQ','BHEL'],
['BIOCON-EQ','BIOCON'],
['BLUESTARCO-EQ','BLUESTARCO'],
['BOSCHLTD-EQ','BOSCHLTD'],
['BPCL-EQ','BPCL'],
['BRITANNIA-EQ','BRITANNIA'],
['BSE-EQ','BSE'],
['CAMS-EQ','CAMS'],
['CANBK-EQ','CANBK'],
['CDSL-EQ','CDSL'],
['CGPOWER-EQ','CGPOWER'],
['CHOLAFIN-EQ','CHOLAFIN'],
['CIPLA-EQ','CIPLA'],
['COALINDIA-EQ','COALINDIA'],
['COFORGE-EQ','COFORGE'],
['COLPAL-EQ','COLPAL'],
['CONCOR-EQ','CONCOR'],
['CROMPTON-EQ','CROMPTON'],
['CUMMINSIND-EQ','CUMMINSIND'],
['CYIENT-EQ','CYIENT'],
['DABUR-EQ','DABUR'],
['DALBHARAT-EQ','DALBHARAT'],
['DELHIVERY-EQ','DELHIVERY'],
['DIVISLAB-EQ','DIVISLAB'],
['DIXON-EQ','DIXON'],
['DLF-EQ','DLF'],
['DMART-EQ','DMART'],
['DRREDDY-EQ','DRREDDY'],
['EICHERMOT-EQ','EICHERMOT'],
['ETERNAL-EQ','ETERNAL'],
['EXIDEIND-EQ','EXIDEIND'],
['FEDERALBNK-EQ','FEDERALBNK'],
['FORTIS-EQ','FORTIS'],
['GAIL-EQ','GAIL'],
['GLENMARK-EQ','GLENMARK'],
['GMRAIRPORT-EQ','GMRAIRPORT'],
['GODREJCP-EQ','GODREJCP'],
['GODREJPROP-EQ','GODREJPROP'],
['GRASIM-EQ','GRASIM'],
['HAL-EQ','HAL'],
['HAVELLS-EQ','HAVELLS'],
['HCLTECH-EQ','HCLTECH'],
['HDFCAMC-EQ','HDFCAMC'],
['HDFCBANK-EQ','HDFCBANK'],
['HDFCLIFE-EQ','HDFCLIFE'],
['HEROMOTOCO-EQ','HEROMOTOCO'],
['HFCL-EQ','HFCL'],
['HINDALCO-EQ','HINDALCO'],
['HINDPETRO-EQ','HINDPETRO'],
['HINDUNILVR-EQ','HINDUNILVR'],
['HINDZINC-EQ','HINDZINC'],
['HUDCO-EQ','HUDCO'],
['ICICIBANK-EQ','ICICIBANK'],
['ICICIGI-EQ','ICICIGI'],
['ICICIPRULI-EQ','ICICIPRULI'],
['IDEA-EQ','IDEA'],
['IDFCFIRSTB-EQ','IDFCFIRSTB'],
['IEX-EQ','IEX'],
['IGL-EQ','IGL'],
['IIFL-EQ','IIFL'],
['INDHOTEL-EQ','INDHOTEL'],
['INDIANB-EQ','INDIANB'],
['INDIGO-EQ','INDIGO'],
['INDUSINDBK-EQ','INDUSINDBK'],
['INDUSTOWER-EQ','INDUSTOWER'],
['INFY-EQ','INFY'],
['INOXWIND-EQ','INOXWIND'],
['IOC-EQ','IOC'],
['IRCTC-EQ','IRCTC'],
['IREDA-EQ','IREDA'],
['IRFC-EQ','IRFC'],
['ITC-EQ','ITC'],
['JINDALSTEL-EQ','JINDALSTEL'],
['JIOFIN-EQ','JIOFIN'],
['JSWENERGY-EQ','JSWENERGY'],
['JSWSTEEL-EQ','JSWSTEEL'],
['JUBLFOOD-EQ','JUBLFOOD'],
['KALYANKJIL-EQ','KALYANKJIL'],
['KAYNES-EQ','KAYNES'],
['KEI-EQ','KEI'],
['KFINTECH-EQ','KFINTECH'],
['KOTAKBANK-EQ','KOTAKBANK'],
['KPITTECH-EQ','KPITTECH'],
['LAURUSLABS-EQ','LAURUSLABS'],
['LICHSGFIN-EQ','LICHSGFIN'],
['LICI-EQ','LICI'],
['LODHA-EQ','LODHA'],
['LT-EQ','LT'],
['LTF-EQ','LTF'],
['LTIM-EQ','LTIM'],
['LUPIN-EQ','LUPIN'],
['M&M-EQ','M&M'],
['MANAPPURAM-EQ','MANAPPURAM'],
['MANKIND-EQ','MANKIND'],
['MARICO-EQ','MARICO'],
['MARUTI-EQ','MARUTI'],
['MAXHEALTH-EQ','MAXHEALTH'],
['MAZDOCK-EQ','MAZDOCK'],
['MCX-EQ','MCX'],
['MFSL-EQ','MFSL'],
['MOTHERSON-EQ','MOTHERSON'],
['MPHASIS-EQ','MPHASIS'],
['MUTHOOTFIN-EQ','MUTHOOTFIN'],
['NATIONALUM-EQ','NATIONALUM'],
['NAUKRI-EQ','NAUKRI'],
['NBCC-EQ','NBCC'],
['NCC-EQ','NCC'],
['NESTLEIND-EQ','NESTLEIND'],
['NHPC-EQ','NHPC'],
['NMDC-EQ','NMDC'],
['NTPC-EQ','NTPC'],
['NUVAMA-EQ','NUVAMA'],
['NYKAA-EQ','NYKAA'],
['OBEROIRLTY-EQ','OBEROIRLTY'],
['OFSS-EQ','OFSS'],
['OIL-EQ','OIL'],
['ONGC-EQ','ONGC'],
['PAGEIND-EQ','PAGEIND'],
['PATANJALI-EQ','PATANJALI'],
['PAYTM-EQ','PAYTM'],
['PERSISTENT-EQ','PERSISTENT'],
['PETRONET-EQ','PETRONET'],
['PFC-EQ','PFC'],
['PGEL-EQ','PGEL'],
['PHOENIXLTD-EQ','PHOENIXLTD'],
['PIDILITIND-EQ','PIDILITIND'],
['PIIND-EQ','PIIND'],
['PNB-EQ','PNB'],
['PNBHOUSING-EQ','PNBHOUSING'],
['POLICYBZR-EQ','POLICYBZR'],
['POLYCAB-EQ','POLYCAB'],
['POWERGRID-EQ','POWERGRID'],
['PPLPHARMA-EQ','PPLPHARMA'],
['PRESTIGE-EQ','PRESTIGE'],
['RBLBANK-EQ','RBLBANK'],
['RECLTD-EQ','RECLTD'],
['RELIANCE-EQ','RELIANCE'],
['RVNL-EQ','RVNL'],
['SAIL-EQ','SAIL'],
['SAMMAANCAP-EQ','SAMMAANCAP'],
['SBICARD-EQ','SBICARD'],
['SBILIFE-EQ','SBILIFE'],
['SBIN-EQ','SBIN'],
['SHREECEM-EQ','SHREECEM'],
['SHRIRAMFIN-EQ','SHRIRAMFIN'],
['SIEMENS-EQ','SIEMENS'],
['SOLARINDS-EQ','SOLARINDS'],
['SONACOMS-EQ','SONACOMS'],
['SRF-EQ','SRF'],
['SUNPHARMA-EQ','SUNPHARMA'],
['SUPREMEIND-EQ','SUPREMEIND'],
['SUZLON-EQ','SUZLON'],
['SYNGENE-EQ','SYNGENE'],
['TATACHEM-EQ','TATACHEM'],
['TATACONSUM-EQ','TATACONSUM'],
['TATAELXSI-EQ','TATAELXSI'],
['TATAMOTORS-EQ','TATAMOTORS'],
['TATAPOWER-EQ','TATAPOWER'],
['TATASTEEL-EQ','TATASTEEL'],
['TATATECH-EQ','TATATECH'],
['TCS-EQ','TCS'],
['TECHM-EQ','TECHM'],
['TIINDIA-EQ','TIINDIA'],
['TITAGARH-EQ','TITAGARH'],
['TITAN-EQ','TITAN'],
['TORNTPHARM-EQ','TORNTPHARM'],
['TORNTPOWER-EQ','TORNTPOWER'],
['TRENT-EQ','TRENT'],
['TVSMOTOR-EQ','TVSMOTOR'],
['ULTRACEMCO-EQ','ULTRACEMCO'],
['UNIONBANK-EQ','UNIONBANK'],
['UNITDSPR-EQ','UNITDSPR'],
['UNOMINDA-EQ','UNOMINDA'],
['UPL-EQ','UPL'],
['VBL-EQ','VBL'],
['VEDL-EQ','VEDL'],
['VOLTAS-EQ','VOLTAS'],
['WIPRO-EQ','WIPRO'],
['YESBANK-EQ','YESBANK'],
['ZYDUSLIFE-EQ','ZYDUSLIFE']
]


# In[ ]:




