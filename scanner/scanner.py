import concurrent.futures
import logging
from strategy.example_strategy import MACD_HMA_Strategy

class Scanner:
    def __init__(self, api_handler, config):
        self.api = api_handler
        self.config = config
        self.instruments = self.config.get('instruments', [])
        self.trade_settings = self.config.get('trade_settings', {})
        self.strategy = MACD_HMA_Strategy(self.api, self.trade_settings)

    def _scan_instrument(self, instrument):
        """
        Wrapper function to scan a single instrument.
        instrument is a list like ['RELIANCE-EQ', 'RELIANCE']
        """
        instrument_name, instrument_details = instrument
        try:
            self.strategy.execute_for_instrument(instrument_details, instrument_name)
        except Exception as e:
            logging.error(f"Error scanning instrument {instrument_name}: {e}")

    def run(self):
        """
        Runs the scanner across all instruments using multiple threads.
        """
        if not self.instruments:
            logging.warning("No instruments found in the configuration file.")
            return

        logging.info(f"Starting scanner for {len(self.instruments)} instruments...")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # map the function to the list of instruments
            executor.map(self._scan_instrument, self.instruments)

        logging.info("Scanner run finished.")
