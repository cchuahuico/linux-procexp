from PyQt4.QtGui import QAction, QMainWindow, QSplitter, QTableWidget, QTableWidgetItem, QColor
from PyQt4.QtCore import Qt, pyqtSlot, QModelIndex
from .proctablewidget import ProcTableWidget

class ProcExpWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

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
        self.setGeometry(300, 300, 1050, 650)
        self.setWindowTitle('Linux Process Explorer')
        self.procTable = ProcTableWidget()
        self.procTable.clicked.connect(self.showDescriptors)
        self.descriptorsTable = QTableWidget()
        self.descriptorsTable.setColumnCount(3)
        self.descriptorsTable.setHorizontalHeaderLabels(('ID', 'Type', 'Object'))
        self.descriptorsTable.verticalHeader().setVisible(False)
        self.descriptorsTable.setShowGrid(False)
        self.descriptorsTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.descriptorsTable.horizontalHeader().setStretchLastSection(True)

        # TODO: find a way to get the row height from the QTreeView
        self.descriptorsTable.verticalHeader().setDefaultSectionSize(24)

        mainSplitter = QSplitter(Qt.Vertical)
        mainSplitter.addWidget(self.procTable)
        mainSplitter.addWidget(self.descriptorsTable)
        self.setCentralWidget(mainSplitter)

    @pyqtSlot(QModelIndex)
    def showDescriptors(self, processMIdx):
        try:
            self.descriptorsTable.setRowCount(0)
            self.descriptorsTable.clearContents()
            descriptors = processMIdx.internalPointer().descriptors()
            self.descriptorsTable.setRowCount(len(descriptors))
        except PermissionError:
            self.descriptorsTable.setRowCount(1)
            self.descriptorsTable.setSpan(0, 0, 1, 3)
            permDeniedMsg = QTableWidgetItem('<Permission Denied>')
            permDeniedMsg.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            permDeniedMsg.setTextAlignment(Qt.AlignCenter)
            permDeniedMsg.setTextColor(QColor(255, 0, 0))
            self.descriptorsTable.setItem(0, 0, permDeniedMsg)
        else:
            for row, descriptor in enumerate(descriptors):
                idItem = QTableWidgetItem(str(descriptor.id))
                idItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                typeItem = QTableWidgetItem(descriptor.type)
                typeItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                nameItem = QTableWidgetItem(descriptor.name)
                nameItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                self.descriptorsTable.setItem(row, 0, idItem)
                self.descriptorsTable.setItem(row, 1, typeItem)
                self.descriptorsTable.setItem(row, 2, nameItem)