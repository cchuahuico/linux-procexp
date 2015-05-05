import sys
from PyQt4.QtGui import QApplication
from linux_procexp.ui.procexpwindow import ProcExpWindow

def main():
    app = QApplication(sys.argv)
    mw = ProcExpWindow()
    mw.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()