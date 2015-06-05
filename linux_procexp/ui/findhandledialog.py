from PyQt4.QtGui import QDialog
from PyQt4.QtCore import Qt

class FindHandleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose)
