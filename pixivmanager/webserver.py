import asyncio
import json
from pathlib import Path

from aiohttp import WSMsgType, web
from aiohttp.web_request import Request

from .config import Config
from .daemon import Daemon
from .models import DatabaseHelper


async def index(request: Request):
    print(request.headers)
    return web.Response(text='HELLO')


async def websocket_handler(request: Request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            try:
                j = json.loads(msg.data)
            except:
                raise web.HTTPBadRequest

            if j.get('action') == 'close':
                await ws.close()
            else:
                await ws.send_json({'message': 'qwp'})
        elif msg.type == WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    print('websocket connection closed')
    return ws


def main(daemon: Daemon, config: Config):
    app = web.Application()
    app['db'] = DatabaseHelper(config.database_uri, create_tables=False)

    app.add_routes([
        web.get('/', index),
        web.get('/ws', websocket_handler),
        web.static('/img/origin', config.pixiv_works_dir)
    ])
    # https://github.com/tornadoweb/tornado/issues/2352
    asyncio.set_event_loop(asyncio.new_event_loop())
    web.run_app(
        app,
        host=config.cfg['web_ui']['ip'],
        port=config.cfg['web_ui']['port'])
