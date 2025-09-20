import logging
from datetime import datetime, timedelta
from api.shoonya import ShoonyaAPIHandler

# --- INSTRUCTIONS ---
# 1. Run this script from your terminal: python api_test.py
# 2. It will ask for your 2FA token.
# 3. It will then attempt to fetch data for a single, hardcoded NFO token.
#
# --- WHAT TO DO WITH THE OUTPUT ---
# - If you see data printed, it means the API call works and there is a subtle bug
#   in the main application that we need to find.
# - If you see "API response: None" or an error, it confirms the issue is with the
#   API or your account. You can send this ENTIRE script and its output to your
#   broker's API support team.
#
# --- SAMPLE MESSAGE FOR BROKER SUPPORT ---
#
# Subject: Issue with get_time_price_series for NFO symbols
#
# Hello,
#
# I am unable to fetch historical time series data for any NFO options contracts
# using the get_time_price_series function. It consistently returns None or an
# empty response for all valid, non-expired NFO tokens.
#
# I have confirmed the issue is not with the interval, time window, or exchange
# parameter. Equity data (NSE) works fine, but NFO data does not.
#
# Below is a simple, self-contained Python script that demonstrates the issue.
# Please run it with valid credentials to reproduce the error.
#
# [Paste the entire content of this api_test.py file here]
#
# When I run it, the output is:
#
# [Paste the output from your terminal here]
#
# Could you please investigate why this API call is failing for NFO symbols?
#
# Thank you.
# -----------------------------------------------------------------------------

def setup_logging():
    """Sets up basic logging."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """Main function to run the API test."""
    setup_logging()

    # --- Pick a sample NFO token to test ---
    # This is a random NIFTY option token. If you have a specific one from your
    # fresh NFO_symbols.csv that you want to test, replace the values below.
    test_token = "53899" # Example Token
    test_exchange = "NFO" # Exchange for the token
    test_symbol = "NIFTY26SEP24C23500" # Symbol for logging

    logging.info(f"--- Starting API Test for one symbol: {test_symbol} ---")

    # --- Initialize API ---
    try:
        logging.info("Initializing API and authenticating...")
        api = ShoonyaAPIHandler(config_path='stocks.yaml')
        logging.info("Authentication successful.")
    except Exception as e:
        logging.error(f"Failed to initialize API: {e}", exc_info=True)
        return

    # --- Attempt to Fetch Data ---
    try:
        logging.info(f"Attempting to fetch 5-minute data for token: {test_token} on exchange: {test_exchange}")

        end_time = datetime.now()
        start_time = end_time - timedelta(days=5)

        time_series = api.get_time_price_series(
            exchange=test_exchange,
            token=test_token,
            starttime=start_time.timestamp(),
            endtime=end_time.timestamp(),
            interval=5 # Using 5-min interval as a test
        )

        logging.info("--- TEST RESULT ---")
        print(f"API response: {time_series}")
        logging.info("--- END OF TEST ---")

        if time_series:
            logging.info("SUCCESS: Data was received from the API.")
        else:
            logging.error("FAILURE: No data was received from the API (response was None or empty).")

    except Exception as e:
        logging.error(f"An exception occurred during the API call: {e}", exc_info=True)

if __name__ == "__main__":
    main()
