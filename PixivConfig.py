import json
import logging
import os
import sys
import urllib.parse
from datetime import datetime
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
    'storage',  #Directory to save downloaded works amd database files
    'debug': False,
    'pixiv': {
        'refresh_token': ''  #Refresh token for auto relogin
    },
    'downloader': {
        'threads': 5  #Image download threads
    },
    'web_ui': {
        'ip': '127.0.0.1',  #Web server listened IP
        'port': 5266,  #Web server listened port
        'thumbnail_cache': True  #Enable thumbnail cache for better performance
    },
    'database': {
        'method': 'sqlite',  #sqlite or mysql
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


def init_logger(logger_name, log_file) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    cf = logging.FileHandler(filename=log_file, encoding='utf-8')
    ch.setLevel(logging.INFO)
    cf.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s : %(message)s')
    ch.setFormatter(logger_formatter)
    cf.setFormatter(logger_formatter)
    logger.addHandler(ch)
    logger.addHandler(cf)
    return logger


class PixivConfig(object):
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
