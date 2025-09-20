import argparse
import logging
import os
import time
import pandas as pd
import concurrent.futures
from api.shoonya import ShoonyaAPIHandler
from strategy.example_strategy import MACD_HMA_Strategy

# --- Configuration ---
LOG_LEVEL = logging.INFO
# WARNING: Setting max_workers too high can overwhelm the API. Start low and increase.
MAX_WORKERS = 10
# Delay between API calls in each thread to prevent rate limiting
API_DELAY_SECONDS = 0.1

def setup_logging():
    """Sets up the logging for the script."""
    logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

def scan_symbol(symbol_data, strategy_instance):
    """
    Scans a single symbol (a row from the CSV).

    :param symbol_data: A dictionary-like object representing one row.
    :param strategy_instance: An instance of the trading strategy.
    :return: The original symbol_data if a signal is found, otherwise None.
    """
    try:
        token = symbol_data.get('Token')
        exchange = symbol_data.get('Exchange')
        trading_symbol = symbol_data.get('TradingSymbol')

        if not all([token, exchange, trading_symbol]):
            logging.warning(f"Skipping row due to missing data: {symbol_data}")
            return None

        logging.info(f"Scanning: {trading_symbol}")

        # Fetch historical data for the option itself
        # Using 5-min candles for testing API data retrieval
        df = strategy_instance._get_historical_data(
            instrument_token=token,
            exchange=exchange,
            interval=5,
            num_candles=200
        )

        # Respect API rate limits
        time.sleep(API_DELAY_SECONDS)

        if df.empty or len(df) < 60:
            return None

        # Apply strategy to generate signals
        df_with_signals = strategy_instance.generate_signals(df)

        # Check the most recent completed candle for a signal
        signal = df_with_signals.iloc[-2]['signal']

        if signal in ['BUY', 'SELL']:
            logging.critical(f"****** {signal} SIGNAL FOUND for {trading_symbol} ******")
            return symbol_data

    except Exception as e:
        logging.error(f"Error processing {symbol_data.get('TradingSymbol', 'Unknown')}: {e}", exc_info=True)

    return None

def main(args):
    """Main execution function."""
    setup_logging()

    # --- Initialize API and Strategy ---
    try:
        logging.info("Initializing API and authenticating...")
        with open('stocks.yaml', 'r') as f:
            config = yaml.safe_load(f)
        api = ShoonyaAPIHandler(config_path='stocks.yaml')
        strategy = MACD_HMA_Strategy(api, config.get('trade_settings', {}), strategy_settings=config.get('strategy_settings', {}))
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Failed to initialize API. Please check credentials and 2FA. Error: {e}")
        return

    # --- Read Input CSV ---
    try:
        logging.info(f"Reading symbols from {args.input_file}...")
        symbols_df = pd.read_csv(args.input_file)
        # Convert DataFrame to a list of dictionaries for easy processing
        symbols_to_scan = symbols_df.to_dict('records')
        logging.info(f"Found {len(symbols_to_scan)} symbols to scan.")
    except FileNotFoundError:
        logging.error(f"Input file not found: {args.input_file}")
        return
    except Exception as e:
        logging.error(f"Failed to read or process CSV file: {e}")
        return

    # --- Setup Output File ---
    if os.path.exists(args.output_file):
        os.remove(args.output_file)
        logging.info(f"Removed existing output file: {args.output_file}")

    # --- Parallel Scanning ---
    logging.info(f"Starting scan with {MAX_WORKERS} parallel workers...")
    found_signals = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create a future for each symbol to be scanned
        future_to_symbol = {executor.submit(scan_symbol, symbol_data, strategy): symbol_data for symbol_data in symbols_to_scan}

        for i, future in enumerate(concurrent.futures.as_completed(future_to_symbol)):
            result = future.result()
            if result:
                found_signals.append(result)

            # Log progress
            if (i + 1) % 100 == 0:
                logging.info(f"Progress: Scanned {i + 1}/{len(symbols_to_scan)} symbols...")

    # --- Save Results ---
    if found_signals:
        logging.info(f"Found {len(found_signals)} signals in total. Saving to {args.output_file}...")
        results_df = pd.DataFrame(found_signals)
        results_df.to_csv(args.output_file, index=False)
        logging.info("Results saved successfully.")
    else:
        logging.info("Scan complete. No signals found matching the criteria.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan NFO symbols for trading signals.")
    parser.add_argument(
        "--input_file",
        type=str,
        default="NFO_symbols.csv",
        help="Path to the input CSV file with NFO symbols."
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="resultant.csv",
        help="Path to save the resulting signals."
    )

    # Need to load yaml to get creds for API init
    import yaml

    parsed_args = parser.parse_args()
    main(parsed_args)
