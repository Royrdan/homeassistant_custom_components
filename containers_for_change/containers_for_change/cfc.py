import sys
import yaml
import requests
import datetime

class containers_for_change():

    def __init__(self, username, password, address, suburb, postcode, mobile, bag_location, unit=''):
        self.api_url = "https://coex-api.romeo.digital/"
        self.base_url = "https://cfcbookings.italicsbold.com.au"
        self.username = username
        self.password = password
        self.headers = {}
        if unit:
            address_type = 'Unit'
        else:
            address_type = 'House'
        self.customer_details = {
            'address_type': address_type,
            'unit': unit,
            'address': address,
            'suburb': suburb,
            'postcode': postcode,
            'mobile': mobile,
            'bag_location': bag_location,
        }
        self.client_secret = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
        self.login_access_token = None
        self.access_token = None
        self.headers = {
            'Authorization': '',
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate',
            'accept-language': 'en-AU,en-US;q=0.9,en;q=0.8',
            'cache-control': 'no-cache',
            'connection': 'keep-alive',
            'host': 'cfcbookings.italicsbold.com.au',
            'origin': 'https://localhost',
            'referer': 'https://localhost/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Linux; Android 12; SM-G988B Build/SP2A.220305.013; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.65 Mobile Safari/537.36',
            'x-requested-with': 'au.containersforchange.app',
        }

    def get_access_token(self, token_type):
        if token_type == 'login':
            url = self.api_url + 'auth/login/api'
            data = {'username': self.username, 'password': self.password}
        elif token_type == 'access':
            url = self.base_url + "/oauth/token"
            data={
                'client_id': 2,
                'client_secret': self.client_secret,
                'username': 'hello@italicsbold.com.au',
                'password': '123123',
                'grant_type': 'password',
            }
        else:
            return 'Authorization Failed invalid token requested'

        req_raw = requests.post(url , data=data )
        if req_raw.status_code < 200 or req_raw.status_code > 299:
            return "Error: Returned status code " + str(req_raw.status_code)
        try:
            req = req_raw.json()
            if token_type == 'login':
                self.login_access_token = req['access_token']
                return None
            else:
                self.access_token = req['access_token']
                return None

        except Exception as e:
            return f'Authorization Failed {e}'

    def get_customer_details(self):
        if not self.login_access_token:
            error = self.get_access_token('login')
            if error:
                return error
        self.headers['Authorization'] = 'Bearer ' + self.login_access_token
        ext = 'user-info'
        req_raw = requests.get(self.api_url + ext, headers = self.headers)
        if req_raw.status_code < 200 or req_raw.status_code > 299:
            return "Error: Returned status code " + str(req_raw.status_code)
        try:
            req = req_raw.json()
            self.customer_details.update(req)
        except Exception as e:
            return e

    def get_closest_date(self):
        self.headers['Authorization'] = 'Bearer ' + self.access_token
        ext = "/api/locations"

        try:
            req_raw = requests.get(self.base_url + ext, headers = self.headers)
            if req_raw.status_code < 200 or req_raw.status_code > 299:
                return None, None, "Error: Returned status code " + str(req_raw.status_code)
            locations = req_raw.json()['locations']
            location_id = None
            date = None
            for location in locations:
                if self.customer_details['postcode'] in location['postcodes_array']:
                    if self.customer_details['suburb'] in location['allowed_suburbs_array']:
                        location_id = location['id']
                        dates_list = [datetime.datetime.strptime(date['date'], '%Y-%m-%d') for date in location['location_dates'] ]
                        date = min(dates_list).strftime('%Y-%m-%d')
                        break
        except Exception as e:
            return None, None, e

        return location_id, date, None

    def book_collection(self, bags):
        # check if logged in
        if not self.login_access_token:
            print('Logging in...')
            error = self.get_access_token('login')
            if error:
                return None, error
            print('Login Access Token:\n' + self.login_access_token)
        # check if access token
        if not self.access_token:
            print('Retreiving access token...')
            error = self.get_access_token('access')
            if error:
                return None, error
            print('Access Token:\n' + self.access_token)

        print('Getting customer details...')
        error = self.get_customer_details()
        if error:
            return None, error
        print(self.customer_details)
        print('Getting location details and dates...')
        location_id, date, error = self.get_closest_date()
        if error:
            return None, error

        full_address = f"{self.customer_details['address']}, {self.customer_details['suburb']}, {self.customer_details['defaultSchemeId']}, Australia"
        if self.customer_details['unit']:
            full_address = f"{self.customer_details['unit']}, {full_address}"

        booking_details = {
            "scheme_id": self.customer_details['consumerId'],
            "email": self.username,
            "first_name": self.customer_details['firstName'],
            "last_name": self.customer_details['lastName'],
            "mobile": self.customer_details['mobile'],
            "active": 1,
            "address_type": self.customer_details['address_type'],
            "unit": self.customer_details['unit'],
            "street": '',
            "suburb": self.customer_details['suburb'],
            "postcode": self.customer_details['postcode'],
            "bag_location": self.customer_details['bag_location'],
            "date": date,
            "bags": bags,
            "location_id": location_id,
            "address": full_address,
        }
        self.headers['Authorization'] = 'Bearer ' + self.access_token
        ext = "/api/bookings"

        print('request url ' + self.base_url + ext)
        print(self.headers)
        print(booking_details)


        req_raw = requests.post(
            self.base_url + ext,
            headers = self.headers,
            data = booking_details,
        )
        if req_raw.status_code < 200 or req_raw.status_code > 299:
            return None, "Error: Returned status code " + str(req_raw.status_code)

        req = req_raw.json()
        try:
            return req['id'], "Success"
        except:
            return None, "Returned invalid data"
