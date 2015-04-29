from PySide import QtGui

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.initUI()

    def initMenuBar(self):
        exitItem = QtGui.QAction('Exit', self)
        exitItem.setShortcut('Ctrl+Q')
        exitItem.setStatusTip('Exit application')
        exitItem.triggered.connect(self.close)

        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(exitItem)

    def initUI(self):
        self.initMenuBar()
        self.setGeometry(300, 300, 750, 550)
        self.setWindowTitle('Linux Process Explorer')

