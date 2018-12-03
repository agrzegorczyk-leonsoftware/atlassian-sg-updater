#!/usr/bin/env python3.6
# 20181203 AGR

import argparse
import requests

IP_LIST_URL='https://ip-ranges.atlassian.com/'

parser = argparse.ArgumentParser()
parser.add_argument('--sync-token', type=int, required=True)
args=parser.parse_args()

if requests.get(IP_LIST_URL).json()['syncToken'] != args.sync_token:
    raise ValueError('syncToken changed in '+IP_LIST_URL)