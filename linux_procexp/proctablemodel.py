import re
import os
import os.path
from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex
from .process import Process

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.data = Process(pid)
        self.children = []
        self.parent = parent

    def __len__(self):
        return len(self.children)

    def insertChild(self, child):
        self.children.append(child)


class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Name', 'PID', 'Owner']
        self._initializeProcTree()

    def _initializeProcTree(self):
        pids = []
        for path in os.listdir('/proc'):
            base = os.path.basename(path)
            if re.match('\d+', base) and base != '1':
                pids.append(int(base))

        # the root is always the process whose pid is 1
        self.root = ProcessNode(1)
        procTable = {1: self.root}

        for pid in pids:
            if pid not in procTable:
                node = ProcessNode(pid)
                procTable[pid] = node
                if node.parent.pid in procTable:
                    procTable[node.parent.pid].insertChild(node)
                else:
                    procTable[node.parent.pid] = ProcessNode(node.parent.pid)
                node.parent = procTable[node.parent.pid]

    def index(self, row, col, parentMIdx):
        pass

    def parent(self, childMIdx):

        return self.createIndex(row, 0, parent)

    def rowCount(self, parentMIdx):
        pass

    def columnCount(self, parentMIdx):
        pass

    def data(self, mIdx, role=Qt.DisplayRole):
        pass

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        return self.headers[section]

    def flags(self, mIdx):
        # TODO: according to doc this should be overriden but might not be needed
        super().flags(mIdx)