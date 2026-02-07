from threading import Thread, Event
import time
import toml
from Adafruit_LED_Backpack import BicolorMatrix8x8


class bcmatrix():
    # Pixels are an array of bitmasks, running top row to bottom row.
    # Each bitmask sets bit 0 (right) to bit 7 (left)
    ANIMATION_FRAMES = [
        [  0,   0,   0,  24,  24,   0,   0,   0],
        [  0,   0,  36,   0,   0,  36,   0,   0],
        [  0,  66,   0,   0,   0,   0,  66,   0],
        [129,   0,   0,   0,   0,   0,   0, 129],
        [195, 129,   0,   0,   0,   0, 129, 195],
        [231, 129, 129,   0,   0, 129, 129, 231],
        [255, 129, 129, 129, 129, 129, 129, 255],
        [255, 255, 195, 195, 195, 195, 255, 255],
        [255, 255, 255, 231, 231, 255, 255, 255],
        [255, 255, 255, 255, 255, 255, 255, 255],
        [  0, 126, 126, 126, 126, 126, 126,   0],
        [  0,   0,  60,  60,  60,  60,   0,   0]
    ]
    
    DELAY = 0.07

    def __init__(self, config):
        self._matrix = BicolorMatrix8x8.BicolorMatrix8x8(address=config['address'], busnum=config['i2c_bus'])
        self._matrix.begin()
        self._matrix.set_brightness(config['brightness'])

        self.event = None

    def _animation_running(self):
        return self.event is not None

    def start_animation(self, color):
        if self.event is not None:
            raise ValueError('Animation is already active')

        self.color = color
        self.event = Event()
        Thread(target=self._run_animation, args=(self.event,)).start()

    def stop_animation(self):
        if self.event is not None:
            self.event.set()
            time.sleep(self.DELAY + 0.1)

    def _run_animation(self, event):
        frame_number = 0

        while not self.event.is_set():
            self._matrix.clear()

            frame = self.ANIMATION_FRAMES[frame_number]
            for row in range(len(frame)):
                row_mask = frame[row]
                for col in range(8):
                    if 1 << col & row_mask:
                        self._matrix.set_pixel(row, col, self.color)

            self._matrix.write_display()
            frame_number += 1
            if frame_number >= len(self.ANIMATION_FRAMES):
                frame_number = 0

            time.sleep(self.DELAY)

        self.event = None
        self._matrix.clear()
        self._matrix.write_display()

    def clear(self):
        if not self._animation_running():
            self._matrix.clear()
        else:
            raise ValueError('Animation is active')

    def set_pixel(self, row, col, color):
        if not self._animation_running():
            self._matrix.set_pixel(row, col, color)
        else:
            raise ValueError('Animation is active')

    def write_display(self):
        if not self._animation_running():
            self._matrix.write_display()
        else:
            raise ValueError('Animation is active')

if __name__ == "__main__":
    with open('config.toml') as config_file:
        config = toml.load(config_file)

    bcm = bcmatrix(config['matrix'])

    while True:    
        bcm.start_animation(BicolorMatrix8x8.RED)
        time.sleep(2.5)
        bcm.stop_animation()

        bcm.start_animation(BicolorMatrix8x8.YELLOW)
        time.sleep(2.5)
        bcm.stop_animation()

        bcm.start_animation(BicolorMatrix8x8.GREEN)
        time.sleep(2.5)
        bcm.stop_animation()
