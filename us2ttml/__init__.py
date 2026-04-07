"""UltraStar to TTML add-on."""

from PySide6.QtGui import QAction, QIcon

from usdb_syncer.gui import hooks, notification
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.logger import song_logger
from usdb_syncer.song_txt import SongTxt
from usdb_syncer.utils import AppPaths

ISO_639_1_LANGUAGE_CODES = {
    "Albanian": "sq",
    "Arabic": "ar",
    "Armenian": "hy",
    "Austrian": "de",
    "Bavarian": "de",
    "Bosnian": "bs",
    "Breton": "br",
    "Bulgarian": "bg",
    "Catalan": "ca",
    "Chinese": "zh",
    "Croatian": "hr",
    "Czech": "cs",
    "Danish": "da",
    "Drents": "nl",
    "Duala": "dua",  # no ISO 639-1
    "Dutch": "nl",
    "English": "en",
    "Estonian": "et",
    "Fantasy": "mis",  # no ISO 639-1
    "Finnish": "fi",
    "French": "fr",
    "Gaelic": "ga",
    "Galician": "gl",
    "German": "de",
    "Greek": "el",
    "Haitian": "ht",
    "Hebrew": "he",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Icelandic": "is",
    "Indonesian": "id",
    "Irish": "ga",
    "Italian": "it",
    "Japanese": "ja",
    "Joik": "se",
    "Korean": "ko",
    "Latin": "la",
    "Latvian": "lv",
    "Lithuanian": "lt",
    "Malagasy": "mg",
    "Malay": "ms",
    "Maori": "mi",
    "Multiple": "mul",  # no ISO 639-1
    "North Sami": "se",
    "Norwegian": "no",
    "Other": "mis",  # no ISO 639-1
    "Persian": "fa",
    "Polish": "pl",
    "Portuguese": "pt",
    "Portuguese (Brazil)": "pt",
    "Quechua": "qu",
    "Quenya": "mis",  # no ISO 639-1
    "Romanian": "ro",
    "Russian": "ru",
    "Samoan": "sm",
    "Scat": "mis",  # no ISO 639-1
    "Scots": "sco",  # no ISO 639-1
    "Serbian": "sr",
    "Slovak": "sk",
    "Slovenian": "sl",
    "Spanish": "es",
    "Sranan Tongo": "srn",  # no ISO 639-1
    "Swahili": "sw",
    "Swedish": "sv",
    "Swiss German": "de",
    "Tagalog": "tl",
    "Turkish": "tr",
    "Ukrainian": "uk",
    "Vietnamese": "vi",
    "Welsh": "cy",
    "Wolof": "wo",
    "Yoruba": "yo",
    "Zulu": "zu",
}


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
                f.write(_convert_to_ttml(txt))
            logger.info(f"Converted to TTML: {ttml_path}")
        except Exception as e:
            logger.exception(f"Failed to write TTML file: {e}")

    notification.success(f"Converted {len(songs_to_convert)} songs to TTML.")


def _convert_to_ttml(txt: SongTxt) -> str:
    def ms(note_time: int) -> int:
        return round(txt.headers.bpm.beats_to_ms(note_time) + txt.headers.gap)

    def fmt(ms_val: int) -> str:
        minutes, ms_rem = divmod(ms_val, 60_000)
        seconds, ms_rem = divmod(ms_rem, 1_000)
        return f"{minutes:02}:{seconds:02}.{ms_rem:03}"

    lines_xml: list[str] = []
    dur = 0

    for idx, line in enumerate(txt.notes.all_lines(), start=1):
        notes = list(line.notes)
        if not notes:
            continue

        line_start = ms(notes[0].start)
        line_end = ms(notes[-1].start + notes[-1].duration)

        # merge tilde-only notes and strip tildes from text
        merged: list[tuple[int, int, str]] = []  # (start_ms, end_ms, text)
        for note in notes:
            text = note.text or ""
            start = ms(note.start)
            end = ms(note.start + note.duration)

            # Strip tildes from beginning and end
            cleaned_text = text.strip("~")

            if not cleaned_text:
                # Tilde-only syllable: merge duration with previous
                if merged:
                    prev_start, _prev_end, prev_text = merged[-1]
                    merged[-1] = (prev_start, end, prev_text)
                # if there's no previous note, just drop it
            elif cleaned_text:
                # Preserve trailing space if original had it
                if text.rstrip() != text:
                    cleaned_text += " "
                merged.append((start, end, cleaned_text))

        span_parts: list[str] = []
        for note_index, (start, end, text) in enumerate(merged):
            trimmed_text = text.rstrip()
            span_parts.append(
                f'<span begin="{fmt(start)}" end="{fmt(end)}">{trimmed_text}</span>'
            )
            if text.endswith(" ") and note_index < len(merged) - 1:
                span_parts.append(" ")

        line_text = "".join(span_parts)

        lines_xml.append(
            f'<p begin="{fmt(line_start)}" end="{fmt(line_end)}" '
            f'itunes:key="L{idx}" ttm:agent="v1">{line_text}</p>'
        )
        dur = line_end

    body = "".join(lines_xml)

    # <?xml version="1.0" encoding="UTF-8"?>
    return f"""<tt xmlns="http://www.w3.org/ns/ttml" xmlns:itunes="http://music.apple.com/lyric-ttml-internal" xmlns:ttm="http://www.w3.org/ns/ttml#metadata" itunes:timing="Word" xml:lang="{ISO_639_1_LANGUAGE_CODES.get(txt.headers.main_language(), "und")}"><head><metadata><ttm:agent type="person" xml:id="v1"><ttm:name type="full">{txt.headers.artist}</ttm:name></ttm:agent><iTunesMetadata xmlns="http://music.apple.com/lyric-ttml-internal" leadingSilence="{fmt(txt.headers.gap)}"><translations/><songwriters><songwriter>{"unknown #1"}</songwriter></songwriters></iTunesMetadata></metadata></head><body dur="{fmt(dur)}"><div begin="{fmt(txt.headers.gap)}" end="{fmt(dur)}" itunes:songPart="Song">{body}</div></body></tt>"""


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
