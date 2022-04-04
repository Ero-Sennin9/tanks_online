import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QLabel, QCheckBox, QLCDNumber, QMainWindow
from PyQt5 import QtCore, QtGui, QtWidgets
from untitled import Ui_MainWindow


class Example(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.label_3.setText('<a href="https://ru.stackoverflow.com/"> Регистрация </a>')
        self.label_3.setOpenExternalLinks(True)
        self.pushButton.clicked.connect(self.act)

    def act(self):
        print(self.lineEdit, self.lineEdit_2)
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = Example()
    ex.show()
    sys.exit(app.exec())