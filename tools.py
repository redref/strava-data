import os
import logging
import requests
from bs4 import BeautifulSoup

data_dir = os.path.join(os.path.dirname(
    os.path.dirname(os.path.realpath(__file__))
    ), 'strava_data')
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(funcName)s} %(levelname)s - %(message)s',
)
log = logging.getLogger()


def init_session(args):
    session = requests.session()

    r = session.get('https://www.strava.com/login')
    page = BeautifulSoup(r.text, "html.parser")
    a_token = page.head.find(
        'meta', attrs={'name': 'csrf-token'}).attrs['content']
    log.debug(a_token)

    r = session.post(
        'https://www.strava.com/session',
        {'utf-8': '✓', 'plan': None, 'email': args.email,
         'password': args.passwd, 'authenticity_token': a_token})

    log.debug(requests.utils.dict_from_cookiejar(session.cookies))
    return session
