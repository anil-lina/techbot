from .base_strategy import BaseStrategy
from utils.indicators import (
    groom_data,
    calculate_macd,
    hull_moving_average,
    atr,
    detect_crossovers,
    vwma,
)
import logging
import pandas as pd
from datetime import datetime, timedelta

class MACD_HMA_Strategy(BaseStrategy):
    def __init__(self, api_handler, trade_settings, backtest_settings=None, strategy_settings=None):
        super().__init__(api_handler, trade_settings)
        self.backtest_settings = backtest_settings if backtest_settings else {}
        # Use provided strategy settings or an empty dict
        self.strategy_settings = strategy_settings if strategy_settings else {}

    def generate_signals(self, df):
        """
        Applies indicators and generates buy/sell signals using configurable settings.
        """
        if df.empty:
            return df

        # Get indicator periods from settings, with defaults
        hma_period = self.strategy_settings.get('hma_period', 15)
        vwma_period = self.strategy_settings.get('vwma_period', 17)
        macd_fast = self.strategy_settings.get('macd_fast_period', 12)
        macd_slow = self.strategy_settings.get('macd_slow_period', 26)
        macd_signal = self.strategy_settings.get('macd_signal_period', 9)

        df['HMA'] = hull_moving_average(df['close'], hma_period)
        df['ATR'] = atr(df)
        df['MACD'], df['Signal Line'] = calculate_macd(df, macd_fast, macd_slow, macd_signal)
        df['MACD_Crossover'] = detect_crossovers(df, 'MACD', 'Signal Line')

        if 'volume' in df.columns and df['volume'].sum() > 0:
            df['vwma'] = vwma(df, period=vwma_period)

        df['entry_price'] = df['close']
        df['stop_loss'] = df['low'] - df['ATR']

        df['signal'] = 'HOLD'
        buy_conditions = (df['MACD_Crossover'] == 1) & (df['close'] > df['HMA'])
        df.loc[buy_conditions, 'signal'] = 'BUY'

        sell_conditions = (df['MACD_Crossover'] == -1) & (df['close'] < df['HMA'])
        df.loc[sell_conditions, 'signal'] = 'SELL'

        return df

    def _get_historical_data(self, instrument_token, exchange, interval=1, num_candles=50):
        """
        Fetches and prepares historical data for an instrument.
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(days=5)

        time_series = self.api.get_time_price_series(
            exchange=exchange,
            token=instrument_token,
            starttime=start_time.timestamp(),
            endtime=end_time.timestamp(),
            interval=interval
        )

        if not time_series:
            logging.warning(f"No data received for token {instrument_token}")
            return pd.DataFrame()

        df = groom_data(time_series)
        return df.tail(num_candles) if not df.empty else df

    def execute(self, instrument_info):
        """
        Scanner Logic: Executes the strategy on the stock chart itself.
        """
        from utils.plotting import plot_chart

        instrument_name, _ = instrument_info
        logging.info(f"Scanning stock: {instrument_name}")

        quote = self.api.get_quotes('NSE', instrument_name)
        if not quote or quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        # Use scanner settings from the config file
        interval = self.strategy_settings.get('scan_interval_minutes', 5)
        num_candles = self.strategy_settings.get('scan_num_candles', 100)

        df = self._get_historical_data(quote['token'], quote['exch'], interval=interval, num_candles=num_candles)

        if df.empty or len(df) < 50:
            logging.warning(f"Not enough data for {instrument_name} to scan.")
            return

        df_with_signals = self.generate_signals(df)

        last_signal_info = df_with_signals.iloc[-2]
        signal_type = last_signal_info['signal']

        if signal_type in ['BUY', 'SELL']:
            logging.critical(f"****** {signal_type} SIGNAL DETECTED ON STOCK: {instrument_name} ******")
            try:
                plot_chart(df_with_signals, instrument_name, last_signal_info, title_prefix=f"Stock {signal_type} Signal for")
            except Exception as e:
                logging.error(f"Failed to generate chart for {instrument_name}: {e}", exc_info=True)
        else:
            logging.info(f"No signal for {instrument_name}")
