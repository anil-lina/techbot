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
        self.strategy = MACD_HMA_Strategy(self.api, self.trade_settings, self.backtest_settings)
        self.option_data_cache = {}

    def _get_option_data(self, option_details, start_time, end_time):
        """
        Fetches and caches historical data for an option contract.
        """
        token = option_details['token']
        if token in self.option_data_cache:
            return self.option_data_cache[token]

        logging.info(f"Fetching historical data for {option_details['tsym']} ({token})")
        time_series = self.api.get_time_price_series(
            exchange=option_details['exch'],
            token=token,
            starttime=start_time.timestamp(),
            endtime=end_time.timestamp(),
            interval=5  # 5-minute interval for backtesting
        )

        if not time_series:
            logging.warning(f"No historical data found for {option_details['tsym']}")
            return pd.DataFrame()

        df = groom_data(time_series)
        df_with_signals = self.strategy.generate_signals(df)
        self.option_data_cache[token] = df_with_signals
        return df_with_signals

    def run(self, instrument_name, days=None, show_plot=True):
        if days is None:
            days = self.backtest_settings.get('days', 30)

        logging.info(f"Starting realistic backtest for {instrument_name} for the last {days} days.")

        # 1. Fetch historical data for the underlying equity
        equity_quote = self.api.get_quotes('NSE', instrument_name)
        if not equity_quote or equity_quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        equity_series = self.api.get_time_price_series(
            exchange=equity_quote['exch'], token=equity_quote['token'],
            starttime=start_time.timestamp(), endtime=end_time.timestamp(), interval=5
        )

        if not equity_series:
            logging.error(f"Could not fetch historical data for {instrument_name}.")
            return

        equity_df = groom_data(equity_series)

        trades = []
        slippage = self.backtest_settings.get('slippage', 0.01)

        # Find the corresponding option symbol for the given instrument name
        option_symbol = None
        for inst in self.config['instruments']:
            if inst[0] == instrument_name:
                option_symbol = inst[1]
                break

        if not option_symbol:
            logging.error(f"Could not find options symbol for {instrument_name} in stocks.yaml")
            return

        # 2. Iterate through each candle of the underlying equity's data
        for i in range(len(equity_df)):
            current_candle = equity_df.iloc[i]
            current_time = current_candle['time']
            current_price = current_candle['close']

            # 3. Find the relevant ITM options for the current moment in time
            # Note: This is a simplified simulation. A real implementation would need to handle expiry dates robustly.
            # We are assuming get_itm finds the nearest expiry options for the given price.
            call_details, put_details = self.api.get_itm(current_price, option_symbol)
            if not call_details or not put_details:
                continue

            # 4. Process both Call and Put options
            for option_details in [call_details, put_details]:
                option_df = self._get_option_data(option_details, start_time, end_time)
                if option_df.empty:
                    continue

                # Find the corresponding candle in the option's data
                option_candle = option_df[option_df['time'] == current_time]
                if option_candle.empty:
                    continue

                # 5. Check for entry signal ON THE OPTION'S DATA at the current time
                if option_candle.iloc[0]['signal'] == 'BUY':
                    # Avoid re-entry if a position is already open in a similar option
                    if any(t['exit_price'] is None for t in trades):
                        continue

                    entry_price = option_candle.iloc[0]['entry_price'] * (1 + slippage)
                    sl = option_candle.iloc[0]['stop_loss']
                    # Set a take-profit target, e.g., 2x the risk (ATR)
                    tp = entry_price + (entry_price - sl) * 1.5

                    trade = {
                        'entry_date': current_time,
                        'entry_price': entry_price,
                        'stop_loss': sl,
                        'take_profit': tp,
                        'exit_date': None,
                        'exit_price': None,
                        'symbol': option_details['tsym']
                    }

                    # 6. Simulate the trade by looking ahead in the option's data
                    for j in range(option_candle.index[0] + 1, len(option_df)):
                        future_candle = option_df.iloc[j]
                        if future_candle['low'] <= sl:
                            trade['exit_price'] = sl * (1 - slippage)
                            trade['exit_date'] = future_candle['time']
                            break
                        if future_candle['high'] >= tp:
                            trade['exit_price'] = tp * (1 - slippage)
                            trade['exit_date'] = future_candle['time']
                            break

                    trades.append(trade)

        if not trades:
            logging.warning("No trades were executed in this backtest.")
            return

        # 7. Calculate and print statistics
        trade_df = pd.DataFrame(trades)
        trade_df.dropna(subset=['exit_price'], inplace=True) # Analyze completed trades only

        if not trade_df.empty:
            trade_df['pnl'] = trade_df['exit_price'] - trade_df['entry_price']
            total_pnl = trade_df['pnl'].sum()
            wins = trade_df[trade_df['pnl'] > 0]
            losses = trade_df[trade_df['pnl'] <= 0]
            win_rate = (len(wins) / len(trade_df)) * 100 if not trade_df.empty else 0
            avg_win = wins['pnl'].mean()
            avg_loss = losses['pnl'].mean()
            risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf

            print("\n--- Backtest Results ---")
            print(f"Total Trades: {len(trade_df)}")
            print(f"Win Rate: {win_rate:.2f}%")
            print(f"Total PnL: {total_pnl:.2f}")
            print(f"Average Win: {avg_win:.2f}")
            print(f"Average Loss: {avg_loss:.2f}")
            print(f"Risk/Reward Ratio: {risk_reward:.2f}")
            print("------------------------\n")

            # 8. Generate plot for the first traded option for simplicity
            if show_plot and not trade_df.empty:
                first_trade_symbol = trade_df.iloc[0]['symbol']
                first_trade_token = self.api.searchscrip('NFO', first_trade_symbol)['values'][0]['token']
                plot_df = self.option_data_cache[first_trade_token]
                plot_backtest(plot_df, trade_df[trade_df['symbol'] == first_trade_symbol], first_trade_symbol)
        else:
            print("No completed trades to analyze.")
