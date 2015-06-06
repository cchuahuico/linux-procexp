from PyQt4.QtGui import QDialog, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton, \
     QTableWidget, QTableWidgetItem
from PyQt4.QtCore import Qt, pyqtSlot

class FindHandleDialog(QDialog):
    def __init__(self, model, parent):
        super().__init__(parent)
        self.model = model
        self.setModal(False)
        self.setAttribute(Qt.WA_DeleteOnClose)
        # QDialogs at least in GNOME do not have a close button by default
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle('Linux Process Explorer Search')
        self.setGeometry(0, 0, 900, 500)
        self.move((parent.width() - self.width()) / 2 + parent.x(),
                  (parent.height() - self.height()) / 2 + parent.y())

        lblSearch = QLabel('Descriptor or Lib substring:')
        self.txtSearch = QLineEdit()
        btnSearch = QPushButton('&Search')
        btnSearch.clicked.connect(self.onBtnSearchClicked)
        btnCancel = QPushButton('&Cancel')
        searchLayout = QHBoxLayout()
        searchLayout.addWidget(lblSearch)
        searchLayout.addWidget(self.txtSearch)
        searchLayout.addWidget(btnSearch)
        searchLayout.addWidget(btnCancel)
        self.tblResults = QTableWidget(0, 4)
        self.tblResults.setHorizontalHeaderLabels(('Process', 'PID', 'Type', 'Name'))
        self.tblResults.horizontalHeader().setStretchLastSection(True)
        self.tblResults.verticalHeader().setVisible(False)
        self.tblResults.setShowGrid(False)
        self.tblResults.setSelectionBehavior(QTableWidget.SelectRows)
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(searchLayout)
        mainLayout.addWidget(self.tblResults)
        self.setLayout(mainLayout)

    @pyqtSlot(bool)
    def onBtnSearchClicked(self, checked=False):
        handleSubstr = self.txtSearch.text()
        if handleSubstr:
            results = self.model.findHandlesBySubstr(handleSubstr)
            self.tblResults.setRowCount(len(results))
            for row, res in enumerate(results):
                for col, prop in enumerate(res):
                    self.tblResults.setItem(row, col, QTableWidgetItem(str(prop)))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Enter and self.txtSearch.hasFocus():
            self.onBtnSearchClicked()
            return
        super().keyPressEvent(event)



