from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QObject, QTimer, pyqtSignal, pyqtSlot
from .procutil import Process, ProcUtil

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.pid = pid
        self.children = []
        self.parent = parent
        self.tempProperties = []

        if pid == 0:
            # The node with pid = 0 is a dummy node used as the root node
            # and the parent of both init (pid = 1) and kthreadd (pid = 2)
            # This is needed because in Linux (at least) the kernel thread
            # daemon does not have init as its ppid
            self.data = None
        else:
            self.data = Process(pid)
            self.properties = []
            self.retrieveProperties()
            self.assignProperties()

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

    def retrieveProperties(self):
        proc = self.data
        try:
            self.tempProperties = [
                proc.name(),
                round(proc.cpu_percent(), 2) or "",
                round(proc.memory_percent(), 2) or "",
                proc.pid(),
                "{}M".format(proc.virtual_memory().rss // 1048576),
                proc.owner().name,
                proc.nice(),
                proc.priority()
            ]
        except FileNotFoundError:
            self.tempProperties = None
            raise

    # update() and fields() below have to be locked because
    # update() is called from a worker thread whereas fields()
    # is called by the main GUI thread. This is done because
    # the update can be slow and causes the GUI to lag
    def assignProperties(self):
        self.properties = self.tempProperties
        return self.properties is not None

    def fields(self, colIdx):
            return self.properties[colIdx]


class ProcTableModelRefresher(QObject):
    modelRefresh = pyqtSignal(list, list)

    def __init__(self, model, refreshInterval=2000, parent=None):
        super().__init__(parent)
        self.model = model
        self.procTable = model.procTable
        self.root = model.root
        self.refreshInterval = refreshInterval
        self.timer = QTimer(self)

    @property
    def interval(self):
        return self.refreshInterval

    @interval.setter
    def interval(self, interval):
        self.timer.start(interval)
        self.refreshInterval = interval

    @pyqtSlot()
    def startRefreshTimer(self):
        self.timer.timeout.connect(self.refresh)
        self.timer.start(self.refreshInterval)

    @pyqtSlot()
    def refresh(self):
        newProcNodes = []
        for pid in ProcUtil.pids():
            if pid not in self.procTable:
                self.procTable[pid] = Process(pid)
                newProcNodes.append(pid)

        pidsToRemove = []
        for pid, node in list(self.procTable.items()):
            if pid == 0:
                continue
            try:
                node.retrieveProperties()
            except FileNotFoundError:
                del self.procTable[node.pid]
                pidsToRemove.append(node.pid)

        self.modelRefresh.emit(newProcNodes, pidsToRemove)


class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Process Name', 'CPU %', 'Mem %', 'PID',
                        'RSS', 'User', 'Nice', 'Priority']

        # add a dummy root as this is not included in the treeview
        self.root = ProcessNode(0)
        self.procTable = {0: self.root}
        self.initializeProcTree()

    def initializeProcTree(self):
        print("InitializeProcTree")
        for pid in ProcUtil.pids():
            if pid in self.procTable:
                node = self.procTable[pid]
            else:
                node = ProcessNode(pid)
                self.procTable[pid] = node
            ppid = node.data.parent_pid()
            if ppid not in self.procTable:
                self.procTable[ppid] = ProcessNode(ppid)
            self.procTable[ppid].insertChild(node)
            node.parent = self.procTable[ppid]

    def updateHierarchy(self, newProcNodes):
        for node in newProcNodes:
            ppid = node.data.parent_pid
            node.parent = self.procTable[ppid]
            self.procTable[ppid].insertChild(node)

            # notify the view the new nodes have been added to the hierarchy
            # so that it can display them
            parentNode = node.parent
            grandParent = parentNode.parent
            parentMIdx = self.createIndex(grandParent.rowOfChild(parentNode), 0, grandParent)
            childIdx = parentNode.rowOfChild(node)
            self.rowsInserted.emit(parentMIdx, childIdx, childIdx)

    def updateNodeProperties(self, root):
        if root.assignProperties():
            for childNode in root.children:
                self.updateNodeProperties(childNode)
        else:
            parentNode = root.parent
            grandParent = parentNode.parent
            parentMIdx = self.createIndex(grandParent.rowOfChild(parentNode), 0, grandParent)
            childIdx = parentNode.rowOfChild(root)
            parentNode.removeChild(root)
            self.model.rowsRemoved.emit(parentMIdx, childIdx, childIdx)

    @pyqtSlot(list, list)
    def update(self, newProcNodes, pidsToRemove):
        self.updateHierarchy(newProcNodes)
        for child in self.root.children:
            self.updateNodeProperties(child)
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def index(self, row, col, parentMIdx):
        print("index({}, {}, parentMIdx={})".format(row, col, self.nodeFromIndex(parentMIdx).pid))
        node = self.nodeFromIndex(parentMIdx)
        return self.createIndex(row, col, node.childAtRow(row))

    def parent(self, childMIdx):
        print("parent(childMIdx={})".format(self.nodeFromIndex(childMIdx).pid))

        childNode = self.nodeFromIndex(childMIdx)
        parent = childNode.parent
        if not parent:
            return QModelIndex()
        row = parent.rowOfChild(childNode)
        return self.createIndex(row, 0, parent)

    def rowCount(self, parentMIdx):
        print("rowCount(parentMIdx={})".format(self.nodeFromIndex(parentMIdx).pid))
        return len(self.nodeFromIndex(parentMIdx))

    def columnCount(self, parentMIdx):
        print("columnCount(parentMIdx={})".format(self.nodeFromIndex(parentMIdx).pid))

        return len(self.headers)

    def data(self, mIdx, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            print("data(mIdx={})".format(self.nodeFromIndex(mIdx).pid))
            node = self.nodeFromIndex(mIdx)
            return node.fields(mIdx.column())
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def nodeFromIndex(self, index):
        return index.internalPointer() if index.isValid() else self.root