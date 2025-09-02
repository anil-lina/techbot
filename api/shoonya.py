import yaml
from NorenRestApiPy.NorenApi import NorenApi
import logging
from datetime import datetime

class ShoonyaAPIHandler(NorenApi):
    def __init__(self, config_path='stocks.yaml'):
        self._config_path = config_path
        self._load_config()
        super().__init__(host='https://api.shoonya.com/NorenWClientTP/',
                         websocket='wss://api.shoonya.com/NorenWSTP/')
        self._login()

    def _load_config(self):
        with open(self._config_path) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        self.creds = self.config.get('shoonya_creds', {})

    def _login(self):
        try:
            totp = input('Enter 2FA: ')
            ret = self.login(
                userid=self.creds['user'],
                password=self.creds['pwd'],
                twoFA=totp,
                vendor_code=self.creds['vc'],
                api_secret=self.creds['apikey'],
                imei=self.creds['imei']
            )
            if ret and ret.get('stat') == 'Ok':
                logging.info("Login successful.")
            else:
                logging.error(f"Login failed: {ret}")
                raise ConnectionError("Failed to login to Shoonya API")
        except Exception as e:
            logging.error(f"An error occurred during login: {e}")
            raise

    def get_itm(self, spot_price, idx_search, trade_date=None):
        if trade_date is None:
            trade_date = datetime.now()

        base = 100
        # Adjust base for specific indices if needed
        if idx_search in ['NIFTY', 'BANKNIFTY']:
            base = 50 if idx_search == 'NIFTY' else 100

        spot_price = float(spot_price)
        logging.info(f'LAST TRADING PRICE {idx_search} - {spot_price}')

        # A more flexible way to find strikes
        put_strike = base * round(spot_price / base)
        call_strike = base * round(spot_price / base)

        logging.info(f'{idx_search} - Searching around strike: {call_strike}')

        call_scrip_search = self.searchscrip('NFO', f"{idx_search} {call_strike}")
        put_scrip_search = self.searchscrip('NFO', f"{idx_search} {put_strike}")

        call_scrip = self._find_option(call_scrip_search, 'CE', call_strike, trade_date)
        put_scrip = self._find_option(put_scrip_search, 'PE', put_strike, trade_date)

        if not call_scrip or not put_scrip:
            logging.error("Could not find appropriate call or put scrips.")
            return None, None

        return call_scrip, put_scrip

    def _find_option(self, search_result, option_type, strike, trade_date):
        if not (search_result and search_result.get('stat') == 'Ok'):
            return None

        matching_options = []
        for value in search_result.get('values', []):
            # Check for option type. We look for nearest strike, not exact.
            if value.get('optt') == option_type:
                try:
                    # Expiry date format from Shoonya API is typically DDMMMYYYY
                    expiry_date = datetime.strptime(value.get('optexp'), '%d%b%Y')
                    # Only consider options that haven't expired yet
                    if expiry_date.date() >= trade_date.date():
                        # Calculate strike difference
                        strike_diff = abs(float(value.get('strprc', 0)) - strike)
                        matching_options.append((expiry_date, strike_diff, value))
                except (ValueError, TypeError):
                    # Ignore options with invalid date formats or other errors
                    continue

        if not matching_options:
            return None

        # Sort by expiry date first, then by how close the strike is
        matching_options.sort(key=lambda x: (x[0], x[1]))

        # Return the details of the best matching option
        return matching_options[0][2]
