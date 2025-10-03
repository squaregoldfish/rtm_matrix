import toml
from hashlib import md5
import copy
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from dateutil import parser
from datetime import datetime, timedelta
import time
import pytz
from tzlocal import get_localzone
import logging
from operator import itemgetter
from Adafruit_LED_Backpack import BicolorMatrix8x8
import time

RTM_URL = 'https://api.rememberthemilk.com/services/rest/?'
RATE_LIMIT = 1
RATE_LIMIT_BACKOFF = 1
ALL_TASKS = '_all'
OVERDUE = -1
TODAY = 0
FUTURE = 1

# Temporary colors
RED = 0
YELLOW = 1
GREEN = 2

# Pre-defined symbols
NETWORK_ERROR = [[0, 7], [1, 7], [2, 7], [3, 7], [1, 6], [2, 5], [3, 4], [2, 4], [1, 4], [0, 4]]
GENERIC_ERROR = [[0, 7], [1, 7], [2, 7], [3, 7], [4, 7], [0, 6], [0, 5], [2, 6], [4, 6], [4, 5]]

def midnight(date_object):
    return date_object.replace(hour=0, minute=0, second=0, microsecond=0)

class rtm():
    def __init__(self, config):
        self.key = config['api_key']
        self.secret = config['shared_secret']
        self.token = config['token']
        self.tasks = list()
        self.last_request = None
        self.last_request_status = None
        self.processing_error = False

    def _request(self, method, params):
        if self.last_request is not None and (datetime.now() - self.last_request).seconds < RATE_LIMIT:
            time.sleep(RATE_LIMIT_BACKOFF)

        request_params = copy.deepcopy(params)
        request_params['method'] = method
        request_params['api_key'] = self.key
        request_params['auth_token'] = self.token
        request_params['format'] = 'json'

        request_params = dict(sorted(request_params.items()))

        request_string = RTM_URL
        sig = self.secret
        for (key, value) in request_params.items():
            request_string += f'{key}={value}&'
            sig += f'{key}{value}'

        request_string += f'api_sig={md5(sig.encode("utf-8")).hexdigest()}'
        
        session = requests.Session()
        retry = Retry(connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        response = session.get(request_string)
        self.last_request_status = response.status_code
        self.last_request = datetime.now()

        return response.json() if response.status_code == 200 else None

    def fetch_tasks(self):
        try:
            params = dict()
            params['filter'] = 'status:incomplete AND dueBefore:"3 days of today"'

            raw_tasks = self._request('rtm.tasks.getList', params)

            if raw_tasks is None:
                self.tasks = None
            else:
                task_list = list()

                today = midnight(datetime.now(get_localzone())).date()

                task_series = raw_tasks['rsp']['tasks']['list']

                for series in task_series:
                    for task in series['taskseries']:
                        recurring = 'rrule' in task
                        task_name = task['name']

                        for task_entry in task['task']:
                            entry_date = parser.parse(task_entry['due'])
                            local_date = midnight(entry_date.astimezone(get_localzone())).date()

                            if local_date < today:
                                status = OVERDUE
                            elif local_date == today:
                                status = TODAY
                            else:
                                status = FUTURE

                            task_item = dict()
                            task_item['due'] = local_date.strftime("%Y-%m-%d")
                            task_item['status'] = status
                            task_item['recurring'] = recurring

                            task_list.append(task_item)

                self.tasks = sorted(task_list, key=itemgetter('due'))
            self.processing_error = False
        except Exception as e:
            self.processing_error = True
            logging.error(e)

    def get_tasks(self):
        return self.tasks

def display_symbol(matrix, points, color):
    for point in points:
        matrix.set_pixel(point[0], point[1], color)

def display_vertical_binary(matrix, column, number, color):
    for bit in range(8):
        if 1 << bit & number:
            matrix.set_pixel(7 - bit, column, color)

def display_network_error(matrix, status_code):
    display_symbol(matrix, NETWORK_ERROR, BicolorMatrix8x8.RED)

    hundreds = int(status_code / 100)
    rest = status_code % 100
    display_vertical_binary(matrix, 1, hundreds, BicolorMatrix8x8.YELLOW)
    display_vertical_binary(matrix, 0, rest, BicolorMatrix8x8.YELLOW)

def display_binary_tasks(matrix, count, start_row, color):
    for bit in range(8):
        if 1 << bit & count:
            matrix.set_pixel(start_row, 7 - bit, color)

    for bit in range(8, 16):
        if 1 << bit & count:
            matrix.set_pixel(start_row - 1, 7 - bit, color)

def get_row(number):
    return 7 - int(number / 8)

def get_col(number):
    return 7 - number % 8

def display_simple_tasks(matrix, overdue, today, future):
    current_pos = 0
    for i in range(overdue):
        matrix.set_pixel(get_row(current_pos), get_col(current_pos), BicolorMatrix8x8.RED)
        current_pos += 1

    for i in range(current_pos, overdue + today):
        matrix.set_pixel(get_row(current_pos), get_col(current_pos), BicolorMatrix8x8.YELLOW)
        current_pos += 1

    for i in range(current_pos, overdue + today + future):
        matrix.set_pixel(get_row(current_pos), get_col(current_pos), BicolorMatrix8x8.GREEN)
        current_pos += 1


def display_tasks(matrix, overdue, today, future):
    if overdue + today + future > 64:
        display_binary_tasks(matrix, overdue, 7, BicolorMatrix8x8.RED)
        display_binary_tasks(matrix, today, 4, BicolorMatrix8x8.YELLOW)
        display_binary_tasks(matrix, future, 1, BicolorMatrix8x8.GREEN)
    else:
        display_simple_tasks(matrix, overdue, today, future)




if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    # Initialise matrix display
    matrix_config = config['matrix']
    matrix = BicolorMatrix8x8.BicolorMatrix8x8(address=matrix_config['address'], busnum=matrix_config['i2c_bus'])
    matrix.begin()
    matrix.set_brightness(matrix_config['brightness'])

    instance = rtm(config['rtm'])

    while True:
        instance.fetch_tasks()
        matrix.clear()

        if instance.last_request_status != 200:
            display_network_error(matrix, instance.last_request_status)
        elif instance.processing_error:
            display_symbol(matrix, GENERIC_ERROR, BicolorMatrix8x8.RED)
        else:
            overdue = 0
            today = 0
            future = 0

            for task in instance.get_tasks():
                if task['status'] == OVERDUE:
                    overdue += 1
                elif task['status'] == TODAY:
                    today += 1
                else:
                    future += 1

            display_tasks(matrix, overdue, today, future)

        matrix.write_display()
        time.sleep(60)
