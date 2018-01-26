#!/usr/bin/env python3

import os
import sys
import locale
from datetime import datetime
from bs4 import BeautifulSoup
import multiprocessing
import traceback
import logging
import json

from tools import *

locale.setlocale(locale.LC_ALL, 'en_US.utf8')

# log.setLevel(logging.INFO)


def process_type(a_type, infos):
    if a_type in ['Run', 'Long Run']:
        return 'Run'
    elif a_type in ['Ride']:
        return 'Ride'
    elif a_type in ['Swim']:
        return 'Swim'
    elif a_type in ['Workout', 'Race']:
        if 'shoes' in infos:
            return 'Run'
        elif 'bike' in infos:
            return 'Ride'
    raise Exception('Unknown activity type %s' % a_type)


def process_date(date):
    try:
        return datetime.strptime(date, "%I:%M %p on %A, %B %d, %Y")
    except Exception as e:
        try:
            return datetime.strptime(date, "%A, %B %d, %Y")
        except Exception as f:
            raise e


def process_value(key, value):
    hundred = False
    if value.endswith('/km'):
        value = value[:-3]
    if value.endswith('/100m'):
        value = value[:-5]
        hundred = True
    if key in ['pace', 'moving_time', 'elapsed_time', 'duration']:
        split = value.split(':')
        res = 0
        mul = 1
        while len(split) != 0:
            i = split.pop()
            res += int(i) * mul
            mul *= 60
        if hundred:
            res *= 10
        return res
    elif value.endswith('km'):
        return int(float(value[:-2].replace(',', '')) * 1000)
    elif value.endswith('m'):
        return int(value[:-1].replace(',', ''))


def process_activity(history, athlete_dir, activity):
    activity_file = os.path.join(athlete_dir, activity)
    with open(activity_file, 'r') as f:
        a_type = f.readline().strip()
        date = f.readline().strip()
        c = f.read()
    if a_type == '':
        raise Exception("Empty activity")
    if date == '':
        raise Exception("Activity with no date")
    date_d = process_date(date)
    log.debug(activity_file)

    soup = BeautifulSoup(c, "html.parser")
    stats = {}
    for stat_name_div in soup.find_all(
        'div', class_=['label', 'spans5', 'gear spans8']
    ):
        stat_name = stat_name_div.get_text().replace('\n', '').lower()
        split = stat_name.split(':')
        if len(split) > 1:
            # Gear parse
            stat_name = split[0]
            value = split[1].replace('\n', '').split('(')[0]
        else:
            stat_name = stat_name.replace(' ', '_')
            value = stat_name_div.parent.find('strong').get_text()
            value = process_value(stat_name, value)
        stats[stat_name] = value

    stats['type'] = process_type(a_type, stats)
    history[int(date_d.timestamp())] = stats
    log.debug(stats)


def process_athelete_worker(a):
    while True:
        athlete = q.get()
        history = {}
        athlete_dir = os.path.join(data_dir, athlete)
        for activity in os.listdir(athlete_dir):
            try:
                process_activity(history, athlete_dir, activity)
            except Exception as e:
                log.debug(traceback.format_exc())
                log.warning(
                    'Activity problem %s/%s : %s' %
                    (athlete_dir, activity, e))
        with open(os.path.join(data_dir, athlete, 'history'), 'w+') as f:
            f.write(json.dumps(history))

if __name__ == '__main__':
    q = multiprocessing.Queue(maxsize=200)

    ps = []
    for i in range(12):
        p = multiprocessing.Process(
            target=process_athelete_worker, args=(q,))
        p.start()
        ps.append(p)

    for athlete in os.listdir(data_dir):
        tag_file = os.path.join(data_dir, athlete, 'history')
        s_file = os.path.join(data_dir, athlete, 'status')
        if os.path.isfile(s_file) and not os.path.isfile(tag_file):
            q.put(athlete)

    for p in ps:
        p.join()
