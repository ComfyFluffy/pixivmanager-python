import os
import time
import sys

import click

from . import exceptions
from .config import Config
from .downloader import PixivDownloader
from .models import DatabaseHelper
from .papi import PixivAPI


@click.command()
@click.argument('download_type', type=click.Choice(('bookmark', 'works')))
@click.option(
    '--user',
    default=0,
    type=click.INT,
    help='User to download. Default is the current user.')
@click.option(
    '--max', 'max_times', default=None, type=click.INT, help='Max get times.')
@click.option('--private', is_flag=True, help='Download private bookmarks.')
@click.option(
    '--type',
    'works_type',
    default=None,
    type=click.STRING,
    help='Works type to download.\
    \nCan be illusts / manga / ugoira.')
@click.option(  #TODO https://click-docs-zh-cn.readthedocs.io/zh/latest/options.html
    '--tags-include',
    default=None,
    type=click.STRING,
    help='Download works by tags. Split by ;')
@click.option(
    '--tags-exclude',
    default=None,
    type=click.STRING,
    help='Exclude works by tags. Split by ;')
@click.option('--echo', is_flag=True, help='Echo database script')
def main(user, max_times, private, download_type, works_type, tags_include,
         tags_exclude, echo):
    '''
    A simple CMD tool for bookmarks download and user's works download.
    Supports database updating.

    Download type: 0: Bookmarks | 1: User's works
    '''
    try:
        tags_include = None if not tags_include else set(
            tags_include.split(';'))
        tags_exclude = None if not tags_exclude else set(
            tags_exclude.split(';'))
    except:
        print('Value USER | MAX | DOWNLOAD_TYPE must be INT.')
        exit(-1)

    pcfg = Config('config.json')
    papi = PixivAPI(
        language=pcfg.cfg['pixiv']['language'],
        logger=pcfg.get_logger('PixivAPI'))

    login_result = None

    def login_with_pw():
        import getpass
        username = input('E-mail / Pixiv ID: ')
        password = getpass.getpass()
        return papi.login(username, password)

    try:
        refresh_token = pcfg.cfg['pixiv']['refresh_token']
        if refresh_token:
            login_result = papi.login(refresh_token=refresh_token)
        else:
            login_result = login_with_pw()
    except exceptions.LoginTokenError:
        login_result = login_with_pw()
    except exceptions.LoginPasswordError:
        click.echo('Username / password error!')

    if not login_result:
        exit(-1)

    pcfg.cfg['pixiv']['refresh_token'] = papi.refresh_token
    pcfg.save_cfg()
    logger = pcfg.get_logger('PixivCMD')
    pdb = DatabaseHelper(pcfg.database_uri, echo=echo)
    pdl = PixivDownloader(
        pcfg.pixiv_works_dir, logger=pcfg.get_logger('PixivDownloader'))
    if download_type == 'bookmarks':
        logger.info('Downloading all bookmarks...')
    elif download_type == 'works':
        logger.info('Downloading user\'s works...')
    if not user:
        user = papi.pixiv_user_id
    pdl.all_works(download_type, papi, pdb.sessionmaker(), user, max_times,
                  works_type, tags_include, tags_exclude)

    while pdl.unfinished_tasks:
        # Wait until all tasks done.
        time.sleep(0.1)

    pdl.dq.join()
    logger.info('Works download task done! User ID: %s' % papi.pixiv_user_id)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
