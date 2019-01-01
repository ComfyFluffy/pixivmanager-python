import configparser
import logging
import os

workdir = 'storage'

headers = {
    'App-OS':
    'android',
    'App-OS-Version':
    '8.1.0',
    'App-Version':
    '5.0.112',
    'User-Agent':
    'PixivAndroidApp/5.0.112 (Android 8.1.0; Android SDK built for x86)',
    "Referer":
    "https://app-api.pixiv.net/"
}

_config_file = 'config.ini'

_cfg = configparser.ConfigParser()

_cfg['DEFAULT']['workdir'] = workdir
_cfg['DEFAULT']['debug'] = '0'
_cfg['pixiv'] = {}
_cfg['downloader'] = {'thread_count': 5}
_cfg['web_ui'] = {}
_cfg['web_ui']['port'] = '5266'
_cfg['web_ui']['thumbnail_cache'] = '0'

_cfg.read(_config_file)

with open(_config_file, 'w') as cfile:
    _cfg.write(cfile)


def init_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    cf = logging.FileHandler(
        filename=workdir + '/PixivManager.log', encoding='utf-8')
    ch.setLevel(logging.INFO)
    cf.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(name)s : %(message)s')
    ch.setFormatter(logger_formatter)
    cf.setFormatter(logger_formatter)
    logger.addHandler(ch)
    logger.addHandler(cf)
    return logger


def read_cfg(section, option):
    try:
        result = _cfg[section][option]
        if result == '':
            return
        else:
            return result
    except KeyError:
        return
    except:
        logger.exception('Read config error: %s | %s' % (section, option))
        return


def set_cfg(section, option, value):
    try:
        _cfg[section][option] = value
        # logger.info('Set config: %s : %s = %s' % (section, option, value))
        with open(_config_file, 'w') as cfile:
            _cfg.write(cfile)
        return True
    except:
        logger.exception(
            'Set config error: %s | %s | %s' % (section, option, value))
        return False


def get_workdir():
    return workdir


if not os.path.exists(workdir):
    os.makedirs(workdir)
if not workdir.endswith(('/', '\\')):
    workdir = os.path.abspath(workdir) + os.path.sep
else:
    workdir = os.path.abspath(workdir)
logger = init_logger('Config')
