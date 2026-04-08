"""Apple Music TTML converter add-on."""

import re
from pathlib import Path

from defusedxml import ElementTree

from usdb_syncer.logger import logger
from usdb_syncer.meta_tags import MetaTags
from usdb_syncer.settings import FormatVersion
from usdb_syncer.song_txt.auxiliaries import BeatsPerMinute
from usdb_syncer.song_txt.headers import Headers
from usdb_syncer.song_txt.song_txt import SongTxt
from usdb_syncer.song_txt.tracks import Line, LineBreak, Note, NoteKind, Tracks


def _convert_ttml_to_song(
    ttml_file: Path, ttml_content: str, bpm: BeatsPerMinute
) -> SongTxt | None:
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

    logger.info(f"Converting {ttml_file} to UltraStar TXT format...")

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
    else:
        artist_element = root.find(".//amll:meta[@key='artists']", namespaces)
        if artist_element is not None and (artist_value := artist_element.get("value")):
            artist = artist_value.strip()

    # Extract title from metadata
    title = "Unknown Title"
    title_element = root.find(".//ttm:title", namespaces)
    if title_element is not None and title_element.text:
        title = title_element.text.strip()
    else:
        title_element = root.find(".//amll:meta[@key='musicName']", namespaces)
        if title_element is not None and (title_value := title_element.get("value")):
            title = title_value.strip()

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

    # Extract gap (span > p > div > itunes:iTunesMetadata leadingSilence)
    gap_ms = 0
    if (first_span := root.find(".//{*}span", namespaces)) is not None:
        begin_str = first_span.get("begin")
        if begin_str:
            gap_ms = ttml_time_to_ms(begin_str)
    elif (first_p := root.find(".//{*}p", namespaces)) is not None:
        begin_str = first_p.get("begin")
        if begin_str:
            gap_ms = ttml_time_to_ms(begin_str)
    elif (div_element := root.find(".//{*}div", namespaces)) is not None:
        begin_str = div_element.get("begin")
        if begin_str:
            gap_ms = ttml_time_to_ms(begin_str)
    else:
        itunes_metadata = root.find(".//itunes:iTunesMetadata", namespaces)
        if itunes_metadata is not None:
            leading_silence = itunes_metadata.get("leadingSilence")
            if leading_silence:
                gap_ms = ttml_time_to_ms(leading_silence)

    first_beat_offset = bpm.secs_to_beats(gap_ms / 1000)

    # Parse spans (syllables) from paragraphs
    lines = []
    paragraphs = root.findall(".//{*}p")

    for paragraph in paragraphs:
        spans = paragraph.findall(".//{*}span")
        notes = []

        for i, span in enumerate(spans):
            begin_str = span.get("begin")
            end_str = span.get("end")
            tail = span.tail or "" if i < len(spans) - 1 else ""
            text = "".join(span.itertext()).strip() + tail or "~"

            if begin_str and end_str:
                begin_ms = ttml_time_to_ms(begin_str)
                end_ms = ttml_time_to_ms(end_str)

                start_beat = bpm.secs_to_beats(begin_ms / 1000)

                duration_beat = max(1, bpm.secs_to_beats(end_ms / 1000) - start_beat)

                note = Note(
                    kind=NoteKind.REGULAR,
                    start=start_beat - first_beat_offset,
                    duration=duration_beat,
                    pitch=0,
                    text=text,
                )
                notes.append(note)

        if len(notes) == 0:
            continue
        line_break = LineBreak(
            previous_line_out_time=notes[-1].start + notes[-1].duration,
            next_line_in_time=None,
        )

        line = Line(notes=notes, line_break=line_break)
        lines.append(line)

    if len(lines) == 0:
        return None

    lines[-1].line_break = None
    tracks = Tracks(track_1=lines, track_2=None)

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
            providedby="USDB Syncer ttml2us Converter Add-on",
        ),
        notes=tracks,
        meta_tags=MetaTags(),
        logger=logger,
    )
