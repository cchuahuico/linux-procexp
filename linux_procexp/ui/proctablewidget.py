import threading
from PyQt4.QtGui import QTreeView
from PyQt4.QtCore import QTimer, QThread, QObject, pyqtSignal
from ..proctablemodel import ProcTableModel
import time

class Worker(QObject):
    dataReady = pyqtSignal()

    def __init__(self, model):
        super().__init__()
        self.model = model

    def repeat(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(2000)

    def update(self):
        time.sleep(0.5)
        def updateNodes(node):

            if node.update():
                if not node.children:
                    return

                for child in node.children:
                    updateNodes(child)
        updateNodes(self.model)

        self.dataReady.emit()


class ProcTableWidget(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)
        self.model = ProcTableModel(self)
        self.setModel(self.model)
        self.expandAll()
        self.resizeColumnToContents(0)
        #self.timer = QTimer(self)
        #self.timer.timeout.connect(self.spawn)
        #self.timer.start(3000)

        self.thread = QThread(self)
        self.obj = Worker(self.model.root)
        self.obj.dataReady.connect(self.updateAll)
        self.thread.started.connect(self.obj.repeat)
        self.obj.moveToThread(self.thread)
        self.thread.start()


    def updateAll(self):
        self.reset()
        #self.model.beginResetModel()
        #self.model().update()
        #self.model.endResetModel()
        #self.model().reset()
        self.expandAll()



