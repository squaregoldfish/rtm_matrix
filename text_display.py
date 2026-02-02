import board
from adafruit_ht16k33.segments import Seg14x4
import toml
import re
import time
from threading import Thread, Event


class text_display():
    SCROLL_DELAY = 0.2

    def __init__(self, config):
        i2c = board.I2C()
        self._display = Seg14x4(i2c, address=config['address'])
        self._display.brightness = config['brightness']
        
        self._scroll_event = None
        self.clear()

    def clear(self):
        self._stop_scroll()
        self._display.print('    ')

    def write(self, text):
        self._stop_scroll()
        text = text.strip().upper()

        no_dots = re.sub(r'\.', '', text)
        text = text + ' ' * (4 - len(no_dots))

        if len(re.sub(r'\.', '', text)) <= 4:
            self._display.print(text)
        else:
            self._scroll_text(text)

    def dots(self, count):
        self.clear()
        if count >= 1:
            self._display.set_digit_raw(0, 16384)
        if count >= 2:
            self._display.set_digit_raw(1, 16384)
        if count >= 3:
            self._display.set_digit_raw(2, 16384)
        if count >= 4:
            self._display.set_digit_raw(3, 16384)

    def _scroll_text(self, text):
        Thread(target=self._scroll_animation, args=(text,)).start()

    def _scroll_animation(self, text):
        self._scroll_event = Event()

        # Front padding
        text = '   ' + text + '   '

        pos = 0
        while not self._scroll_event.is_set():
            print_start = pos
            print_end = pos + 4

            self._display.print(text[print_start:print_end])
            time.sleep(self.SCROLL_DELAY)

            if pos >= len(text):
                pos = 0
            else:
                pos += 1

        self._scroll_event = None

    def _stop_scroll(self):
        if self._scroll_event is not None:
            self._scroll_event.set()
            time.sleep(self.SCROLL_DELAY)


if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    text = text_display(config['text'])

    while True:
        text.write('DEMO')
        time.sleep(5)

        text.write('The quick brown fox jumped over the lazy dog')
        time.sleep(15)

        count = 4
        while count >= 0:
            text.dots(count)
            time.sleep(0.25)
            count -= 1

        

