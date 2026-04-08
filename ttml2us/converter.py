"""Apple Music TTML converter add-on."""

import re

from defusedxml import ElementTree

from usdb_syncer.logger import logger
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.settings import FormatVersion
from usdb_syncer.song_txt.auxiliaries import BeatsPerMinute
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.song_txt.song_txt import SongTxt
from usdb_syncer.song_txt.tracks import Line, LineBreak, Note, NoteKind, Tracks


def _convert_ttml_to_song(ttml_content: str, bpm: BeatsPerMinute) -> SongTxt:
    """Convert TTML content to UltraStar SongTxt format."""

    # Helper to convert TTML time format (MM:SS.mmm) to milliseconds
    def ttml_time_to_ms(time_str: str) -> int:
        """Convert TTML time format MM:SS.mmm or SS.mmm to milliseconds."""
        match = re.match(r"(?:(\d+):)?(\d+)\.(\d+)", time_str)
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")
        minutes_str, seconds, millis = match.groups()
        minutes = int(minutes_str) if minutes_str else 0
        return minutes * 60 * 1000 + int(seconds) * 1000 + int(millis)

    logger.info("Converting TTML content to UltraStar TXT format...")

    try:
        root = ElementTree.fromstring(ttml_content)
    except ElementTree.ParseError as e:
        logger.error(f"Failed to parse TTML XML: {e}")
        raise

    # Define namespaces
    namespaces = {
        "ttml": "http://www.w3.org/ns/ttml",
        "itunes": "http://music.apple.com/lyric-ttml-internal",
        "ttm": "http://www.w3.org/ns/ttml#metadata",
        "amll": "http://www.example.com/ns/amll",
    }

    # Extract artist from metadata
    artist = "Unknown Artist"
    agent = root.find(".//ttm:agent/ttm:name", namespaces)
    if agent is not None and agent.text:
        artist = agent.text.strip()

    # Extract title from metadata
    title = "Unknown Title"
    title_element = root.find(".//ttm:title", namespaces)
    if title_element is not None and title_element.text:
        title = title_element.text.strip()

    # Extract language(s) from metadata (if available)
    language_elements = root.findall(".//amll:meta[@key='language']", namespaces)
    languages = []
    if language_elements:
        languages = [
            val for lang in language_elements if (val := lang.get("value")) is not None
        ]
    else:
        language = root.get("{http://www.w3.org/XML/1998/namespace}lang")
        if not language:
            language = root.get("xml:lang")
        if not language:
            language = root.get("lang")
        languages = [language] if language else []

    # Extract genre(s) from metadata (if available)
    genre_elements = root.findall(".//amll:meta[@key='genre']", namespaces)
    genres = [
        val
        for genre_element in genre_elements
        if (val := genre_element.get("value")) is not None
    ]

    # Extract year from metadata (if available)
    year = None
    year_element = root.find(".//amll:meta[@key='year']", namespaces)

    if year_element is not None:
        year = year_element.get("value")

    # Extract creator from metadata (if available)
    creator = None
    creator_element = root.find(".//amll:meta[@key='creator']", namespaces)
    if creator_element is not None:
        creator = creator_element.get("value")

    # Extract gap (leadingSilence in milliseconds)
    gap_ms = 0
    itunes_metadata = root.find(".//itunes:iTunesMetadata", namespaces)
    if itunes_metadata is not None:
        leading_silence = itunes_metadata.get("leadingSilence")
        if leading_silence:
            gap_ms = ttml_time_to_ms(leading_silence)

    # Parse spans (syllables) from paragraphs
    lines_list = []
    paragraphs = root.findall(".//ttml:p", namespaces)
    all_notes_with_breaks = []
    min_start_beat = None

    for p_idx, paragraph in enumerate(paragraphs):
        spans = paragraph.findall(".//ttml:span", namespaces)
        notes = []
        last_end_ms = 0

        for span in spans:
            begin_str = span.get("begin")
            end_str = span.get("end")
            text = "".join(span.itertext()).strip() or "~"

            if begin_str and end_str:
                begin_ms = ttml_time_to_ms(begin_str)
                end_ms = ttml_time_to_ms(end_str)
                last_end_ms = end_ms

                start_beat = bpm.secs_to_beats(begin_ms / 1000)

                # Track minimum start beat for normalization
                if min_start_beat is None or start_beat < min_start_beat:
                    min_start_beat = start_beat

                duration_beat = max(1, bpm.secs_to_beats(end_ms / 1000) - start_beat)

                note = Note(
                    kind=NoteKind.REGULAR,
                    start=start_beat,
                    duration=duration_beat,
                    pitch=0,
                    text=text,
                )
                notes.append(note)

        # Store paragraph data for later processing
        if notes:
            line_break_beat = (
                bpm.secs_to_beats(last_end_ms / 1000) if last_end_ms > 0 else 0
            )
            all_notes_with_breaks.append(
                (p_idx, notes, line_break_beat, len(paragraphs))
            )

    # Normalize all beats to start at 0
    if min_start_beat is None:
        min_start_beat = 0

    for p_idx, notes, line_break_beat, total_paragraphs in all_notes_with_breaks:
        # Adjust note timings
        for note in notes:
            note.start -= min_start_beat

        # Adjust line break timing
        line_break = None
        if p_idx < total_paragraphs - 1:
            # Not the last paragraph, add a line break
            adjusted_line_break_beat = line_break_beat - min_start_beat
            line_break = LineBreak(
                previous_line_out_time=adjusted_line_break_beat, next_line_in_time=None
            )

        line = Line(notes=notes, line_break=line_break)
        lines_list.append(line)

    tracks = Tracks(track_1=lines_list, track_2=None)

    return SongTxt(
        headers=Headers(
            unknown={},
            title=title,
            artist=artist,
            bpm=bpm,
            gap=gap_ms,
            version=FormatVersion.V1_2_0.value,
            language=", ".join(languages) if languages else None,
            genre=", ".join(genres) if genres else None,
            year=year,
            creator=creator,
            audio=f"{artist} - {title}.m4a",
            cover=f"{artist} - {title} [CO].jpg",
            providedby="USDB Syncer TTML Converter Add-on",
        ),
        notes=tracks,
        meta_tags=MetaTags(),
        logger=logger,
    )
