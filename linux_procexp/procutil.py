import os
import os.path
import re
import pwd
from collections import namedtuple
from enum import Enum

class ProcessState(Enum):
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

    Owner = namedtuple('Owner', ['uid', 'name'])
    FileDescriptor = namedtuple('FileDescriptor', ['id', 'type', 'name'])
    MappedRegion = namedtuple('MappedRegion', ['start', 'end', 'permissions',
                                                'offset', 'dev', 'inode', 'file_path'])
    VirtualMemory = namedtuple('VirtualMemory', ['vsize', 'rss'])

    def __init__(self, pid, parent=None):
        # initializer takes pid as an int since it's more intuitive for the class
        # consumer. however, this class mainly uses pid as a string for path joins
        self._pid = str(pid)

        # if the Process object is initialized with a parent, it is treated as a thread
        # and will have a different directory  representing its runtime objects
        self.pid_dir = os.path.join(self.PROC_PATH, str(parent.pid()), ProcInfoFileName.THREADS, self._pid) \
            if parent else os.path.join(self.PROC_PATH, self._pid)

        if not os.path.exists(self.pid_dir):
            raise ValueError('{} does not exist'.format(self.pid_dir))

        self._parent = parent

        # both these variables are used to calculate the cpu percent use
        # of this process. remembering the old values is needed because we
        # want this to behave more like top rather than ps in that the percentage
        # is computed based on time (e.g. cpu % for last second)
        self._last_total_work = 0
        self._last_proc_work = 0

        # all the instance variables defined from here are computed only when needed
        # because either the information is not included in the default view or they
        # are likely to change during the process' execution
        self._cmdline = ''

    def get_full_path(self, dir_name):
        return os.path.join(self.pid_dir, dir_name)

    def get_stat_info(self, prop_idx):
        with open(self.get_full_path(ProcInfoFileName.STAT)) as f:
            return f.read().split(' ')[prop_idx]

    def pid(self):
        return int(self._pid)

    def name(self):
        # TODO: decide what to do with kernel support. for example, this is only
        # valid for kernel >= 2.2
        try:
            proc_name = os.path.basename(os.readlink(os.path.join(
                self.pid_dir, ProcInfoFileName.EXE)))
        except PermissionError:
            # most of the time exe has more stringent permissions so
            # grab the name from the cmdline instead
            cmdline = self.cmdline()
            if cmdline:
                proc_name = cmdline[0]
                if os.path.exists(proc_name):
                    proc_name = os.path.basename(proc_name)
            else:
                proc_name = self.get_stat_info(1).strip("()")
        return proc_name

    def virtual_memory(self):
        return Process.VirtualMemory(int(self.get_stat_info(22)) / 1024,
                                     int(self.get_stat_info(23)) / 1024)

    def memory_percent(self):
        return self.virtual_memory().rss / ProcUtil.memory_info().total * 100

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
                    ruid = line_info.split()[1]
                    break
        return Process.Owner(ruid, pwd.getpwuid(int(ruid)).pw_name)

    def cpu_percent(self):
        with open(os.path.join(self.PROC_PATH, ProcInfoFileName.STAT)) as f:
            # add the aggregated (all cpus) jiffies stored in the first line
            total_work = sum(int(val) for val in f.readline().split()[1:])

        proc_work = int(self.get_stat_info(13)) + int(self.get_stat_info(14))
        try:
            cpu_percent = (proc_work - self._last_proc_work) / \
                          (total_work - self._last_total_work) * 100
        except ZeroDivisionError:
            cpu_percent = 0

        self._last_total_work = total_work
        self._last_proc_work = proc_work
        return cpu_percent

    def state(self):
        return ProcessState(self.get_stat_info(2))

    def memory_maps(self, resolvedev=True):
        with open(self.get_full_path(ProcInfoFileName.MEM_MAP)) as f:
            maps = []
            for line in f:
                map_toks = line.split()
                start, end = map_toks[0].split('-')
                if resolvedev:
                    major, minor = map_toks[3].split(':')
                    try:
                        # TODO major minor here do not correspond to /proc/partitions
                        dev_name = ProcUtil.dev_name(int(major), int(minor))
                    except DeviceNameNotFound:
                        dev_name = ''
                else:
                    dev_name = map_toks[3]
                maps.append(Process.MappedRegion(start, end, map_toks[1], map_toks[2],
                                                 dev_name, map_toks[4], map_toks[5]))
        return maps

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
                line = f.read().rstrip('\0')
                if line.count('\0') == 0:
                    # contrary to man, the commandline arguments are sometimes not
                    # separated by a null byte (e.g. some chromium processes)
                    self._cmdline = line.split()
                else:
                    self._cmdline = line.split('\0')

        return self._cmdline

class DeviceNameNotFound(Exception):
    pass

class ProcUtil(object):
    MemInfo = namedtuple('MemInfo', ['total', 'free', 'available', 'buffers', 'cached',
                                     'swapcached', 'active', 'inactive'])

    @staticmethod
    def pids():
        return [int(entry) for entry in os.listdir('/proc') if re.match('\d+', entry)]

    @staticmethod
    def dev_name(major, minor):
        with open('/proc/partitions') as f:
            part_table = {}
            # first line are headers, second line is a blank line
            next(f); next(f)
            for dev_entry in f:
                fields = dev_entry.split()
            part_table[(fields[0], fields[1])] = fields[3]

        try:
            return part_table[(major, minor)]
        except KeyError:
            raise DeviceNameNotFound('No device name mapping for {}:{}'.format(major, minor))

    @staticmethod
    def memory_info():
        with open('/proc/meminfo') as f:
            mem_data = []
            for i, entry in enumerate(f):
                # by default mem info is in KB, return everything in bytes
                mem_data.append(int(entry.split()[1]) / 1024)
                # not interested in other mem info
                if i == 7:
                    break
        return ProcUtil.MemInfo(*mem_data)
