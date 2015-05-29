from PyQt4.QtGui import QTreeView
from PyQt4.QtCore import QThread, pyqtSlot, Qt
from ..proctablemodel import ProcTableModel, ProcTableModelRefresher

class ProcTableWidget(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTreeView.SelectRows)

        # setting uniform row heights allows optimization of the view
        self.setUniformRowHeights(True)
        self.model = ProcTableModel(self)
        self.setModel(self.model)
        self.expandAll()

        # resize the column to fit all process names
        self.resizeColumnToContents(0)

        # keeps track of the previous sort order shown by the sort indicator.
        # this allows for a third state for the sort order: no sort
        self.prevSortOrder = None
        self.header().setClickable(True)
        self.header().sectionClicked.connect(self.setSortIndicator)

        # ideally this should be set dynamically in setSortIndicator()
        # i.e. its state should be based on the status indicator
        # however, the the status indicator in the widget break when
        # setSortingEnabled() is set to False. can't leave it to on off
        # state either because the AbstractItemModel's sort() doesn't
        # get
        self.setSortingEnabled(True)

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
        if self.header().isSortIndicatorShown():
            # the 'no sort' state is only accessible by changing
            # the sort order of the process name column
            if columnIdx == 0 and self.prevSortOrder == Qt.DescendingOrder:
                self.header().setSortIndicatorShown(False)
        else:
            self.header().setSortIndicatorShown(True)
            # force the sort indicator to start with ascendingorder
            # so the cycling of sort order is predictable otherwise,
            # the sort order can start with DescendingOrder and vice versa
            # which makes it hard to detect when it's time to set the
            # 'no sort' state
            self.header().setSortIndicator(columnIdx, Qt.AscendingOrder)

        self.prevSortOrder = self.header().sortIndicatorOrder()


