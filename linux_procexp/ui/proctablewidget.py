from PyQt4.QtGui import QTreeView
from PyQt4.QtCore import QThread
from ..proctablemodel import ProcTableModel, ProcTableModelRefresher

class ProcTableWidget(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setUniformRowHeights(True)
        self.model = ProcTableModel(self)
        self.setModel(self.model)
        self.expandAll()
        self.resizeColumnToContents(0)

        self.refreshThread = QThread(self)
        self.modelRefresher = ProcTableModelRefresher(self.model)
        self.modelRefresher.moveToThread(self.refreshThread)
        self.refreshThread.started.connect(self.modelRefresher.startRefreshTimer)
        self.refreshThread.start()