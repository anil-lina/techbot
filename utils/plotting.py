import mplfinance as mpf
from datetime import datetime

def plot_chart(df, symbol, signal_candle=None, title_prefix="Signal for"):
    """
    Generates a static chart using mplfinance, highlighting a signal.
    """
    # mplfinance requires a DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        # This should not happen with the current groom_data, but as a safeguard:
        df_copy = df.copy()
        df_copy.set_index('time', inplace=True)
    else:
        df_copy = df

    ap = [] # addplot list

    # HMA Indicator
    ap.append(mpf.make_addplot(df_copy['HMA'], color='blue'))

    # VWAP Indicator (if present)
    if 'vwma' in df_copy.columns:
        ap.append(mpf.make_addplot(df_copy['vwma'], color='purple', linestyle='dotted'))

    # MACD Plot
    ap.append(mpf.make_addplot(df_copy['MACD'], panel=1, color='purple', ylabel='MACD'))
    ap.append(mpf.make_addplot(df_copy['Signal Line'], panel=1, color='orange'))

    # Highlight the signal candle with a vertical line
    vlines = []
    if signal_candle is not None:
        signal_time = signal_candle.name
        vlines = dict(vlines=[signal_time], colors=['g' if signal_candle['signal'] == 'BUY' else 'r'], linestyle='--')

    # Add the motivational quote
    quote = "Consistency over blast"
    chart_title = f'{title_prefix} {symbol}\n"{quote}"'

    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_signal_{timestamp}.png"

    mpf.plot(df_copy, type='candle', style='yahoo',
             title=chart_title,
             addplot=ap,
             panel_ratios=(3, 1),
             vlines=vlines,
             show_nontrading=True, # This is the key change to show a continuous timeline
             savefig=filename)

    print(f"Generated signal chart: {filename}")


def plot_backtest(df, trade_df, instrument_name):
    """
    Generates a static chart for the backtest results using mplfinance.
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        df_copy = df.copy()
        df_copy.set_index('time', inplace=True)
    else:
        df_copy = df

    ap = []
    ap.append(mpf.make_addplot(df_copy['HMA'], color='blue'))

    # Plot trades
    if not trade_df.empty:
        entry_points = trade_df[trade_df['entry_price'].notna()]
        exit_points = trade_df[trade_df['exit_price'].notna()]

        # Create scatter plots for buy and sell markers
        buy_markers = [float('nan')] * len(df_copy)
        sell_markers = [float('nan')] * len(df_copy)

        for i, trade in entry_points.iterrows():
            if trade['entry_date'] in df_copy.index:
                idx = df_copy.index.get_loc(trade['entry_date'])
                buy_markers[idx] = trade['entry_price'] * 0.98 # Place marker slightly below the price

        for i, trade in exit_points.iterrows():
            if trade['exit_date'] in df_copy.index:
                idx = df_copy.index.get_loc(trade['exit_date'])
                sell_markers[idx] = trade['exit_price'] * 1.02 # Place marker slightly above the price

        ap.append(mpf.make_addplot(buy_markers, type='scatter', color='green', marker='^', markersize=100))
        ap.append(mpf.make_addplot(sell_markers, type='scatter', color='red', marker='v', markersize=100))

    ap.append(mpf.make_addplot(df_copy['MACD'], panel=1, color='purple', ylabel='MACD'))
    ap.append(mpf.make_addplot(df_copy['Signal Line'], panel=1, color='orange'))

    quote = "Consistency over blast"
    chart_title = f'Backtest Analysis for {instrument_name}\n"{quote}"'

    filename = f"{instrument_name}_backtest.png"

    mpf.plot(df_copy, type='candle', style='yahoo',
             title=chart_title,
             addplot=ap,
             panel_ratios=(3, 1),
             show_nontrading=True,
             savefig=filename)

    print(f"Generated backtest chart: {filename}")
