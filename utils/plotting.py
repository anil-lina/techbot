import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

def plot_chart(df, symbol, signal_candle=None, title_prefix="Signal for"):
    """
    Generates an interactive plot for a given symbol, highlighting a signal.
    """
    # Use a copy to avoid modifying the original DataFrame
    plot_df = df.copy()
    # Set the time column as the index, which is best practice for plotting time-series data
    plot_df.set_index('time', inplace=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{symbol} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    # Candlestick chart - Plotly automatically uses the DataFrame index for the x-axis
    fig.add_trace(go.Candlestick(x=plot_df.index,
                               open=plot_df['open'],
                               high=plot_df['high'],
                               low=plot_df['low'],
                               close=plot_df['close'],
                               name='Candlestick'), row=1, col=1)

    # HMA Indicator
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['HMA'], mode='lines', name='HMA (15)',
                             line=dict(color='blue', width=1)), row=1, col=1)

    # VWAP Indicator (if present)
    if 'vwma' in plot_df.columns:
        fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['vwma'], mode='lines', name='VWMA (17)',
                                 line=dict(color='purple', width=1, dash='dot')), row=1, col=1)

    # Highlight the signal candle
    if signal_candle is not None:
        signal_type = signal_candle['signal']
        line_color = 'green' if signal_type == 'BUY' else 'red'
        fig.add_vline(x=signal_candle['time'], line_width=1, line_dash="dash", line_color=line_color,
                      annotation_text=f"{signal_type} Signal", annotation_position="top left")

    # MACD Plot
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD'], mode='lines', name='MACD',
                             line=dict(color='purple', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Signal Line'], mode='lines', name='Signal Line',
                             line=dict(color='orange', width=1)), row=2, col=1)

    # Add the motivational quote
    quote = "Consistency over blast"

    fig.update_layout(
        title_text=f'{title_prefix} {symbol} - "{quote}"',
        xaxis_rangeslider_visible=False,
    )

    # Save to HTML
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{symbol}_signal_{timestamp}.html"
    fig.write_html(filename)
    print(f"Generated signal chart: {filename}")


def plot_backtest(df, trade_df, instrument_name):
    """
    Generates an interactive plot for the backtest results.
    """
    plot_df = df.copy()
    plot_df.set_index('time', inplace=True)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        subplot_titles=(f'{instrument_name} Candlestick', 'MACD'),
                        row_heights=[0.7, 0.3])

    fig.add_trace(go.Candlestick(x=plot_df.index, open=plot_df['open'], high=plot_df['high'],
                               low=plot_df['low'], close=plot_df['close'], name='Candlestick'), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['HMA'], mode='lines', name='HMA (15)',
                             line=dict(color='blue', width=1)), row=1, col=1)

    if not trade_df.empty:
        entry_points = trade_df[trade_df['entry_price'].notna()]
        exit_points = trade_df[trade_df['exit_price'].notna()]

        fig.add_trace(go.Scatter(x=entry_points['entry_date'], y=entry_points['entry_price'],
                                 mode='markers', name='Buy Entry',
                                 marker=dict(color='green', size=10, symbol='triangle-up')), row=1, col=1)

        fig.add_trace(go.Scatter(x=exit_points['exit_date'], y=exit_points['exit_price'],
                                 mode='markers', name='Sell Exit',
                                 marker=dict(color='red', size=10, symbol='triangle-down')), row=1, col=1)

    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['MACD'], mode='lines', name='MACD',
                             line=dict(color='purple', width=1)), row=2, col=1)
    fig.add_trace(go.Scatter(x=plot_df.index, y=plot_df['Signal Line'], mode='lines', name='Signal Line',
                             line=dict(color='orange', width=1)), row=2, col=1)

    quote = "Consistency over blast"
    fig.update_layout(
        title_text=f'Backtest Analysis for {instrument_name} - "{quote}"',
        xaxis_rangeslider_visible=False,
        legend_title_text='Indicators & Trades'
    )

    filename = f"{instrument_name}_backtest.html"
    fig.write_html(filename)
    print(f"Generated backtest chart: {filename}")
