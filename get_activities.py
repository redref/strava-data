#!/usr/bin/env python3

import os
import sys
import argparse
from bs4 import BeautifulSoup
import multiprocessing

from tools import *


def get_activities(session, athlete):
    for year in ['2016', '2017', '2018']:
        for m in range(12):
            month = "{0:02d}".format(m + 1)
            while True:
                r = session.get(
                    "https://www.strava.com/athletes/%s#interval_type" %
                    athlete,
                    params={
                        'chart_type': 'miles', 'interval_type': 'month',
                        'interval': '%s%s' % (year, month), 'year_offset': 0
                    })
                if r.status_code == requests.codes.ok:
                    break
            page = BeautifulSoup(r.text, 'html.parser')
            interval_rides = page.find("div", {"id": "interval-rides"})
            activities = interval_rides.select('a[href]')
            ids = []
            for activity in activities:
                href = activity.attrs['href']
                if href.startswith('/activities/'):
                    rid = href[12:]
                    try:
                        rid = rid[0:rid.index('/')]
                    except ValueError as e:
                        pass
                    yield rid
            if year == '2018' and month == '01':
                break


def get_activity(session, activity):
    while True:
        r = session.get(
            "https://www.strava.com/activities/%s" % activity)
        if r.status_code == requests.codes.ok:
            break
    page = BeautifulSoup(r.text, "html.parser")
    title = page.find('span', attrs={'class': 'title'})
    a_type = title.contents[-1].replace('\n', '').replace('–', '')
    stats = page.find('div', attrs={'class': 'activity-stats'})
    time = page.body.find('time')
    time_str = time.contents[-1].replace('\n', '').replace('–', '')
    return a_type + "\n" + time_str + "\n" + \
        "".join([str(item) for item in stats.contents])


def get_activities_worker(q, args):
    session = init_session(args)
    while True:
        athlete = q.get()
        for activity in get_activities(session, athlete):
            activity_file = os.path.join(data_dir, athlete, activity)
            if os.path.isfile(activity_file):
                continue
            log.info(activity_file)
            with open(activity_file, 'w+') as f:
                f.write(get_activity(session, activity))

        tag_file = os.path.join(data_dir, athlete, 'status')
        with open(tag_file, 'w+') as f:
            f.write('201801')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Request strava for random athletes data')
    parser.add_argument('email', nargs='?', help='Strava account email')
    parser.add_argument('passwd', nargs='?', help='Strava account password')
    args = parser.parse_args()

    if not args.email or not args.passwd:
        log.error('Email or password not set')
        parser.print_help()
        sys.exit(1)

    q = multiprocessing.Queue(maxsize=200)

    ps = []
    for i in range(32):
        p = multiprocessing.Process(
            target=get_activities_worker, args=(q, args))
        p.start()
        ps.append(p)

    for athlete in os.listdir(data_dir):
        tag_file = os.path.join(data_dir, athlete, 'status')
        if not os.path.isfile(tag_file):
            q.put(athlete)

    for p in ps:
        p.join()
