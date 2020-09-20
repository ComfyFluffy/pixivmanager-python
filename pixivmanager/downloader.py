import os
import queue
import re
import shutil
import threading
import zipfile
from logging import Logger
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count

import imageio
import requests
from sqlalchemy.orm.session import Session

from . import exceptions
from .pixivapi import PixivAPI
from .constant import HTTP_HEADERS, DOWNLOADER_TIMEOUT
from .helpers import _retry, init_logger
from .models import User, Works, WorksLocal

find_date = re.compile(r'img/(\d{4}/\d{2}/\d{2}/\d{2}/\d{2}/\d{2})/')
find_d = re.compile(r'\d*')


class PixivDownloader:
    '''
    Multi-thread downloader for Pixiv works. Database is required.
    Also corvent ugoira to GIF.
    root_download_dir structure:
        image file: (works_id)_p(page).(png, jpg, gif)
        Single page: (author_id)/(image file)
        Multiple pages: (author_id)/(works_id)/(image file)
        Ugoira: (author_id)/(works_id)/(works_id)_ugoira0.gif & zip
    '''
    logger = init_logger('_PixivDownloader_')

    def __init__(self,
                 root_download_dir: Path,
                 threads=5,
                 logger: Logger = None):
        if threads > 32:
            raise ValueError('too many threads: %s' % threads)
        self.root_download_dir = Path(root_download_dir)
        self.dq = queue.Queue()
        self.s = requests.Session()
        self.s.headers = dict(HTTP_HEADERS)
        self.download_threads_list = []
        self.ugoira_maker_pool = ThreadPoolExecutor(
            max_workers=cpu_count() - 1 or 1)

        if logger:
            self.logger = logger
        self.logger.info('Downloader threads: %s' % threads)
        for x in range(0, threads):
            t = threading.Thread(
                target=self._worker, name='downloader_%s' % x, daemon=True)
            self.download_threads_list.append(t)
            t.start()

    @property
    def unfinished_tasks(self):
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
            # Check downloaded file length. Will retry if not match.
            raise exceptions.DownloadException(
                'Downloaded file length not match!')
        part_image_path.replace(
            image_path)  # Replace .part file with origin filename.

        if ugoira_info:
            with zipfile.ZipFile(image_path) as ugoira_zip:
                self.save_ugoira_gif(ugoira_info, ugoira_zip, parent_dir)
        self.logger.info('Downloaded: %s' % filename)

    def save_ugoira_gif(self, ugoira_info, ugoira_zip_path, parent_dir: Path):
        'Use ImageIO to corvent Ugoira ZIP to GIF.'
        wid = ugoira_info['works_id']
        self.logger.info('Making GIF for ugoira %s' % wid)
        tgif: Path = parent_dir / ('%s_ugoira_tmp.gif' % wid)
        gif: Path = parent_dir / ('%s_ugoira.gif' % wid)
        with zipfile.ZipFile(ugoira_zip_path) as ugoira_zip:
            in_zip_files = ugoira_zip.namelist()
            images = [imageio.imread(ugoira_zip.read(f)) for f in in_zip_files]
        imageio.mimsave(tgif, images, duration=ugoira_info['delay'])
        tgif.replace(gif)

    @_retry((requests.RequestException, exceptions.DownloadException,
             zipfile.BadZipFile))
    def _download(self, url: str, download_dir: Path, filename_suffix: str, ugoira_info):
        filename_o = Path(url.split('/')[-1].split('?')[0])
        if filename_suffix:
            filename = filename_o.stem + '_' + filename_suffix + filename_o.suffix
        else:
            filename = str(filename_o)
        parent_dir: Path = self.root_download_dir / download_dir
        image_path = parent_dir / filename
        fd = find_d.findall(str(download_dir))
        fd = [x for x in fd if x]
        wid = ''
        if len(fd) == 3:
            aid = fd[0]
            wid = fd[1]
        elif len(fd) == 1:
            aid = fd[0]

        if image_path.exists() or (parent_dir / filename_o).exists() or (self.root_download_dir / aid / wid / filename_o).exists():
            if ugoira_info and not (parent_dir / (
                    '%s_ugoira.gif' % ugoira_info['works_id'])).exists():
                self.ugoira_maker_pool.submit(
                    self.save_ugoira_gif, ugoira_info, image_path, parent_dir)
            return
        # print(fd,download_dir,image_path)
        # return
        parent_dir.mkdir(parents=True, exist_ok=True)
        with self.s.get(url, stream=True, timeout=DOWNLOADER_TIMEOUT) as res:
            if res.status_code == 200:
                total_size = int(res.headers['Content-Length'])
                self._save_file(parent_dir, filename, res.raw, total_size,
                                ugoira_info)
            elif url.find('1920x1080') != -1:
                self._download((url.replace('1920x1080', '600x600')),
                               download_dir, filename_suffix, ugoira_info)
            else:
                self.logger.warn(
                    'Status code: %s | Url: %s' % (res.status_code, url))

    def _worker(self):
        while True:
            task = self.dq.get()
            try:
                self._download(task[0], task[1], task[2], task[3])
            except Exception:
                self.logger.exception('Download error: ' + str(task))
            self.dq.task_done()

    def _add(self, url: str, download_dir: Path, filename: str, ugoira_info=None):
        task = (url, download_dir, filename, ugoira_info)
        self.dq.put(task)

    def single_works(self,
                     works: Works,
                     image_size='original',
                     ugoira_info=None):
        if ugoira_info and works.works_type == 'ugoira':
            img_parent_dir: Path = Path(str(works.author_id)) / (str(
                works.works_id) + '_' + find_date.findall(ugoira_info['zip_url'])[0].replace('/', ''))
            zip_url = ugoira_info['zip_url'].replace('600x600', '1920x1080')
            # Replace size for higher resolution
            self._add(zip_url, img_parent_dir, '', ugoira_info)
            self._add(
                getattr(works.image_urls[0], image_size), img_parent_dir, '')
            return 2
        if works.page_count == 1:
            self._add(
                getattr(works.image_urls[0], image_size),
                Path(str(works.author_id)),
                find_date.findall(getattr(works.image_urls[0], image_size))[0].replace('/', ''))

            return 0
        else:
            for url in works.image_urls:
                self._add(
                    getattr(url, image_size),
                    Path(str(works.author_id)) / (str(works.works_id) + '_' + find_date.findall(getattr(url, image_size))[0].replace('/', '')), '')
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
        tags_cache = {}

        while next_url:
            n += len(r['illusts'])
            self.logger.info('Processed works: %s' % n)

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
                    users_new.append(u['id'])

            for wj in r['illusts']:
                if not wj['visible']:
                    self.logger.warning('Works %s is invisible!' % wj['id'])
                    continue

                ugoira_json = papi.raw_ugoira_metadata(wj['id']).json() \
                    if wj['type'] == 'ugoira' else None
                works = Works.from_json(
                    session,
                    wj,
                    language=papi.language,
                    ugoira_json=ugoira_json,
                    tags_cache=tags_cache)

                ugoira_info = {
                    'works_id':
                    wj['id'],
                    'zip_url':
                    ugoira_json['ugoira_metadata']['zip_urls']['medium'],
                    'delay': [
                        f['delay'] // 10 / 100  # 1/100s
                        for f in ugoira_json['ugoira_metadata']['frames']
                    ]
                } if wj['type'] == 'ugoira' and ugoira_json else None

                works_tags = {t['name'] for t in wj['tags']}
                if works_type and works.works_type != works_type \
                        or tags_include and not tags_include <= works_tags \
                        or tags_exclude and tags_exclude <= works_tags:
                    continue
                works_ids.append(works.works_id)
                self.single_works(works, ugoira_info=ugoira_info)
                works.is_downloaded = True
            session.commit()

            next_url = r['next_url']
            if max_get_times != None:
                max_get_times -= 1
                if max_get_times < 1:
                    break
            if next_url:
                res = papi.get(next_url)
                r = res.json()

        works_ids.reverse()
        for wid in works_ids:
            WorksLocal.create_if_not_exist(session, wid)
        session.commit()

        if users_new:
            self.logger.info('Updating users info...')
            for u in users_new:
                self.logger.info('Updating user: %s' % u)
                User.from_json(session, papi.raw_user_detail(u).json())
                session.flush()
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
        '''Download user's works or bookmarks.'''
        assert download_type in ('works', 'bookmark')
        if download_type == 'works':
            self.logger.info('Download user\'s works: %s' % user_id)
            res = papi.raw_user_works(user_id)
        elif download_type == 'bookmark':
            self.logger.info('Download user\'s bookmarks: %s' % user_id)
            res = papi.raw_user_bookmark_first(user_id)
        if res:
            self._analyze_res(res, papi, session, max_get_times, works_type,
                              tags_include, tags_exclude)
