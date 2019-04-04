class PixivException(Exception):
    'The base exception'


class DownloadError(PixivException):
    'Downloaded file error'