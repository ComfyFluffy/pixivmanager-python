from flask import send_from_directory, Flask, request, abort
from flask_restful import Api, Resource
from pathlib import Path
from glob import glob
import os

from PixivConfig import PixivConfig, cd_script_dir, IMAGE_TYPES
import PixivModel as PM
from PixivAPI import PixivAPI

cd_script_dir()

CONFIG_FILE = 'config.json'

app = Flask('PixivWeb')
api = Api(app)

pcfg = PixivConfig(CONFIG_FILE)
pdb = PM.PixivDB(pcfg.database_uri, echo=True)
papi = PixivAPI(logger=pcfg.get_logger('PixivAPI'))


@app.route('/local/avatar/<path:path>')
def send_local_user_avatar(path):
    return send_from_directory(pcfg.avatars_dir, path)


@app.route('/local/works/<path:path>')
def send_local_works(path):
    return send_from_directory(pcfg.pixiv_works_dir, path)


def get_int_list(s):
    try:
        return list(map(int, request.args.getlist(s)))
    except ValueError:
        abort(400)


def get_image_url(user_id, works_id, page, is_multi_page, is_ugoira=False):
    lpath = pcfg.pixiv_works_dir / str(user_id)
    if is_multi_page or is_ugoira:
        lpath = lpath / str(works_id)
    if is_ugoira:
        patten = ('%s/%s_ugoira0.*' % (lpath, works_id))
        is_multi_page = True
    else:
        patten = '%s/%s/%s_p%s.*' % (lpath, works_id, works_id, page)

    files = list(filter(lambda x: (x[-3:] in IMAGE_TYPES), glob(patten)))
    if files:
        _f = os.path.basename(files[0])
        f = '%s/%s' % (works_id, _f) if is_multi_page else _f
        origin = '/local/works/%s/%s' % (user_id, f)
    else:
        origin = '/proxy/pixiv_image/%s/%s?page=%s' % (user_id, works_id, page)
    return origin


def works_to_json(w: PM.Works):
    is_multi_page = w.page_count != 1
    origin_image_urls = [
        get_image_url(w.author_id, w.works_id, p, is_multi_page,
                      w.works_type == 'ugoira') for p in range(w.page_count)
    ]
    r = {
        'works_id': w.works_id,
        'author_id': w.author_id,
        'type': w.works_type,
        'title': w.title,
        'page_count': w.page_count,
        'total_views': w.total_views,
        'total_bookmarks': w.total_bookmarks,
        'is_bookmarked': w.is_bookmarked,
        'bookmark_rate': w.bookmark_rate,
        'create_date': w.create_date,
        'origin_image_urls': origin_image_urls,
        'caption': w.caption.caption_text
    }
    return r


def user_to_json(u: PM.User):
    return {
        'user_id': u.user_id,
        'name': u.name,
        'account': u.account,
        'is_followed': u.is_followed,
        'total_illusts': u.total_illusts,
        'total_manga': u.total_manga,
        'total_novels': u.total_novels
    }


def ugoira_to_json(ug: PM.Ugoira):
    author_id = ug.author_id
    p = str(pcfg.pixiv_works_dir / str(author_id) / str(ug.works_id))
    f = glob(str(p) + ('/%s_ugoira*.zip' % ug.works_id))
    zip_url = '/local/works/%s/%s/%s' % (author_id, ug.works_id,os.path.basename(f[0]))\
        if f else '/proxy/pixiv_ugoira_zip/%s/%s_ugoira.zip' % (author_id,ug.works_id)
    return {'works_id': ug.works_id, 'delay': ug.delay, 'zip_url': zip_url}


class QueryWorks(Resource):
    def get(self):
        with pdb.get_session() as session:
            r = session.query(PM.Works.works_id)\
                    .join(PM.WorksLocal)\
                    .order_by(PM.WorksLocal.local_id.desc())\
                    .slice(0, 30)
        print(r)
        return [r[0] for w in r]


class QueryWorksDetail(Resource):
    def query(self, works_ids):
        if not works_ids:
            abort(400)
        with pdb.get_session() as session:
            r = session.query(PM.Works).filter(
                PM.Works.works_id.in_(works_ids)).all()

        return [works_to_json(w) for w in r] if r else []

    def get(self):
        return self.query(get_int_list('works_ids[]'))


class QueryUserDetail(Resource):
    def query(self, user_ids):
        if not user_ids:
            abort(400)
        with pdb.get_session() as session:
            r = session.query(PM.User).filter(
                PM.User.user_id.in_(user_ids)).all()

        return [user_to_json(u) for u in r] if r else []

    def get(self):
        return self.query(get_int_list('user_ids[]'))


class QueryUgoira(Resource):
    def get(self, works_id):
        with pdb.get_session() as session:
            r = session.query(PM.Ugoira).filter(
                PM.Ugoira.works_id == works_id).one_or_none()

        return ugoira_to_json(r) if r else None


class QueryUser(Resource):
    def get(self):
        pass


api.add_resource(QueryWorks, '/api/v1/query/works')
api.add_resource(QueryUser, '/api/v1/query/user')
api.add_resource(QueryWorksDetail, '/api/v1/detail/works')
api.add_resource(QueryUserDetail, '/api/v1/detail/user')
api.add_resource(QueryUgoira, '/api/v1/detail/ugoira/<int:works_id>')
app.run(debug=True)
