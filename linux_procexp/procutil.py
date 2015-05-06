import os
import os.path
import re
import pwd
from collections import namedtuple
from enum import Enum

class ProcessStates(Enum):
    ZOMBIE = 'Z'
    RUNNING = 'R'
    SLEEPING = 'S'
    DISKSLEEP = 'D'
    STOPPED = 'T'
    DEAD = 'X'

class ProcInfoFileName:
    THREADS = 'task'
    FD = 'fd'
    EXE = 'exe'
    CMDLINE = 'cmdline'
    CWD = 'cwd'
    MEM_MAP = 'maps'
    STAT = 'stat'
    STATUS = 'status'

class Process(object):
    PROC_PATH = '/proc'

    ProcessOwner = namedtuple('ProcessOwner', ['uid', 'name'])
    FileDescriptor = namedtuple('FileDescriptor', ['id', 'type', 'name'])
    MappedRegion = namedtuple('MappedRegions', ['start', 'end', 'permissions',
                                                'offset', 'dev', 'inode', 'file_path'])

    def __init__(self, pid, parent=None):
        # initializer takes pid as an int since it's more intuitive for the class
        # consumer. however, this class mainly uses pid as a string for path joins
        self._pid = str(pid)

        # if the Process object is initialized with a parent, it is treated as a thread
        # and will have a different directory  representing its runtime objects
        self.pid_dir = os.path.join(self.PROC_PATH, str(parent.pid), ProcInfoFileName.THREADS, self._pid) \
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
        with open(self.get_full_path(ProcInfoFileName.STAT)) as f:
            return f.read().split(' ')[prop_idx]

    def pid(self):
        return int(self._pid)

    def name(self):
        # TODO: decide what to do with kernel support. for example, this is only
        # valid for kernel >= 2.2
        try:
            proc_name = os.readlink(os.path.join(self.pid_dir, ProcInfoFileName.EXE))
        except PermissionError:
            # most of the time exe has more stringent permissions so
            # grab the name from the cmdline instead
            proc_name = self.cmdline()[0]

        # as a last resort, grab name from stat
        if not proc_name:
            # name from stat has the form: '(name)'
            return self.get_stat_info(1)[1:-1]
        return os.path.basename(proc_name)

    def mem_usage(self):
        pass

    def priority(self):
        return int(self.get_stat_info(17))

    def nice(self):
        return int(self.get_stat_info(18))

    def parent_pid(self):
        if not self._parent:
            self._parent = self.get_stat_info(3)
        return int(self._parent)

    def owner(self):
        with open(self.get_full_path(ProcInfoFileName.STATUS)) as f:
            for count, line_info in enumerate(f):
                if count == 7:
                    # use the real uid
                    ruid = re.split('\s+', line_info)[1]
                    break
        return Process.ProcessOwner(ruid, pwd.getpwuid(int(ruid)).pw_name)

    def cpu_usage(self):
        pass

    def state(self):
        return ProcessStates(self.get_stat_info(2))

    def mem_map(self):
        # TODO: look into adding the libraries to the descriptors list
        with open(self.get_full_path(ProcInfoFileName.MEM_MAP)) as f:
            return [Process.MappedRegion(re.split('\s+', entry)) for entry in f]

    def cwd(self):
        return os.readlink(self.get_full_path(ProcInfoFileName.CWD))

    def descriptors(self, fspathonly=False):
        fd_dir = self.get_full_path(ProcInfoFileName.FD)
        descriptor_list = []
        for fd in os.listdir(fd_dir):
            fd_file_path = os.path.join(fd_dir, fd)
            fd_obj = os.readlink(fd_file_path)
            is_fs_file = '/' in fd_obj
            # if fspathonly is set, do not include the fds
            # that do not exist in the filesystem
            if fspathonly and not is_fs_file:
                continue

            fd_type = 'file'
            # a 'special' file such as socket or a pipe
            # e.g. pipe:[123664], socket:[7842325]
            if ':' in fd_obj and not is_fs_file:
                fd_type = fd_obj.split(':')[0]

            descriptor_list.append(Process.FileDescriptor(int(fd),fd_type, fd_obj))
        return descriptor_list

    def threads(self):
        return [Process(tid, self) for tid in os.listdir(os.path.join(
            self.pid_dir, ProcInfoFileName.THREADS))]

    def cmdline(self):
        if not self._cmdline:
            with open(self.get_full_path(ProcInfoFileName.CMDLINE)) as f:
                # cmdline args are separated by null characters and terminated
                # by a null character
                self._cmdline = f.read().split('\0')[:-1]
        return self._cmdline

class ProcUtil(object):
    @staticmethod
    def pids():
        return [entry for entry in os.listdir('/proc') if re.match('\d+', entry)]