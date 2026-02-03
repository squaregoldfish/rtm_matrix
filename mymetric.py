import bcmatrix
import counters
import rtm
import text_display
import toml

with open('config.toml') as config_file:
    config = toml.load(config_file)


# Displays
matrix = bcmatrix.bcmatrix(config['matrix'])
text = text_display.text_display(config['text'])

# RememberTheMilk
rtm = rtm.RTM(matrix, config['rtm'])

counters = counters.Counters(text, config['counters'])
