import board
from adafruit_ht16k33.segments import Seg14x4
import shutil
import time
import toml

with open('config.toml') as config_file:
    config = toml.load(config_file)

space_config = config['space']

i2c = board.I2C()
display = Seg14x4(i2c, address=space_config['address'])
display.brightness = space_config['brightness']

while True:
    # Get disk usage statistics for the /Media mount point
    total, used, free = shutil.disk_usage(space_config['path'])

    # Convert free space to terabytes (1 TB = 1024^4 bytes)
    free_gb = free / (1024 ** 3)

    display.print(int(free_gb))
    time.sleep(5)

