import re
import os
import os.path
import time
import threading
from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex
from .procutil import Process, ProcUtil

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.pid = pid
        #self.lock = threading.Lock()

        if pid == 0:
            # The node with pid = 0 is a dummy node used as the root node
            # and the parent of both init (pid = 1) and kthreadd (pid = 2)
            # This is needed because in Linux (at least) the kernel thread
            # daemon does not have init as its ppid
            self.data = None
        else:
            self.data = Process(pid)
            self.properties = []
            #self.grabData()
            self.update()

        self.children = []
        self.parent = parent


    def __len__(self):
        return len(self.children)

    def insertChild(self, child):
        assert child not in self.children
        self.children.append(child)

    def rowOfChild(self, childNode):
        for i, child in enumerate(self.children):
            if child == childNode:
                return i
        return -1

    def removeChild(self, childNode):
        self.children.remove(childNode)

    def childAtRow(self, row):
        return self.children[row]

    def grabData(self):
        if self.pid == 0:
            self.newprops = []
            return
        self.newprops = self.data.get_props()

    def update(self):
        if self.pid == 0:
            return True
        try:
            #with self.lock:
            self.properties = self.data.get_props()

            #self.properties = [ 1,2,3,4,5,6,7,8]
            return True
        # this process no longer exists
        except FileNotFoundError:
            self.parent.removeChild(self)
            self.parent = None
            return False

    def fields(self, colIdx):
        return self.properties[colIdx]

class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Process Name', 'CPU %', 'Mem %', 'PID',
                        'RSS', 'User', 'Nice', 'Priority']
        self.initializeProcTree()

    def update(self):
        def updateNodes(node):
            if node.update():
                if not node.children:
                    return

                for child in node.children:
                    updateNodes(child)
        updateNodes(self.root)

    def initializeProcTree(self):
        # add a dummy root as this is not included in the treeview
        self.root = ProcessNode(0)
        procTable = {0: self.root}

        for pid in ProcUtil.pids():
            if pid in procTable:
                node = procTable[pid]
            else:
                node = ProcessNode(pid)
                procTable[pid] = node
            ppid = node.data.parent_pid()
            if ppid not in procTable:
                procTable[ppid] = ProcessNode(ppid)
            procTable[ppid].insertChild(node)
            node.parent = procTable[ppid]

    def index(self, row, col, parentMIdx):
        node = self.nodeFromIndex(parentMIdx)
        return self.createIndex(row, col, node.childAtRow(row))

    def parent(self, childMIdx):
        childNode = self.nodeFromIndex(childMIdx)
        parent = childNode.parent
        if not parent:
            return QModelIndex()
        row = parent.rowOfChild(childNode)
        return self.createIndex(row, 0, parent)

    def rowCount(self, parentMIdx):
        return len(self.nodeFromIndex(parentMIdx))

    def columnCount(self, parentMIdx):
        return len(self.headers)

    def data(self, mIdx, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            node = self.nodeFromIndex(mIdx)
            return node.fields(mIdx.column())
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def nodeFromIndex(self, index):
        return index.internalPointer() if index.isValid() else self.root