from .config import Config


class Daemon:
    def __init__(self, pcfg: Config):
        pass


def main(pcfg: Config):
    from .webapi import run as webapi_run
    daemon = Daemon(pcfg)
    webapi_run(daemon)
