import json
import os
import urllib.parse
from pathlib import Path

from .helpers import init_logger

DEFAULT_CFG = {
    'storage_dir': '',
    # Directory to save downloaded works amd database files
    # Default: ~/.pixivmanager-python
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
        'refresh_token': '',
        # Refresh token for auto relogin
        'language': 'en'
        # Language for getting translated tags, etc.
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


class Config:
    'JSON config loding and saving.'
    home_root_path = Path.home() / '.pixivmanager-python'

    def __init__(self, cfg_json_file):
        self.cfg_json_file = Path(cfg_json_file)

        if self.cfg_json_file.exists():
            with self.cfg_json_file.open('r', encoding='utf8') as cf:
                loaded_cfg = json.load(cf)
        else:
            loaded_cfg = {}

        self.cfg = {**DEFAULT_CFG, **loaded_cfg}
        self.validate_cfg()
        self.storage_dir = self.get_path(
            self.cfg['storage_dir']
        ) if self.cfg['storage_dir'] else self.home_root_path
        self.pixiv_works_dir = self.get_path(
            self.cfg['pixiv_works_dir']
        ) if self.cfg['pixiv_works_dir'] else self.storage_dir / 'works'
        self.avatars_dir = self.get_path(
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
                urllib.parse.quote_plus(  #Only password is encoded
                    d_mysql['password']),
                d_mysql['host'],
                d_mysql['database'])

    def get_path(self, path) -> Path:
        path = Path(path)
        if not path.is_absolute():
            raise ValueError('Absolute path required!')
        else:
            return path


if __name__ == "__main__":
    Config('config.json')
