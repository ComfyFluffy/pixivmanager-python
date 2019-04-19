from logging import Logger

import requests

from . import exceptions
from .constant import CLIENT_ID, CLIENT_SECRET, HTTP_HEADERS, TIMEOUT
from .helpers import _retry, init_logger

proxy = {
    'http': 'http://127.0.0.1:8888',
    'https': 'http://127.0.0.1:8888',
}


class PixivAPI:
    '''
    A Pixiv base API.
    raw_ returns requests Response.'''
    logger = init_logger('_PixivAPI_')
    language = 'en'
    pixiv_user_id = -1  # Login user's Pixiv ID
    refresh_token = None

    def __init__(self,
                 language: str = None,
                 logger: Logger = None,
                 save_to_db=False):
        if logger:
            self.logger = logger
        self.s = requests.Session()
        self.s.headers = dict(HTTP_HEADERS)
        if language:
            self.language = language
            self.s.headers['Accept-Language'] = language

        if False:
            self.s.proxies = proxy
            self.s.verify = 'storage/fiddler.pem'

    @_retry(
        requests.RequestException,
        delay=2,
        tries=5,
        error_msg='Network exception occurred! Retrying...')
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
            return True

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
                raise exceptions.LoginPasswordError(
                    login_result.raw.decode('unicode_escape'))

        def login_token(refresh_token):
            self.logger.info('Login with token...')
            datas['grant_type'] = 'refresh_token'
            datas['refresh_token'] = refresh_token
            login_result = self.s.post(auth_url, data=datas, timeout=TIMEOUT)
            if login_result.status_code == 200:
                return on_succeed(login_result)
            else:
                self.logger.warning('Can not login with token!')
                raise exceptions.LoginTokenError

        if username and password:
            return login_password(username, password)
        elif refresh_token:
            return login_token(refresh_token)
        elif not self.refresh_token:
            raise ValueError(
                'Neither username & password or refresh token found!')
        else:
            return login_token(self.refresh_token)

    @_retry(requests.RequestException, delay=2, tries=5)
    def _get(self, url):
        self.logger.debug('Accessed url: %s' % url)
        if not self.s.headers.get('Authorization'):
            self.logger.warning('Empty Pixiv access token!')
        result = self.s.get(url, timeout=TIMEOUT)
        if result.status_code == 200:
            return result
        elif result.status_code == 400:
            self.logger.warning('Status code: 400')
            self.logger.debug('400 | %s | %s' % (url, result.text))
            if result.json()['message'].find('invalid_grant') != -1:
                self.logger.warning('Access Token expired. Refreshing...')
                self.login()
                result = self.s.get(url, timeout=TIMEOUT)
            return result
        elif result.status_code == 403:
            self.logger.warning('Status code: 403')
            self.logger.debug('403 | %s | %s' % (url, result.text))
            return result
        else:
            self.logger.warn('Status code: %s' % result.status_code)
            self.logger.debug(
                '%s | %s | %s' % (result.status_code, url, result.text))
            return result

    def get(self, url, caller=''):
        result = self._get(url)
        if result.status_code == 200:
            return result
        else:
            self.logger.warn('%s(%r) Got empty result' % (caller, url))

    def raw_user_detail(self, user_id):
        return self.get(
            'https://app-api.pixiv.net/v1/user/detail?user_id=%d' %
            int(user_id), 'raw_user')

    def raw_user_bookmark_first(self, user_id, private=False):
        p = 'private' if private else 'public'
        return self.get(
            'https://app-api.pixiv.net/v1/user/bookmarks/illust?user_id=%d&restrict=%s'
            % (int(user_id), p), 'raw_bookmark_first')

    def raw_works_detail(self, work_id):
        return self.get(
            'https://app-api.pixiv.net/v1/illust/detail?illust_id=%d' %
            int(work_id), 'raw_work_detail')

    def raw_ugoira_metadata(self, ugoira_id):
        return self.get(
            'https://app-api.pixiv.net/v1/ugoira/metadata?illust_id=%d' %
            int(ugoira_id), 'raw_ugoira')

    def raw_user_works(self, user_id):
        return self.get(
            'https://app-api.pixiv.net/v1/user/illusts?user_id=%d' %
            int(user_id), 'raw_user_works')
