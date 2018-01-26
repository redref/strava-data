#!/usr/bin/env python3

import os
import sys
import argparse
from bs4 import BeautifulSoup
from string import ascii_lowercase, ascii_uppercase
import multiprocessing

from tools import *


def get_athletes(session, letters):
    # Strava will not get result above page 50
    for page in range(50):
        if page != 0:
            real_page = '&page=%s' % (page + 1)
        else:
            real_page = ''
        while True:
            r = session.get(
                'https://www.strava.com/athletes/search'
                '?utf8=✓&text=%s%s' %
                (letters, real_page))
            if r.status_code == requests.codes.ok:
                break
        page = BeautifulSoup(r.text, "html.parser")
        for el in page.body.select('[data-athlete-id]'):
            if el.attrs['data-requires-approval'] == 'false':
                yield el.attrs['data-athlete-id']


def get_athletes_worker(q, args):
    session = init_session(args)
    while True:
        b = q.get()
        for athlete_id in get_athletes(session, b):
            athlete_folder = os.path.join(data_dir, athlete_id)
            if not os.path.isdir(athlete_folder):
                log.debug(athlete_folder)
                os.mkdir(athlete_folder)

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
    for i in range(12):
        p = multiprocessing.Process(
            target=get_athletes_worker, args=(q, args))
        p.start()
        ps.append(p)

    for one in ascii_lowercase + ascii_uppercase:
        if one in ['a', 'b', 'c', 'd']:
            continue
        for two in ascii_lowercase + ascii_uppercase:
            q.put("%s%s" % (one, two))

    for p in ps:
        p.join()
