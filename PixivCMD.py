#!/usr/bin/python3
'''
A simple CMD tool for bookmarks download and user's works download.
Supports database updating.
'''

import os
import sys
import time

import click

import PixivAPI
import PixivConfig
import PixivDB
import PixivDownloader
import PixivHelper

os.chdir(os.path.dirname(sys.argv[0]))


@click.command()
@click.argument('download_type')
@click.option(
    '--user',
    default=0,
    type=click.INT,
    help='User to download. Default yourself.')
@click.option(
    '--max', 'max_times', default=-1, type=click.INT, help='Max get times.')
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
@click.option(
    '--type',
    'works_type',
    default=None,
    type=click.STRING,
    help='Works type to download.\
    \nCan be illusts / manga / ugoira.')
def main(user, max_times, private, download_type, works_type, tags_include,
         tags_exclude):
    '''
    A simple CMD tool for bookmarks download and user's works download.
    Supports database updating.

    Download type: 0: Bookmarks | 1: User's works
    '''
    try:
        user = int(user)
        max_times = int(max_times)
        download_type = int(download_type)
        tags_include = [] if not tags_include else tags_include.split(';')
        tags_exclude = [] if not tags_exclude else tags_exclude.split(';')
    except:
        print('Value USER | MAX | DOWNLOAD_TYPE must be INT.')
        exit(-1)

    pcfg = PixivConfig.PixivConfig('config.json')
    papi = PixivAPI.PixivAPI(pcfg)
    try:
        if pcfg.cfg['pixiv']['refresh_token']:
            login_result = papi.login()
        else:
            import getpass
            username = input('E-mail / Pixiv ID: ')
            password = getpass.getpass()
            login_result = papi.login(username, password)
    except KeyboardInterrupt:
        exit(0)

    if login_result != 0:
        exit(-1)
    pdb = PixivDB.PixivDB()
    pdl = PixivDownloader.PixivDownloader(pcfg)
    user = None if user == 0 else user
    try:
        if download_type == 0:
            print('Downloading all bookmarks...')
            PixivHelper.download_all_bookmarks(user, papi, pdb, pdl, private,
                                               max_times, works_type,
                                               tags_include, tags_exclude)
        elif download_type == 1:
            print('Downloading user\'s works...')
            PixivHelper.download_all_user(user, papi, pdb, pdl, max_times,
                                          works_type, tags_include,
                                          tags_exclude)
        while True:
            if not pdl.dq.empty():
                time.sleep(1)
            else:
                break
        pdl.dq.join()
    except KeyboardInterrupt:
        exit(0)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
