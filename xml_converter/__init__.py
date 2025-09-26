"""SingStar XML converter add-on"""

import re
from enum import Enum, StrEnum
from pathlib import Path

import pycld2 as cld2
from lxml import etree
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QDialog, QFileDialog, QWidget

from usdb_syncer import logger
from usdb_syncer.gui import hooks
from usdb_syncer.gui.mw import MainWindow
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.settings import Newline
from usdb_syncer.song_txt import Headers, SongTxt, Tracks
from usdb_syncer.song_txt.auxiliaries import replace_false_apostrophes
from usdb_syncer.song_txt.tracks import BeatsPerMinute, Line, LineBreak, Note, NoteKind
from usdb_syncer.usdb_scraper import SessionManager, get_logged_in_usdb_user
from usdb_syncer.utils import AppPaths
from xml_converter.XMLConverterDialog import Ui_Dialog

SINGSTAR_XML_NAMESPACE_URI = "http://www.singstargame.com"
NS_MAP_DEFAULT = {"ss": SINGSTAR_XML_NAMESPACE_URI}

# XML Element Names
XML_ELEM_MELODY = "MELODY"
XML_ELEM_TRACK = "TRACK"
XML_ELEM_SENTENCE = "SENTENCE"
XML_ELEM_NOTE = "NOTE"
XML_ELEM_NOTE_MARKER = "MARKER_N"

# XML Attribute Names
XML_ATTR_MELODY_DUET = "Duet"
XML_ATTR_MELODY_GENRE = "Genre"
XML_ATTR_MELODY_RESOLUTION = "Resolution"
XML_ATTR_MELODY_TEMPO = "Tempo"
XML_ATTR_MELODY_VERSION = "Version"
XML_ATTR_MELODY_YEAR = "Year"
XML_ATTR_TRACK_ARTIST = "Artist"
XML_ATTR_TRACK_NAME = "Name"
XML_ATTR_SENTENCE_SINGER = "Singer"
XML_ATTR_NOTE_BONUS = "Bonus"  # Golden Note
XML_ATTR_NOTE_DURATION = "Duration"
XML_ATTR_NOTE_FREESTYLE = "FreeStyle"
XML_ATTR_NOTE_LYRIC = "Lyric"
XML_ATTR_NOTE_MIDI_NOTE = "MidiNote"
XML_ATTR_NOTE_RAP = "Rap"

# Common String Values
XML_VALUE_YES = "Yes"
SINGER_SOLO_1 = "Solo 1"
SINGER_SOLO_2 = "Solo 2"
SINGER_GROUP = "Group"

# Default values
DEFAULT_EDITION = "SingStar PS3 DLC"
DEFAULT_ARTIST = "Artist"
DEFAULT_TITLE = "Title"

VOWELS = "aeiouäöüAEIOUÄÖÜ"
DIPHTHONGS = {
    "aa",
    "ae",
    "ah",
    "ai",
    "au",
    "ay",
    "Ah",
    "ea",
    "eah",
    "ee",
    "ei",
    "eu",
    "ey",
    "eye",
    "ie",
    "io",
    "oa",
    "oe",
    "oh",
    "ooh",
    "oi",
    "oo",
    "ou",
    "oy",
    "Oh",
    "Ooh",
    "ue",
    "ui",
}


def on_window_loaded(main_window: MainWindow) -> None:
    """Add a button to the tools menu."""
    icon_path = AppPaths.addons / "xml_converter" / "resources" / "document-convert.png"
    icon = QIcon(icon_path.as_posix())
    action = QAction(icon, "Convert SingStar XML files", main_window)
    action.triggered.connect(lambda: XMLConverterDialog(main_window).show())
    main_window.menu_tools.addAction(action)


def convert_singstar_xml_to_ultrastar_txt(
    input_path: Path, overwrite: bool = False
) -> bool:
    """Converts a SingStar XML file to an UltraStar TXT file."""

    converter = XmlConverter(input_path)
    song_txt = converter.convert_to_songtxt()

    if song_txt:
        output_path = (
            input_path.parent
            / f"{song_txt.headers.artist} - {song_txt.headers.title}.txt"
        )
        try:
            if overwrite or not output_path.exists():
                song_txt.write_to_file(output_path, Encoding.UTF_8, Newline.CRLF.value)
                logger.logger.info(
                    f"Successfully wrote UltraStar TXT to: {output_path}"
                )
                return True
            else:
                logger.logger.warning(
                    f"File {output_path} already exists. Conversion skipped."
                )
                return False
        except IOError as e:
            logger.logger.error(f"Failed to write output file '{output_path}': {e}")
            return False
    else:
        logger.logger.error(
            f"Conversion failed for '{input_path.name}'. No output generated."
        )
        return False


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
            if convert_singstar_xml_to_ultrastar_txt(
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


class XMLVersion(Enum):
    """Version of SingStar XML files."""

    V1 = 1
    V2 = 2
    V4 = 4

    def __str__(self) -> str:
        return f"{self.value}"


class Encoding(StrEnum):
    """Supported encodings for song txts."""

    UTF_8 = "utf-8"
    ISO_8859_1 = "iso-8859-1"

    @classmethod
    def from_string(cls, value: str | None) -> "Encoding":
        """Converts a string to an Encoding enum value."""
        if value == "ISO-8859-1":
            return cls.ISO_8859_1
        if value == "UTF-8":
            return cls.UTF_8
        logger.logger.warning(
            f"Unknown encoding '{value}'. Defaulting to {cls.UTF_8.upper()}."
        )
        return cls.UTF_8


class Resolution(Enum):
    """Resolution of SingStar XML files (ticks per beat related)."""

    SEMIQUAVER = 1
    DEMISEMIQUAVER = 2

    @classmethod
    def from_string(cls, value: str | None) -> "Resolution":
        """Converts a string to a Resolution enum value."""
        match value:
            case "Semiquaver":
                return cls.SEMIQUAVER
            case "Demisemiquaver":
                return cls.DEMISEMIQUAVER
            case _:
                logger.logger.warning(
                    f"Unknown resolution '{value}'. Defaulting to Demisemiquaver."
                )
                return cls.DEMISEMIQUAVER

    def __str__(self) -> str:
        return self.name.capitalize()


def _parse_bool_attribute(value: str | None) -> bool:
    """Converts common XML boolean string ('Yes'/'No') to Python bool."""
    return value == XML_VALUE_YES


def _fix_lyric_string(lyric: str | None) -> str:
    """Cleans and formats the syllable text."""
    if not lyric:
        return ""
    if lyric == "-":
        # replace hyphens by tildes as vowel repetition markers
        return "~"
    if lyric.endswith(" -"):
        # remove follow-up syllable markers
        return lyric[:-2]  # remove space and hyphen, no space after
    if lyric.endswith("-") and len(lyric) > 1 and lyric[-2].isalpha():
        # preserve true trailing hyphens of hyphenated words
        return lyric
    # in all other cases add an inter-word space at the end
    return lyric + " "


def fix_tilde_spacing(notes: list) -> None:
    tilde_indices = []

    for i, note in enumerate(notes):
        if note.text.strip() == "~":
            tilde_indices.append(i)
        else:
            if tilde_indices:
                for j in tilde_indices[:-1]:
                    notes[j].text = "~"
                notes[tilde_indices[-1]].text = "~ "
                tilde_indices.clear()

    if tilde_indices:
        for j in tilde_indices[:-1]:
            notes[j].text = "~"
        notes[tilde_indices[-1]].text = "~ "


def _add_space_to_last_tilde(notes: list[Note]) -> None:
    """Adds a space to the last tilde in a sequence of repeated syllables."""
    i = 0
    while i < len(notes):
        if notes[i].text == "~":
            # Look ahead to find the end of the ~ sequence
            while i + 1 < len(notes) and notes[i + 1].text == "~":
                i += 1
            # We are now at the last ~ in the sequence
            notes[i].text = "~ "
        i += 1


def _split_on_first_vowel_or_diphthong(text: str) -> tuple[str, str] | None:
    matches: list[tuple[int, int]] = []

    # Collect diphthong positions first
    for i in range(len(text) - 1):
        if text[i : i + 2].lower() in DIPHTHONGS:
            matches.append((i, 2))
    # Collect single vowels (not part of diphthong already matched)
    for i, char in enumerate(text):
        if char in VOWELS and all(
            not (start <= i < start + length) for start, length in matches
        ):
            matches.append((i, 1))

    if not matches:
        return None

    # Sort by position
    matches.sort(key=lambda x: x[0])
    first_match = matches[0]
    split_idx = first_match[0] + first_match[1]
    return text[:split_idx], text[split_idx:]


def _split_lyrics_to_tildes(notes: list[Note]) -> None:
    """Split syllables across tilde notes on first vowel or diphthong."""
    i = 0
    while i < len(notes) - 1:
        current = notes[i]
        if (
            current.text.strip()
            and current.text.strip() != "~"
            and notes[i + 1].text.strip() == "~"
        ):
            # Find the end of the ~ cluster
            j = i + 1
            while j + 1 < len(notes) and notes[j + 1].text.strip() == "~":
                j += 1

            split_result = _split_on_first_vowel_or_diphthong(current.text.strip())
            if split_result:
                left, right = split_result
                current.text = left

                # Clear intermediate ~ notes
                for k in range(i + 1, j):
                    notes[k].text = "~"

                # Assign right part only to the last ~ note
                notes[j].text = f"~{right.rstrip()} "  # Append space here, not before

                i = j
        i += 1


def _insert_missing_spaces(text: str) -> str:
    """Inserts missing spaces in artist and title,
    e.g. 'MyChemicalRomance' --> 'My Chemical Romance'
    but keeps all caps intact, e.g. 'HIM' --> 'HIM'
    """
    return re.sub(r"(?<=[a-z])([A-Z0-9])", r" \1", text)


class XmlConverter:
    """Converts a Singstar XML file to an UltraStar TXT object using lxml."""

    def __init__(self, input_path: Path) -> None:
        self.input_path = input_path
        self.raw_bytes: bytes | None = None
        self.text: str = ""
        self.root: etree._Element | None = None
        self.ns_map: dict[str, str] | None = None
        self.ns_prefix: str = ""
        self.artist: str = DEFAULT_ARTIST
        self.title: str = DEFAULT_TITLE
        self.version: XMLVersion = XMLVersion.V1
        self.resolution: Resolution = Resolution.DEMISEMIQUAVER
        self.raw_tempo: float | None = None
        self.bpm: BeatsPerMinute
        self.gap: int = 0
        self.language: str | None = None
        self.edition: str = DEFAULT_EDITION
        self.genre: str | None = None
        self.year: str | None = None
        self.is_duet: bool = False
        self.medley_start: int | None = None
        self.medley_end: int | None = None
        self.p1_name: str | None = None
        self.p2_name: str | None = None

    def _read_and_parse_xml(self) -> bool:
        """Reads the XML file, detects encoding, and parses it using lxml."""
        if not self._read_raw_bytes():
            return False
        encoding = self._detect_encoding()
        if not self._parse_xml(encoding):
            if encoding != Encoding.ISO_8859_1:
                logger.logger.warning("Retrying parse with ISO-8859-1 encoding...")
                return self._parse_xml(Encoding.ISO_8859_1)
            else:
                return False
        else:
            return True

    def _read_raw_bytes(self) -> bool:
        """Reads raw bytes from the input file."""
        try:
            self.raw_bytes = self.input_path.read_bytes()
            if not self.raw_bytes:
                logger.logger.error(f"Input file is empty: {self.input_path}")
                return False
            else:
                return True
        except IOError as e:
            logger.logger.error(f"Error reading file bytes: {e}")
            return False

    def _detect_encoding(self) -> Encoding:
        """Attempts to detect file encoding based on the XML declaration."""
        encoding = Encoding.UTF_8
        if not self.raw_bytes:
            return encoding
        try:
            preview_len = min(len(self.raw_bytes), 150)
            first_line = self._try_decode_preview(preview_len)

            if first_line.startswith("<?xml"):
                encoding_match = re.search(
                    r'encoding="([^"]+)"', first_line, re.IGNORECASE
                )
                if encoding_match:
                    encoding = Encoding.from_string(encoding_match.group(1))
                    logger.logger.info(
                        f"Detected encoding '{encoding}' from XML declaration."
                    )
                else:
                    logger.logger.info(
                        "XML declaration found, but no encoding specified. Using "
                        f"default encoding '{encoding}'."
                    )
            else:
                logger.logger.warning(
                    f"XML declaration not found. Using default encoding '{encoding}'."
                )
        except Exception as e:  # noqa: BLE001
            logger.logger.warning(
                f"Failed to detect encoding reliably: {e}. "
                f"Using default encoding '{encoding}'."
            )

        return encoding

    def _try_decode_preview(self, preview_len: int) -> str:
        """Attempts to decode the first line for encoding detection."""
        if not self.raw_bytes:
            return ""
        try:
            return self.raw_bytes[:preview_len].decode(Encoding.UTF_8).split("\n", 1)[0]
        except UnicodeDecodeError:
            try:
                return (
                    self.raw_bytes[:preview_len]
                    .decode(Encoding.ISO_8859_1)
                    .split("\n", 1)[0]
                )
            except UnicodeDecodeError:
                return ""

    def _parse_xml(self, encoding: Encoding) -> bool:
        """Parses the raw bytes into XML tree using the specified encoding."""
        if not self.raw_bytes:
            return False
        try:
            parser = etree.XMLParser(encoding=encoding, recover=True)
            self.root = etree.fromstring(self.raw_bytes, parser=parser)
            self.text = self.raw_bytes.decode(encoding)
            self._detect_namespace()
        except etree.XMLSyntaxError as e:
            logger.logger.error(f"Failed to parse XML with encoding '{encoding}': {e}")
            return False
        except Exception as e:  # noqa: BLE001
            logger.logger.error(f"Unexpected error during XML parsing: {e}")
            return False
        else:
            return True

    def _detect_namespace(self) -> None:
        """Detects if the XML uses namespaces."""
        if self.root is not None and self.root.tag.startswith("{"):
            self.ns_map = NS_MAP_DEFAULT
            self.ns_prefix = "ss:"
        else:
            self.ns_map = None
            self.ns_prefix = ""

    def _extract_metadata(self) -> None:
        """Extracts metadata from comments (regex) and root attributes (lxml)."""
        if self.root is None:
            logger.logger.error("Cannot extract metadata, XML root is not parsed.")
            return
        self.parse_artist_title()
        # Attributes from root <MELODY> tag
        self.version = XMLVersion(int(self.root.get(XML_ATTR_MELODY_VERSION, "1")))
        self.genre = self.root.get(XML_ATTR_MELODY_GENRE, None)
        self.year = self.root.get(XML_ATTR_MELODY_YEAR, None)
        self.is_duet = _parse_bool_attribute(self.root.get(XML_ATTR_MELODY_DUET, "No"))
        self.parse_bpm()
        self.parse_duet_singer_names()
        logger.logger.info(
            f"Extracted Metadata: Artist='{self.artist}', Title='{self.title}', "
            f"BPM={self.bpm} (Raw Tempo={self.raw_tempo}, Res={self.resolution}), "
            f"Duet={self.is_duet}"
        )

    def parse_bpm(self) -> None:
        """Calculates BPM from Tempo and Resolution"""
        if not self.root:
            return
        if resolution := self.root.get(XML_ATTR_MELODY_RESOLUTION, None):
            self.resolution = Resolution.from_string(resolution)
        if tempo := self.root.get(XML_ATTR_MELODY_TEMPO, None):
            self.raw_tempo = float(tempo)
        if not self.resolution or not self.raw_tempo:
            logger.logger.error("Song tempo could not be determined, skipping.")
            return
        adjusted_tempo = self.raw_tempo * self.resolution.value
        self.bpm = BeatsPerMinute(adjusted_tempo)

    def parse_duet_singer_names(self) -> None:
        """Parses duet singer names (from TRACK elements)"""
        if not self.is_duet or not self.root:
            return

        singers: list[str] = []
        for track in self.root.findall(
            f".//{self.ns_prefix}{XML_ELEM_TRACK}", namespaces=self.ns_map
        ):
            artist_name = track.get(XML_ATTR_TRACK_ARTIST)
            if artist_name:
                singers.append(artist_name)
            else:
                logger.logger.warning(
                    "Duet track found with missing 'Artist' attribute."
                )
        if len(singers) >= 1:
            self.p1_name = singers[0]
        if len(singers) >= 2:
            self.p2_name = singers[1]
        if len(singers) == 0:
            logger.logger.warning("Duet flag is set, but no track artist names found.")
            self.is_duet = False
        elif len(singers) == 1:
            logger.logger.warning(
                "Duet flag is set, but only one track artist name found."
            )

    def parse_artist_title(self) -> None:
        """Artist/Title from Comments (using regex on raw text)"""
        artist_regex = r"<!--\s*Artist:\s*(.*?)\s*-->"
        title_regex = r"<!--\s*Title:\s*(.*?)\s*-->"
        artist_match = re.search(artist_regex, self.text, re.IGNORECASE)
        title_match = re.search(title_regex, self.text, re.IGNORECASE)
        self.artist = (
            _insert_missing_spaces(
                replace_false_apostrophes(
                    artist_match.group(1)
                    .strip()
                    .replace("&amp", "&")
                    .replace(" Ft ", " feat. ")
                    .replace(" Feat ", " feat. ")
                )
            )
            if artist_match
            else DEFAULT_ARTIST
        )
        self.title = (
            _insert_missing_spaces(
                replace_false_apostrophes(
                    title_match.group(1).strip().replace("&amp", "&")
                )
            )
            if title_match
            else DEFAULT_TITLE
        )

    def _extract_tracks(self) -> Tracks:
        """Extracts note data for P1 and P2 tracks using lxml"""
        if self.root is None:
            logger.logger.error("Cannot extract tracks, XML root is not parsed.")
            return Tracks([], [])

        p1_lines: list[Line] = []
        p2_lines: list[Line] = []
        tracks = Tracks([], [])

        match self.version:
            case XMLVersion.V1:
                # Version 1: <SENTENCE> elements directly under <MELODY>
                logger.logger.info(
                    f"XML Version {self.version}. "
                    "Processing SENTENCE elements directly under MELODY "
                )
                p1_lines, p2_lines = self._parse_sentences_v1(self.root)
            case XMLVersion.V2 | XMLVersion.V4:
                # Version 2/4: <SENTENCE> elements under each <TRACK> element
                logger.logger.info(
                    f"XML Version {self.version}. "
                    "Processing TRACK-based SENTENCE elements "
                )
                track_elements = self.root.findall(
                    f".//{self.ns_prefix}{XML_ELEM_TRACK}", namespaces=self.ns_map
                )
                p1_lines, p2_lines = self._parse_sentences_v2_v4(track_elements)
            case _ as unreachable:
                assert unreachable

        tracks.track_1 = p1_lines
        tracks.track_2 = p2_lines

        for line in tracks.track_1 + tracks.track_2:
            fix_tilde_spacing(line.notes)

        return tracks

    def _remove_last_linebreak(self, lines: list[Line]) -> None:
        for line in reversed(lines):
            if line.notes:
                line.line_break = None
                break

    def _parse_sentences_v1(
        self, parent: etree._Element
    ) -> tuple[list[Line], list[Line]]:
        """Parses v1 SENTENCE elements and distributes them to P1 and P2"""
        track_1: list[Line] = []
        track_2: list[Line] = []
        current_singer = "Solo 1"
        current_beat = 0

        sentence_elements = parent.findall(
            f"./{self.ns_prefix}{XML_ELEM_SENTENCE}", namespaces=self.ns_map
        )
        for sentence in sentence_elements:
            singer = sentence.get("Singer", current_singer)
            current_singer = singer  # carry forward default if missing next time

            line, current_beat = self._parse_sentence_to_line(sentence, current_beat)
            if not line.notes:
                continue

            _add_space_to_last_tilde(line.notes)
            _split_lyrics_to_tildes(line.notes)

            if self.is_duet:
                match singer:
                    case "Solo 2":
                        track_2.append(line)
                    case "Group":
                        track_1.append(line)
                        track_2.append(line)
                    case _:
                        track_1.append(line)
            else:
                track_1.append(line)

        self._remove_last_linebreak(track_1)
        self._remove_last_linebreak(track_2)

        return track_1, track_2

    def _parse_sentences_v2_v4(
        self, track_elements: list[etree._Element]
    ) -> tuple[list[Line], list[Line]]:
        """Parses v2 SENTENCE elements and distributes them to P1 and P2"""
        track_1: list[Line] = []
        track_2: list[Line] = []
        current_singer = "Solo 1"

        for idx, track_element in enumerate(track_elements):
            current_beat = 0
            sentence_elements = track_element.findall(
                f"./{self.ns_prefix}{XML_ELEM_SENTENCE}", namespaces=self.ns_map
            )
            for sentence in sentence_elements:
                singer = sentence.get("Singer", current_singer)
                current_singer = singer  # carry forward default if missing next time

                line, current_beat = self._parse_sentence_to_line(
                    sentence, current_beat
                )
                if not line.notes:
                    continue

                _add_space_to_last_tilde(line.notes)
                # experimental
                _split_lyrics_to_tildes(line.notes)

                if idx == 0:
                    track_1.append(line)
                else:
                    track_2.append(line)

        self._remove_last_linebreak(track_1)
        self._remove_last_linebreak(track_2)

        return track_1, track_2

    def _parse_sentence_to_line(
        self, sentence: etree._Element, start_beat: int
    ) -> tuple[Line, int]:
        line = Line(notes=[], line_break=None)
        current_beat = start_beat

        for note_elem in sentence.findall(
            f"./{self.ns_prefix}{XML_ELEM_NOTE}", namespaces=self.ns_map
        ):
            try:
                # Detect medley markers
                self.extract_medley_markers(current_beat, note_elem)

                pitch = int(note_elem.get(XML_ATTR_NOTE_MIDI_NOTE, "0"))
                duration = int(note_elem.get(XML_ATTR_NOTE_DURATION, "0"))
                if duration <= 0:
                    continue

                if pitch <= 0:
                    current_beat += duration
                    continue

                lyric = _fix_lyric_string(note_elem.get(XML_ATTR_NOTE_LYRIC, ""))

                if not lyric.strip() and not _parse_bool_attribute(
                    note_elem.get(XML_ATTR_NOTE_FREESTYLE)
                ):
                    current_beat += duration
                    continue

                kind = self.get_note_kind(note_elem)

                note = Note(
                    kind=kind,
                    start=current_beat,
                    duration=duration,
                    pitch=pitch,
                    text=lyric,
                )
                line.notes.append(note)
                current_beat += duration

            except (ValueError, KeyError) as e:
                logger.logger.warning(
                    f"Skipping invalid note at beat {current_beat}: {e}"
                )
                try:
                    current_beat += int(note_elem.get(XML_ATTR_NOTE_DURATION, "0"))
                except Exception:  # noqa: BLE001
                    logger.logger.exception(
                        "Failed to parse note duration, timing might be off"
                    )

        if line.notes:
            if not line.notes[-1].text.endswith(" "):
                line.notes[-1].text += " "
            line.line_break = LineBreak(
                previous_line_out_time=current_beat, next_line_in_time=None
            )

        return line, current_beat

    def get_note_kind(self, note_elem: etree._Element) -> NoteKind:
        is_golden = _parse_bool_attribute(note_elem.get(XML_ATTR_NOTE_BONUS, False))
        is_rap = _parse_bool_attribute(note_elem.get(XML_ATTR_NOTE_RAP, False))
        is_freestyle = _parse_bool_attribute(
            note_elem.get(XML_ATTR_NOTE_FREESTYLE, False)
        )

        kind = NoteKind.REGULAR
        if is_freestyle and not is_rap:
            kind = NoteKind.FREESTYLE
        elif is_rap:
            kind = NoteKind.GOLDEN_RAP if is_golden else NoteKind.RAP
        elif is_golden:
            kind = NoteKind.GOLDEN
        return kind

    def extract_medley_markers(
        self, current_beat: int, note_elem: etree._Element
    ) -> None:
        for marker in note_elem.findall(
            f"./{self.ns_prefix}{XML_ELEM_NOTE_MARKER}", namespaces=self.ns_map
        ):
            match marker.get("Type"):
                case "MedleyNormalBegin":
                    self.medley_start = current_beat
                case "MedleyNormalEnd":
                    self.medley_end = current_beat

    def convert_to_songtxt(self) -> SongTxt | None:
        """Orchestrates the conversion process and returns a SongTxt object."""
        logger.logger.info(f"Starting conversion for: {self.input_path.name}")

        if not self._read_and_parse_xml():
            return None

        self._extract_metadata()
        extracted_tracks = self._extract_tracks()
        print(
            extracted_tracks.track_1[4].notes[-1].start,
            extracted_tracks.track_1[4].notes[-1].text,
        )

        mp3_filename = f"{self.artist} - {self.title}.mp4"
        cover_filename = f"{self.artist} - {self.title} [CO].jpg"
        background_filename = f"{self.artist} - {self.title} [BG].jpg"
        if self.is_duet:
            self.title += " [DUET]"
            self.edition += ", [DUET]-Songs"

        headers = Headers(
            unknown={},
            title=self.title,
            artist=self.artist,
            bpm=self.bpm,
            gap=self.gap,
            language=self.language,
            edition=self.edition,
            genre=self.genre,
            year=self.year,
            creator=get_logged_in_usdb_user(SessionManager.session()),
            mp3=mp3_filename,
            cover=cover_filename,
            background=background_filename,
            medleystartbeat=self.medley_start
            if self.medley_start and self.medley_end
            else None,
            medleyendbeat=self.medley_end
            if self.medley_end and self.medley_start
            else None,
            p1=self.p1_name if self.is_duet and self.p1_name else None,
            p2=self.p2_name if self.is_duet and self.p2_name else None,
        )

        song_txt = SongTxt(
            headers=headers,
            notes=extracted_tracks,
            meta_tags=MetaTags(),
            logger=logger.logger,
        )

        if language := self.detect_language(song_txt):
            logger.logger.info(f"Detected language: {language}")
            song_txt.headers.language = language

        song_txt.fix_first_timestamp()
        song_txt.fix_low_bpm()
        song_txt.notes.fix_overlapping_and_touching_notes(logger.logger)
        song_txt.notes.fix_pitch_values(logger.logger)
        song_txt.notes.fix_apostrophes(logger.logger)
        song_txt.headers.fix_apostrophes(logger.logger)
        song_txt.notes.fix_linebreaks_yass_style(song_txt.headers.bpm, logger.logger)
        song_txt.notes.fix_first_words_capitalization(logger.logger)
        if language:
            song_txt.notes.fix_quotation_marks(language, logger.logger)

        metatags = []
        if self.medley_start and self.medley_end:
            metatags.append(
                f"medley={song_txt.headers.medleystartbeat}-{song_txt.headers.medleyendbeat}"
            )
        if self.p1_name and self.p2_name:
            metatags.append(f"p1={self.p1_name}")
            metatags.append(f"p2={self.p2_name}")

        song_txt.headers.video = ",".join(metatags) if metatags else None

        logger.logger.info(f"Conversion successful for: {self.input_path.name}")
        return song_txt

    def detect_language(self, song_txt: SongTxt) -> str | None:
        lyrics = song_txt.unsynchronized_lyrics()
        is_reliable, _, details = cld2.detect(lyrics)
        if is_reliable:
            return details[0][0].capitalize()
        else:
            return None


hooks.MainWindowDidLoad.subscribe(on_window_loaded)
