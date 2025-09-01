import argparse
import yaml
import logging
from api.shoonya import ShoonyaAPIHandler
from scanner.scanner import Scanner
from backtester.backtest import Backtester

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Trading Bot")
    parser.add_argument('mode', choices=['scan', 'backtest'], help="The mode to run the bot in.")
    parser.add_argument('--instrument', type=str, help="The instrument to backtest (e.g., 'RELIANCE-EQ'). Required for backtest mode.")
    parser.add_argument('--days', type=int, help="Number of days to backtest.")

    args = parser.parse_args()

    # Load configuration
    try:
        with open('stocks.yaml', 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("stocks.yaml not found. Please create it.")
        return
    except yaml.YAMLError as e:
        logging.error(f"Error parsing stocks.yaml: {e}")
        return

    # Initialize API Handler
    try:
        api = ShoonyaAPIHandler(config_path='stocks.yaml')
    except Exception as e:
        logging.error(f"Failed to initialize API: {e}")
        return

    # Run selected mode
    if args.mode == 'scan':
        scanner = Scanner(api, config)
        scanner.run()
    elif args.mode == 'backtest':
        if not args.instrument:
            parser.error("--instrument is required for backtest mode.")

        backtester = Backtester(api, config)
        backtester.run(instrument_name=args.instrument, days=args.days)

if __name__ == "__main__":
    main()
