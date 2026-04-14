"""UltraStar to TTML add-on."""

from PySide6.QtGui import QAction, QIcon

from usdb_syncer.gui import hooks, notification
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.utils import AppPaths


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the songs context menu."""
    icon_path = AppPaths.addons / "us2ttml" / "resources" / "document-convert.png"
    icon = QIcon(icon_path.as_posix())
    action = QAction(icon, "Convert to TTML", main_window)
    action.triggered.connect(lambda: _convert_selection_to_ttml(main_window))
    main_window.menu_songs.addAction(action)


def _convert_selection_to_ttml(main_window: MainWindow) -> None:
    """Convert selected songs to TTML if they have local txt files."""
    songs_to_convert = [
        song
        for song in main_window.table.selected_songs()
        if song.sync_meta and song.sync_meta.txt_path()
    ]

    if not songs_to_convert:
        notification.warning("No songs with local txt files selected.")
        return

    for song in songs_to_convert:
        if not song.sync_meta or not (txt_path := song.sync_meta.txt_path()):
            continue

        logger = song_logger(song.song_id)
        txt = SongTxt.try_from_file(txt_path, logger)
        if not txt:
            logger.error(f"Failed to parse txt file: {txt_path}")
            continue

        ttml_path = txt_path.with_suffix(".ttml")
        try:
            with ttml_path.open("w", encoding="utf-8") as f:
                f.write(txt.synchronized_lyrics_ttml())
            logger.info(f"Converted to TTML: {ttml_path}")
        except Exception as e:
            logger.exception(f"Failed to write TTML file: {e}")

    notification.success(f"Converted {len(songs_to_convert)} songs to TTML.")


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
