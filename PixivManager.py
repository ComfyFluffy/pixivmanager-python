#!/usr/bin/python3
import os
import sys

if sys.argv[0] != 'PixivManager.py':
    os.chdir(os.path.dirname(sys.argv[0]))

import WebAPI

try:
    try:
        sys.getwindowsversion()
        isWindows = True
    except AttributeError:
        isWindows = False

    if isWindows:
        import win32api, win32process, win32con
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle,
                                      win32process.BELOW_NORMAL_PRIORITY_CLASS)
    # else:
    #     os.nice(1)  # pylint: disable=E1101
except Exception as e:
    print('Can not set proccess priority. %s' % e)

WebAPI.start()
