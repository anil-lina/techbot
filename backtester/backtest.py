import pandas as pd
import logging
from datetime import datetime, timedelta
from strategy.example_strategy import MACD_HMA_Strategy
from utils.plotting import plot_backtest
from utils.indicators import groom_data
import numpy as np

class Backtester:
    def __init__(self, api_handler, config):
        self.api = api_handler
        self.config = config
        self.trade_settings = self.config.get('trade_settings', {})
        self.backtest_settings = self.config.get('backtest_settings', {})
        self.strategy_settings = self.config.get('strategy_settings', {})
        self.strategy = MACD_HMA_Strategy(
            self.api,
            self.trade_settings,
            self.backtest_settings,
            self.strategy_settings
        )

    def run(self, instrument_name, days=None, show_plot=True):
        """
        Runs a backtest by simulating trades on the stock's own historical data.
        """
        if days is None:
            days = self.backtest_settings.get('days', 30)

        logging.info(f"Starting backtest for {instrument_name} on its own equity data for the last {days} days.")

        # 1. Fetch historical data for the equity
        equity_quote = self.api.get_quotes('NSE', instrument_name)
        if not equity_quote or equity_quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        interval = self.strategy_settings.get('backtest_interval_minutes', 5)

        equity_series = self.api.get_time_price_series(
            exchange=equity_quote['exch'], token=equity_quote['token'],
            starttime=start_time.timestamp(), endtime=end_time.timestamp(), interval=interval
        )

        if not equity_series:
            logging.error(f"Could not fetch historical data for {instrument_name}.")
            return

        # 2. Generate signals on the equity data
        df = groom_data(equity_series)
        df_with_signals = self.strategy.generate_signals(df)

        # 3. Simulate trades based on signals
        trades = []
        position_open = False
        slippage = self.backtest_settings.get('slippage', 0.01)

        for i, candle in df_with_signals.iterrows():
            # Check for entry
            if candle['signal'] == 'BUY' and not position_open:
                entry_price = candle['entry_price'] * (1 + slippage)
                stop_loss_price = candle['stop_loss']

                trade = {
                    'entry_date': i, # i is the timestamp index
                    'entry_price': entry_price,
                    'stop_loss': stop_loss_price,
                    'exit_date': None,
                    'exit_price': None,
                    'exit_reason': None,
                    'symbol': instrument_name
                }
                trades.append(trade)
                position_open = True

            # Check for exit
            elif position_open:
                active_trade = trades[-1]
                # Check for stop-loss hit
                if candle['low'] <= active_trade['stop_loss']:
                    active_trade['exit_price'] = active_trade['stop_loss'] * (1 - slippage)
                    active_trade['exit_date'] = i
                    active_trade['exit_reason'] = 'Stop-Loss'
                    position_open = False
                # Check for sell signal exit
                elif candle['signal'] == 'SELL':
                    active_trade['exit_price'] = candle['close'] * (1 - slippage)
                    active_trade['exit_date'] = i
                    active_trade['exit_reason'] = 'Sell Signal'
                    position_open = False

        if not trades:
            logging.warning("No trades were executed in this backtest.")
            return

        # 4. Calculate and print statistics
        trade_df = pd.DataFrame(trades)
        completed_trades = trade_df.dropna(subset=['exit_price']).copy()

        if not completed_trades.empty:
            completed_trades['pnl'] = completed_trades['exit_price'] - completed_trades['entry_price']
            total_pnl = completed_trades['pnl'].sum()
            wins = completed_trades[completed_trades['pnl'] > 0]
            losses = completed_trades[completed_trades['pnl'] <= 0]
            win_rate = (len(wins) / len(completed_trades)) * 100
            avg_win = wins['pnl'].mean()
            avg_loss = losses['pnl'].mean()
            risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

            print("\n--- Backtest Results ---")
            print(f"Total Trades: {len(completed_trades)}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Total PnL: {total_pnl:.2f}")
            print(f"Average Win: {avg_win:.2f}")
            print(f"Average Loss: {avg_loss:.2f}")
            print(f"Risk/Reward Ratio: {risk_reward:.2f}")
            print("------------------------\n")

            # 5. Generate plot
            if show_plot:
                plot_backtest(df_with_signals, completed_trades, instrument_name)
        else:
            print("No completed trades to analyze.")
