# -*- coding: utf-8 -*-

import re
import os
import os.path
from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QVariant
from .process import Process

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.data = Process(pid)
        self.children = []
        self.parent = parent
        self.fields = [self.data.name, self.data.pid, self.data.owner.name]

    def __len__(self):
        return len(self.children)

    def insertChild(self, child):
        self.children.append(child)

    def rowOfChild(self, childNode):
        for i, child in enumerate(self.children):
            if child == childNode:
                return i
        return -1

    def childAtRow(self, row):
        return self.children[row]

    def fields(self, colIdx):
        return self.fields[colIdx]

class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Name', 'PID', 'Owner']
        self.initializeProcTree()

    def initializeProcTree(self):
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
                ppid = node.data.parent_pid
                if ppid != 0:
                    if ppid not in procTable:
                        procTable[ppid] = ProcessNode(ppid)
                    procTable[ppid].insertChild(node)
                    node.parent = procTable[ppid]

    def index(self, row, col, parentMIdx):
        node = self.nodeFromIndex(parentMIdx)
        return self.createIndex(row, col, node.childAtRow(row))

    def parent(self, childMIdx):
        node = self.nodeFromIndex(childMIdx)
        row = node.rowOfChild(node)
        parent = node.parent
        if not parent:
            return QModelIndex()
        return self.createIndex(row, 0, parent)

    def rowCount(self, parentMIdx):
        return len(self.nodeFromIndex(parentMIdx))

    def columnCount(self, parentMIdx):
        return len(self.headers)

    def data(self, mIdx, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            node = self.nodeFromIndex(mIdx)
            return node.fields[mIdx.column()]
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def nodeFromIndex(self, index):
        return index.internalPointer() if index.isValid() else self.root