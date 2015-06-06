from PyQt4.QtGui import QAction, QMainWindow, QSplitter, QTableWidget, QTableWidgetItem, QColor, QApplication
from PyQt4.QtCore import Qt, pyqtSlot, QModelIndex, QEvent
from .proctablewidget import ProcTableWidget
from ..proctablemodel import ProcTableModel
from .findhandledialog import FindHandleDialog

class ProcExpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        # setup menu bar
        exitItem = QAction('Exit', self)
        exitItem.setShortcut('Ctrl+Q')
        exitItem.setStatusTip('Exit application')
        exitItem.triggered.connect(self.close)
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(exitItem)

        # setup widgets
        self.model = ProcTableModel(self)
        self.procTable = ProcTableWidget(self.model)
        self.procTable.clicked.connect(self.showDescriptors)
        self.handlesTable = QTableWidget()
        self.handlesTable.setColumnCount(2)
        self.handlesTable.setHorizontalHeaderLabels(('Type', 'Object Name'))
        self.handlesTable.verticalHeader().setVisible(False)
        self.handlesTable.setShowGrid(False)
        self.handlesTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.handlesTable.horizontalHeader().setStretchLastSection(True)

        # TODO: find a way to get the row height from the QTreeView
        self.handlesTable.verticalHeader().setDefaultSectionSize(24)

        mainSplitter = QSplitter(Qt.Vertical)
        mainSplitter.addWidget(self.procTable)
        mainSplitter.addWidget(self.handlesTable)
        self.setCentralWidget(mainSplitter)

        desktopGeometry = QApplication.desktop().screenGeometry()
        self.setGeometry(0, 0, 1280, 700)
        self.move((desktopGeometry.width() - self.width()) / 2,
                  (desktopGeometry.height() - self.height()) / 2)
        self.setWindowTitle('Linux Process Explorer')

        # find handle dialog
        self.findDialog = None

    @pyqtSlot(int)
    def removeFindDialog(self):
        self.findDialog = None

    def keyPressEvent(self, event):
        if event.type() == QEvent.KeyPress:
            modifiers = event.modifiers()
            if event.key() == Qt.Key_F and modifiers & Qt.ControlModifier:
                if self.findDialog is None:
                    self.findDialog = FindHandleDialog(self)
                    self.findDialog.finished.connect(self.removeFindDialog)
                    self.findDialog.show()
                else:
                    self.findDialog.activateWindow()
                return
        super().keyPressEvent(event)


    @pyqtSlot(QModelIndex)
    def showDescriptors(self, processMIdx):
        try:
            self.handlesTable.setRowCount(0)
            self.handlesTable.clearContents()
            descriptors = self.model.getProcDescriptors(processMIdx)
            libs = self.model.getProcLibraries(processMIdx)
            self.handlesTable.setRowCount(len(descriptors) + len(libs))
        except PermissionError:
            self.handlesTable.setRowCount(1)
            self.handlesTable.setSpan(0, 0, 1, 2)
            permDeniedMsg = QTableWidgetItem('<Permission Denied>')
            permDeniedMsg.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            permDeniedMsg.setTextAlignment(Qt.AlignCenter)
            permDeniedMsg.setTextColor(QColor(255, 0, 0))
            self.handlesTable.setItem(0, 0, permDeniedMsg)
        else:
            for row, descriptor in enumerate(descriptors):
                typeItem = QTableWidgetItem(descriptor.type)
                typeItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                nameItem = QTableWidgetItem(descriptor.name)
                nameItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.handlesTable.setItem(row, 0, typeItem)
                self.handlesTable.setItem(row, 1, nameItem)

            for row, libName in enumerate(libs, start=len(descriptors)):
                typeItem = QTableWidgetItem('Shared Library')
                typeItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                nameItem = QTableWidgetItem(libName)
                nameItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.handlesTable.setItem(row, 0, typeItem)
                self.handlesTable.setItem(row, 1, nameItem)
