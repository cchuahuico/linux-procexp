import sys
from PySide import QtGui

from ui.mainwindow import MainWindow

def main():
    app = QtGui.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()