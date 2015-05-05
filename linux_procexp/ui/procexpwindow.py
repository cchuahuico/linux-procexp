from PyQt4.QtGui import QAction, QMainWindow

class ProcExpWindow(QMainWindow):
    def __init__(self):
        super().__init__()
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

