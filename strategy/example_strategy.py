from .base_strategy import BaseStrategy
from utils.indicators import (
    groom_data,
    calculate_macd,
    hull_moving_average,
    atr,
    detect_crossovers,
)
import logging
import pandas as pd
from datetime import datetime, timedelta

class MACD_HMA_Strategy(BaseStrategy):
    def __init__(self, api_handler, trade_settings, backtest_settings=None, strategy_settings=None):
        super().__init__(api_handler, trade_settings)
        self.strategy_settings = strategy_settings if strategy_settings else {}

    def generate_signals(self, df):
        if df.empty: return df

        hma_period = self.strategy_settings.get('hma_period', 50)
        atr_period = self.strategy_settings.get('atr_period', 14)
        macd_fast = self.strategy_settings.get('macd_fast_period', 12)
        macd_slow = self.strategy_settings.get('macd_slow_period', 26)
        macd_signal = self.strategy_settings.get('macd_signal_period', 9)

        df['HMA'] = hull_moving_average(df['close'], hma_period)
        df['ATR'] = atr(df, n=atr_period)
        df['MACD'], df['Signal Line'] = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df['MACD_Crossover'] = detect_crossovers(df, 'MACD', 'Signal Line')

        long_conditions = ((df['close'] > df['HMA']) & (df['MACD_Crossover'] == 1))
        short_conditions = ((df['close'] < df['HMA']) & (df['MACD_Crossover'] == -1))

        df['signal'] = 'HOLD'
        df.loc[long_conditions, 'signal'] = 'BUY'
        df.loc[short_conditions, 'signal'] = 'SELL'

        return df

    def _get_historical_data(self, instrument_token, exchange, interval=60, num_candles=200):
        end_time = datetime.now()
        # The user confirmed a 10-day window works. The API likely has a smaller limit for options data.
        start_time = end_time - timedelta(days=10)
        time_series = self.api.get_time_price_series(
            exchange=exchange, token=instrument_token,
            starttime=start_time.timestamp(), endtime=end_time.timestamp(),
            interval=interval
        )
        if not time_series:
            logging.warning(f"No data received for token {instrument_token}")
            return pd.DataFrame()

        df = groom_data(time_series)
        return df

    def execute(self, instrument_info):
        """
        Scanner Logic: Analyzes stock chart and returns signal info.
        """
        from utils.plotting import plot_chart

        instrument_name, option_symbol = instrument_info
        logging.info(f"Scanning stock: {instrument_name}")

        quote = self.api.get_quotes('NSE', instrument_name)
        if not quote or quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return None

        # --- Signal analysis on the stock ---
        df_1h = self._get_historical_data(quote['token'], quote['exch'], interval=60, num_candles=200)

        if df_1h.empty or len(df_1h) < 60:
            logging.warning(f"Not enough 1H data for {instrument_name} to scan.")
            return None

        df_with_signals = self.generate_signals(df_1h)

        last_signal_info = df_with_signals.iloc[-2]
        signal_type = last_signal_info['signal']

        result = {'instrument': instrument_name, 'signal': 'HOLD', 'strike': None}

        if signal_type in ['BUY', 'SELL']:
            logging.critical(f"****** {signal_type} SIGNAL ON STOCK: {instrument_name} ******")
            try:
                plot_chart(df_with_signals, instrument_name, last_signal_info, title_prefix=f"Stock {signal_type} Signal for")
            except Exception as e:
                logging.error(f"Failed to generate chart for {instrument_name}: {e}", exc_info=True)

            last_price = float(quote.get('lp', 0))
            atm_strike = round(last_price / 100) * 100

            result['signal'] = signal_type
            result['strike'] = atm_strike
        else:
            logging.info(f"No signal for {instrument_name}.")

        return result
