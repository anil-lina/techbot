import matplotlib
# Set the backend to a non-interactive one before importing mplfinance
matplotlib.use('Agg')
import mplfinance as mpf
from datetime import datetime
import pandas as pd
import os

def _ensure_charts_dir_exists():
    """Checks for a './charts' directory and creates it if it doesn't exist."""
    if not os.path.exists('charts'):
        os.makedirs('charts')

def plot_chart(df, symbol, signal_candle=None, title_prefix="Signal for"):
    """
    Generates a static chart using mplfinance, highlighting a signal.
    """
    _ensure_charts_dir_exists()

    # mplfinance requires a DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df_copy = df.copy()
        df_copy.set_index('time', inplace=True)
    else:
        df_copy = df

    ap = [] # addplot list

    ap.append(mpf.make_addplot(df_copy['HMA'], color='blue'))

    if 'vwma' in df_copy.columns:
        ap.append(mpf.make_addplot(df_copy['vwma'], color='purple', linestyle='dotted'))

    ap.append(mpf.make_addplot(df_copy['MACD'], panel=1, color='purple', ylabel='MACD'))
    ap.append(mpf.make_addplot(df_copy['Signal Line'], panel=1, color='orange'))

    vlines = []
    if signal_candle is not None:
        signal_time = signal_candle.name
        vlines = dict(vlines=[signal_time], colors=['g' if signal_candle['signal'] == 'BUY' else 'r'], linestyle='--')

    quote = "Consistency over blast"
    chart_title = f'{title_prefix} {symbol}\n"{quote}"'

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"charts/{symbol}_signal_{timestamp}.png"

    mpf.plot(df_copy, type='candle', style='yahoo',
             title=chart_title,
             addplot=ap,
             panel_ratios=(3, 1),
             vlines=vlines,
             show_nontrading=True,
             savefig=filename)

    print(f"Generated signal chart: {filename}")


def plot_backtest(df, trade_df, instrument_name):
    """
    Generates a static chart for the backtest results using mplfinance.
    """
    _ensure_charts_dir_exists()

    if not isinstance(df.index, pd.DatetimeIndex):
        df_copy = df.copy()
        df_copy.set_index('time', inplace=True)
    else:
        df_copy = df

    ap = []
    ap.append(mpf.make_addplot(df_copy['HMA'], color='blue'))

    if not trade_df.empty:
        buy_markers = [float('nan')] * len(df_copy)
        sell_markers = [float('nan')] * len(df_copy)

        for _, trade in trade_df.iterrows():
            if trade['entry_date'] in df_copy.index:
                idx = df_copy.index.get_loc(trade['entry_date'])
                buy_markers[idx] = trade['entry_price'] * 0.98

            if trade['exit_date'] in df_copy.index:
                idx = df_copy.index.get_loc(trade['exit_date'])
                sell_markers[idx] = trade['exit_price'] * 1.02

        ap.append(mpf.make_addplot(buy_markers, type='scatter', color='green', marker='^', markersize=100))
        ap.append(mpf.make_addplot(sell_markers, type='scatter', color='red', marker='v', markersize=100))

    ap.append(mpf.make_addplot(df_copy['MACD'], panel=1, color='purple', ylabel='MACD'))
    ap.append(mpf.make_addplot(df_copy['Signal Line'], panel=1, color='orange'))

    quote = "Consistency over blast"
    chart_title = f'Backtest Analysis for {instrument_name}\n"{quote}"'

    filename = f"charts/{instrument_name}_backtest.png"

    mpf.plot(df_copy, type='candle', style='yahoo',
             title=chart_title,
             addplot=ap,
             panel_ratios=(3, 1),
             show_nontrading=True,
             savefig=filename)

    print(f"Generated backtest chart: {filename}")
