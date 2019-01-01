import os
import queue
import re
import shutil
import threading
import zipfile

import imageio
import requests
import retrying

import Config
import PixivException

workdir = Config.get_workdir()
sep = os.path.sep
download_dir = workdir + 'works' + sep
headers = {
    'App-OS':
    'android',
    'App-OS-Version':
    '8.1.0',
    'App-Version':
    '5.0.112',
    'User-Agent':
    'PixivAndroidApp/5.0.112 (Android 8.1.0; Android SDK built for x86)',
    "Referer":
    "https://app-api.pixiv.net/"
}
logger = Config.init_logger('Downloader')

pfilename = re.compile(r'\d*_.*')


def _on_download_err(exception):
    logger.exception('Download error!')
    return isinstance(exception, requests.RequestException) or isinstance(
        exception, PixivException.DownloadError) or isinstance(
            exception, zipfile.BadZipFile)


def filename_get_id(filename):
    p = re.compile(r'^([1-9]\d*)_.*\.')
    idl = p.findall(filename)
    return None if idl == [] else idl[0]


class PixivDownloader():
    def __init__(self):
        self.dq = queue.Queue()
        self.s = requests.Session()
        self.s.headers = headers
        self.download_threads = []
        thread_count = int(Config.read_cfg('downloader', 'thread_count'))
        logger.info('Downloader threads: %s' % thread_count)
        for x in range(0, thread_count):
            t = threading.Thread(target=self.worker, name='downloader_%s' % x,daemon=True)
            self.download_threads.append(t)
            t.start()
            # logger.info('Started download thread %s' % x)

    def save_file(self,
                  dirname,
                  filename,
                  content,
                  length=None,
                  ugoira_info=None):
        path = dirname + filename
        logger.info('Downloading: ' + filename)
        with open(path + '.tmp', 'wb') as f:
            shutil.copyfileobj(content, f)
        with open(path + '.tmp', 'rb') as f:
            flength = os.fstat(f.fileno()).st_size
        if length != None and length != flength:
            raise PixivException.DownloadError(
                'Downloaded file length not match!')
        os.rename(path + '.tmp', path)
        if ugoira_info is not None:
            logger.info('Making GIF for ugoira %s' % ugoira_info['works_id'])
            with zipfile.ZipFile(path) as ugoira_zip:
                tgif = dirname + '%s_ugoira_tmp.gif' % ugoira_info['works_id']
                gif = dirname + '%s_ugoira.gif' % ugoira_info['works_id']
                files = ugoira_zip.namelist()
                images = [imageio.imread(ugoira_zip.read(f)) for f in files]
                delay = [f // 10 / 100 for f in ugoira_info['ugoira']['delay']]
                imageio.mimsave(tgif, images, duration=delay)  #1/100s
                if os.path.exists(gif):
                    os.remove(gif)
                os.rename(tgif, gif)
        logger.info('Download successful: ' + filename)

    @retrying.retry(
        stop_max_attempt_number=5,
        retry_on_exception=_on_download_err,
        wait_fixed=2000)
    def download(self, url, path, ugoira_info=None):
        filename = pfilename.findall(url)[0]
        full_path = download_dir + path + filename
        if os.path.exists(full_path):
            return
        try:
            os.makedirs(download_dir + path)
        except FileExistsError:
            pass
        with self.s.get(url, stream=True) as res:
            if res.status_code == 200:
                total_size = int(res.headers['Content-Length'])
                self.save_file(download_dir + path, filename, res.raw,
                               total_size, ugoira_info)
            elif url.find('1920x1080') != -1:
                self.download((url.replace('1920x1080', '600x600')), path)
            else:
                logger.warn(
                    'Status code: %s | Url: %s' % (res.status_code, url))

    def worker(self):
        while True:
            task = self.dq.get()
            # if task is None:
            #     break
            try:
                self.download(task[0], task[1], task[2])
            except Exception:
                logger.exception('Download error: %s' % task)
            self.dq.task_done()

    def add(self, url, path, ugoira_info=None):
        task = [url, path, ugoira_info]
        self.dq.put(task)

    # def stop(self):
    #     for _ in self.download_threads:
    #         self.dq.put(None)

    def _get_mpath(self, work_info):
        return '%s%s%s%s' % (work_info['author_id'], sep,
                             work_info['works_id'], sep)

    def works(self, works_info):
        if works_info == None:
            return -1
        if works_info['type'] == 'ugoira':
            zip_url = works_info['ugoira']['zip_url'].replace(
                '600x600', '1920x1080')
            self.add(zip_url, self._get_mpath(works_info), works_info)
            self.add(works_info['image_urls'], self._get_mpath(works_info))
            return 2
        if works_info['page_count'] == 1:
            self.add(works_info['image_urls'],
                     '%s%s' % (works_info['author_id'], sep))
            return 0
        else:
            path = self._get_mpath(works_info)
            for url in works_info['image_urls']:
                self.add(url, path)
            return 1
