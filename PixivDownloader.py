import os
import queue
import re
import shutil
import threading
import zipfile
from logging import Logger
from pathlib import Path

import imageio
import requests
from sqlalchemy.orm.session import Session

import PixivConfig
import PixivException
from PixivAPI import PixivAPI
from PixivModel import Ugoira, User, Works, WorksLocal


class PixivDownloader:
    logger = PixivConfig.init_logger('_PixivDownloader_')

    def __init__(self,
                 root_download_dir: Path,
                 threads=5,
                 logger: Logger = None):
        assert threads <= 32
        self.root_download_dir = Path(root_download_dir)
        self.dq = queue.Queue()
        self.s = requests.Session()
        self.s.headers = dict(PixivConfig.HTTP_HEADERS)
        self.download_threads_list = []
        if logger:
            self.logger = logger
        self.logger.info('Downloader threads: %s' % threads)
        for x in range(0, threads):
            t = threading.Thread(
                target=self._worker, name='downloader_%s' % x, daemon=True)
            self.download_threads_list.append(t)
            t.start()

    @property
    def finished(self):
        return self.dq.unfinished_tasks

    def _save_file(self, parent_dir: Path, filename: str, content_stream,
                   slength: int, ugoira_info):
        parent_dir = Path(parent_dir)
        image_path: Path = parent_dir / filename
        part_image_path: Path = parent_dir / (filename + '.part')
        self.logger.info('Downloading: %s' % filename)
        with part_image_path.open('wb') as f:
            shutil.copyfileobj(content_stream, f)
        flength = os.stat(part_image_path).st_size
        if slength and slength != flength:
            raise PixivException.DownloadError(
                'Downloaded file length not match!')
        part_image_path.replace(image_path)

        if ugoira_info:
            with zipfile.ZipFile(image_path) as ugoira_zip:
                self.save_ugoira_gif(ugoira_info, ugoira_zip, parent_dir)
        self.logger.info('Downloaded: %s' % filename)

    def save_ugoira_gif(self, ugoira_info, ugoira_zip, parent_dir: Path):
        wid = ugoira_info['works_id']
        self.logger.info('Making GIF for ugoira %s' % wid)
        tgif: Path = parent_dir / ('%s_ugoira_tmp.gif' % wid)
        gif: Path = parent_dir / ('%s_ugoira.gif' % wid)
        in_zip_files = ugoira_zip.namelist()
        images = [imageio.imread(ugoira_zip.read(f)) for f in in_zip_files]
        imageio.mimsave(tgif, images, duration=ugoira_info['delay'])
        tgif.replace(gif)

    @PixivConfig._retry((requests.RequestException,
                         PixivException.DownloadError, zipfile.BadZipFile),
                        error_msg='Unable to download file. Retrying...',
                        logger=logger)
    def _download(self, url: str, download_dir: Path, ugoira_info):
        filename: str = url.split('/')[-1].split('?')[0]
        parent_dir: Path = self.root_download_dir / download_dir
        image_path = parent_dir / filename
        if image_path.exists():
            if ugoira_info and not (parent_dir / (
                    '%s_ugoira.gif' % ugoira_info['works_id'])).exists():
                with zipfile.ZipFile(image_path) as ugoira_zip:
                    self.save_ugoira_gif(ugoira_info, ugoira_zip, parent_dir)
            return
        parent_dir.mkdir(parents=True, exist_ok=True)
        with self.s.get(url, stream=True) as res:
            if res.status_code == 200:
                total_size = int(res.headers['Content-Length'])
                self._save_file(parent_dir, filename, res.raw, total_size,
                                ugoira_info)
            elif url.find('1920x1080') != -1:
                self._download((url.replace('1920x1080', '600x600')),
                               download_dir, ugoira_info)
            else:
                self.logger.warn(
                    'Status code: %s | Url: %s' % (res.status_code, url))

    def _worker(self):
        while True:
            task = self.dq.get()
            try:
                self._download(task[0], task[1], task[2])
            except Exception:
                self.logger.exception('Download error: ' + str(task))
            self.dq.task_done()

    def _add(self, url: str, download_dir: Path, ugoira_info=None):
        task = (url, download_dir, ugoira_info)
        self.dq.put(task)

    def single_works(self,
                     works: Works,
                     image_size='original',
                     ugoira_info=None):
        if ugoira_info and works.works_type == 'ugoira':
            img_parent_dir: Path = Path(str(works.author_id)) / str(
                works.works_id)
            zip_url = ugoira_info['zip_url'].replace('600x600', '1920x1080')
            self._add(zip_url, img_parent_dir, ugoira_info)
            self._add(getattr(works.image_urls[0], image_size), img_parent_dir)
            return 2
        if works.page_count == 1:
            self._add(
                getattr(works.image_urls[0], image_size),
                Path(str(works.author_id)))
            return 0
        else:
            for url in works.image_urls:
                self._add(
                    getattr(url, image_size),
                    Path(str(works.author_id)) / str(works.works_id))
            return 1

    def _analyze_res(self,
                     res,
                     papi: PixivAPI,
                     session: Session,
                     max_get_times: int,
                     works_type: str,
                     tags_include: set = None,
                     tags_exclude: set = None):
        n = 0
        r = res.json()
        next_url = True
        works_ids = []
        users_new = []
        users_dict = {
            w['user']['id']: w['user']
            for w in r['illusts'] if w['visible']
        }

        for u in users_dict.values():
            unew = User.create_if_empty(
                session,
                u['id'],
                name=u['name'],
                account=u['account'],
                is_followed=u['is_followed'])
            if unew:
                users_new.append(unew)
        session.commit()

        while next_url:
            n += len(r['illusts'])
            self.logger.info('Got works: %s' % n)

            for wj in r['illusts']:
                if not wj['visible']:
                    self.logger.warn('Works %s is invisible!' % wj['id'])
                    continue
                ugoira_json = papi.raw_ugoira_metadata(wj['id']).json() \
                    if wj['type'] == 'ugoira' else None
                works = Works.from_json(session, wj, ugoira_json=ugoira_json)
                if wj['type'] == 'ugoira' and ugoira_json:
                    ugoira_info = {
                        'works_id':
                        wj['id'],
                        'zip_url':
                        ugoira_json['ugoira_metadata']['zip_urls']['medium'],
                        'delay': [
                            f['delay'] // 10 / 100  #1/100s
                            for f in ugoira_json['ugoira_metadata']['frames']
                        ]
                    }
                else:
                    ugoira_info = None
                works_tags = {t.tag_text for t in works.tags}
                if works_type and works.works_type != works_type \
                or tags_include and not tags_include.issubset(works_tags) \
                or tags_exclude and tags_exclude.issubset(works_tags):
                    continue
                works_ids.append(works.works_id)
                self.single_works(works, ugoira_info=ugoira_info)
            session.commit()

            next_url = r['next_url']
            if max_get_times != None:
                max_get_times -= 1
                if max_get_times < 1:
                    break
            if next_url:
                res = papi.get_url(next_url)
                r = res.json()

        works_ids.reverse()
        for wid in works_ids:
            WorksLocal.create_if_not_exist(session, wid)
        session.commit()

        if users_new:
            self.logger.info('Updating users info...')
            for u in users_new:
                self.logger.info('Updating user: %s' % u.user_id)
                User.from_json(session, papi.raw_user_detail(u.user_id).json())
            session.commit()

    def all_works(self,
                  download_type: str,
                  papi: PixivAPI,
                  session: Session,
                  user_id: int,
                  max_get_times: int,
                  works_type: str,
                  tags_include=None,
                  tags_exclude=None):
        assert download_type in ('user', 'bookmark')
        if download_type == 'user':
            self.logger.info('Download user\'s works: %s' % user_id)
            res = papi.raw_user_works(user_id)
        elif download_type == 'bookmark':
            self.logger.info('Download user\'s bookmarks: %s' % user_id)
            res = papi.raw_user_bookmark_first(user_id)
        if res:
            self._analyze_res(res, papi, session, max_get_times, works_type,
                              tags_include, tags_exclude)


#TODO Move helper into downloader
