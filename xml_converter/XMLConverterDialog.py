# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'XMLConverterDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QDialog,
    QDialogButtonBox, QHBoxLayout, QLineEdit, QPlainTextEdit,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        Dialog.resize(767, 628)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.pushbutton_pick_xml_folder = QPushButton(Dialog)
        self.pushbutton_pick_xml_folder.setObjectName(u"pushbutton_pick_xml_folder")

        self.horizontalLayout_2.addWidget(self.pushbutton_pick_xml_folder)

        self.lineEdit_xml_dir = QLineEdit(Dialog)
        self.lineEdit_xml_dir.setObjectName(u"lineEdit_xml_dir")
        self.lineEdit_xml_dir.setReadOnly(True)

        self.horizontalLayout_2.addWidget(self.lineEdit_xml_dir)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.plainTextEdit_xml_conversion = QPlainTextEdit(Dialog)
        self.plainTextEdit_xml_conversion.setObjectName(u"plainTextEdit_xml_conversion")
        self.plainTextEdit_xml_conversion.setReadOnly(True)

        self.verticalLayout.addWidget(self.plainTextEdit_xml_conversion)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.checkbox_overwrite = QCheckBox(Dialog)
        self.checkbox_overwrite.setObjectName(u"checkbox_overwrite")

        self.horizontalLayout.addWidget(self.checkbox_overwrite)

        self.pushbutton_convert = QPushButton(Dialog)
        self.pushbutton_convert.setObjectName(u"pushbutton_convert")
        self.pushbutton_convert.setEnabled(False)

        self.horizontalLayout.addWidget(self.pushbutton_convert)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        self.horizontalLayout.addWidget(self.buttonBox)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"XML Converter", None))
        self.pushbutton_pick_xml_folder.setText(QCoreApplication.translate("Dialog", u"Select SingStar song folder", None))
        self.plainTextEdit_xml_conversion.setPlainText("")
        self.checkbox_overwrite.setText(QCoreApplication.translate("Dialog", u"Overwrite existing", None))
        self.pushbutton_convert.setText(QCoreApplication.translate("Dialog", u"Convert", None))
    # retranslateUi

