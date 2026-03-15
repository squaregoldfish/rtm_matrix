from alerts import Alerts
import json
import os
import requests
import socket
import sys
import toml
import traceback
from urllib.parse import parse_qs

def get_incidents(api_key):
  url = 'https://api.uptimerobot.com/v3/incidents'

  payload = 'cursor=1'
  headers = {
    'accept': 'application/json',
    'authorization': f'Bearer {api_key}'
  }

  response = requests.request('GET', url, data=payload, headers=headers)
  if response.status_code != 200:
    raise Exception("HTTP ERROR " + str(response.status_code))

  data = json.loads(response.text)
  if 'message' in data.keys():
    raise Exception(f'API call failed: {data["message"]}')

  return data['data']


with open('config.toml') as config_file:
    config = toml.load(config_file)

api_key = config['uptime_robot']['api_key']
alert_port = config['alerts']['port']

stored_last_incident = None

if os.path.exists('last_incident.txt'):
    with open('last_incident.txt') as incident_file:
        stored_last_incident = incident_file.read()

incidents = get_incidents(api_key)

api_last_incident = None

for incident in incidents:
    # Keep the first incident ID to be stored.
    if api_last_incident is None:
        api_last_incident = incident['id']

    # If we hit the previous last incident ID, stop
    if incident['id'] == stored_last_incident:
        break

    # If the incident is not resolved, raise an alert
    if incident['resolvedAt'] is None:
        monitor_name = incident['monitor']['friendlyName']

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', alert_port))
            msg = f'{Alerts.RED} {monitor_name} down'
            s.sendall(str.encode(msg))
            print(s.recv(1024).decode())

with open('last_incident.txt', 'w') as incident_file:
    incident_file.write(api_last_incident)
