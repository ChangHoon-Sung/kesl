# simple fork
import os
import time
import pathlib
import setproctitle

def child():
    setproctitle.setproctitle('opentest-child')

    path = pathlib.Path('child.txt')

    with open(path, 'w') as f:
        print('child open')

        n = 30
        print(f'sleep {n}seconds')
        time.sleep(n)
    
    path.unlink() 

    os._exit(0)

def parent():
    setproctitle.setproctitle('opentest-parent')
    newpid = os.fork()
    if newpid == 0:
        child()
    else:
        ppath = pathlib.Path('parent.txt')
        with open(ppath, 'w') as f:
            print('parent open')
            while os.waitpid(-1, os.WNOHANG) == (0, 0):
                time.sleep(1)
        
        ppath.unlink()
        print('Parent finished')

if __name__ == '__main__':
    parent()