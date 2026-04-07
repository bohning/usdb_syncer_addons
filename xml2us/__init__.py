"""SingStar XML converter add-on"""

from pathlib import Path

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer.gui import hooks
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.utils import AppPaths
from xml_converter.XMLConverterDialog import Ui_Dialog
from xml_converter import converter


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
        self.xml_selected_dir: str | None = None
        self.xml_actual_dir: str | None = None
        self.pushbutton_pick_xml_folder.clicked.connect(self._select_xml_folder)
        self.pushbutton_convert.clicked.connect(self.convert_xml_files)

    def _select_xml_folder(self) -> None:
        self.xml_selected_dir = QFileDialog.getExistingDirectory(
            self, "Select SingStar Song Directory"
        )
        if not self.xml_selected_dir:
            return
        self.lineEdit_xml_dir.setText(self.xml_selected_dir)

        self.plainTextEdit_xml_conversion.appendPlainText(
            f"Scanning directory '{self.xml_selected_dir}' for SingStar XML files..."
        )
        songs_xml_files = [
            f
            for f in Path(self.xml_selected_dir).rglob("songs_*_0.xml")
            if not f.name.startswith("._")
        ]

        if not songs_xml_files:
            self.plainTextEdit_xml_conversion.appendPlainText(
                "No SingStar .xml files found under the specified directory."
            )
            return

        if len({file.parent for file in songs_xml_files}) > 1:
            self.plainTextEdit_xml_conversion.appendPlainText(
                "Multiple directories containing SingStar .xml files found under the specified directory. Please select a more specific directory."
            )
            return

        found_dir = songs_xml_files[0].parent
        self.plainTextEdit_xml_conversion.appendPlainText(
            f"Found matching songs.xml file in {found_dir}"
        )

        melody_xml_files = [
            f for f in found_dir.glob("*/melody_*.xml") if not f.name.startswith("._")
        ]

        if not melody_xml_files:
            self.plainTextEdit_xml_conversion.appendPlainText(
                "No song directories found near the matching songs.xml."
            )
            return

        self.xml_actual_dir = found_dir
        self.plainTextEdit_xml_conversion.appendPlainText(
            f"Found {len({file.parent for file in melody_xml_files})} song directories. Ready to convert!"
        )
        self.pushbutton_convert.setEnabled(True)
        self.pushbutton_convert.setFocus()

    def convert_xml_files(self) -> None:
        """Converts all XML files in the specified directory."""
        if not self.xml_actual_dir:
            return

        self.plainTextEdit_xml_conversion.appendPlainText(
            f"--- Processing: {self.xml_actual_dir} ---"
        )
        if converter.convert_singstar_dir_to_ultrastar(
            self.xml_actual_dir, overwrite=self.checkbox_overwrite.isChecked()
        ):
            self.plainTextEdit_xml_conversion.appendPlainText(
                f"--- Successfully finished: {self.xml_actual_dir} ---"
            )
        else:
            self.plainTextEdit_xml_conversion.appendPlainText(
                f"--- Failed to process: {self.xml_actual_dir} ---"
            )
        self.plainTextEdit_xml_conversion.appendPlainText(
            "Check the warnings and errors in the log for more details such as possible failed single songs."
        )


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
