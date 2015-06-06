from PyQt4.QtGui import QTreeView
from PyQt4.QtCore import QThread, pyqtSlot, Qt
from ..proctablemodel import ProcTableModelRefresher

class ProcTableWidget(QTreeView):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectRows)

        # setting uniform row heights allows optimization of the view
        self.setUniformRowHeights(True)
        self.model = model
        self.setModel(self.model)
        self.expandAll()

        # resize the column to fit all process names
        self.resizeColumnToContents(0)

        # keeps track of the previous sort order shown by the sort indicator.
        # this allows for a third state for the sort order: no sort
        self.prevSortOrder = None
        self.header().setClickable(True)
        self.header().sectionClicked.connect(self.setSortIndicator)

        # this worker thread grabs the latest process properties
        # so the GUI doesn't lag when it needs to update process data
        self.refreshThread = QThread(self)
        self.modelRefresher = ProcTableModelRefresher(self.model)
        self.modelRefresher.moveToThread(self.refreshThread)
        self.modelRefresher.modelRefresh.connect(self.model.update)
        self.refreshThread.started.connect(self.modelRefresher.startRefreshTimer)
        self.refreshThread.start()

    @pyqtSlot(int)
    def setSortIndicator(self, columnIdx):
        if self.isSortingEnabled():
            # the 'no sort' state is only accessible by changing
            # the sort order of the process name column
            if columnIdx == 0 and self.prevSortOrder == Qt.DescendingOrder:
                self.header().setSortIndicatorShown(False)
                self.setSortingEnabled(False)
                self.model.removeSort()
                # setClickable() has to be set to True again after
                # calling setSortingEnabled(False) otherwise, the headers
                # cannot be clicked and the columns cannot be sorted
                self.header().setClickable(True)
        else:
            self.header().setSortIndicatorShown(True)
            # force the sort indicator to start with ascendingorder
            # so the cycling of sort order is predictable otherwise,
            # the sort order can start with DescendingOrder and vice versa
            # which makes it hard to detect when it's time to set the
            # 'no sort' state
            self.header().setSortIndicator(columnIdx, Qt.AscendingOrder)
            self.setSortingEnabled(True)

        self.prevSortOrder = self.header().sortIndicatorOrder()


