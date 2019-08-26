import asyncio
import json
from pathlib import Path
import os
from logging import Logger

from aiohttp import WSMsgType, web
from aiohttp.web_request import Request

from .config import Config
from .daemon import Daemon
from .models import DatabaseHelper
from .query import tags_like
from concurrent.futures import ThreadPoolExecutor


class App:
    ws_clients = []
    ws_id = 0

    def query_with_db(self, query):
        with self.db.get_session() as session:
            query.session = session
            return query.all()

    async def _search_tags(self, d: dict):
        term = d['term']
        if term and len(term) < 256:
            q = tags_like(term, d['exclude'])
            r = await self.query_db(q)
            return {
                'id':
                d.get('id'),
                'result': [{
                    'name': t.tag_text,
                    'translation': t.get_translation(self.language)
                } for t in r]
            }

    async def query_db(self, query):
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.pool, self.query_with_db, query)

    async def index(self, request: Request):
        raise web.HTTPFound('/ui/')

    async def ui(self, request: Request):
        return web.FileResponse(self.index_html)

    async def websocket_handler(self, request: Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.ws_clients.append(ws)
        print(self.ws_clients)

        peername = request.transport.get_extra_info('peername')
        self.logger.info(
            'WebSocket client connected: %s:%s, current client(s): %s' %
            (peername[0], peername[1], len(self.ws_clients)))

        await ws.send_json({'message': 'hi'})

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        d = json.loads(msg.data)
                        print(d)
                    except json.JSONDecodeError:
                        raise web.HTTPBadRequest

                    try:
                        action = d.get('action')
                        if action:
                            r = await self.ws_actions[action](d)
                    except:
                        r = None
                        self.logger.exception('Error handling ws message')

                    if r:
                        await ws.send_json(r)
                    else:
                        await ws.send_json({'message': 'no such action'})
                elif msg.type == WSMsgType.ERROR:
                    self.logger.warning(
                        'WebSocket connection closed with exception %s' %
                        ws.exception())
                    break
        finally:
            self.ws_clients.remove(ws)
            self.logger.info(
                'WebSocket client closed: %s:%s, current client(s): %s' %
                (peername[0], peername[1], len(self.ws_clients)))

        return ws

    def __init__(self, config: Config, daemon: Daemon):
        self.ws_actions = {'search_tags': self._search_tags}
        self.app = web.Application()
        self.db = DatabaseHelper(
            config.database_uri, create_tables=False, echo=True)
        self.config = config
        self.daemon = daemon
        self.pool = ThreadPoolExecutor(max_workers=4)
        self.web_ui_dir = Path(os.path.dirname(__file__)) / 'web_ui'
        self.index_html = self.web_ui_dir / 'index.html'
        self.language = config.cfg['pixiv']['language']

        self.logger = config.get_logger('WebServer', 'WebServer.log')
        self.logger.info('Starting web server...')

        self.app.add_routes([
            web.get('/', self.index),
            web.get('/ui', self.index),
            web.get('/ui/', self.ui),
            web.get('/ws', self.websocket_handler),
            web.static('/ui/', self.web_ui_dir, follow_symlinks=True),
            web.static(
                '/img/origin',
                self.config.pixiv_works_dir,
                follow_symlinks=True)
        ])

    def run_app(self):
        asyncio.set_event_loop(asyncio.new_event_loop())
        web.run_app(
            self.app,
            host=self.config.cfg['web_ui']['ip'],
            port=self.config.cfg['web_ui']['port'])


def main(daemon: Daemon, config: Config):
    app = App(config, daemon)
    app.run_app()
    # app = init_app(config, daemon)
    # asyncio.set_event_loop(asyncio.new_event_loop())
    # web.run_app(
    #     app,
    #     host=config.cfg['web_ui']['ip'],
    #     port=config.cfg['web_ui']['port'])
