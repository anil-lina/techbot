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
        self.option_data_cache = {}

    def _get_option_data(self, option_details, start_time, end_time):
        """
        Fetches and caches historical data for an option contract.
        """
        token = option_details['token']
        if token in self.option_data_cache:
            return self.option_data_cache[token]

        logging.info(f"Fetching historical data for {option_details['tsym']} ({token})")

        interval = self.strategy_settings.get('backtest_interval_minutes', 5)

        time_series = self.api.get_time_price_series(
            exchange=option_details['exch'],
            token=token,
            starttime=start_time.timestamp(),
            endtime=end_time.timestamp(),
            interval=interval
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

        for i in range(len(equity_df)):
            current_candle = equity_df.iloc[i]
            current_time = current_candle.name
            current_price = current_candle['close']

            call_details, put_details = self.api.get_itm(current_price, option_symbol, trade_date=current_time)

            for option_details in [call_details, put_details]:
                if not option_details:
                    continue

                option_df = self._get_option_data(option_details, start_time, end_time)
                if option_df.empty:
                    continue

                if current_time not in option_df.index:
                    continue

                option_candle = option_df.loc[current_time]

                if option_candle['signal'] == 'BUY':
                    if any(t['exit_price'] is None for t in trades):
                        continue

                    entry_price = option_candle['entry_price'] * (1 + slippage)
                    sl = option_candle['stop_loss']
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

                    future_candles = option_df[option_df.index > current_time]
                    for future_time, future_candle in future_candles.iterrows():
                        if future_candle['low'] <= sl:
                            trade['exit_price'] = sl * (1 - slippage)
                            trade['exit_date'] = future_time
                            break
                        if future_candle['high'] >= tp:
                            trade['exit_price'] = tp * (1 - slippage)
                            trade['exit_date'] = future_time
                            break

                    trades.append(trade)

        if not trades:
            logging.warning("No trades were executed in this backtest.")
            return

        trade_df = pd.DataFrame(trades)
        trade_df.dropna(subset=['exit_price'], inplace=True)

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

            if show_plot and not trade_df.empty:
                first_trade_symbol = trade_df.iloc[0]['symbol']

                # Find token for the first traded symbol to retrieve its data from cache
                first_trade_details = self.api.searchscrip('NFO', first_trade_symbol)
                if first_trade_details and first_trade_details['stat'] == 'Ok':
                    first_trade_token = first_trade_details['values'][0]['token']
                    if first_trade_token in self.option_data_cache:
                        plot_df = self.option_data_cache[first_trade_token]
                        plot_backtest(plot_df, trade_df[trade_df['symbol'] == first_trade_symbol], first_trade_symbol)
        else:
            print("No completed trades to analyze.")
