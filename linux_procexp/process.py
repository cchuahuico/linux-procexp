import os
import os.path
from collections import namedtuple

ProcessOwner = namedtuple('ProcessOwner', 'uid', 'gid', 'name')

class Process(object):
    PROC_PATH = '/proc'
    THREADS_DIR_NAME = 'task'
    CMDLINE_FILE_NAME = 'cmdline'

    def __init__(self, pid, parent=None):
        self.pid = pid
        self.cmdline = ''
        self.parent = parent
        if parent:
            self.pid_dir = os.path.join(self.PROC_PATH, parent.pid, self.THREADS_DIR_NAME, self.pid)
        else:
            self.pid_dir = os.path.join(self.PROC_PATH, self.pid)

        if not os.path.exists(self.pid_dir):
            raise ValueError('This process/thread does not exist in {}'.format(self.PROC_PATH))

    @property
    def pid(self):
        return self.pid

    @property
    def mem_usage(self):
        pass

    @property
    def priority(self):
        pass

    @property
    def owner(self):
        pass


    @property
    def cpu_usage(self):
        pass

    @property
    def descriptors(self):
        pass

    @property
    def threads(self):
        # should call this method if this is a thread
        assert self.parent is None
        return [Process(tid, self) for tid in os.listdir(os.path.join(self.pid_dir, self.THREADS_DIR_NAME))]

    @property
    def cmdline(self):
        # read cmdline only when needed since it is possible for this
        # information to be filtered in the UI
        if not self.cmdline:
            with open(os.path.join(self.pid_dir, self.CMDLINE_FILE_NAME)) as f:
                self.cmdline = f.read()

        return self.cmdline


