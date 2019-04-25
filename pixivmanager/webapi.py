import uuid
import json
import signal

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.options as options
from tornado_sqlalchemy import as_future, make_session_factory, SessionMixin

from .daemon import Daemon
from .config import Config
from .models import Works


class Application(tornado.web.Application):
    is_closing = False

    def __init__(self, handlers, daemon: Daemon, config: Config, logger,
                 **settings):
        self.daemon = daemon
        self.config = config
        self.logger = logger
        super().__init__(handlers=handlers, **settings)

    def signal_handler(self, signum, frame):
        self.is_closing = True

    def try_exit(self):
        if self.is_closing:
            # clean up here
            tornado.ioloop.IOLoop.instance().stop()


class WSHandler(tornado.websocket.WebSocketHandler, SessionMixin):
    def check_origin(self, origin):
        return True

    def open(self):
        print('WS OPENED')

    def on_message(self, message):
        self.write_message({'message': 'qwp'})

    def on_close(self):
        print('WS DISCONNECTED')


class IndexHandler(tornado.web.RequestHandler, SessionMixin):
    async def get(self):
        with self.make_session() as session:
            r = await as_future(session.query(Works).limit(30).all)
            print('\nDONE\n')
            self.write({
                'illusts': [{
                    'title':
                    w.title,
                    'works_id':
                    w.works_id,
                    'caption':
                    w.caption.caption_text if w.caption else None
                } for w in r]
            })


def run(daemon: Daemon, config: Config):
    settings = {
        'static_path': 'web_ui/static',
        'debug': True,
        'session_factory': make_session_factory(
            config.database_uri, echo=True)
    }
    logger = config.get_logger('WebAPI')
    app = Application([
        ('/', IndexHandler),
        ('/ws', WSHandler),
    ], daemon, config, logger, **settings)
    app.listen(config.cfg['web_ui']['port'])

    signal.signal(signal.SIGINT, app.signal_handler)
    tornado.ioloop.PeriodicCallback(app.try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
