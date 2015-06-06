from PyQt4.QtGui import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget
from PyQt4.QtCore import Qt

class FindHandleDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose)
        # QDialogs at least in GNOME do not have a close button by default
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle('Linux Process Explorer Search')
        if parent:
            self.setGeometry(0, 0, 900, 500)
            self.move((parent.width() - self.width()) / 2 + parent.x(),
                      (parent.height() - self.height()) / 2 + parent.y())

        lblSearch = QLabel('Descriptor or Lib substring:')
        txtSearch = QLineEdit()
        btnSearch = QPushButton('Search')
        btnCancel = QPushButton('Cancel')
        searchLayout = QHBoxLayout()
        searchLayout.addWidget(lblSearch)
        searchLayout.addWidget(txtSearch)
        searchLayout.addWidget(btnSearch)
        searchLayout.addWidget(btnCancel)
        tblResults = QTableWidget(0, 4)
        tblResults.setHorizontalHeaderLabels(('Process', 'PID', 'Type', 'Name'))
        tblResults.horizontalHeader().setStretchLastSection(True)
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(searchLayout)
        mainLayout.addWidget(tblResults)
        self.setLayout(mainLayout)

