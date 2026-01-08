import board
from adafruit_ht16k33.segments import Seg14x4
import shutil
import time
import toml
import threading
import os
import requests
import re
import socket
import glob

counter_data = dict()
#counter_data['O'] = None
#counter_data['C'] = None
counter_data['T'] = None
counter_data['R'] = None
counter_data['A'] = None
counter_data['P'] = None
counter_data['Y'] = None
counter_data['S'] = None
counter_data['W'] = None
counter_data['D'] = None
counter_data['N'] = None
counter_data['E'] = None
counter_data['V'] = None
counter_data['I'] = None
counter_data['B'] = None
lock = threading.Lock()

def space(path, dest):
    while True:
        free_result = None

        try:
            total, used, free = shutil.disk_usage(path)
            free_result = free / (1024 ** 3)
            if free_result > 1000:
                free_result = free_result / 1000
        except:
            pass

        with lock:
            counter_data[dest] = free_result

        time.sleep(5)

def int_file_source(file, trim, dest):
    while True:
        file_result = None

        try:
            if os.path.exists(file):
                with open(file) as f:
                    file_result = f.readline().strip()
                    if trim > 0:
                        file_result = file_result[:(trim * -1)]

            counter_data[dest] = int(file_result)
        except:
            pass

        time.sleep(5)

def file_source(file, trim, dest):
    while True:
        file_result = None

        try:
            if os.path.exists(file):
                with open(file) as f:
                    file_result = f.readline().strip()
                    if trim > 0:
                        file_result = file_result[:(trim * -1)]
        except:
            pass

        with lock:
            counter_data[dest] = file_result

        time.sleep(300)

def number_server(host, port, dest):
    while True:
        number_result = None

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((host, port))
                data = client_socket.recv(1024)  # Receive data from the server
                number_result = int(data)
        except:
            pass

        with lock:
            counter_data[dest] = number_result

        time.sleep(15)

        
def json_url_source(url, extract):
    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            json_data = response.json()

            for (dest, path) in extract.items():
                current = json_data
                for entry in path:
                    if isinstance(entry, str):
                        current = current[entry]
                    elif isinstance(entry, int):
                        current = current[entry]
                    else:
                        raise ValueError("Path entries must be either string (key) or int (index).")

                with lock:
                    counter_data[dest] = current
                    #match = re.search(r'\b\d+\b', current)
                    #if match:
                    #    counter_data[dest]  = int(match.group())

        except Exception as e:
            print(e)
            with lock:
                for dest in extract.keys():
                    counter_data[dest] = None

        time.sleep(300)

def int_url_source(url, dest):
    while True:
        result = None

        try:
            response = requests.get(url)
            response.raise_for_status()
            result = int(response.text)
        except:
            pass

        with lock:
            counter_data[dest] = result

        time.sleep(60)

def file_line_count(file, dest):
    while True:
        result = None

        try:
            with open(file, 'r') as f:
                result = sum(1 for line in f)
        except:
            pass

        with lock:
            counter_data[dest] = result

        time.sleep(60)

def dir_file_count(directory, dest):
    while True:
        result = None

        try:
            result = len(glob.glob(os.path.join(directory, '**'), recursive=True))
        except:
            pass

        with lock:
            counter_data[dest] = result

        time.sleep(60)


def main():
    # Config
    with open('config.toml') as config_file:
        config = toml.load(config_file)['counter']

    # Threads
    bagpuss = threading.Thread(target=space, args=(config['space_path'], 'B'))
    bagpuss.start()

    tasks = threading.Thread(target=int_file_source, args=('task_count.txt', 0, 'T'))
    tasks.start()

    freshrss = threading.Thread(target=int_url_source, args=(config['freshrss_url'], 'R'))
    freshrss.start()

    media_extract = {
        'P': ['Podcasts'],
        'Y': ['YouTube'],
        'S': ['Streams'],
        'W': ['Readeck'],
        'D': ['oldest'],
        'N': ['oldest_diff']
    }
    media = threading.Thread(target=json_url_source, args=(config['media_url'], media_extract))
    media.start()

    sizes = threading.Thread(target=number_server, args=(config['sizes_host'], config['sizes_port'], 'A'))
    sizes.start()

    #temperature = threading.Thread(target=file_source, args=(config['temperature_file'], 2, 'O'))
    #temperature.start()

    #co2 = threading.Thread(target=int_file_source, args=(config['co2_file'], 3, 'C'))
    #co2.start()
    
    scr_count = threading.Thread(target=int_file_source, args=(config['dir_file'], 0, 'E'))
    scr_count.start()

    vid_count = threading.Thread(target=dir_file_count, args=(config['dir_count_1'], 'V'))
    vid_count.start()

    photo_count = threading.Thread(target=dir_file_count, args=(config['dir_count_2'], 'I'))
    photo_count.start()


    
    i2c = board.I2C()
    display = Seg14x4(i2c, address=config['address'])
    display.brightness = config['brightness']

    while True:
        for key in counter_data.keys():
            value = counter_data[key]

            if value is None:
                text = f'{key}---'
            elif type(value) == int:
                if value >= 1000000:
                    text = f'{key}***'
                elif value >= 1000:
                    val = float(value) / 1000
                    if val > 10:
                        text = f'{key}{val:.1f}'
                    else:
                        text = f'{key}{val:.2f}'
                else:
                    text = f'{key}{value:3d}'
            elif type(value) == float:
                text = f'{key}{value:.2f}'
            else:
                display_value = value.rjust(4) if '.' in value else value.rjust(3)
                text = f'{key}{display_value}'

            display.print(text)
            time.sleep(3)





if __name__ == '__main__':
    main()

