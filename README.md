# Trading Bot

This is a Python-based trading bot designed to scan for opportunities and backtest trading strategies for equity options.

## Features

- **Modular Code:** The project is broken down into easy-to-understand modules for the API, strategy, scanner, and backtester.
- **Configuration File:** Easily manage your settings, credentials, and instrument lists in the `stocks.yaml` file.
- **Multi-Threaded Scanner:** The scanner runs checks for multiple instruments at the same time to quickly find trading signals.
- **Realistic Backtester:** Test your strategy on historical data. The backtester simulates how you would trade options based on signals from the underlying stock.
- **HTML Charting:** The bot generates interactive HTML charts (using Plotly) for every signal found by the scanner and for every backtest run, so you can visually analyze the results.

## Setup Instructions

1.  **Install Dependencies:**
    First, you need to install all the required Python libraries. Run the following command in your terminal:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Your Credentials:**
    Open the `stocks.yaml` file. You **must** fill in your Shoonya API credentials under the `shoonya_creds` section.
    ```yaml
    shoonya_creds:
      user: your_user_id
      pwd: your_password
      vc: your_vc
      apikey: your_api_key
      imei: your_imei
    ```

## How to Run the Bot

The bot can be run in two modes: `scan` for live scanning or `backtest` for testing your strategy.

### To Run the Scanner

The scanner will check all the instruments listed in your `stocks.yaml` file for trading signals based on the defined strategy.

Run this command in your terminal:
```bash
python main.py scan
```
When a signal is found, it will attempt to place an order and will also generate an HTML chart file named something like `RELIANCE24OCT2800CE_signal_20240901_103000.html`.

### To Run a Backtest

The backtester will test the strategy on a single instrument over a historical period (default is 30 days).

Run this command in your terminal. You must specify the instrument you want to test.
```bash
python main.py backtest --instrument RELIANCE-EQ
```
*   Replace `RELIANCE-EQ` with the symbol of the stock you want to test.

This will print a summary of the backtest results (like PnL and Win Rate) and generate an HTML chart file in the `charts/backtest/` folder.

---

### How to Run the High-Speed NFO Scanner

This is a separate, powerful tool for scanning a large list of options contracts directly.

**1. Prepare Your Input File:**
You must create a file named `NFO_symbols.csv` in the root directory. It must contain the following headers:
`Exchange,Token,LotSize,Symbol,TradingSymbol,Expiry,Instrument,OptionType,StrikePrice,TickSize`

This file should contain the 76,000+ NFO symbols you want to scan.

**2. Run the Scanner:**
Use this command to start the scan. It will process the symbols in parallel.
```bash
python nfo_scanner.py
```

**3. Check the Output:**
The scanner will create a file named `resultant.csv`. This file will contain the full rows from your input CSV for any options that matched the strategy's BUY or SELL criteria. The file is created fresh on each run.
