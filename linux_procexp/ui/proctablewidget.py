from PyQt4.QtGui import QTreeView
from ..proctablemodel import ProcTableModel

class ProcTableWidget(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setUniformRowHeights(True)
        self.setModel(ProcTableModel())
