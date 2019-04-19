CLIENT_ID = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
CLIENT_SECRET = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'
# Copied from https://github.com/Mapaler/PixivUserBatchDownload

TIMEOUT = 20  # HTTP GET request timeout

CF_LOGGER_FORMAT = '[%(asctime)s] [%(levelname)s] %(name)s : %(message)s'
CH_LOGGER_FORMAT = '[%(asctime)s] %(name)s %(message)s'

IMAGE_TYPES = ('jpg', 'png', 'gif')

ISO_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'

HTTP_HEADERS = {
    'User-Agent':
    'PixivAndroidApp/5.0.132 (Android 8.1.0; Android SDK built for x86)',
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
    'App-OS': 'android',
    'App-OS-Version': '8.1.0',
    'App-Version': '5.0.132',
    'Referer': 'https://app-api.pixiv.net/'
}