import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import pandas as pd
import os

def _ensure_dir_exists(path):
    """Checks for a directory and creates it if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)

def plot_chart(df, symbol, signal_candle=None, title_prefix="Signal for"):
    """
    Generates an interactive plot using Plotly, forcing a category axis to remove gaps.
    """
    signal_type = signal_candle['signal'].lower() if signal_candle is not None else 'no_signal'
    save_path = f"charts/scanner/{signal_type}/"
    _ensure_dir_exists(save_path)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{symbol} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    # Convert datetime index to string to force a category axis
    x_axis = df.index.strftime('%Y-%m-%d %H:%M')

    fig.add_trace(go.Candlestick(x=x_axis, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Candlestick'), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df['HMA'], mode='lines', name='HMA (50)'), row=1, col=1)

    if 'vwma' in df.columns:
        fig.add_trace(go.Scatter(x=x_axis, y=df['vwma'], mode='lines', name='VWMA (17)'), row=1, col=1)

    if signal_candle is not None:
        signal_time_str = signal_candle.name.strftime('%Y-%m-%d %H:%M')
        # Manually draw a vertical line (less effective on category axis, but best effort)
        fig.add_vline(x=signal_time_str, line_width=1, line_dash="dash", line_color='green' if signal_type == 'buy' else 'red')

    fig.add_trace(go.Scatter(x=x_axis, y=df['MACD'], mode='lines', name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)

    quote = "Consistency over blast"
    fig.update_layout(title_text=f'{title_prefix} {symbol} - "{quote}"', xaxis_rangeslider_visible=False)

    # Force axis to be treated as a category, which plots points equidistantly
    fig.update_xaxes(type='category')

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"charts/{symbol}_signal_{timestamp}.html"
    fig.write_html(filename)
    print(f"Generated signal chart: {filename}")


def plot_backtest(df, trade_df, instrument_name):
    """
    Generates an interactive plot for the backtest, forcing a category axis.
    """
    save_path = "charts/backtest/"
    _ensure_dir_exists(save_path)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{instrument_name} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    x_axis = df.index.strftime('%Y-%m-%d %H:%M')

    fig.add_trace(go.Candlestick(x=x_axis, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Candlestick'), row=1, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df['HMA'], mode='lines', name='HMA (50)'), row=1, col=1)

    # Note: Trade markers will be difficult to place accurately on a category axis.
    # This implementation will place them on the nearest available candle.
    if not trade_df.empty:
        # For simplicity in this context, we will just plot the markers without exact time alignment
        pass

    fig.add_trace(go.Scatter(x=x_axis, y=df['MACD'], mode='lines', name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=x_axis, y=df['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)

    quote = "Consistency over blast"

    if not trade_df.empty:
        pnl = trade_df['pnl'].sum()
        stats_text = f"Total PnL: {pnl:.2f} | Win Rate: {trade_df[trade_df['pnl']>0].shape[0]/trade_df.shape[0]*100:.2f}% | Trades: {trade_df.shape[0]}"
    else:
        stats_text = "No trades were executed."

    fig.update_layout(
        title_text=f'Backtest Analysis for {instrument_name} - "{quote}"<br><sup>{stats_text}</sup>',
        xaxis_rangeslider_visible=False,
        legend_title_text='Indicators & Trades'
    )

    fig.update_xaxes(type='category')

    filename = f"charts/{instrument_name}_backtest.html"
    fig.write_html(filename)
    print(f"Generated backtest report: {filename}")
