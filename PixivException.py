class PixivException(Exception):
    pass

class DownloadError(PixivException):
    'Downloaded file error'