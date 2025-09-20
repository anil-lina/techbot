import logging
import pandas as pd
from api.shoonya import ShoonyaAPIHandler

def setup_logging():
    """Sets up the logging for the script."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main execution function to fetch and save all NFO symbols."""
    setup_logging()

    # --- Initialize API ---
    try:
        logging.info("Initializing API and authenticating...")
        api = ShoonyaAPIHandler(config_path='stocks.yaml')
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Failed to initialize API. Please check credentials and 2FA. Error: {e}")
        return

    # --- Fetch All NFO Symbols ---
    # The searchscrip function with a wildcard or a common stock can return many symbols.
    # A common technique is to search for a high-volume underlying like NIFTY or RELIANCE.
    # Searching for '*' might not be supported; we'll search for a common prefix.
    logging.info("Fetching all tradable NFO symbols... This may take a moment.")

    # We will search for common prefixes to get a wide range of symbols.
    # A more robust solution might require an API endpoint that lists all symbols directly.
    # This is a best-effort approach.
    all_symbols = []
    search_prefixes = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" # Search for each letter

    for prefix in search_prefixes:
        logging.info(f"Searching for symbols starting with {prefix}...")
        results = api.searchscrip(exchange='NFO', searchtext=prefix)
        if results and results.get('stat') == 'Ok':
            all_symbols.extend(results.get('values', []))

    if not all_symbols:
        logging.error("Could not fetch any symbols from the API. The API might be down or the search method needs adjustment.")
        return

    logging.info(f"Found a total of {len(all_symbols)} symbols. Processing and saving...")

    # --- Create and Save DataFrame ---
    df = pd.DataFrame(all_symbols)

    # The user specified these headers. We must match them.
    # Let's check the columns we received from the API (via one sample)
    # Common names are 'exch', 'token', 'lotsize', 'symbol', 'tsym', 'expiry', 'instname', 'opttype', 'strprc', 'ti'
    # We will rename our DataFrame columns to match the user's requested headers.

    column_mapping = {
        'exch': 'Exchange',
        'token': 'Token',
        'ls': 'LotSize',
        'symbol': 'Symbol',
        'tsym': 'TradingSymbol',
        'optexp': 'Expiry',
        'instname': 'Instrument',
        'optt': 'OptionType',
        'strprc': 'StrikePrice',
        'ti': 'TickSize'
    }

    df.rename(columns=column_mapping, inplace=True)

    # Ensure all required columns are present, fill missing ones with empty string
    required_headers = ['Exchange','Token','LotSize','Symbol','TradingSymbol','Expiry','Instrument','OptionType','StrikePrice','TickSize']
    for header in required_headers:
        if header not in df.columns:
            df[header] = ''

    # Keep only the required columns in the specified order
    df = df[required_headers]

    output_file = 'NFO_symbols.csv'
    try:
        df.to_csv(output_file, index=False)
        logging.info(f"Successfully saved {len(df)} symbols to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save the CSV file: {e}")

if __name__ == "__main__":
    main()
