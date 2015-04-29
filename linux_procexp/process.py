# -*- coding: utf-8 -*-

import os
import os.path
from collections import namedtuple

ProcessOwner = namedtuple('ProcessOwner', ['uid', 'gid', 'name'])
FileDescriptor = namedtuple('FileDescriptor', ['id', 'type', 'name'])

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

    def __init__(self, pid, parent=None):
        # if the Process object is initialized with a parent, it is treated as a thread
        # and will have a different directory  representing its runtime objects
        self.pid_dir = os.path.join(self.PROC_PATH, parent.pid, self.THREADS_DIR_NAME, pid) \
            if parent else os.path.join(self.PROC_PATH, pid)

        if not os.path.exists(self.pid_dir):
            raise ValueError('Process id: {} does not exist in {}'.format(
                self.pid, self.PROC_PATH))

        self.pid = pid
        self._parent = parent

        # TODO: decide what to do with kernel support. for example, this is only
        # valid for kernel >= 2.2
        self.name = os.readlink(os.path.join(self.pid_dir, self.EXE_FILE_NAME))

        # all the instance variables defined from here are computed only when needed
        # because either the information is not included in the default view or they
        # are likely to change during the process' execution
        self._cmdline = ''
        self._state = ''
        self._cwd = ''

    def get_full_path(self, dir_name):
        return os.path.join(self.pid_dir, dir_name)

    @property
    def parent(self):
        if self._parent:
            return self._parent
        # else get parent and return it

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
    def state(self):
        pass

    @property
    def cwd(self):
        self._cwd = os.readlink(self.get_full_path(self.CWD_FILE_NAME))
        return self._cwd

    @property
    def descriptors(self):
        fd_path = self.get_full_path(self.FD_DIR_NAME)
        # TODO: use python-magic to implement the type field for descriptors
        return (FileDescriptor(fid, 'UNIMPLEMENTED', os.readlink(os.path.join(fd_path, fid)))
            for fid in os.listdir(fd_path))

    @property
    def threads(self):
        return (Process(tid, self) for tid in os.listdir(os.path.join(
            self.pid_dir, self.THREADS_DIR_NAME)))

    @property
    def cmdline(self):
        if not self._cmdline:
            with open(self.get_full_path(self.CMDLINE_FILE_NAME)) as f:
                # read and remove the null character '\x00' at the end
                self._cmdline = f.read()[:-1]

                # according to: http://linux.die.net/man/5/proc
                # if cmdline is empty then this process is a zombie
                if not self._cmdline:
                    self._state = ProcessStates.ZOMBIE

        return self._cmdline