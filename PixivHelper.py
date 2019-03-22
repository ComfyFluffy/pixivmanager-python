from PixivAPI import PixivAPI
from PixivModel import PixivDB
from PixivDownloader import PixivDownloader
from logging import Logger


def analyze(res,
            papi: PixivAPI,
            pdb: PixivDB,
            pdl: PixivDownloader,
            logger: Logger,
            max_get_times=-1,
            update_users=True,
            works_type=None,
            tags_include=[],
            tags_exclude=[]):
    r = res.json()
    next_url = r['next_url']
    n = 0
    tags_include = set(tags_include)
    tags_exclude = set(tags_exclude)
    with PixivDB.DBCursor() as dbc:
        if update_users:
            dbc.execute('SELECT user_id FROM users')
            all_users = {u[0] for u in dbc.fetchall()}
        works_info = []
        while True:
            n += len(r['illusts'])
            logger.info('Got works: %s' % n)
            max_get_times -= 1
            for w in r['illusts']:
                info = papi.works_to_dict(w)
                if info != None:
                    tags = set(info['tags'])
                    #TODO async user info
                    if works_type and info['type'] != works_type \
                    or tags_include and not tags_include.issubset(tags) \
                    or tags_exclude and tags_exclude.issubset(tags):
                        continue
                    aid = info['author_id']
                    if aid not in all_users:
                        all_users.add(aid)
                        user_info = papi.get_user(info['author_id'])
                        if user_info:
                            pdb.set_user(dbc, user_info)
                    works_info.append(info)
                    pdl.works(info)
            if next_url == None or max_get_times == 0:
                break
            r = papi.get_url(next_url).json()
            next_url = r['next_url']
        works_info.reverse()
        # t = 0
        for w in works_info:
            if w:
                # t += 1
                pdb.set_works(dbc, w)
            # if t % 100 == 0:


def download_all_bookmarks(user_id,
                           papi: PixivAPI,
                           pdb: PixivDB,
                           pdl: PixivDownloader,
                           logger: Logger,
                           private=False,
                           max_get_times=-1,
                           works_type=None,
                           tags_include=[],
                           tags_exclude=[]):
    res = papi.raw_bookmark_first(user_id, private)
    if res == None:
        return
    analyze(
        res,
        papi,
        pdb,
        pdl,
        logger,
        max_get_times,
        works_type=works_type,
        tags_include=tags_include,
        tags_exclude=tags_exclude)


def download_all_user(user_id,
                      papi: PixivAPI,
                      pdb: PixivDB,
                      pdl: PixivDownloader,
                      logger: Logger,
                      max_get_times=-1,
                      works_type=None,
                      tags_include=[],
                      tags_exclude=[]):
    res = papi.raw_user_works(user_id)
    if res == None:
        return
    analyze(
        res,
        papi,
        pdb,
        pdl,
        logger,
        max_get_times,
        works_type=works_type,
        tags_include=tags_include,
        tags_exclude=tags_exclude)
