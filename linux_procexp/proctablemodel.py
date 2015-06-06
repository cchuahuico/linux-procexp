import logging
import re
from PyQt4.QtCore import QAbstractItemModel, Qt, QModelIndex, QObject, \
     QTimer, pyqtSignal, pyqtSlot
from .procutil import Process, ProcUtil

LOG_FILENAME = 'linux-procexp.log'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG, filemode='w')

class ProcessNode(object):
    def __init__(self, pid, parent=None):
        self.pid = pid
        self.children = []
        self.parent = parent
        self.tempProperties = []
        self.properties = []

        if pid == 0:
            # The node with pid = 0 is a dummy node used as the root node
            # and the parent of both init (pid = 1) and kthreadd (pid = 2)
            # This is needed because in Linux (at least) the kernel thread
            # daemon does not have init as its ppid
            self.data = None
        else:
            self.data = Process(pid)
            self.retrieveProperties()
            self.assignProperties()

    def __len__(self):
        return len(self.children)

    def insertChild(self, child):
        self.children.append(child)

    def rowOfChild(self, childNode):
        for i, child in enumerate(self.children):
            if child == childNode:
                return i
        raise ValueError('Node({0}) does not contain child({0})'.format(self.pid))

    def removeChild(self, childNode):
        self.children.remove(childNode)

    def childAtRow(self, row):
        return self.children[row]

    def mappedLibraries(self):
        return {mapped.name for mapped in self.data.memory_maps(resolvedev=False)
                if re.match('.*\.so.*', mapped.name)}

    def descriptors(self):
        return self.data.descriptors()

    def retrieveProperties(self):
        proc = self.data
        try:
            self.tempProperties = [
                proc.name(),
                round(proc.cpu_percent(), 2),
                round(proc.memory_percent(), 2),
                proc.pid(),
                "{}M".format(proc.virtual_memory().rss // 1048576),
                proc.owner().name,
                proc.nice(),
                proc.priority()
            ]
        except FileNotFoundError:
            self.tempProperties = []
            raise

    def assignProperties(self):
        self.properties = self.tempProperties
        return len(self.properties) > 0

    def fields(self, colIdx):
            return self.properties[colIdx]


class ProcTableModelRefresher(QObject):
    modelRefresh = pyqtSignal(list)

    def __init__(self, model, refreshInterval=2000, parent=None):
        super().__init__(parent)
        self.procTable = model.procTable
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
        for pid, node in list(self.procTable.items()):
            try:
                node.retrieveProperties()
            except FileNotFoundError:
                del self.procTable[pid]

        newProcNodes = []
        for pid in ProcUtil.pids():
            if pid not in self.procTable:
                newNode = ProcessNode(pid)
                self.procTable[pid] = newNode
                newProcNodes.append(newNode)

        self.modelRefresh.emit(newProcNodes)


class ProcTableModel(QAbstractItemModel):
    def __init__(self, parent=None):
        super().__init__(parent)

        # headers or columns available in the treeview
        self.headers = ['Process Name', 'CPU %', 'Mem %', 'PID',
                        'RSS', 'User', 'Nice', 'Priority']

        # the model is in a sorted state when the widget
        # has setSortingEnabled() set to true
        self.sorted = False

        # only set when sorted == True. count starts from 0
        self.sortedColIdx = -1

        # only set when sorted == True. Either Qt.AscendingOrder
        # or Qt.DescendingOrder
        self.sortOrder = None

        # add a dummy root node. this root node is not shown in the
        # view (only its children) but it is needed by the view to
        # show the hierarchy. also, it simplifies sorting of processes
        self.root = ProcessNode(0)

        # this is a map of pid -> ProcessNode NOT including the dummy
        # root node. the dummy node is not included because adding
        # that in will require if pid == 0 checks when processing nodes
        # e.g. when updating all nodes
        self.procTable = {}
        self.setProcHierarchy(ProcUtil.pids())

    def setProcHierarchy(self, pids):
        logging.debug("setProcHierarchy")
        for pid in pids:
            if pid in self.procTable:
                node = self.procTable[pid]
            else:
                node = ProcessNode(pid)
                self.procTable[pid] = node
            ppid = node.data.parent_pid()
            if ppid not in self.procTable and ppid != 0:
                self.procTable[ppid] = ProcessNode(ppid)
            if ppid == 0:
                self.root.insertChild(node)
                node.parent = self.root
            else:
                self.procTable[ppid].insertChild(node)
                node.parent = self.procTable[ppid]

    def parentModelIndex(self, node):
        parentNode = node.parent
        grandParent = parentNode.parent
        return self.createIndex(grandParent.rowOfChild(parentNode), 0, grandParent)

    def addNodesToHierarchy(self, newProcNodes):
        for node in newProcNodes:
            node.parent = self.procTable[node.data.parent_pid()]
            parentMIdx = self.parentModelIndex(node)
            insertionRow = self.rowCount(parentMIdx)
            self.beginInsertRows(parentMIdx, insertionRow , insertionRow)
            node.parent.insertChild(node)
            self.endInsertRows()

    def updateNodeProperties(self, root):
        if root.assignProperties():
            for childNode in root.children:
                self.updateNodeProperties(childNode)
        else:
            childIdx = root.parent.rowOfChild(root)
            self.beginRemoveRows(self.parentModelIndex(root), childIdx, childIdx)
            root.parent.removeChild(root)
            self.endRemoveRows()

    @pyqtSlot(list)
    def update(self, newProcNodes):
        self.layoutAboutToBeChanged.emit()
        if newProcNodes:
            self.addNodesToHierarchy(newProcNodes)

        for child in self.root.children:
            self.updateNodeProperties(child)

        if self.sorted:
            self.root.children.sort(key=lambda node: node.properties[self.sortedColIdx],
                                    reverse=self.sortOrder == Qt.AscendingOrder)
        self.layoutChanged.emit()
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def removeSort(self):
        self.sorted = False
        self.sortOrder = None
        self.sortedColIdx = -1
        self.layoutAboutToBeChanged.emit()
        self.root.children = []
        self.setProcHierarchy(self.procTable.keys())
        self.layoutChanged.emit()

    def sort(self, columnIdx, order):
        self.layoutAboutToBeChanged.emit()
        if not self.sorted:
            for pid, node in self.procTable.items():
                node.parent = self.root
                node.children = []
                if node not in self.root.children:
                    self.root.insertChild(node)
            self.sorted = True

        self.root.children.sort(key=lambda x: x.properties[columnIdx],
                                reverse=order == Qt.AscendingOrder)
        self.sortOrder = order
        self.sortedColIdx = columnIdx
        self.layoutChanged.emit()

    def getProcDescriptors(self, procMIdx):
        procNode = procMIdx.internalPointer()
        return procNode.descriptors()

    def getProcLibraries(self, procMidx):
        procNode = procMidx.internalPointer()
        return procNode.mappedLibraries()

    def index(self, row, col, parentMIdx):
        logging.debug("index({}, {}, parentMIdx={})".format(row, col, self.nodeFromIndex(parentMIdx).pid))
        node = self.nodeFromIndex(parentMIdx)
        return self.createIndex(row, col, node.childAtRow(row))

    def parent(self, childMIdx):
        logging.debug("parent(childMIdx={})".format(self.nodeFromIndex(childMIdx).pid))
        childNode = self.nodeFromIndex(childMIdx)
        parent = childNode.parent
        if not parent:
            return QModelIndex()
        row = parent.rowOfChild(childNode)
        return self.createIndex(row, 0, parent)

    def rowCount(self, parentMIdx):
        logging.debug("rowCount(parentMIdx={})".format(self.nodeFromIndex(parentMIdx).pid))
        return len(self.nodeFromIndex(parentMIdx))

    def columnCount(self, parentMIdx):
        logging.debug("columnCount(parentMIdx={})".format(self.nodeFromIndex(parentMIdx).pid))
        return len(self.headers)

    def data(self, mIdx, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            logging.debug("data(mIdx={})".format(self.nodeFromIndex(mIdx).pid))
            node = self.nodeFromIndex(mIdx)
            # show nothing for properties that are '0'
            return node.fields(mIdx.column()) or ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def nodeFromIndex(self, index):
        return index.internalPointer() if index.isValid() else self.root