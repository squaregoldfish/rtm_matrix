from datetime import datetime
import glob
import json
import os
import requests
import shutil
import socket
from threading import Thread
import time

class Counters():
    DELAY = 3

    def __init__(self, display, config):
        self._display = display
        self._config = config
        self._url_cache = dict()

        with open(config['file']) as cin:
            self._counters = json.loads(cin.read())

        for c in self._counters:
            c['text'] = None
            c['last_get'] = None

        Thread(target=self._display_counters).start()
        Thread(target=self._retrieve_counters).start()
        

    def _display_counters(self):
        while True:
            for c in self._counters:
                if c['text'] is not None:
                    self._display.write(c['label'] + c['text'])
                    time.sleep(self.DELAY)
        

    def _retrieve_counters(self):
        while True:
            for c in self._counters:
                if c['last_get'] is None or (datetime.now() - c['last_get']).total_seconds() > c['delay']:
                    c['text'] = getattr(self, '_' + c['method'])(*c['params'])
                    c['last_get'] = datetime.now()

            time.sleep(1)

    def _get_url(self, url):
        if url not in self._url_cache.keys():
            # Find the URL's minimum delay
            min_delay = 999999999
            for counter in self._counters:
                if counter['params'][0] == url and counter['delay'] < min_delay:
                    min_delay = counter['delay']

            self._url_cache[url] = {
                "delay": min_delay,
                "last_get": None,
                "response": None
            }

        cache_entry = self._url_cache[url]
        if cache_entry['last_get'] is None or (datetime.now() - cache_entry['last_get']).total_seconds() > cache_entry['delay']:
            response = requests.get(url)
            response.raise_for_status()
            cache_entry['response'] = response.text
            cache_entry['last_get'] = datetime.now()

        return cache_entry['response']


    @staticmethod
    def _format_number(number):
        text = None

        if number is not None and int(number) > 0:
            value = int(number)
            if value >= 1000000:
                text = f'***'
            elif value >= 1000:
                val = float(value) / 1000
                if val > 10:
                    text = f'{val:.1f}'
                else:
                    text = f'{val:.2f}'
            else:
                text = f'{value:3d}'

        return text

    @staticmethod
    def _number_file(file):
        file_result = None

        if os.path.exists(file):
            with open(file) as f:
                file_result = f.readline().strip()

        return Counters._format_number(file_result)

    def _number_url(self, url):
        result = None

        try:
            result = int(self._get_url(url))
        except:
            pass

        return Counters._format_number(result)

    @staticmethod
    def _number_server(host, port):
        result = None
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((host, port))
                data = client_socket.recv(1024)
                result = int(data)
        except:
            pass

        return Counters._format_number(result)


    def _number_json_url_source(self, url, key):
        result = None

        try:
            response = json.loads(self._get_url(url))
            result = response[key]
        except:
            pass
    
        return Counters._format_number(result)

    def _text_json_url_source(self, url, key):
        result = None

        response = json.loads(self._get_url(url))
        result = response[key]
    
        return result

    @staticmethod
    def _dir_count(path):
        result = None

        try:
            result = len(glob.glob(os.path.join(path, '**'), recursive=True)) - 1
        except:
            pass

        return Counters._format_number(result)
        
    @staticmethod
    def _free_space(path):
        result = None

        try:
            total, used, free = shutil.disk_usage(path)
            result = free / (1024 ** 2)
            if result > 1000:
                result = result / 1000
        except:
            pass

        return Counters._format_number(int(result))

