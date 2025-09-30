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
            params['filter'] = 'status:incomplete AND dueBefore:"1 month of today"'

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

                            if status != FUTURE:
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


if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    instance = rtm(config['rtm'])
    instance.fetch_tasks()

    if instance.last_request_status != 200:
        print('N')
    elif instance.processing_error:
        print('E')
    else:
        points = list()

        for task in instance.get_tasks():
            if task['recurring']:
                points.append(YELLOW)
            elif task['status'] == OVERDUE:
                points.append(RED)
            elif task['status'] == TODAY:
                points.append(GREEN)
            
        print(points)
