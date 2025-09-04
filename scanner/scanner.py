import concurrent.futures
import logging
from strategy.example_strategy import MACD_HMA_Strategy
import os
import pandas as pd

class Scanner:
    def __init__(self, api_handler, config):
        self.api = api_handler
        self.config = config
        self.instruments = self.config.get('instruments', [])
        self.trade_settings = self.config.get('trade_settings', {})
        self.strategy_settings = self.config.get('strategy_settings', {})
        self.strategy = MACD_HMA_Strategy(
            self.api,
            self.trade_settings,
            strategy_settings=self.strategy_settings
        )

    def _scan_instrument(self, instrument):
        """
        Wrapper function to scan a single instrument.
        Returns a dictionary with signal info.
        """
        try:
            return self.strategy.execute(instrument)
        except Exception as e:
            logging.error(f"Error scanning instrument {instrument[0]}: {e}", exc_info=True)
            return None

    def _ensure_dir_exists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def run(self):
        """
        Runs the scanner and saves buy/sell signals to separate CSV files.
        """
        if not self.instruments:
            logging.warning("No instruments found in the configuration file.")
            return

        # Define paths and ensure base charts directory exists
        base_path = 'charts/'
        buy_csv_path = os.path.join(base_path, 'buy.csv')
        sell_csv_path = os.path.join(base_path, 'sell.csv')
        self._ensure_dir_exists(base_path)

        # Delete old CSV files
        if os.path.exists(buy_csv_path): os.remove(buy_csv_path)
        if os.path.exists(sell_csv_path): os.remove(sell_csv_path)
        logging.info("Removed old signal CSV files.")

        logging.info(f"Starting scanner for {len(self.instruments)} instruments...")

        buy_signals = []
        sell_signals = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_instrument = {executor.submit(self._scan_instrument, inst): inst for inst in self.instruments}

            for future in concurrent.futures.as_completed(future_to_instrument):
                try:
                    result = future.result()
                    if result and result['signal'] != 'HOLD':
                        signal_info = {
                            'instrument': result['instrument'],
                            'strike_price': result['strike']
                        }
                        if result['signal'] == 'BUY':
                            buy_signals.append(signal_info)
                        elif result['signal'] == 'SELL':
                            sell_signals.append(signal_info)
                except Exception as exc:
                    logging.error(f'A scan generated an exception: {exc}')

        # Save buy signals
        if buy_signals:
            df_buy = pd.DataFrame(buy_signals)
            df_buy.to_csv(buy_csv_path, index=False)
            logging.info(f"Found {len(buy_signals)} BUY signals. Saved to {buy_csv_path}")
        else:
            logging.info("No BUY signals found during the scan.")

        # Save sell signals
        if sell_signals:
            df_sell = pd.DataFrame(sell_signals)
            df_sell.to_csv(sell_csv_path, index=False)
            logging.info(f"Found {len(sell_signals)} SELL signals. Saved to {sell_csv_path}")
        else:
            logging.info("No SELL signals found during the scan.")

        logging.info("Scanner run finished.")
