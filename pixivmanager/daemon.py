from .config import Config
import threading
import time


class Daemon:
    web_server_thread: threading.Thread = None

    def __init__(self, config: Config, web_server_starter):
        self.config = config
        self.web_server_starter = web_server_starter

    def start_web_server(self):
        if self.web_server_thread:
            print('already started')
            return
        self.web_server_thread = threading.Thread(
            target=self.web_server_starter,
            args=(self, self.config),
            daemon=True)
        self.web_server_thread.start()


def main(config: Config):
    from .webserver import main as webserver_main

    daemon = Daemon(config, webserver_main)
    daemon.start_web_server()

    while True:
        time.sleep(233)
