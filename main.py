import sys
from PyQt4 import QtGui
from linux_procexp.ui.procexpwindow import ProcExpWindow

def main():
    app = QtGui.QApplication(sys.argv)
    mw = ProcExpWindow()
    mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()