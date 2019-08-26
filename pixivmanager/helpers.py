import logging
import os
import sys
import time
import traceback
from datetime import datetime
from functools import wraps

import coloredlogs

from .constant import CF_LOGGER_FORMAT, CH_LOGGER_FORMAT, ISO_TIME_FORMAT

VERSION_UNDER_3_7 = sys.version_info < (3, 7)


def cd_script_dir():
    p = os.path.dirname(sys.argv[0])
    if p:
        os.chdir(p)


def iso_to_datetime(date_str: str):
    if VERSION_UNDER_3_7:
        # Replace timezone info for python under version 3.7
        date_str = date_str.replace('+09:00', '+0900')
    return datetime.strptime(date_str, ISO_TIME_FORMAT)


def _retry(exception,
           tries=5,
           delay=3,
           backoff=1,
           error_msg=None,
           logger=None,
           print_traceback=False):
    'An retrying decorator.'

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
    'A decorator that checks the time spent by the function.'

    @wraps(f)
    def f_do(*args, **kwargs):
        try:
            t1 = datetime.now()
            return f(*args, **kwargs)
        finally:
            print(f.__name__, datetime.now() - t1)

    return f_do


def init_colorama():
    'Init colorama on Windows for colored output.'
    try:
        import colorama
        colorama.init()
    except ImportError:
        print('Unable to import colorama!')


def init_logger(logger_name, log_file=None) -> logging.Logger:
    'Init colored logger.'
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_logger_formatter = coloredlogs.ColoredFormatter(CH_LOGGER_FORMAT)
    ch.setFormatter(ch_logger_formatter)
    logger.addHandler(ch)

    if log_file:
        cf = logging.FileHandler(filename=log_file, encoding='utf-8')
        cf.setLevel(logging.DEBUG)
        cf.setFormatter(logging.Formatter(CF_LOGGER_FORMAT))
        logger.addHandler(cf)

    return logger
