import yaml
from NorenRestApiPy.NorenApi import NorenApi
import logging

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

    def get_itm(self, spot_price, idx_search):
        base = 100
        spot_price = float(spot_price)
        logging.info(f'LAST TRADING PRICE {idx_search} - {spot_price}')

        put_strike = round(base * round((spot_price + (spot_price * 0.0035)) / base))
        call_strike = round(base * round((spot_price - (spot_price * 0.0035)) / base))

        logging.info(f'{idx_search} - Call side: {call_strike}, Put side: {put_strike}')

        # This part of the logic needs to be verified as it depends on the exact format of the search result
        # Assuming the original logic for index [3] and [2] is correct for call and put respectively
        call_scrip_search = self.searchscrip('NFO', f"{idx_search} {call_strike}")
        put_scrip_search = self.searchscrip('NFO', f"{idx_search} {put_strike}")

        # It's safer to search for the correct CE/PE instrument rather than relying on a fixed index
        call_scrip = self._find_option(call_scrip_search, 'CE', call_strike)
        put_scrip = self._find_option(put_scrip_search, 'PE', put_strike)

        if not call_scrip or not put_scrip:
            logging.error("Could not find appropriate call or put scrips.")
            return None, None

        return call_scrip, put_scrip

    def _find_option(self, search_result, option_type, strike):
        if search_result and search_result.get('stat') == 'Ok':
            for value in search_result.get('values', []):
                if value.get('optt') == option_type and float(value.get('strprc', 0)) == strike:
                    return value
        return None
