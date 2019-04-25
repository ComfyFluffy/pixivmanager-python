from .config import Config


class Daemon:
    def __init__(self, config: Config):
        pass


def main(config: Config):
    from .webapi import run as webapi_run
    daemon = Daemon(config)
    webapi_run(daemon, config)
