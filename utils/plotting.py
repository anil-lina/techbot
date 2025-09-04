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
    Generates an interactive plot using Plotly, saving to the new folder structure.
    """
    signal_type = signal_candle['signal'].lower() if signal_candle is not None else 'no_signal'
    save_path = f"charts/scanner/{signal_type}/"
    _ensure_dir_exists(save_path)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{symbol} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Candlestick'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['HMA'], mode='lines', name='HMA (50)'), row=1, col=1)

    if 'vwma' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['vwma'], mode='lines', name='VWMA (17)'), row=1, col=1)

    if signal_candle is not None:
        line_color = 'green' if signal_type == 'buy' else 'red'
        signal_time = signal_candle.name
        y_min, y_max = df['low'].min(), df['high'].max()
        fig.add_trace(go.Scatter(x=[signal_time, signal_time], y=[y_min, y_max], mode='lines', line=dict(color=line_color, width=1, dash='dash'), name=f'{signal_type.upper()} Signal'))

    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)

    quote = "Consistency over blast"
    fig.update_layout(title_text=f'{title_prefix} {symbol} - "{quote}"', xaxis_rangeslider_visible=False)

    # This now uses the default plotly behavior which hides non-trading days.

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{save_path}{symbol}_signal_{timestamp}.html"
    fig.write_html(filename)
    print(f"Generated signal chart: {filename}")


def plot_backtest(df, trade_df, instrument_name):
    """
    Generates an interactive plot for the backtest results using Plotly.
    """
    save_path = "charts/backtest/"
    _ensure_dir_exists(save_path)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{instrument_name} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Candlestick'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['HMA'], mode='lines', name='HMA (50)'), row=1, col=1)

    if not trade_df.empty:
        entry_points = trade_df[trade_df['entry_price'].notna()]
        exit_points = trade_df[trade_df['exit_price'].notna()]
        fig.add_trace(go.Scatter(x=entry_points['entry_date'], y=entry_points['entry_price'], mode='markers', name='Buy Entry', marker=dict(color='green', size=10, symbol='triangle-up')), row=1, col=1)
        fig.add_trace(go.Scatter(x=exit_points['exit_date'], y=exit_points['exit_price'], mode='markers', name='Sell Exit', marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], mode='lines', name='MACD'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['Signal Line'], mode='lines', name='Signal Line'), row=2, col=1)

    quote = "Consistency over blast"
    # Create stats table for HTML report
    pnl = trade_df['pnl'].sum()
    stats_text = f"Total PnL: {pnl:.2f} | Win Rate: {trade_df[trade_df['pnl']>0].shape[0]/trade_df.shape[0]*100:.2f}% | Trades: {trade_df.shape[0]}"

    fig.update_layout(
        title_text=f'Backtest Analysis for {instrument_name} - "{quote}"<br><sup>{stats_text}</sup>',
        xaxis_rangeslider_visible=False,
        legend_title_text='Indicators & Trades'
    )

    filename = f"{save_path}{instrument_name}_backtest.html"
    fig.write_html(filename)
    print(f"Generated backtest report: {filename}")
