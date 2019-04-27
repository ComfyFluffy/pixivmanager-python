from aiohttp import web
from .daemon import Daemon
from pathlib import Path
from .config import Config
from aiohttp.web_request import Request
import asyncio


async def index(request: Request):
    print(request.headers)
    return web.Response(text='HELLO')


def main(daemon: Daemon, config: Config):
    app = web.Application()

    app.add_routes([
        web.get('/', index),
        web.static('/img/origin', config.pixiv_works_dir)
    ])
    # https://github.com/tornadoweb/tornado/issues/2352
    asyncio.set_event_loop(asyncio.new_event_loop())
    web.run_app(app, host='127.0.0.1', port=5266)
