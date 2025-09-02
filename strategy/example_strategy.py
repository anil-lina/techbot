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

        # Define entry and stop-loss
        df['entry_price'] = df['close']  # Entry at close of signal candle
        df['stop_loss'] = df['low'] - df['ATR'] # SL is low of candle minus ATR

        # Generate signals based on strategy rules
        # Buy signal: MACD crossover and close is above HMA
        df['signal'] = 'HOLD'
        buy_conditions = (df['MACD_Crossover'] == 1) & (df['close'] > df['HMA'])
        df.loc[buy_conditions, 'signal'] = 'BUY'

        # In a real scenario, you would also define sell signals.
        # For now, we focus on the entry signal as in the original script.

        return df

    def _get_historical_data(self, instrument_token, exchange, interval=1, num_candles=50):
        """
        Fetches and prepares historical data for an instrument.
        Fetches a limited number of recent candles.
        """
        end_time = datetime.now()
        # Estimate start time based on interval and number of candles
        start_time = end_time - timedelta(minutes=interval * (num_candles + 5)) # Add buffer

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
        return df.tail(num_candles) # Return only the required number of candles

    def execute(self, instrument_info):
        """
        Main execution logic for the strategy for a given instrument.
        This is intended to be called by the scanner.
        """
        instrument_name, instrument_symbol = instrument_info
        logging.info(f"Running strategy for {instrument_name}...")

        # 1. Get underlying quote to find ITM options
        quote = self.api.get_quotes('NSE', instrument_name)
        if not quote or quote.get('stat') != 'Ok':
            logging.error(f"Could not get quote for {instrument_name}")
            return

        last_price = float(quote.get('lp', 0))
        if last_price == 0:
            logging.error(f"Last price is zero for {instrument_name}")
            return

        # 2. Find ITM call and put options
        call_details, put_details = self.api.get_itm(last_price, instrument_symbol)

        if not call_details:
            logging.warning(f"Could not find ITM call for {instrument_name}")
        else:
            self._process_option(call_details, "CE")

        if not put_details:
            logging.warning(f"Could not find ITM put for {instrument_name}")
        else:
            self._process_option(put_details, "PE")

    def _process_option(self, option_details, option_type):
        """
        Fetches data, generates signals, and places an order for an option.
        """
        from utils.plotting import plot_chart # Import here to avoid circular dependency issues

        logging.info(f"Processing {option_details['tsym']} ({option_type})")

        # Get recent historical data for the option
        df = self._get_historical_data(option_details['token'], option_details['exch'], interval=1, num_candles=50)

        if df.empty or len(df) < 20: # Need enough data for indicators
            logging.warning(f"Not enough data for {option_details['tsym']}")
            return

        # Generate signals
        df_with_signals = self.generate_signals(df)

        # Check for a buy signal on the most recent complete candle
        last_signal = df_with_signals.iloc[-2] # Use -2 to avoid acting on a still-forming candle

        if last_signal['signal'] == 'BUY':
            logging.info(f"BUY SIGNAL DETECTED for {option_details['tsym']}")

            try:
                order_response = self.api.place_order(
                    buy_or_sell='B',
                    product_type='I', # Intraday
                    exchange=option_details['exch'],
                    tradingsymbol=option_details['tsym'],
                    quantity=self.trade_settings.get('lots', 1) * int(option_details['ls']),
                    discloseqty=0,
                    price_type='MKT', # Market order for faster execution
                    price=0,
                    trigger_price=None,
                    retention='DAY',
                    remarks='Automated scanner trade'
                )
                logging.info(f"Order placed for {option_details['tsym']}: {order_response}")

                # Generate a chart for the signal
                plot_chart(df_with_signals, option_details['tsym'], last_signal)

            except Exception as e:
                logging.error(f"Failed to place order for {option_details['tsym']}: {e}")
        else:
            logging.info(f"No signal for {option_details['tsym']}")
