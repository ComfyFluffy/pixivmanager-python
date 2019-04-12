class PixivException(Exception):
    pass


class DownloadException(PixivException):
    pass


class APIException(PixivException):
    pass


class LoginPasswordError(APIException):
    pass


class LoginTokenError(APIException):
    pass