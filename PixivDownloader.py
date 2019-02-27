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
import retrying

import PixivConfig
import PixivException


class PixivDownloader():
    def __init__(self, logger: Logger, root_download_dir: Path, threads=5):
        self.root_download_dir = root_download_dir
        self.dq = queue.Queue()
        self.s = requests.Session()
        self.s.headers = dict(PixivConfig.HTTP_HEADERS)
        self.download_threads_list = []
        self.logger = logger
        self.logger.info('Downloader threads: %s' % threads)
        for x in range(0, threads):
            t = threading.Thread(
                target=self.__worker, name='downloader_%s' % x, daemon=True)
            self.download_threads_list.append(t)
            t.start()

    def __on_download_err(self, exception):
        self.logger.error('Download error! %s' % exception)
        return isinstance(exception,
                          (requests.RequestException,
                           PixivException.DownloadError, zipfile.BadZipFile))

    def __save_file(self,
                    parent_dir: Path,
                    filename: str,
                    content_stream,
                    slength=0,
                    ugoira_info=None):
        parent_dir = Path(parent_dir)
        image_path: Path = parent_dir / filename
        part_image_path: Path = image_path.with_suffix(image_path.suffix +
                                                       '.part')
        self.logger.info('Downloading: %s' % filename)
        with part_image_path.open('wb') as f:
            shutil.copyfileobj(content_stream, f)
            flength = os.fstat(f.fileno()).st_size
        if slength and slength != flength:
            raise PixivException.DownloadError(
                'Downloaded file length not match!')
        part_image_path.replace(image_path)

        if ugoira_info:
            self.logger.info(
                'Making GIF for ugoira %s' % ugoira_info['works_id'])
            with zipfile.ZipFile(image_path) as ugoira_zip:
                tgif: Path = parent_dir / '%s_ugoira_tmp.gif' % ugoira_info['works_id']
                gif: Path = parent_dir / '%s_ugoira.gif' % ugoira_info['works_id']
                in_zip_files = ugoira_zip.namelist()
                images = [
                    imageio.imread(ugoira_zip.read(f)) for f in in_zip_files
                ]
                delay = [f // 10 / 100 for f in ugoira_info['ugoira']['delay']]
                imageio.mimsave(tgif, images, duration=delay)  #1/100s
                tgif.replace(gif)
        self.logger.info('Downloaded: %s' % filename)

    @retrying.retry(
        stop_max_attempt_number=5,
        retry_on_exception=__on_download_err,
        wait_fixed=2000)
    def __download(self, url: str, download_dir: Path, ugoira_info=None):
        filename: str = url.split('/')[-1].split('?')[0]
        parent_dir: Path = self.root_download_dir / download_dir
        if (parent_dir / filename).exists():
            return
        parent_dir.mkdir(exist_ok=True)
        with self.s.get(url, stream=True) as res:
            if res.status_code == 200:
                total_size = int(res.headers['Content-Length'])
                self.__save_file(parent_dir, filename, res.raw, total_size,
                                 ugoira_info)
            elif url.find('1920x1080') != -1:
                self.__download((url.replace('1920x1080', '600x600')),
                                download_dir, ugoira_info)
            else:
                self.logger.warn(
                    'Status code: %s | Url: %s' % (res.status_code, url))

    def __worker(self):
        while True:
            task = self.dq.get()
            try:
                self.__download(task[0], task[1], task[2])
            except Exception:
                self.logger.exception('Download error: %s' % task)
            self.dq.task_done()

    def __add(self, url: str, download_dir: Path, ugoira_info=None):
        task = [url, download_dir, ugoira_info]
        self.dq.put(task)

    def works(self, works_info):
        if not works_info:
            return -1

        img_parent_dir: Path = Path(str(works_info['author_id'])) / str(
            works_info['works_id'])
        if works_info['type'] == 'ugoira':
            zip_url = works_info['ugoira']['zip_url'].replace(
                '600x600', '1920x1080')
            self.__add(zip_url, img_parent_dir, works_info)
            self.__add(works_info['image_urls'], img_parent_dir)
            return 2
        if works_info['page_count'] == 1:
            self.__add(works_info['image_urls'],
                       Path(str(works_info['author_id'])))
            return 0
        else:
            for url in works_info['image_urls']:
                self.__add(url, img_parent_dir)
            return 1
