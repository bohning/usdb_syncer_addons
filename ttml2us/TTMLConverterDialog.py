################################################################################
## Form generated from reading UI file 'TTMLConverterDialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
)


class Ui_Dialog:
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        Dialog.resize(767, 628)
        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pushbutton_pick_ttml_folder = QPushButton(Dialog)
        self.pushbutton_pick_ttml_folder.setObjectName("pushbutton_pick_ttml_folder")

        self.horizontalLayout_2.addWidget(self.pushbutton_pick_ttml_folder)

        self.lineEdit_ttml_dir = QLineEdit(Dialog)
        self.lineEdit_ttml_dir.setObjectName("lineEdit_ttml_dir")
        self.lineEdit_ttml_dir.setReadOnly(True)

        self.horizontalLayout_2.addWidget(self.lineEdit_ttml_dir)

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.tableWidget_ttml_conversion = QTableWidget(Dialog)
        self.tableWidget_ttml_conversion.setObjectName("tableWidget_ttml_conversion")
        self.tableWidget_ttml_conversion.setColumnCount(6)
        self.tableWidget_ttml_conversion.setRowCount(0)
        self.tableWidget_ttml_conversion.setAlternatingRowColors(True)

        self.verticalLayout.addWidget(self.tableWidget_ttml_conversion)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.checkbox_overwrite = QCheckBox(Dialog)
        self.checkbox_overwrite.setObjectName("checkbox_overwrite")

        self.horizontalLayout.addWidget(self.checkbox_overwrite)

        self.pushbutton_convert = QPushButton(Dialog)
        self.pushbutton_convert.setObjectName("pushbutton_convert")
        self.pushbutton_convert.setEnabled(False)

        self.horizontalLayout.addWidget(self.pushbutton_convert)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName("buttonBox")
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
        Dialog.setWindowTitle(
            QCoreApplication.translate("Dialog", "TTML Converter", None)
        )
        self.pushbutton_pick_ttml_folder.setText(
            QCoreApplication.translate("Dialog", "Select TTML folder", None)
        )
        self.checkbox_overwrite.setText(
            QCoreApplication.translate("Dialog", "Overwrite existing", None)
        )
        self.pushbutton_convert.setText(
            QCoreApplication.translate("Dialog", "Convert", None)
        )

    # retranslateUi
