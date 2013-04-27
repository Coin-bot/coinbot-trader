#!/usr/bin/env python
##
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import base64
import hashlib
import hmac
import json
import time
import urllib

import webapp2
from google.appengine.api import urlfetch
import config


class MainHandler(webapp2.RequestHandler):
    def get(self):
        self.response.write('Coin-bot Trader!')


class BaseMtGoxHandler(webapp2.RequestHandler):
    MTGOX_API_BASE = 'https://data.mtgox.com/api/2/'

    def _nonce(self):
        return str(int(time.time() * 1e6))

    def _request(self, method, path, data=None):
        hash_data = path + chr(0)
        if data:
            data["nonce"] = self._nonce()
            hash_data += urllib.urlencode(data)
        secret = base64.b64decode(config.MTGOX_SECRET)
        hmac_val = base64.b64encode(hmac.new(secret, hash_data, hashlib.sha512).digest())

        headers = {
            'User-Agent': 'Coin-Bot Trader',
            'Rest-Key': config.MTGOX_KEY,
            'Rest-Sign': hmac_val,
        }
        payload = json.dumps(data)
        result = urlfetch.fetch(url=self.MTGOX_API_BASE + path, method=method, payload=payload, headers=headers)
        return result


class MtGoxOrderHandler(BaseMtGoxHandler):
    def get(self):
        secret = self.request.get("secret")
        if secret != config.SECRET:  # check secret
            self.abort(403)
        currency = self.request.get("currency")
        order_type = self.request.get("order_type")
        amount = self.request.get("amount")
        price = self.request.get("price")
        if currency == '' or order_type == '' or amount == '' or price == '' \
            or currency not in ['USD', 'AUD', 'EUR'] or order_type not in ['ask', 'bid']:  # parameters are missing or not valid
            self.abort(500)
        amount = float(amount)
        price = float(price)
        if amount < 0.01 or (config.MTGOX_MAX_AMOUNT and amount > config.MTGOX_MAX_AMOUNT) or (
                config.MTGOX_MIN_AMOUNT and amount < config.MTGOX_MIN_AMOUNT):  # validate amount
            self.abort(500)
        if (config.MTGOX_MAX_PRICE and price > config.MTGOX_MAX_PRICE) or (
                config.MTGOX_MIN_PRICE and price < config.MTGOX_MIN_PRICE):  # validate price
            self.abort(500)
        data = {
            "type": order_type,
            "amount_int": amount * 1e8,
            "price_int": price * 1e5
        }
        self._request(method="POST", path="BTC%s/MONEY/ORDER/ADD" % currency.upper(), data=data)


url_map = [
    ('/', MainHandler),
    ('/mtgox/order', MtGoxOrderHandler)
]


app = webapp2.WSGIApplication(url_map, debug=True)
