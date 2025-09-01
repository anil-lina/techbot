import pandas as pd
import numpy as np

def myround(x, prec=2, base=.05):
  return round(base * round(float(x)/base),prec)

def calculate_macd(data):
    short_ema = data['close'].ewm(span=12, adjust=False).mean()
    long_ema = data['close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal_line = macd.ewm(span=9, adjust=False).mean()
    return macd, signal_line

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

def hull_moving_average(s, period):
  """
  Calculates the Hull Moving Average (HMA).
  Note: The original implementation was complex and might not be standard.
  This is a more readable version of the same calculation.
  """
  wma_half = s.rolling(period // 2).mean()
  wma_full = s.rolling(period).mean()
  diff = (2 * wma_half) - wma_full
  hma = diff.rolling(int(np.sqrt(period))).mean()
  return hma


def vwma(data, period=17):
    volume = data['volume']
    close = data['close']
    vol_close = volume * close
    vwma = vol_close.rolling(period).sum() / volume.rolling(period).sum()
    return vwma

def detect_crossovers(df, column1, column2):
    df['Signal'] = 0
    # Ensure we are working with a copy to avoid SettingWithCopyWarning
    df_copy = df.copy()
    df_copy['Signal'] = np.where(df_copy[column1] > df_copy[column2], 1, 0)
    df_copy['crossover'] = df_copy['Signal'].diff()
    return df_copy['crossover']


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

def calculate_ema(df, ema_lengths):
    def compute_ema(series, span):
        return series.ewm(span=span, adjust=False).mean()

    for length in ema_lengths:
        column_name = f'ema_{length}'
        df[column_name] = compute_ema(df['close'], length)
    return df

def groom_data(ret_df):
    """
    Cleans and prepares the raw data from the API.
    """
    df = pd.DataFrame(data=ret_df)
    if df.empty:
        return df
    df = df.filter(["time", "into", "inth", "intl", "intc", "intv"], axis=1)
    df.columns = ["time", "open", "high", "low", "close", "volume"]
    df["time"] = pd.to_datetime(df["time"], format="%d-%m-%Y %H:%M:%S")
    df.sort_values(by="time", inplace=True, ignore_index=True)
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": int})
    return df
