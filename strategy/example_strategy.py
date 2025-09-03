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
        """
        Applies new strategy indicators and generates signals.
        """
        if df.empty:
            return df

        # Get indicator periods from settings
        hma_period = self.strategy_settings.get('hma_period', 50)
        atr_period = self.strategy_settings.get('atr_period', 14) # ATR is 14 by default in atr()
        macd_fast = self.strategy_settings.get('macd_fast_period', 12)
        macd_slow = self.strategy_settings.get('macd_slow_period', 26)
        macd_signal = self.strategy_settings.get('macd_signal_period', 9)

        # --- Indicator Calculations ---
        df['HMA'] = hull_moving_average(df['close'], hma_period)
        df['ATR'] = atr(df, n=atr_period)
        df['MACD'], df['Signal Line'] = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df['MACD_Crossover'] = detect_crossovers(df, 'MACD', 'Signal Line')

        # --- Signal Generation ---
        df['signal'] = 'HOLD'

        # LONG Entry Rules
        long_conditions = (
            (df['close'] > df['HMA']) &
            (df['MACD_Crossover'] == 1) &
            (df['MACD'] > 0) # Crossover should ideally be above zero line for confirmation
        )
        df.loc[long_conditions, 'signal'] = 'BUY'

        # SHORT Entry Rules
        short_conditions = (
            (df['close'] < df['HMA']) &
            (df['MACD_Crossover'] == -1) &
            (df['MACD'] < 0) # Crossover should ideally be below zero line for confirmation
        )
        df.loc[short_conditions, 'signal'] = 'SELL'

        # --- Exit & Risk Management Calculations ---
        # These columns will be calculated but only used if the backtester is updated to support them.
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0

        for i in range(len(df)):
            if df['signal'].iloc[i] == 'BUY':
                entry_price = df['close'].iloc[i]
                stop_loss_price = df['low'].iloc[i] - (3 * df['ATR'].iloc[i])
                risk_per_share = entry_price - stop_loss_price
                take_profit_price = entry_price + (risk_per_share * 2.5)
                df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
                df.iloc[i, df.columns.get_loc('take_profit')] = take_profit_price

            elif df['signal'].iloc[i] == 'SELL':
                entry_price = df['close'].iloc[i]
                stop_loss_price = df['high'].iloc[i] + (3 * df['ATR'].iloc[i])
                risk_per_share = stop_loss_price - entry_price
                take_profit_price = entry_price - (risk_per_share * 2.5)
                df.iloc[i, df.columns.get_loc('stop_loss')] = stop_loss_price
                df.iloc[i, df.columns.get_loc('take_profit')] = take_profit_price

        return df

    def _get_historical_data(self, instrument_token, exchange, interval=60, num_candles=200):
        """
        Fetches historical data. Timeframe is now hardcoded to 60min for primary signals.
        """
        end_time = datetime.now()
        # Fetch enough data for a 50-period HMA on a 1H chart. 200 candles = ~1 month of data.
        start_time = end_time - timedelta(days=30)

        time_series = self.api.get_time_price_series(
            exchange=exchange, token=instrument_token,
            starttime=start_time.timestamp(), endtime=end_time.timestamp(),
            interval=interval
        )

        if not time_series:
            logging.warning(f"No data received for token {instrument_token}")
            return pd.DataFrame()

        return groom_data(time_series)

    def execute(self, instrument_info):
        """
        Scanner Logic: Executes the new strategy on the 1H stock chart.
        """
        from utils.plotting import plot_chart

        instrument_name, _ = instrument_info
        logging.info(f"Scanning stock with new strategy: {instrument_name}")

        quote = self.api.get_quotes('NSE', instrument_name)
        if not quote or quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        # Fetch 1-Hour data for signal generation
        df_1h = self._get_historical_data(quote['token'], quote['exch'], interval=60, num_candles=200)

        if df_1h.empty or len(df_1h) < 60: # Need at least 50 for HMA + buffer
            logging.warning(f"Not enough 1H data for {instrument_name} to scan.")
            return

        df_with_signals = self.generate_signals(df_1h)

        last_signal_info = df_with_signals.iloc[-2]
        signal_type = last_signal_info['signal']

        if signal_type in ['BUY', 'SELL']:
            logging.critical(f"****** {signal_type} SIGNAL (New Strategy) ON STOCK: {instrument_name} ******")
            try:
                plot_chart(df_with_signals, instrument_name, last_signal_info, title_prefix=f"New Strategy {signal_type} Signal for")
            except Exception as e:
                logging.error(f"Failed to generate chart for {instrument_name}: {e}", exc_info=True)
        else:
            logging.info(f"No signal for {instrument_name} with new strategy.")
