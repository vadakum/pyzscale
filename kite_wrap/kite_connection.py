

import logging
import requests
import pyotp
import json
from typing import Final
from kiteconnect import KiteConnect


KiteLoginUrl : Final = "https://kite.zerodha.com/api/login"
TwoFactorAuthUrl : Final = "https://kite.zerodha.com/api/twofa"
#Redirect URL http://127.0.0.1
"""
Login using UserCredentials
"""


class ClientConnection:

    def __init__(self, creds):
        logging.debug('Creating kite client connection...')
        session = requests.Session()
        response = session.post(
            KiteLoginUrl,
            data={'user_id': creds['user_id'], 'password': creds['password']}
        )
        request_id = json.loads(response.text)['data']['request_id']
        logging.debug(
            f"Request id fetched from response of: {KiteLoginUrl}, is {request_id}")
        pyotp_pin = pyotp.TOTP(creds['totp_key']).now()
        logging.debug(
            f"Pyotp pin: ******, trying to login to auth url {TwoFactorAuthUrl}")
        session.post(TwoFactorAuthUrl,
                     data={'user_id':
                           creds['user_id'],
                           'request_id': request_id,
                           'twofa_value': pyotp_pin,
                           'twofa_type': 'totp'
                           }
                     )
        logging.debug(f"Connecting to kite using api_key...{creds['api_key']}")
        self._conn = KiteConnect(api_key=creds['api_key'])
        redir_url = self._conn.login_url()
        logging.debug(f"Kite redirect-url is {redir_url}, (this needs to be authenticated once through web)")
        request_token = None
        try:
            response = session.get(redir_url)
            logging.debug(f"Response url :{response.url}")
            logging.debug(f"response text => {response.text}")
        except Exception as e:
            e_msg = str(e)
            request_token = e_msg.split('request_token=')[1].split(' ')[
                0].split('&action')[0]
            logging.debug(f"Successfully fetched request Token {request_token}")
        if not request_token:
            raise ValueError("Unable to fetch request token using alternate method.")
        self._conn.generate_session(request_token, creds['api_secret'])
        if not self._conn.access_token:
            raise ValueError("Kite generate_session failed!")
        logging.info(f"Login successfull and session created for user: [{creds['user_id']}]!")

    def get(self) -> KiteConnect:
        return self._conn
