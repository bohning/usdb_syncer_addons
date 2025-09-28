"""SingStar XML converter add-on"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer.gui import hooks
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.utils import AppPaths
from xml_converter.XMLConverterDialog import Ui_Dialog
import converter


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the tools menu."""
    icon_path = AppPaths.addons / "xml_converter" / "resources" / "document-convert.png"
    icon = QIcon(icon_path.as_posix())
    action = QAction(icon, "Convert SingStar XML files", main_window)
    action.triggered.connect(lambda: XMLConverterDialog(main_window).show())
    main_window.menu_tools.addAction(action)


class XMLConverterDialog(Ui_Dialog, QDialog):
    """Dialog to convert SingStar XML files to UltraStar TXTs."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.xml_dir: str | None = None
        self.xml_files: list[Path] | None = None
        self.pushbutton_pick_xml_folder.clicked.connect(self._select_xml_folder)
        self.pushbutton_convert.clicked.connect(self.convert_xml_files)

    def _select_xml_folder(self) -> None:
        self.xml_dir = QFileDialog.getExistingDirectory(
            self, "Select XML Song Directory"
        )
        if not self.xml_dir:
            return
        self.lineEdit_xml_dir.setText(self.xml_dir)

        self.plainTextEdit_xml_conversion.appendPlainText(
            f"Scanning directory '{self.xml_dir}' for SingStar XML files..."
        )
        self.xml_files = [
            f
            for f in Path(self.xml_dir).rglob("melody*.xml")
            if not f.name.startswith("._")
        ]

        if not self.xml_files:
            self.plainTextEdit_xml_conversion.appendPlainText(
                "No .xml files found in the specified directory."
            )
            return

        self.plainTextEdit_xml_conversion.appendPlainText(
            f"Found {len(self.xml_files)} XML file(s). Ready to convert!"
        )
        self.pushbutton_convert.setEnabled(True)
        self.pushbutton_convert.setFocus()

    def convert_xml_files(self) -> None:
        """Converts all XML files in the specified directory."""
        if not self.xml_files:
            return

        successful_conversions = 0
        failed_conversions = 0

        for xml_file in self.xml_files:
            self.plainTextEdit_xml_conversion.appendPlainText(
                f"--- Processing: {xml_file.name} ---"
            )
            # Output path defaults to same directory as input xml
            if converter.convert_singstar_xml_to_ultrastar_txt(
                xml_file, overwrite=self.checkbox_overwrite.isChecked()
            ):
                successful_conversions += 1
            else:
                failed_conversions += 1
            self.plainTextEdit_xml_conversion.appendPlainText(
                f"--- Finished: {xml_file.name} ---"
            )

        self.plainTextEdit_xml_conversion.appendPlainText(
            f"{successful_conversions} successful and {failed_conversions} failed "
            "conversions."
        )


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
