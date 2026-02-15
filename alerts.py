from Adafruit_LED_Backpack import BicolorMatrix8x8
import board
import digitalio
import queue
import socket
from threading import Thread
import time


class Alerts():
    RED = 'RED'
    YELLOW = 'YEL'
    GREEN = 'GRN'
    
    def __init__(self, config, matrix, text):
        self._matrix = matrix
        self._text = text
        self._queue = queue.Queue()
        self.showing_alert = False
        self._rtm = None

        # Initialise push button
        self._button = digitalio.DigitalInOut(board.D16)
        self._button.direction = digitalio.Direction.INPUT
        self._button.pull = digitalio.Pull.DOWN

        Thread(target=self._start_server, args=(config['port'], )).start()
        Thread(target=self._button_monitor).start()

    def register_rtm(self, rtm):
        self._rtm = rtm
    
    def _button_push(self):
        if self.showing_alert:
            self._matrix.stop_animation()
            self._text.dots(4)
            self.showing_alert = False
            if not self._queue.empty():
                self._show_next_alert()
            else:
                if self._rtm is not None:
                    self._rtm.display_tasks()


    def _button_monitor(self):
        while True:
            if self._button.value:
                self._button_push()
            time.sleep(0.1)


    def _start_server(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind(('0.0.0.0', port))
            server_socket.listen()

            print('Server started')
            while True:
                conn, addr = server_socket.accept()
                with conn:
                    data = conn.recv(1024).decode('utf-8')

                    color, message = data.split(' ', 1)
                    message = message.strip()

                    response = 'OK'

                    if color not in [self.RED, self.YELLOW, self.GREEN]:
                        response = f'Invalid color {color}'
                    elif len(message) == 0:
                        response = f'Empty message'
                    else:
                        self._queue.put([self._get_matrix_color(color), message])
                        self._show_next_alert()

                    conn.sendall(response.encode('utf-8'))

    def _show_next_alert(self):
        if not self.showing_alert and not self._queue.empty():
            color, message = self._queue.get()
            self._matrix.start_animation(color)
            self._text.write(message)

            self.showing_alert = True

    def _get_matrix_color(self, color):
        if color == self.RED:
            return BicolorMatrix8x8.RED
        elif color == self.GREEN:
            return BicolorMatrix8x8.GREEN
        elif color == self.YELLOW:
            return BicolorMatrix8x8.YELLOW
        else:
            raise ValueError('Invalid color')
