import os
import sqlite3
import sys
import time

import Config
import PixivAPI

logger = Config.init_logger('PixivDB')
db_file = 'database.db'
db_path = Config.get_workdir() + db_file


class DBCursor():
    def __init__(self, row=False, **kwargs):
        self.connect = sqlite3.connect(db_path, **kwargs)
        if row:
            self.connect.row_factory = sqlite3.Row
        try:
            self.uri = kwargs['uri']
        except KeyError:
            self.uri = False

    def __enter__(self):
        return self.connect.cursor()

    def __exit__(self, etype, value, traceback):
        if not etype and not self.uri:
            self.connect.commit()
            logger.info('Database commited.')
        self.connect.close()
        # print(etype, value, traceback)


class PixivDB():
    def __init__(self):
        if not os.path.exists(db_path):
            with DBCursor() as dbc:
                with open('init_db.sql', 'r', encoding='utf-8') as sql:
                    SQL_INIT_DB = sql.read()
                dbc.executescript(SQL_INIT_DB)
                logger.info('Created database: %s' % db_path)

    def get_connect(self, read_only=True, timeout=0):
        return sqlite3.connect(db_path, uri=read_only, timeout=timeout)

    def _get_gender(self, g):
        if g == 'female':
            return 1
        elif g == 'male':
            return 0
        else:
            return -1

    def read_user(self, user_id):
        sqll = 'SELECT * FROM users WHERE user_id="%s"' % user_id
        try:
            dbconn = self.get_connect()
            dbc = dbconn.cursor()
            r = dbc.execute(sqll).fetchone()
        except:
            logger.exception('Error read_works(%s)' % user_id)
        finally:
            dbconn.close()
        if r == None:
            return
        return {
            'user_id': r[1],
            'name': r[2],
            'account': r[3],
            'gender': r[4],
            'total_illusts': r[5],
            'total_manga': r[6],
            'total_novels': r[7],
            'is_followed': bool(r[8]),
            # 'country_code': r[9]
        }

    def set_user(self, dbcursor: sqlite3.Cursor, user_info, update=True):
        if user_info == None:
            return
        user_id = user_info['user_id']
        try:
            placeholders = ', '.join('?' * len(user_info))
            columns = ', '.join(user_info.keys())
            sql = "INSERT INTO users (%s) VALUES (%s)" % (columns,
                                                          placeholders)
            dbcursor.execute(sql, list(user_info.values()))
            logger.debug('New user: %s' % user_id)
        except sqlite3.IntegrityError:
            if update:
                columns = ' = ?,'.join(user_info.keys())
                sql = 'UPDATE users SET %s= ? WHERE user_id =%s' % (columns,
                                                                    user_id)
                dbcursor.execute(sql, list(user_info.values()))
                # logger.debug('Updated user: %s' % user_id)

    def sqls_to_works(self,
                      sqls: list,
                      total_count: int,
                      get_ugoira=False,
                      get_url=False):
        result = {'illusts': [], 'total_count': total_count}
        for r in sqls:
            tags = r[11].split() if r[11] != None else None
            custom_tags = r[12].split() if r[12] != None else None
            info = {
                'works_id': r[1],
                'author_id': r[2],
                'type': r[3],
                'title': r[4],
                'caption': r[5],
                'create_date': r[6],
                'page_count': r[7],
                'total_bookmarks': r[8],
                'total_view': r[9],
                'is_bookmarked': r[10],
                'tags': tags,
                'custom_tags': custom_tags,
                'bookmark_rate': r[13]
            }
            if get_url:
                info['image_urls'] = r[14]
            # if get_ugoira and info['type'] == 'ugoira':
            #     dbc = self.dbconn.cursor()
            #     sqlu = 'SELECT * FROM ugoira WHERE works_id="%s"' % info['works_id']
            #     ru = dbc.execute(sqlu).fetchone()
            #     info['ugoira'] = {
            #         'works_id': ru[0],
            #         'delay': ru[1].split(),
            #         'zip_url': ru[2]
            #     }
            result['illusts'].append(info)
        return result

    def read_works(self, works_id):
        try:
            int(works_id)
        except ValueError:
            return
        sqll = 'SELECT * FROM works WHERE works_id="%s"' % works_id
        try:
            dbconn = self.get_connect()
            dbc = dbconn.cursor()
            r = dbc.execute(sqll).fetchone()
        except:
            logger.exception('Error read_works(%s)' % works_id)
        finally:
            dbconn.close()
        if r == None:
            return
        return self.sqls_to_works([r], 1)[0]

    def set_works(self, dbcursor: sqlite3.Cursor, works_info, update=True):
        if works_info == None:
            logger.warning('Got empty info')
            return
        works_id = works_info['works_id']
        image_urls = works_info['image_urls'] if isinstance(
            works_info['image_urls'],
            str) else ' '.join(works_info['image_urls'])
        db_works = {
            'works_id':
            works_id,
            'author_id':
            works_info['author_id'],
            'type':
            works_info['type'],
            'title':
            works_info['title'],
            'caption':
            works_info['caption'],
            'create_date':
            works_info['create_date'],
            'page_count':
            works_info['page_count'],
            'total_bookmarks':
            works_info['total_bookmarks'],
            'total_view':
            works_info['total_view'],
            'is_bookmarked':
            works_info['is_bookmarked'],
            'tags':
            ' %s ' % '  '.join(works_info['tags'])
            if works_info['tags'] else '',
            'image_urls':
            image_urls,
            'bookmark_rate':
            '%.5f' % (works_info['total_bookmarks'] / works_info['total_view'])
        }
        if works_info['type'] == 'ugoira':
            db_ugoira = {
                'works_id':
                works_id,
                'delay':
                ' '.join([str(d) for d in works_info['ugoira']['delay']]),
                'zip_url':
                works_info['ugoira']['zip_url']
            }
        try:
            placeholders = ', '.join('?' * len(db_works))
            columns = ', '.join(db_works.keys())
            sql = "INSERT INTO works (%s) VALUES (%s)" % (columns,
                                                          placeholders)
            dbcursor.execute(sql, list(db_works.values()))
            if works_info['type'] == 'ugoira':
                u_placeholders = ', '.join('?' * len(db_ugoira))
                u_columns = ', '.join(db_ugoira.keys())
                u_sql = "INSERT INTO ugoira (%s) VALUES (%s)" % (
                    u_columns, u_placeholders)
                dbcursor.execute(u_sql, list(db_ugoira.values()))
            logger.debug('New works: %s' % works_id)
            return 1
        except sqlite3.IntegrityError:
            if update:
                columns = ' = ?,'.join(db_works.keys())
                sql = 'UPDATE works SET %s= ? WHERE works_id =%s' % (columns,
                                                                     works_id)
                dbcursor.execute(sql, list(db_works.values()))
                if works_info['type'] == 'ugoira':
                    u_columns = ' = ?,'.join(db_ugoira.keys())
                    u_sql = 'UPDATE ugoira SET %s= ? WHERE works_id =%s' % (
                        u_columns, works_id)
                    dbcursor.execute(u_sql, list(db_ugoira.values()))
                # logger.debug('Updated works: %s' % works_id)
                return 2

    def lookup_works(self,
                     author=None,
                     works_type=None,
                     bookmarked=None,
                     tags_include=[],
                     tags_exclude=[],
                     custom_tags_include=[],
                     custom_tags_exclude=[],
                     sort_by='local_id',
                     sort_asc=False,
                     limit=True,
                     page=0,
                     per_page=30):
        try:
            dbconn = self.get_connect()
            dbc = dbconn.cursor()
            sqll = 'SELECT * FROM works'
            sqll_where = ' WHERE '
            sql_and = ''
            if author:
                a = 'author_id="%s"' % author
                sqll_where += a
                sql_and = ' AND '
            if works_type:
                sqll_where += sql_and
                sql_and = ' AND '
                wt = 'type="%s"' % works_type
                sqll_where += wt
            if bookmarked != None:
                sqll_where += sql_and
                sql_and = ' AND '
                b = 'is_bookmarked=1' if bookmarked else 'is_bookmarked=0'
                sqll_where += b
            if tags_include:
                sqll_where += sql_and
                sql_and = ' AND '
                for tt in tags_include:
                    if tt in tags_exclude:
                        tags_exclude.remove(tt)
                sqll_where += 'tags LIKE "% ' + ' %" AND tags LIKE "% '.join(
                    tags_include) + ' %"'
            if tags_exclude:
                sqll_where += sql_and
                sql_and = ' AND '
                sqll_where += 'NOT tags LIKE "% ' + ' %" AND NOT tags LIKE "% '.join(
                    tags_exclude) + ' %"'
            if custom_tags_include:
                sqll_where += sql_and
                sql_and = ' AND '
                for tt in custom_tags_include:
                    if tt in custom_tags_exclude:
                        custom_tags_exclude.remove(tt)
                sqll_where += 'custom_tags LIKE "% ' + ' %" AND custom_tags LIKE "% '.join(
                    custom_tags_include) + ' %"'
            if custom_tags_exclude:
                sqll_where += sql_and
                sql_and = ' AND '
                sqll_where += 'NOT custom_tags LIKE "% ' + ' %" AND NOT custom_tags LIKE "% '.join(
                    custom_tags_exclude) + ' %"'
            if sqll_where != ' WHERE ':
                sqll += sqll_where
            sqll += ' ORDER BY "%s"' % sort_by
            sqll += ' ASC' if sort_asc else ' DESC'
            if limit:
                sqll += ' LIMIT %s, %s' % (page * per_page, per_page)
                logger.info(sqll)
            if sqll_where == ' WHERE ':
                sqllc = 'SELECT COUNT(local_id) FROM works'
            else:
                sqllc = 'SELECT COUNT(local_id) FROM works ' + sqll_where
            logger.debug(sqllc)
            rc = dbc.execute(sqllc).fetchone()
            rl = dbc.execute(sqll).fetchall()
            r = self.sqls_to_works(rl, rc[0])
            return r
        finally:
            dbconn.close()
