import os
import sys

os.chdir(os.path.dirname(sys.argv[0]))

import WebAPI

try:
    try:
        sys.getwindowsversion()
    except AttributeError:
        isWindows = False
    else:
        isWindows = True

    if isWindows:
        import win32api, win32process, win32con
        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(handle,
                                      win32process.BELOW_NORMAL_PRIORITY_CLASS)
    else:
        os.nice(5) # pylint: disable=E1101
except Exception as e:
    print('Can not set proccess priority. %s' % e)

WebAPI.start()
