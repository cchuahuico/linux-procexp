import os
import os.path
import re
import pwd
from collections import namedtuple

ProcessOwner = namedtuple('ProcessOwner', ['uid', 'name'])
FileDescriptor = namedtuple('FileDescriptor', ['id', 'type', 'name'])
MappedRegion = namedtuple(
    'MappedRegions', ['start', 'end', 'permissions', 'offset', 'dev', 'inode', 'file_path'])

# TODO: look into the enum backports (might be overkill)
class ProcessStates:
    ZOMBIE = 'Z'
    RUNNING = 'R'
    SLEEPING = 'S'
    DISKSLEEP = 'D'
    STOPPED = 'T'
    DEAD = 'X'

class Process(object):
    # TODO: find a better place for these constants
    PROC_PATH = '/proc'
    THREADS_DIR_NAME = 'task'
    FD_DIR_NAME = 'fd'
    EXE_FILE_NAME = 'exe'
    CMDLINE_FILE_NAME = 'cmdline'
    CWD_FILE_NAME = 'cwd'
    MEM_MAP_FILE_NAME = 'maps'
    STAT_FILE_NAME = 'stat'
    STATUS_FILE_NAME = 'status'

    def __init__(self, pid, parent=None):
        # initializer takes pid as an int since it's more intuitive for the class
        # consumer. however, this class mainly uses pid as a string for path joins
        self._pid = str(pid)

        # if the Process object is initialized with a parent, it is treated as a thread
        # and will have a different directory  representing its runtime objects
        self.pid_dir = os.path.join(self.PROC_PATH, str(parent.pid), self.THREADS_DIR_NAME, self._pid) \
            if parent else os.path.join(self.PROC_PATH, self._pid)

        if not os.path.exists(self.pid_dir):
            raise ValueError('{} does not exist'.format(self.pid_dir))

        self._parent = parent

        # all the instance variables defined from here are computed only when needed
        # because either the information is not included in the default view or they
        # are likely to change during the process' execution
        self._cmdline = ''

    def get_full_path(self, dir_name):
        return os.path.join(self.pid_dir, dir_name)

    # TODO: look into the linecache module for optimization
    def get_stat_info(self, prop_idx):
        with open(self.get_full_path(self.STAT_FILE_NAME)) as f:
            return f.read().split(' ')[prop_idx]

    @property
    def pid(self):
        return int(self._pid)

    @property
    def name(self):
        # TODO: decide what to do with kernel support. for example, this is only
        # valid for kernel >= 2.2
        try:
            proc_name = os.readlink(os.path.join(self.pid_dir, self.EXE_FILE_NAME))
        except PermissionError:
            # most of the time exe has more stringent permissions so
            # read and parse cmdline instead
            proc_name = self.cmdline.split(' ')[0]

        if not proc_name:
            # name from stat has the form: '(name)'
            return self.get_stat_info(1)[1:-1]
        return os.path.basename(proc_name)

    @property
    def mem_usage(self):
        pass

    @property
    def priority(self):
        return self.get_stat_info(17)

    @property
    def nice(self):
        return self.get_stat_info(18)

    @property
    def parent_pid(self):
        if not self._parent:
            self._parent = self.get_stat_info(3)
        return int(self._parent)

    @property
    # TODO: look more into real vs effective UID
    def owner(self):
        with open(self.get_full_path(self.STATUS_FILE_NAME)) as f:
            for count, line_info in enumerate(f):
                if count == 7:
                    ruid = re.split('\s+', line_info)[1]

        return ProcessOwner(ruid, pwd.getpwuid(int(ruid)).pw_name)

    @property
    def cpu_usage(self):
        pass

    @property
    def state(self):
        return self.get_stat_info(2)

    @property
    def mem_map(self):
        # TODO: look into adding the libraries to the descriptors list
        with open(self.get_full_path(self.MEM_MAP_FILE_NAME)) as f:
            return [MappedRegion(re.split('\s+', entry)) for entry in f]

    @property
    def cwd(self):
        return os.readlink(self.get_full_path(self.CWD_FILE_NAME))

    @property
    def descriptors(self):
        fd_path = self.get_full_path(self.FD_DIR_NAME)
        # TODO: use python-magic to implement the type field for descriptors
        return [FileDescriptor(fid, 'UNIMPLEMENTED', os.readlink(os.path.join(fd_path, fid)))
            for fid in os.listdir(fd_path)]

    @property
    def threads(self):
        return [Process(tid, self) for tid in os.listdir(os.path.join(
            self.pid_dir, self.THREADS_DIR_NAME))]

    @property
    def cmdline(self):
        if not self._cmdline:
            with open(self.get_full_path(self.CMDLINE_FILE_NAME)) as f:
                # cmdline args are separated by null characters and terminated
                # by a null character
                self._cmdline = f.read().replace('\x00', ' ')[:-1]

        return self._cmdline