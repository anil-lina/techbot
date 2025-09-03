import yaml
from NorenRestApiPy.NorenApi import NorenApi
import logging
from datetime import datetime
import json
import os

class ShoonyaAPIHandler(NorenApi):
    def __init__(self, config_path='stocks.yaml'):
        self._config_path = config_path
        self._session_file = 'session.json'
        self._load_config()
        super().__init__(host='https://api.shoonya.com/NorenWClientTP/',
                         websocket='wss://api.shoonya.com/NorenWSTP/')
        self._login()

    def _load_config(self):
        with open(self._config_path) as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        self.creds = self.config.get('shoonya_creds', {})

    def _save_session(self):
        session_data = {
            'susertoken': self.susertoken,
            'userid': self.creds['user']
        }
        with open(self._session_file, 'w') as f:
            json.dump(session_data, f)
        logging.info("Session token saved.")

    def _load_and_validate_session(self):
        if not os.path.exists(self._session_file):
            return False

        with open(self._session_file, 'r') as f:
            session_data = json.load(f)

        # Set the session token and check if it's valid with a lightweight call
        self.set_session(
            userid=session_data['userid'],
            password=self.creds['pwd'],
            usertoken=session_data['susertoken']
        )

        # Test call to see if session is valid
        test_call = self.get_limits()
        if test_call and test_call.get('stat') == 'Ok':
            logging.info("Successfully re-used existing session.")
            return True
        else:
            logging.warning("Existing session token has expired. Please log in again.")
            os.remove(self._session_file) # Clean up expired session file
            return False

    def _login(self):
        # Try to load an existing session first
        if self._load_and_validate_session():
            return

        # If no valid session, proceed with interactive login
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
                self._save_session() # Save the new session
            else:
                logging.error(f"Login failed: {ret}")
                raise ConnectionError("Failed to login to Shoonya API")
        except Exception as e:
            logging.error(f"An error occurred during login: {e}")
            raise

    def get_itm(self, spot_price, idx_search, trade_date=None):
        if trade_date is None:
            trade_date = datetime.now()

        spot_price = float(spot_price)
        logging.info(f'Finding ITM options for {idx_search} around spot price: {spot_price}')

        search_results = self.searchscrip('NFO', idx_search)

        call_scrip = self._find_option(search_results, 'CE', spot_price, trade_date)
        put_scrip = self._find_option(search_results, 'PE', spot_price, trade_date)

        if not call_scrip:
            logging.warning(f"Could not find a suitable ITM Call for {idx_search}")
        if not put_scrip:
            logging.warning(f"Could not find a suitable ITM Put for {idx_search}")

        return call_scrip, put_scrip

    def _find_option(self, search_result, option_type, spot_price, trade_date):
        if not (search_result and search_result.get('stat') == 'Ok'):
            return None

        matching_options = []
        for value in search_result.get('values', []):
            if value.get('optt') == option_type:
                try:
                    expiry_date = datetime.strptime(value.get('optexp'), '%d%b%Y')
                    strike_price = float(value.get('strprc', 0))

                    is_itm = (option_type == 'CE' and strike_price < spot_price) or \
                             (option_type == 'PE' and strike_price > spot_price)

                    if expiry_date.date() >= trade_date.date() and is_itm:
                        itm_diff = abs(spot_price - strike_price)
                        matching_options.append((expiry_date, itm_diff, value))
                except (ValueError, TypeError):
                    continue

        if not matching_options:
            return None

        matching_options.sort(key=lambda x: (x[0], x[1]))

        return matching_options[0][2]
