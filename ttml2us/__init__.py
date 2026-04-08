"""Apple Music TTML converter add-on."""

from pathlib import Path
from urllib.parse import quote

from defusedxml import ElementTree
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QSpinBox,
    QTableWidgetItem,
    QWidget,
)

from ttml2us import converter
from ttml2us.TTMLConverterDialog import Ui_Dialog
from usdb_syncer.gui import hooks, notification
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.utils import AppPaths


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the tools menu."""
    icon_path = AppPaths.addons / "ttml2us" / "resources" / "document-convert.png"
    icon = QIcon(icon_path.as_posix())
    action = QAction(icon, "Convert TTML files", main_window)
    action.triggered.connect(lambda: TTMLConverterDialog(main_window).show())
    main_window.menu_tools.addAction(action)


class TTMLConverterDialog(Ui_Dialog, QDialog):
    """Dialog to convert TTML files to UltraStar TXTs."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent=parent)
        self.setupUi(self)
        self.ttml_selected_dir: str | None = None
        self.pushbutton_pick_ttml_folder.clicked.connect(self._select_ttml_folder)
        self.pushbutton_convert.clicked.connect(self.convert_ttml_files)
        self.tableWidget_ttml_conversion.setColumnCount(6)
        self.tableWidget_ttml_conversion.setHorizontalHeaderLabels(
            ["File", "Artist", "Title", "BPM", "Search BPM", "Status"]
        )

    def _select_ttml_folder(self) -> None:
        self.ttml_selected_dir = QFileDialog.getExistingDirectory(
            self, "Select TTML Directory"
        )
        if not self.ttml_selected_dir:
            return
        self.lineEdit_ttml_dir.setText(self.ttml_selected_dir)

        songs_ttml_files = [
            f
            for f in Path(self.ttml_selected_dir).rglob("*.ttml")
            if not f.name.startswith("._")
        ]

        if not songs_ttml_files:
            notification.warning("No TTML files found under the specified directory.")
            return

        self._ttml_files = songs_ttml_files
        self.tableWidget_ttml_conversion.setRowCount(0)
        self.tableWidget_ttml_conversion.clearContents()
        self.tableWidget_ttml_conversion.setRowCount(len(self._ttml_files))

        for row, ttml_file in enumerate(self._ttml_files):
            artist, title = self._parse_ttml_metadata(ttml_file)
            self.tableWidget_ttml_conversion.setItem(
                row, 0, QTableWidgetItem(ttml_file.name)
            )
            self.tableWidget_ttml_conversion.setItem(row, 1, QTableWidgetItem(artist))
            self.tableWidget_ttml_conversion.setItem(row, 2, QTableWidgetItem(title))

            bpm_spin = QSpinBox(self.tableWidget_ttml_conversion)
            bpm_spin.setRange(200, 500)
            bpm_spin.setValue(400)
            bpm_spin.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.tableWidget_ttml_conversion.setCellWidget(row, 3, bpm_spin)

            # Add clickable search link for BPM
            search_url = (
                f"https://tunebat.com/Search?q={quote(artist)}%20{quote(title)}"
            )
            search_label = QLabel(f'<a href="{search_url}">Search BPM</a>')
            search_label.setOpenExternalLinks(True)
            self.tableWidget_ttml_conversion.setCellWidget(row, 4, search_label)

            status_item = QTableWidgetItem("Ready")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tableWidget_ttml_conversion.setItem(row, 5, status_item)

        self.tableWidget_ttml_conversion.resizeColumnsToContents()
        self.pushbutton_convert.setEnabled(True)
        self.pushbutton_convert.setFocus()

    def _parse_ttml_metadata(self, ttml_file: Path) -> tuple[str, str]:
        artist = "Unknown Artist"
        title = "Unknown Title"

        try:
            tree = ElementTree.parse(ttml_file)
            root = tree.getroot()
            if root is None:
                return artist, title
            namespaces = {
                "ttml": "http://www.w3.org/ns/ttml",
                "itunes": "http://music.apple.com/lyric-ttml-internal",
                "ttm": "http://www.w3.org/ns/ttml#metadata",
                "amll": "http://www.example.com/ns/amll",
            }
            agent = root.find(".//ttm:agent/ttm:name", namespaces)
            if agent is not None and agent.text:
                artist = agent.text.strip()
            title_element = root.find(".//ttm:title", namespaces)
            if title_element is not None and title_element.text:
                title = title_element.text.strip()
        except ElementTree.ParseError:
            pass

        return artist, title

    def convert_ttml_files(self) -> None:
        """Convert all TTML files in the specified directory."""
        if not self.ttml_selected_dir:
            notification.warning(
                "No directory selected. Please select a directory first."
            )
            return

        success_count = 0
        for row, ttml_file in enumerate(self._ttml_files):
            bpm_widget = self.tableWidget_ttml_conversion.cellWidget(row, 3)
            bpm = converter.BeatsPerMinute(400)
            if isinstance(bpm_widget, QSpinBox):
                bpm = converter.BeatsPerMinute(bpm_widget.value())

            status_item = self.tableWidget_ttml_conversion.item(row, 5)
            if status_item is None:
                status_item = QTableWidgetItem()
                self.tableWidget_ttml_conversion.setItem(row, 5, status_item)

            try:
                with ttml_file.open("r", encoding="utf-8") as f:
                    ttml_content = f.read()

                txt = converter._convert_ttml_to_song(ttml_content, bpm=bpm)
                txt.write_to_file(
                    Path(
                        ttml_file.parent
                        / f"{txt.headers.artist} - {txt.headers.title}.txt"
                    ),
                    encoding="utf-8",
                    newline="\n",
                )
                status_item.setText("Success")
                status_item.setToolTip("Converted successfully")
                success_count += 1
            except (OSError, ElementTree.ParseError, ValueError) as exc:
                status_item.setText("Failed")
                status_item.setToolTip(str(exc))

        if success_count == len(self._ttml_files):
            notification.success(f"Successfully converted {success_count} TTML files.")
        elif success_count > 0:
            notification.warning(
                f"Converted {success_count} of {len(self._ttml_files)} TTML files."
            )
        else:
            notification.error(
                f"Failed to convert TTML files under {self.ttml_selected_dir}."
            )


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
