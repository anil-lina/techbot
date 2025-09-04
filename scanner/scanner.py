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
        Returns any ITM options found.
        """
        try:
            return self.strategy.execute(instrument)
        except Exception as e:
            logging.error(f"Error scanning instrument {instrument[0]}: {e}", exc_info=True)
            return []

    def run(self):
        """
        Runs the scanner across all instruments and saves all found ITM options to a CSV file.
        """
        if not self.instruments:
            logging.warning("No instruments found in the configuration file.")
            return

        # Delete old CSV file if it exists
        csv_path = 'itm_options.csv'
        if os.path.exists(csv_path):
            os.remove(csv_path)
            logging.info(f"Removed old {csv_path}")

        logging.info(f"Starting scanner for {len(self.instruments)} instruments...")

        all_itm_options = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Submit all scan jobs to the executor
            future_to_instrument = {executor.submit(self._scan_instrument, inst): inst for inst in self.instruments}

            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_instrument):
                instrument = future_to_instrument[future]
                try:
                    itm_options = future.result()
                    if itm_options:
                        all_itm_options.extend(itm_options)
                except Exception as exc:
                    logging.error(f'{instrument[0]} generated an exception: {exc}')

        # Save all collected ITM options to a single CSV file
        if all_itm_options:
            df = pd.DataFrame(all_itm_options)
            # Reorder columns for better readability
            cols_to_have = ['underlying', 'tsym', 'optt', 'strprc', 'optexp', 'token', 'exch', 'ls']
            existing_cols = [col for col in cols_to_have if col in df.columns]
            df = df[existing_cols]
            df.to_csv(csv_path, index=False)
            logging.info(f"Successfully saved {len(all_itm_options)} ITM options to {csv_path}")
        else:
            logging.warning("No ITM options were found during the scan.")

        logging.info("Scanner run finished.")
