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

HTTP_HEADERS = {
    'App-OS': 'android',
    'App-OS-Version': '8.1.0',
    'App-Version': '5.0.112',
    'User-Agent':
    'PixivAndroidApp/5.0.112 (Android 8.1.0; Android SDK built for x86)',
    'Referer': 'https://app-api.pixiv.net/'
}
ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

DEFAULT_CFG = {
    'workdir':
    'storage',  # Directory to save downloaded works amd database files
    'debug': False,
    'pixiv': {
        'refresh_token': ''  # Refresh token for auto relogin
    },
    'downloader': {
        'threads': 5  #Image downloader threads
    },
    'web_ui': {
        'ip': '127.0.0.1',  # Web server listened IP
        'port': 5266,  # Web server listened port
        'thumbnail_cache':
        True  # Enable thumbnail cache for better performance
    },
    'database': {
        'method': 'sqlite',  # sqlite or mysql
        'mysql': {
            'username': 'root',
            'password': '',
            'host': 'localhost:3306',
            'database': 'pixivmanager'
        }
    }
}


def cd_script_dir():
    os.chdir(os.path.dirname(sys.argv[0]))


def iso_to_datetime(date_str):
    return datetime.strptime(date_str, ISO_TIME_FORMAT)


def init_logger(logger_name, log_file=None) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s : %(message)s')
    ch.setFormatter(logger_formatter)
    logger.addHandler(ch)
    if log_file:
        cf = logging.FileHandler(filename=log_file, encoding='utf-8')
        cf.setLevel(logging.DEBUG)
        cf.setFormatter(logger_formatter)
        logger.addHandler(cf)
    return logger


def _retry(exception,
           tries=5,
           delay=3,
           backoff=2,
           error_msg=None,
           logger=0,
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
                        logger.error(exception)
                        logger.error(error_msg)
                    elif error_msg:
                        print(exception)
                        print(error_msg)
                    if print_traceback and not logger:
                        traceback.print_exc()

                    time.sleep(_delay)
                    _delay *= backoff

            return f(*args, **kwargs)

        return f_retry

    return deco_retry


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
        self.workdir = Path(self.cfg['workdir'])
        os.makedirs(self.workdir, exist_ok=True)

        if loaded_cfg != self.cfg:
            self.save_cfg()

    def validate_cfg(self):
        assert type(self.cfg['workdir']) is str
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
        return init_logger(logger_name, self.workdir / log_file)

    @property
    def database_uri(self):
        if self.cfg['database']['method'] == 'sqlite':
            return 'sqlite:///%s' % (self.workdir / 'pixivmanager.sqlite.db')
        else:
            d_mysql = self.cfg['database']['mysql']
            return 'mysql://%s:%s@%s/%s?charset=utf8mb4' % (
                d_mysql['username'],
                urllib.parse.quote_plus(
                    d_mysql['password']), d_mysql['host'], d_mysql['database'])
