from PyQt4.QtGui import QAction, QMainWindow, QSplitter, QTableWidget, QTableWidgetItem, QColor
from PyQt4.QtCore import Qt, pyqtSlot, QModelIndex, QEvent
from .proctablewidget import ProcTableWidget
from ..proctablemodel import ProcTableModel
from .findhandledialog import FindHandleDialog

class ProcExpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        self.findDialog = None

    def initMenuBar(self):
        exitItem = QAction('Exit', self)
        exitItem.setShortcut('Ctrl+Q')
        exitItem.setStatusTip('Exit application')
        exitItem.triggered.connect(self.close)

        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(exitItem)

    def initUI(self):
        self.initMenuBar()
        self.setGeometry(300, 300, 1280, 700)
        self.setWindowTitle('Linux Process Explorer')
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

    def keyPressEvent(self, event):
        if event.type() == QEvent.KeyPress:
            modifiers = event.modifiers()
            if event.key() == Qt.Key_F and modifiers & Qt.ControlModifier:
                if self.findDialog is None:
                    self.findDialog = FindHandleDialog(self)
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
            procNode = processMIdx.internalPointer()
            descriptors = procNode.descriptors()
            libs = procNode.mappedLibraries()
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
