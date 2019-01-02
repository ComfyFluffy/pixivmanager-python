import requests
import retrying
from datetime import datetime
import dateutil.parser as dp

import Config
import PixivException
# import PixivModel

logger = Config.init_logger('PixivAPI')

CLIENT_ID = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
CLIENT_SECRET = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'

proxy = {
    'http': 'http://127.0.0.1:8888',
    'https': 'http://127.0.0.1:8888',
}

debug = int(Config.read_cfg('DEFAULT', 'debug'))


def _on_get_url_error(exception):
    logger.error(exception)
    logger.warn('Url access error!')
    if isinstance(exception, requests.RequestException):
        logger.warning('Retrying...')
        return True


class PixivAPI():
    def __init__(self):
        self.s = requests.Session()
        self.headers = {
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
        self.s.headers = self.headers
        if False:
            self.s.proxies = proxy
            self.s.verify = 'Test/fiddler.pem'
        self.refresh_token = None

    def login(self, username=None, password=None, refresh_token=None):
        auth_url = 'https://oauth.secure.pixiv.net/auth/token'
        datas = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'device_token': 'pixiv',
            'get_secure_url': 'true',
        }

        def on_succeed(login_result):
            parsed_result = login_result.json()
            self.pixiv_user_id = parsed_result['response']['user']['id']
            access_token = parsed_result['response']['access_token']
            self.headers['Authorization'] = 'Bearer ' + access_token
            self.s.headers = self.headers
            refresh_token = parsed_result['response']['refresh_token']
            Config.set_cfg('pixiv', 'refresh_token', refresh_token)
            logger.info('Login successful! User ID: %s' % self.pixiv_user_id)

        def login_password(username, password):
            logger.info('Login with password...')
            datas['grant_type'] = 'password'
            datas['username'] = username
            datas['password'] = password
            login_result = self.s.post(auth_url, data=datas, timeout=15)
            if login_result.status_code == 200:
                on_succeed(login_result)
                return 0
            else:
                logger.warning('Password error?')
                return 2

        def login_token(refresh_token):
            logger.info('Login with token...')
            datas['grant_type'] = 'refresh_token'
            datas['refresh_token'] = refresh_token
            login_result = self.s.post(auth_url, data=datas, timeout=15)
            if login_result.status_code == 200:
                on_succeed(login_result)
                return 0
            else:
                logger.warning('Can not login with token!')
                return 1

        try:
            if username != None and password != None:
                return login_password(username, password)
            elif refresh_token != None:
                return login_token(refresh_token)
            else:
                logger.warning('Nothing to do when login!')
        except requests.RequestException:
            logger.exception('Error on login!')
            return 3

    @retrying.retry(
        stop_max_attempt_number=3,
        retry_on_exception=_on_get_url_error,
        wait_fixed=2000)
    def get_url(self, url):
        logger.debug('Accessed url: ' + url)
        if self.headers.get('Authorization') == None:
            logger.warning('Empty Pixiv token! Should login first!')
        result = self.s.get(url)
        if result.status_code == 200:
            return result
        elif result.status_code == 400:
            logger.warning('Status code: 400. Try relogin..')
            logger.debug('%s | %s' % (url, result.text))
            self.login(refresh_token=self.refresh_token)
            result = self.s.get(url)
            if result.status_code != 200:
                logger.exception('Still %s ! | %s | %s' % (result.status_code,
                                                           url, result.text))
            return result
        else:
            logger.exception('Status code: %d' % result.status_code)
            logger.debug('%s | %s' % (url, result.text))
            return result

    def raw_user(self, user_id):
        result = self.get_url(
            'https://app-api.pixiv.net/v1/user/detail?user_id=%s' % user_id)
        if result.status_code == 200:
            return result
        else:
            logger.warn('raw_user() : Got empty result , user_id=%s' % user_id)

    def raw_bookmark_first(self, user_id=None, private=False):
        if private:
            p = 'private'
        else:
            p = 'public'
        user_id = self.pixiv_user_id if user_id == None or 0 or '0' else user_id
        result = self.get_url(
            'https://app-api.pixiv.net/v1/user/bookmarks/illust?user_id=%s&restrict=%s'
            % (user_id, p))
        if result.status_code == 200:
            return result
        else:
            logger.warn('raw_bookmark_first() : Got empty result , user_id=%s'
                        % user_id)

    def raw_work_detail(self, work_id):
        result = self.get_url(
            'https://app-api.pixiv.net/v1/illust/detail?illust_id=%s' %
            work_id)
        if result.status_code == 200:
            return result
        else:
            logger.warn(
                'raw_work_detail() : Got empty result , work_id=%s' % work_id)

    def raw_ugoira(self, ugoira_id):
        result = self.get_url(
            'https://app-api.pixiv.net/v1/ugoira/metadata?illust_id=%s' %
            ugoira_id)
        if result.status_code == 200:
            return result
        else:
            logger.warn(
                'raw_ugoira() : Got empty result , ugoira_id=%s' % ugoira_id)

    def raw_user_works(self, user_id):
        result = self.get_url(
            'https://app-api.pixiv.net/v1/user/illusts?user_id=%s' % user_id)
        if result.status_code == 200:
            return result
        else:
            logger.warn(
                'raw_user_works() : Got empty result , user_id=%s' % user_id)

    def _get_gender(self, g):
        if g == 'female':
            return 1
        elif g == 'male':
            return 0
        else:
            return -1

    def _get_image_urls(self, info):
        if info['page_count'] == 1:
            return info['meta_single_page']['original_image_url']
        else:
            return [
                url['image_urls']['original'] for url in info['meta_pages']
            ]

    def get_user(self, user_id):
        res = self.raw_user(user_id)
        if res == None:
            return
        result = res.json()
        info = {
            'user_id': result['user']['id'],
            'name': result['user']['name'],
            'account': result['user']['account'],
            'gender': self._get_gender(result['profile']['gender']),
            'total_illusts': result['profile']['total_illusts'],
            'total_manga': result['profile']['total_manga'],
            'total_novels': result['profile']['total_novels'],
            'is_followed': result['user']['is_followed'],
            'country_code': result['profile']['country_code']
        }
        # PixivModel.User(res.text)
        return info

    def works_to_dict(self, result_json):
        ri = result_json
        if ri['visible'] == False:
            logger.warn('Work %s is invisible!' % ri['id'])
            return
        tags = list(set(t['name'] for t in ri['tags']))
        tags.sort()
        try:
            tags.remove('R-18G')
            tags.insert(0, 'R-18G')
        except ValueError:
            pass
        try:
            tags.remove('R-18')
            tags.insert(0, 'R-18')
        except ValueError:
            pass
        info = {
            'works_id': ri['id'],
            'author_id': ri['user']['id'],
            'type': ri['type'],
            'title': ri['title'],
            'caption': ri['caption'],
            'create_date': int(dp.parse(ri['create_date']).timestamp()),
            'page_count': ri['page_count'],
            'total_bookmarks': ri['total_bookmarks'],
            'total_view': ri['total_view'],
            'is_bookmarked': ri['is_bookmarked'],
            'tags': tags,
            'image_urls': self._get_image_urls(ri)
        }
        if info['type'] == 'ugoira':
            ug = self.raw_ugoira(ri['id'])
            if ug == None:
                return info
            uginfo = ug.json()
            info['ugoira'] = {
                'zip_url': uginfo['ugoira_metadata']['zip_urls']['medium'],
                'delay':
                [f['delay'] for f in uginfo['ugoira_metadata']['frames']]
            }
        return info

    def get_works(self, work_id):
        res = self.raw_work_detail(work_id)
        if res == None:
            return
        return self.works_to_dict(res.json()['illust'])

    #TODO 收藏夹all，作品id，过滤器


if __name__ == "__main__":
    papi = PixivAPI()
    papi.get_user(3176620)