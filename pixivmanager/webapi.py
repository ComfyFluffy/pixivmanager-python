import uuid
import json
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.options as options

from .daemon import Daemon


class WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        print('WS OPENED')

    def on_message(self, message):
        self.write_message({'message': 'qwp'})

    def on_close(self):
        print('WS DISCONNECTED')


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('qwp')


def run(daemon: Daemon):
    settings = {
        'template_path': 'templates',
        'static_path': 'static',
        'debug': True
    }
    app = tornado.web.Application([
        ('/', IndexHandler),
        ('/ws', WSHandler),
    ], **settings)
    app.listen(5266)
    tornado.ioloop.IOLoop.instance().start()
