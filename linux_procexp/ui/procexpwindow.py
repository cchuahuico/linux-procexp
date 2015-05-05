from PyQt4.QtGui import QAction, QMainWindow
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
        self.setGeometry(300, 300, 950, 650)
        self.setWindowTitle('Linux Process Explorer')
        self.setCentralWidget(ProcTableWidget(self))

