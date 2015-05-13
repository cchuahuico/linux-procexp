import threading
from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QObject, QTimer, pyqtSignal, pyqtSlot
from .procutil import Process, ProcUtil

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.pid = pid
        self.children = []
        self.parent = parent
        self._lock = threading.Lock()

        if pid == 0:
            # The node with pid = 0 is a dummy node used as the root node
            # and the parent of both init (pid = 1) and kthreadd (pid = 2)
            # This is needed because in Linux (at least) the kernel thread
            # daemon does not have init as its ppid
            self.data = None
        else:
            self.data = Process(pid)
            self.properties = []
            self.update()

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

    # update() and fields() below have to be locked because
    # update() is called from a worker thread whereas fields()
    # is called by the main GUI thread. This is done because
    # the update can be slow and causes the GUI to lag
    def update(self):
        with self._lock:
            proc = self.data
            self.properties = [
                proc.name(),
                round(proc.cpu_percent(), 2) or "",
                round(proc.memory_percent(), 2) or "",
                proc.pid(),
                "{}M".format(proc.virtual_memory().rss // 1048576),
                proc.owner().name,
                proc.nice(),
                proc.priority()
            ]

    def fields(self, colIdx):
        with self._lock:
            return self.properties[colIdx]


class ProcTableModelRefresher(QObject):
    modelRefresh = pyqtSignal()

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
        def updateNodes(node):
            try:
                node.update()
                for child in node.children:
                    updateNodes(child)
            # process no longer exists
            except FileNotFoundError:
                parent = node.parent
                grandParent = parent.parent
                parentMIdx = self.model.createIndex(grandParent.rowOfChild(parent), 0, grandParent)
                childIdx = parent.rowOfChild(node)
                parent.removeChild(node)
                self.model.rowsRemoved.emit(parentMIdx, childIdx, childIdx)
                #for child in parent.children:
                    #del self.procTable[child.pid]

        # don't update the dummy root node since it doesn't
        # have a process associated with it
        for child in self.root.children:
            updateNodes(child)

        # tell the view that the underlying data has been updated
        # TODO: should this be done on the view?
        self.model.dataChanged.emit(QModelIndex(), QModelIndex())

        # TODO: unused for now
        self.modelRefresh.emit()


class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Process Name', 'CPU %', 'Mem %', 'PID',
                        'RSS', 'User', 'Nice', 'Priority']

        self.root = None
        self.procTable = {}
        self.initializeProcTree()

    def initializeProcTree(self):
        # add a dummy root as this is not included in the treeview
        self.root = ProcessNode(0)
        self.procTable = {0: self.root}

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