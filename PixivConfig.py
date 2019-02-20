import json
import logging
import os
from pathlib import Path

HTTP_HEADERS = {
    'App-OS':
    'android',
    'App-OS-Version':
    '8.1.0',
    'App-Version':
    '5.0.112',
    'User-Agent':
    'PixivAndroidApp/5.0.112 (Android 8.1.0; Android SDK built for x86)',
    'Referer':
    'https://app-api.pixiv.net/'
}

DEFAULT_CFG = {
    'workdir': 'storage',
    'debug': False,
    'pixiv': {
        'refresh_token': ''
    },
    'downloader': {
        'threads': 5
    },
    'web_ui': {
        'ip': '127.0.0.1',
        'port': 5266,
        'thumbnail_cache': True
    }
}


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


if __name__ == "__main__":
    pconf = PixivConfig(Path('config.json'))
    print(pconf.cfg['pixiv']['refresh_token'])
