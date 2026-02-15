from alerts import Alerts
import argparse
import socket


parser = argparse.ArgumentParser(
                    prog='RTM Matrix Alert Sender',
                    description='Send an alert to the RTM Matrix program')

parser.add_argument('host', help='Server host')
parser.add_argument('port', help='Server port')
parser.add_argument('color', choices=['r', 'g', 'y'], help='Alert colour')
parser.add_argument('message', help="Alert message")

args = parser.parse_args()

server_color = None

if args.color == 'r':
    server_color = Alerts.RED
elif server_color == 'g':
    server_color = Alerts.GREEN
else:
    server_color = Alerts.YELLOW

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((args.host, int(args.port)))
    msg = f'{server_color} {args.message}'
    s.sendall(str.encode(msg))
    print(s.recv(1024).decode())
