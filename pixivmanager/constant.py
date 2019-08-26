CLIENT_ID = 'MOBrBDS8blbauoSck0ZfDbtuzpyT'
CLIENT_SECRET = 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj'
# Copied from https://github.com/Mapaler/PixivUserBatchDownload

TIMEOUT = 20  # HTTP GET request timeout
DOWNLOADER_TIMEOUT = 150  # Image downloader timeout

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

QUERY_WORKS_ORDER_BY_STR = ('works_id', 'author_id', 'works_type', 'title',
                            'page_count', 'total_views', 'total_bookmarks',
                            'is_bookmarked', 'is_downloaded', 'bookmark_rate',
                            'create_date', 'insert_date')
QUERY_USER_ORDER_BY_STR = (
    'local_id',
    'user_id',
    'name',
    'is_followed',
    'insert_date',
    'total_illusts',
    'total_manga',
    'total_novels',
    'total_illust_bookmarks_public',
    'total_follow_users',
)