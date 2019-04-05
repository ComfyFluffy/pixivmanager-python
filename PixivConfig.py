import json
import logging
import os
import sys
import time
import traceback
import urllib.parse
from datetime import datetime
from functools import wraps
from pathlib import Path
import re

import coloredlogs

HTTP_HEADERS = {
    'App-OS': 'android',
    'App-OS-Version': '8.1.0',
    'App-Version': '5.0.132',
    'User-Agent':
    'PixivAndroidApp/5.0.132 (Android 8.1.0; Android SDK built for x86)',
    'Referer': 'https://app-api.pixiv.net/'
}
ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
VERSION_UNDER_3_7 = sys.version < '3.7'
IMAGE_TYPES = ('jpg', 'png', 'gif')

DEFAULT_CFG = {
    'storage_dir': 'storage',
    # Directory to save downloaded works amd database files
    'pixiv_works_dir': '',
    # Saved Pixiv works
    # Defult: (storage_dir)/illusts
    # Structure
    # Single page: /(user_id)/(works_id)_p0.(png)
    # Multi page /user_id/(works_id)/(works_id)_p(x).(png)
    'debug': False,
    'avatars_dir': '',
    # Avatars saving directory
    # Default: (storage_dir)/avatars
    'pixiv': {
        'refresh_token': ''
        # Refresh token for auto relogin
    },
    'downloader': {
        'threads': 5
        #Image downloader threads
    },
    'web_ui': {
        'ip': '127.0.0.1',  # Web server listened IP
        'port': 5266,  # Web server listened port
        'thumbnail_cache': True
        # Enable thumbnail cache for better performance
    },
    'database': {
        'method': 'sqlite',
        # sqlite or mysql
        # SQLite file: (storage_dir)/pixivmanager.sqlite.db
        'mysql': {
            'username': 'root',
            'password': '',
            'host': 'localhost:3306',
            'database': 'pixivmanager'
        }
    }
}

CF_LOGGER_FORMAT = '[%(asctime)s] [%(levelname)s] %(name)s : %(message)s'
CH_LOGGER_FORMAT = '[%(asctime)s] %(name)s %(message)s'
loaded_colorama = False


def cd_script_dir():
    p = os.path.dirname(sys.argv[0])
    if p:
        os.chdir(p)


def iso_to_datetime(date_str: str):
    if VERSION_UNDER_3_7:
        date_str.replace('+09:00', '+0900')
    return datetime.strptime(date_str, ISO_TIME_FORMAT)


def init_colorama():
    global loaded_colorama
    if loaded_colorama:
        return
    import colorama
    colorama.init()
    loaded_colorama = True


def init_logger(logger_name, log_file=None) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    if os.name == 'nt':
        init_colorama()
    ch_logger_formatter = coloredlogs.ColoredFormatter(CH_LOGGER_FORMAT)
    ch.setFormatter(ch_logger_formatter)
    logger.addHandler(ch)

    if log_file:
        cf = logging.FileHandler(filename=log_file, encoding='utf-8')
        cf.setLevel(logging.DEBUG)
        cf.setFormatter(logging.Formatter(CF_LOGGER_FORMAT))
        logger.addHandler(cf)

    return logger


def _retry(exception,
           tries=5,
           delay=3,
           backoff=1,
           error_msg=None,
           logger=None,
           print_traceback=True):
    def deco_retry(f):
        _logger = logger

        @wraps(f)
        def f_retry(*args, **kwargs):
            _tries, _delay = tries, delay
            if not _logger:
                logger: logging.Logger = getattr(args[0], 'logger', None)
            else:
                logger = _logger
            while _tries > 1:
                try:
                    return f(*args, **kwargs)
                except exception:
                    _tries -= 1

                    if print_traceback and logger and error_msg:
                        logger.exception(error_msg)
                    elif logger and error_msg:
                        logger.warning(error_msg)
                        logger.warning(exception)
                    elif error_msg:
                        print(error_msg)
                        print(exception)
                    if print_traceback and not logger:
                        traceback.print_exc()

                    time.sleep(_delay)
                    _delay *= backoff

            return f(*args, **kwargs)

        return f_retry

    return deco_retry


def time_checker(f):
    @wraps(f)
    def f_do(*args, **kwargs):
        try:
            t1 = datetime.now()
            return f(*args, **kwargs)
        finally:
            print(f.__name__, datetime.now() - t1)

    return f_do


class PixivConfig:
    def __init__(self, cfg_json_file):
        self.cfg_json_file = Path(cfg_json_file)

        if self.cfg_json_file.exists():
            with self.cfg_json_file.open('r', encoding='utf8') as cf:
                loaded_cfg = json.load(cf)
        else:
            loaded_cfg = {}

        self.cfg = {**DEFAULT_CFG, **loaded_cfg}
        self.validate_cfg()
        self.storage_dir = Path(self.cfg['storage_dir'])
        self.pixiv_works_dir = Path(
            self.cfg['pixiv_works_dir']
        ) if self.cfg['pixiv_works_dir'] else self.storage_dir / 'works'
        self.avatars_dir = Path(
            self.cfg['avatars_dir']
        ) if self.cfg['avatars_dir'] else self.storage_dir / 'avatars'

        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.pixiv_works_dir, exist_ok=True)
        os.makedirs(self.avatars_dir, exist_ok=True)

        if loaded_cfg != self.cfg:
            self.save_cfg()

    def validate_cfg(self):
        assert type(self.cfg['storage_dir']) is str
        assert type(self.cfg['pixiv_works_dir']) is str
        assert type(self.cfg['avatars_dir']) is str
        assert type(self.cfg['debug']) is bool
        assert type(self.cfg['web_ui']['ip']) is str
        assert type(self.cfg['web_ui']['port']) is int
        assert type(self.cfg['web_ui']['thumbnail_cache']) is bool
        assert type(self.cfg['downloader']['threads']) is int

    def save_cfg(self):
        self.validate_cfg()
        with self.cfg_json_file.open('w', encoding='utf8') as cf:
            json.dump(self.cfg, cf, ensure_ascii=False, indent=4)

    def get_logger(self, logger_name, log_file='PixivManager.log'):
        return init_logger(logger_name, self.storage_dir / log_file)

    @property
    def database_uri(self):
        if self.cfg['database']['method'] == 'sqlite':
            return 'sqlite:///%s' % (
                self.storage_dir / 'pixivmanager.sqlite.db')
        else:
            d_mysql = self.cfg['database']['mysql']
            return 'mysql://%s:%s@%s/%s?charset=utf8mb4' % (
                d_mysql['username'],
                urllib.parse.quote_plus(
                    d_mysql['password']), d_mysql['host'], d_mysql['database'])


if __name__ == "__main__":
    PixivConfig('config.json')
