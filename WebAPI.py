import glob
import io
import logging
import mimetypes
import os
import sys
import threading
import time

from flask import (Flask, abort, jsonify, request, send_file, g, json)
from flask.views import MethodView
from PIL import Image

import Config
import PixivAPI
import PixivDB

SORTS = ('works_id', 'author_id', 'total_bookmarks', 'total_view',
         'is_bookmarked', 'bookmark_rate', 'local_id')

SIZE_INFO = {1: 450, 2: 1200}
WORK_DIR = Config.get_workdir()
WORKS_DIR = WORK_DIR + 'works/'

CACHE_INSERT_SQL = 'INSERT INTO thumbnail VALUES (?,?,?)'

papi_login = False

logger = Config.init_logger('WEB-UI')
debug = bool(int(Config.read_cfg('DEFAULT', 'debug')))
app = Flask(__name__, static_folder='web_ui/static')

mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

thumbnail_cache = bool(int(Config.read_cfg('web_ui', 'thumbnail_cache')))

papi = PixivAPI.PixivAPI()
pdb = PixivDB.PixivDB()

if thumbnail_cache:
    import sqlite3
    import queue


def start():
    global cdbconn
    global cache_queue
    global cache_lock
    if thumbnail_cache:
        logger.info('Thumbnail cache enabled.')

        CACHE_DB_FILE = 'database-thumbnail.db'
        cache_db_path = Config.get_workdir() + CACHE_DB_FILE
        cache_lock = threading.Lock()
        cache_queue = queue.Queue()
        if not os.path.exists(cache_db_path):
            pass  #TODO create db here
            logger.info('Created thumbnail cache database.')
        else:
            cdbconn = sqlite3.connect(cache_db_path, check_same_thread=False)
        # cdbconn.execute('VACUUM')

        cache_worker = threading.Thread(target=cache_save_worker, daemon=True)
        cache_worker.start()

    app.run(
        debug=debug,
        port=int(Config.read_cfg('web_ui', 'port')),
        host='0.0.0.0')


def _info_to_json(r, per_page=30):
    for rr in r['illusts']:
        author_id = rr['author_id']
        works_id = rr['works_id']
        rr['img_url_1'] = '/image/illust/%s/%s?size=1' % (author_id, works_id)
        rr['img_url_2'] = '/image/illust/%s/%s?size=2' % (author_id, works_id)
        if rr['type'] == 'ugoira':
            rr['img_url'] = '/image/ugoira/%s/%s' % (author_id, works_id)
        else:
            rr['img_url'] = '/image/illust/%s/%s' % (author_id, works_id)

    if len(r) < per_page:
        r['next'] = False
    else:
        r['next'] = True
    return r


def _tags(arg):
    if not arg:
        return []
    return arg.split()


def _img_filename(user_id, works_id, page):
    gl_image_file = glob.glob(WORKS_DIR +
                              '%s/%s_p%s.*' % (user_id, works_id, page))
    if not gl_image_file:
        gl_image_file = glob.glob(WORKS_DIR + '%s/%s/%s_p%s.*' %
                                  (user_id, works_id, works_id, page))
    if not gl_image_file:
        gl_image_file = glob.glob(WORKS_DIR + '%s/%s/%s_ugoira%s.*' %
                                  (user_id, works_id, works_id, page))
    if not gl_image_file or gl_image_file[0].endswith('.tmp'):
        return
    return gl_image_file[0]


def cache_save_worker():
    t = 0
    while True:
        try:
            t += 1
            i = cache_queue.get()
            cdbconn.execute(CACHE_INSERT_SQL,
                            [i[0], i[1], sqlite3.Binary(i[2])])
            # if t % 10 == 0:
            cdbconn.commit()
        except:
            logger.exception('Can not save thumbnail to database.')


# def _save_thumbnail_cache(works_id, size, iformat, image_io):
#TODO ASYNC Here


def _read_thumbnail_cache(filename, size):
    sqll = "SELECT thumbnail FROM thumbnail WHERE filename=? AND size=?"
    c = cdbconn.cursor()
    c.execute(sqll, [filename, size])
    r = c.fetchone()
    if r == None:
        return
    r = r[0]
    image_io = io.BytesIO()
    image_io.write(r)
    image_io.seek(0)
    return image_io


def _resize_img(image_filename, size):
    if size:
        try:
            image_io = io.BytesIO()
            img_format = os.path.splitext(image_filename)[1][1:].upper()
            img_format = 'JPEG' if img_format == 'JPG' else img_format

            img = Image.open(image_filename)
            img_size = tuple(img.size)

            img.thumbnail((size, size))
            img.save(image_io, format=img_format)
        except Exception as e:
            img.close()
            image_io.close()
            raise e
        if img_size[0] > size or img_size[1] > size:
            image_io.seek(0)
            cache_queue.put((os.path.basename(image_filename), size,
                             image_io.read()))
        image_io.seek(0)
    else:
        image_io = open(image_filename, 'rb')
    img.close()
    return image_io


def _square_img(image_filename, size=300):
    with Image.open(image_filename) as img:
        s = img.size
        if s[0] > size or s[1] > size:
            if s[0] < s[1]:
                w = size
                h = int(s[1] // (s[0] / size))
            else:
                h = size
                w = int(s[0] // (s[1] / size))
        else:
            return open(image_filename, 'rb')
        img = img.resize((w, h), Image.ANTIALIAS)
        img_format = os.path.splitext(image_filename)[1][1:]
        img_format = 'JPEG' if img_format.upper() == 'JPG' else img_format
        a = (w - size) // 2
        box = (a, 0, a + size, size)
        img = img.crop(box)
        image_io = io.BytesIO()
        img.save(image_io, img_format)
        image_io.seek(0)
        return image_io


@app.route('/', defaults={'path': ''})
# @app.route('/<path:path>')
def catch_all(path):
    with open('web_ui/index.html') as f:
        return f.read()


@app.route('/favicon.ico')
def favicon_ico():
    abort(404)


# @app.route('/api/', defaults={'path': ''})
# @app.route('/api/<path:path>')
# def catch_all_api_err(path):
#     abort(404)

# @app.route('/image/', defaults={'path': ''})
# @app.route('/image/<path:path>')
# def catch_all_image_err(path):
#     abort(404)


@app.route('/api/login', methods=['POST'])
def login():
    global papi_login
    if request.method == 'POST':
        try:
            user = request.form['user']
            password = request.form['password']
        except:
            abort(400)
        try:
            lr = papi.login(username=user, password=password)
        except Exception as e:
            return jsonify({'error': True, 'code': 1, 'message': str(e)})
        if lr == 0:
            papi_login = True
            return jsonify({
                'error': False,
                'code': 0,
                'message': 'Login successful.'
            })
        else:
            return jsonify({
                'error': True,
                'code': 2,
                'message': 'Password error?'
            })


@app.route('/api/works/lookup')
def lookup_works():
    try:
        tags_include = _tags(request.args.get('tags_include'))
        tags_exclude = _tags(request.args.get('tags_exclude'))
        custom_tags_include = _tags(request.args.get('custom_tags_include'))
        custom_tags_exclude = _tags(request.args.get('custom_tags_exclude'))
        sort_by = request.args.get('sort_by')
        sort_by = sort_by if sort_by in SORTS else 'local_id'
        sort_asc = request.args.get('asc')
        sort_asc = False if sort_asc == None else True
        bookmarked = request.args.get('bookmarked')
        if bookmarked != None:
            if bookmarked == '1':
                bookmarked = True
            elif bookmarked == '0':
                bookmarked = False
            else:
                bookmarked = None
        page = request.args.get('page')
        page = 0 if not page else int(page)
        if page < 0:
            raise Exception
        per_page = request.args.get('per_page')
        per_page = 30 if not per_page else int(per_page)
    except:
        abort(400)
    r = pdb.lookup_works(
        author=request.args.get('author'),
        works_type=request.args.get('type'),
        bookmarked=bookmarked,
        tags_include=tags_include,
        tags_exclude=tags_exclude,
        custom_tags_include=custom_tags_include,
        custom_tags_exclude=custom_tags_exclude,
        sort_by=sort_by,
        sort_asc=sort_asc,
        per_page=per_page,
        page=page)
    if not r:
        abort(404)
    return jsonify(_info_to_json(r))


@app.route('/image/illust/<int:user>/<int:works_id>')
def get_img(user, works_id):
    # abort(404)
    page = request.args.get('p')
    size = request.args.get('size')
    square = True if request.args.get('square') != None else False
    try:
        page = int(page) if page else 0
        size = int(size) if size != None and int(size) in [0, 1, 2] else 0
    except:
        abort(400)
    image_file = _img_filename(user, works_id, page)
    if not image_file:
        abort(404)
    if square:
        image_io = _square_img(image_file)
    elif size:
        if thumbnail_cache:
            image_io = _read_thumbnail_cache(
                os.path.basename(image_file), SIZE_INFO[size])
            if not image_io:
                image_io = _resize_img(image_file, SIZE_INFO[size])
        else:
            image_io = _resize_img(image_file, SIZE_INFO[size])
    else:
        image_io = open(image_file, 'rb')
    return send_file(image_io, mimetype=mimetypes.guess_type(image_file)[0])


@app.route('/image/ugoira/<int:user>/<int:works_id>')
def get_ugoira(user, works_id):
    image_file = WORKS_DIR + '%s/%s/%s_ugoira.gif' % (user, works_id, works_id)
    if not os.path.exists(image_file):
        abort(404)
    try:
        image_io = io.BytesIO()
        with open(image_file, 'rb') as f:
            image_io.write(f.read())
        image_io.seek(0)
    except Exception as e:
        image_io.close()
        raise e

    return send_file(image_io, mimetype='image/gif')


def _get_pdb():
    pass


class SessionAPI(MethodView):
    def get(self, uuid):
        with PixivDB.DBCursor() as dbc:
            dbc.execute('SELECT * FROM session')
            r = dbc.fetchone()
            if not r:
                abort(404)
            print(r)
            return r[1]

    def post(self, uuid):
        try:
            j = request.data.decode('utf-8')
        except UnicodeDecodeError:
            abort(400)
        if not j:
            abort(400)
        with PixivDB.DBCursor() as dbc:
            dbc.execute('INSERT INTO session VALUES (?,?)', [
                str(uuid),
            ])
        return str(uuid)


session_view = SessionAPI.as_view('session_api')
app.add_url_rule(
    '/api/session/<uuid:uuid>',
    view_func=session_view,
    methods=['GET', 'POST'])

#TODO stats
