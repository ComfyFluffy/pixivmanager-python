import logging
from datetime import datetime
from logging import Logger

import requests
import retrying

import PixivException
from PixivConfig import HTTP_HEADERS, init_logger

CLIENT_ID = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
CLIENT_SECRET = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'

TIMEOUT = 20

proxy = {
    'http': 'http://127.0.0.1:8888',
    'https': 'http://127.0.0.1:8888',
}


def _on_get_url_error(exception):
    if isinstance(exception, requests.RequestException):
        print('RETRYING...')
        return True


class PixivAPI:
    logger = init_logger('_PixivAPI_')

    def __init__(self, logger: Logger = None):
        if logger:
            self.logger = logger
        self.s = requests.Session()
        self.s.headers = dict(HTTP_HEADERS)

        if False:
            self.s.proxies = proxy
            self.s.verify = 'Test/fiddler.pem'

    def login(self, username='', password='', refresh_token=''):
        auth_url = 'https://oauth.secure.pixiv.net/auth/token'
        datas = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'device_token': 'pixiv',
            'get_secure_url': 'true',
        }

        def on_succeed(login_result):
            parsed_result = login_result.json()
            user_json = parsed_result['response']['user']
            self.pixiv_user_id = user_json['id']
            self.s.headers['Authorization'] = 'Bearer ' + parsed_result[
                'response']['access_token']
            self.refresh_token = parsed_result['response']['refresh_token']
            self.logger.info('Login successful! User ID: %s' % user_json['id'])
            return {
                'status_code': 0,
                'status_message': 'OK',
                'refresh_token': refresh_token,
                'user_id': self.pixiv_user_id
            }

        def login_password(username, password):
            self.logger.info('Login with password...')
            datas['grant_type'] = 'password'
            datas['username'] = username
            datas['password'] = password
            login_result = self.s.post(auth_url, data=datas, timeout=TIMEOUT)
            if login_result.status_code == 200:
                return on_succeed(login_result)
            else:
                self.logger.warning('Password error?')
                return {'status_code': -1, 'status_message': 'PASSWORD ERROR?'}

        def login_token(refresh_token):
            self.logger.info('Login with token...')
            datas['grant_type'] = 'refresh_token'
            datas['refresh_token'] = refresh_token
            login_result = self.s.post(auth_url, data=datas, timeout=TIMEOUT)
            if login_result.status_code == 200:
                return on_succeed(login_result)
            else:
                self.logger.warning('Can not login with token!')
                return {
                    'status_code': -2,
                    'status_message': 'TOKEN LOGIN FAILED'
                }

        try:
            if username and password:
                return login_password(username, password)
            elif refresh_token:
                return login_token(refresh_token)
            else:
                return login_token(self.refresh_token)
        except requests.RequestException as e:
            self.logger.exception('Network exception when logging in!')
            return {
                'status_code': -3,
                'status_message': 'NETWORK EXCEPTION',
                'exception': e
            }

    @retrying.retry(
        stop_max_attempt_number=3,
        retry_on_exception=_on_get_url_error,
        wait_fixed=2000)
    def _get_url(self, url):
        self.logger.debug('Accessed url: %s' % url)
        if not self.s.headers.get('Authorization'):
            self.logger.warning('Empty Pixiv token found! Should login first!')
        result = self.s.get(url, timeout=TIMEOUT)
        if result.status_code == 200:
            return result
        elif result.status_code == 400:
            self.logger.warning('Status code: 400. Try relogin..')
            self.logger.debug('%s | %s' % (url, result.text))
            self.login()
            result = self.s.get(url)
            if result.status_code != 200:
                self.logger.error('Still got %s ! | %s | %s' %
                                  (result.status_code, url, result.text))
            return result
        elif result.status_code == 403:
            self.logger.warning(
                'Status code: 403 | %s, wait for 1 min and retry...' %
                result.text)
            result = self._get_url(url)
            if result.status_code == 403:
                self.logger.error('Still got %s ! | %s | %s' %
                                  (result.status_code, url, result.text))
        else:
            self.logger.warn('Status code: %d' % result.status_code)
            self.logger.debug('%s | %s' % (url, result.text))
            return result

    def get_url(self, url, caller=''):
        result = self._get_url(url)
        if result.status_code == 200:
            return result
        else:
            self.logger.warn('%s(%r) Got empty result' % (caller, url))

    def raw_user_detail(self, user_id):
        return self.get_url(
            'https://app-api.pixiv.net/v1/user/detail?user_id=%s' % user_id,
            'raw_user')

    def raw_user_bookmark_first(self, user_id, private=False):
        p = 'private' if private else 'public'
        return self.get_url(
            'https://app-api.pixiv.net/v1/user/bookmarks/illust?user_id=%s&restrict=%s'
            % (user_id, p), 'raw_bookmark_first')

    def raw_works_detail(self, work_id):
        return self.get_url(
            'https://app-api.pixiv.net/v1/illust/detail?illust_id=%s' %
            work_id, 'raw_work_detail')

    def raw_ugoira_metadata(self, ugoira_id):
        return self.get_url(
            'https://app-api.pixiv.net/v1/ugoira/metadata?illust_id=%s' %
            ugoira_id, 'raw_ugoira')

    def raw_user_works(self, user_id):
        return self.get_url(
            'https://app-api.pixiv.net/v1/user/illusts?user_id=%s' % user_id,
            'raw_user_works')

    #TODO 过滤器
