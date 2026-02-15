from Adafruit_LED_Backpack import BicolorMatrix8x8
import copy
from datetime import datetime, timedelta
from dateutil import parser
from hashlib import md5
import logging
import math
from operator import itemgetter
import requests
from requests.adapters import HTTPAdapter
from threading import Thread
import time
import traceback
from tzlocal import get_localzone
from urllib3.util.retry import Retry


class RTM():
    _RTM_URL = 'https://api.rememberthemilk.com/services/rest/?'
    _RATE_LIMIT = 50
    _RATE_LIMIT_BACKOFF = 15
    _ALL_TASKS = '_all'
    _OVERDUE = -1
    _TODAY = 0
    _FUTURE = 1

    # Pre-defined symbols
    _NETWORK_ERROR = [[0, 7], [1, 7], [2, 7], [3, 7], [1, 6], [2, 5], [3, 4], [2, 4], [1, 4], [0, 4]]
    _GENERIC_ERROR = [[0, 7], [1, 7], [2, 7], [3, 7], [4, 7], [0, 6], [0, 5], [2, 6], [4, 6], [4, 5]]

    def __init__(self, matrix, config):
        self._matrix = matrix

        self._key = config['api_key']
        self._secret = config['shared_secret']
        self._token = config['token']

        self._tasks = list()
        self._last_request = None
        self._last_request_status = None
        self._processing_error = False

        self._alerts = None

        Thread(target=self._run, ).start()

    def _run(self):
        while True:
            self._fetch_tasks()
            if self._alerts is None or not self._alerts.showing_alert:
                self.display_tasks()
            time.sleep(60)

    def register_alerts(self, alerts):
        self._alerts = alerts

    def _request(self, method, params):
        if self._last_request is not None and (datetime.now() - self._last_request).seconds < self._RATE_LIMIT:
            time.sleep(self._RATE_LIMIT_BACKOFF)

        request_params = copy.deepcopy(params)
        request_params['method'] = method
        request_params['api_key'] = self._key
        request_params['auth_token'] = self._token
        request_params['format'] = 'json'

        request_params = dict(sorted(request_params.items()))

        request_string = self._RTM_URL
        sig = self._secret
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
        self._last_request_status = response.status_code
        self._last_request = datetime.now()

        return response.json() if response.status_code == 200 else None

    def _fetch_tasks(self):
        try:
            params = dict()
            params['filter'] = 'status:incomplete AND dueBefore:"3 days of self._TODAY"'

            raw_tasks = self._request('rtm.tasks.getList', params)

            if raw_tasks is None:
                self._tasks = None
            else:
                task_list = list()

                self._TODAY = self._midnight(datetime.now(get_localzone())).date()

                task_series = raw_tasks['rsp']['tasks']['list']

                for series in task_series:
                    for task in series['taskseries']:
                        recurring = 'rrule' in task
                        task_name = task['name']

                        for task_entry in task['task']:
                            entry_date = parser.parse(task_entry['due'])
                            local_date = self._midnight(entry_date.astimezone(get_localzone())).date()

                            if local_date < self._TODAY:
                                status = self._OVERDUE
                            elif local_date == self._TODAY:
                                status = self._TODAY
                            else:
                                status = self._FUTURE

                            task_item = dict()
                            task_item['due'] = local_date.strftime("%Y-%m-%d")
                            task_item['status'] = status
                            task_item['recurring'] = recurring

                            task_list.append(task_item)

                self._tasks = sorted(task_list, key=itemgetter('due'))
            self._processing_error = False
        except Exception as e:
            self._processing_error = True
            logging.error(traceback.format_exc())


    def display_tasks(self):
        if self._last_request_status is not None and self._last_request_status != 200:
            self._display_network_error()
        elif self._processing_error:
            self._display_symbol(self._GENERIC_ERROR, BicolorMatrix8x8.RED)
        else:
            overdue = 0
            today = 0
            future = 0

            for task in self._tasks:
                if task['status'] == self._OVERDUE:
                    overdue += 1
                elif task['status'] == self._TODAY:
                    today += 1
                else:
                    future += 1

            self._draw_tasks(overdue, today, future)
            with open('task_count.txt', 'w') as count_file:
                count_file.write(f'{overdue + today + future}')

    def _display_symbol(self, points, color):
        for point in points:
            self._matrix.set_pixel(point[0], point[1], color)

    def _display_vertical_binary(self, column, number, color):
        for bit in range(8):
            if 1 << bit & number:
                self._matrix.set_pixel(7 - bit, column, color)

    def _display_network_error(self):
        self._display_symbol(self._NETWORK_ERROR, BicolorMatrix8x8.RED)

        print(self._last_request_status)
        hundreds = int(self._last_request_status / 100)
        rest = self._last_request_status % 100
        self._display_vertical_binary(self._matrix, 1, hundreds, BicolorMatrix8x8.YELLOW)
        self._display_vertical_binary(self._matrix, 0, rest, BicolorMatrix8x8.YELLOW)

    def _display_binary_tasks(self, count, start_row, color):
        for bit in range(8):
            if 1 << bit & count:
                self._matrix.set_pixel(start_row, 7 - bit, color)

        for bit in range(8, 16):
            if 1 << bit & count:
                self._matrix.set_pixel(start_row - 1, 15 - bit, color)

    @staticmethod
    def _get_row(number):
        return 7 - int(number / 8)

    @staticmethod
    def _get_col(number):
        return 7 - number % 8

    def _display_simple_tasks(self, overdue, today, future):
        current_pos = -1
        for i in range(overdue):
            current_pos += 1
            self._matrix.set_pixel(self._get_row(current_pos), self._get_col(current_pos), BicolorMatrix8x8.RED)

        # Fast forward to next row
        while (current_pos + 1) % 8 > 0:
            current_pos += 1

        for i in range(today):
            current_pos += 1
            self._matrix.set_pixel(self._get_row(current_pos), self._get_col(current_pos), BicolorMatrix8x8.YELLOW)

        # Fast forward to next row
        while (current_pos + 1) % 8 > 0:
            current_pos += 1

        for i in range(future):
            current_pos += 1
            self._matrix.set_pixel(self._get_row(current_pos), self._get_col(current_pos), BicolorMatrix8x8.GREEN)

    @staticmethod
    def _calc_line_count(count):
        return math.ceil(count / 8)

    def _draw_tasks(self, overdue, today, future):
        overdue_lines = self._calc_line_count(overdue)
        today_lines = self._calc_line_count(today)
        future_lines = self._calc_line_count(future)

        self._matrix.clear()

        if overdue_lines + today_lines + future_lines > 8:
            self._display_binary_tasks(overdue, 7, BicolorMatrix8x8.RED)
            self._display_binary_tasks(today, 4, BicolorMatrix8x8.YELLOW)
            self._display_binary_tasks(future, 1, BicolorMatrix8x8.GREEN)
        else:
            self._display_simple_tasks(overdue, today, future)

        self._matrix.write_display()


    def _midnight(self, date_object):
        return date_object.replace(hour=0, minute=0, second=0, microsecond=0)
