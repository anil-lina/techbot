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
    def __init__(self, api_handler, trade_settings, backtest_settings=None):
        super().__init__(api_handler, trade_settings)
        self.backtest_settings = backtest_settings if backtest_settings else {}

    def generate_signals(self, df):
        """
        Applies indicators and generates buy/sell signals.
        """
        if df.empty:
            return df

        df['HMA'] = hull_moving_average(df['close'], 15)
        df['ATR'] = atr(df)
        df['MACD'], df['Signal Line'] = calculate_macd(df)
        df['MACD_Crossover'] = detect_crossovers(df, 'MACD', 'Signal Line')

        if 'volume' in df.columns and df['volume'].sum() > 0:
            df['vwma'] = vwma(df, period=17)

        # Define entry and stop-loss (used by backtester)
        df['entry_price'] = df['close']
        df['stop_loss'] = df['low'] - df['ATR']

        # Generate signals based on strategy rules
        df['signal'] = 'HOLD'
        # Buy Signal: Bullish crossover and price is above HMA
        buy_conditions = (df['MACD_Crossover'] == 1) & (df['close'] > df['HMA'])
        df.loc[buy_conditions, 'signal'] = 'BUY'

        # Sell Signal: Bearish crossover and price is below HMA
        sell_conditions = (df['MACD_Crossover'] == -1) & (df['close'] < df['HMA'])
        df.loc[sell_conditions, 'signal'] = 'SELL'

        return df

    def _get_historical_data(self, instrument_token, exchange, interval=1, num_candles=50):
        """
        Fetches and prepares historical data for an instrument.
        """
        end_time = datetime.now()
        # Request a wider window (e.g., 5 days) to ensure enough data is captured
        # even when running outside of market hours.
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
        # Return the last N candles, ensuring the DataFrame is not empty
        return df.tail(num_candles) if not df.empty else df

    def execute(self, instrument_info):
        """
        Scanner Logic: Executes the strategy on the stock chart itself.
        If a signal is found, it logs an alert and generates a chart.
        """
        from utils.plotting import plot_chart

        instrument_name, _ = instrument_info
        logging.info(f"Scanning stock: {instrument_name}")

        quote = self.api.get_quotes('NSE', instrument_name)
        if not quote or quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        df = self._get_historical_data(quote['token'], quote['exch'], interval=5, num_candles=100)

        if df.empty or len(df) < 50:
            logging.warning(f"Not enough data for {instrument_name} to scan.")
            return

        df_with_signals = self.generate_signals(df)

        last_signal_info = df_with_signals.iloc[-2]
        signal_type = last_signal_info['signal']

        if signal_type in ['BUY', 'SELL']:
            logging.critical(f"****** {signal_type} SIGNAL DETECTED ON STOCK: {instrument_name} ******")

            # Add extensive logging for debugging the plotting issue
            logging.info(f"--- Debugging Chart Data for {instrument_name} ---")
            logging.info(f"Signal Candle Name (Timestamp): {last_signal_info.name}")
            logging.info(f"Type of Signal Candle Name: {type(last_signal_info.name)}")
            logging.info(f"Signal Candle Info:\n{last_signal_info.to_string()}")
            logging.info(f"DataFrame Index Head:\n{df_with_signals.index.head().to_string()}")
            logging.info(f"--- End of Debugging Info ---")

            try:
                plot_chart(df_with_signals, instrument_name, last_signal_info, title_prefix=f"Stock {signal_type} Signal for")
            except Exception as e:
                logging.error(f"Failed to generate chart for {instrument_name}: {e}", exc_info=True)
        else:
            logging.info(f"No signal for {instrument_name}")
