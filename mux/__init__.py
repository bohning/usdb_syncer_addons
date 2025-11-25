"""Muxing add-on - Combines separate audio and video files into a single video file."""

import subprocess
from pathlib import Path

from usdb_syncer import hooks, settings, usdb_song, utils
from usdb_syncer.logger import Logger, song_logger
from usdb_syncer.song_txt import SongTxt


def on_download_finished(song: usdb_song.UsdbSong) -> None:
    """Automatically mux audio and video after download completes."""
    if not can_mux(song):
        return

    log = song_logger(song.song_id)
    log.info("Detected audio and video from same source, starting automatic muxing...")

    try:
        mux_song(song)
    except (subprocess.SubprocessError, OSError, ValueError):
        log.exception("Failed to mux audio and video")


def can_mux(song: usdb_song.UsdbSong) -> bool:
    """Check if song has both audio and video files from the same resource to mux."""
    if not (sync_meta := song.sync_meta):
        return False

    audio = sync_meta.audio
    video = sync_meta.video

    # Check that both exist, have files, and share the same resource URL
    if not (audio and audio.file and video and video.file):
        return False

    audio_path = sync_meta.audio_path()
    video_path = sync_meta.video_path()

    if not (audio_path and audio_path.exists() and video_path and video_path.exists()):
        return False

    # Only mux if they share the same resource URL
    return audio.file.resource == video.file.resource


def mux_song(song: usdb_song.UsdbSong) -> None:
    """Mux audio and video files for a single song."""
    log = song_logger(song.song_id)

    if not (sync_meta := song.sync_meta):
        log.error("Song has no sync metadata")
        return

    audio_path = sync_meta.audio_path()
    video_path = sync_meta.video_path()
    txt_path = sync_meta.txt_path()

    if not audio_path or not video_path or not txt_path:
        log.error("Missing required files for muxing")
        return

    if not utils.ffmpeg_is_available():
        log.error("ffmpeg is not available. Please install ffmpeg to use muxing.")
        return

    temp_output = (
        video_path.parent / f"{video_path.stem}_muxing_temp{video_path.suffix}"
    )

    if not _run_ffmpeg_mux(audio_path, video_path, temp_output, log):
        return

    if not _replace_video_with_muxed(video_path, temp_output, log):
        return

    if not _update_txt_headers(txt_path, video_path, log):
        return

    _cleanup_audio_file(audio_path, log)
    log.info("Automatic muxing complete!")


def _run_ffmpeg_mux(
    audio_path: Path, video_path: Path, output_path: Path, log: Logger
) -> bool:
    """Run ffmpeg to mux audio and video. Returns True on success."""
    log.info(f"Muxing {audio_path.name} + {video_path.name} → {video_path.name}")

    cmd = [
        "ffmpeg",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-shortest",
        "-y",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        log.info("Muxing completed successfully")
        return output_path.exists()
    except subprocess.TimeoutExpired:
        log.exception("Muxing timed out after 5 minutes")
        return False
    except subprocess.CalledProcessError:
        log.exception("FFmpeg failed to mux files")
        return False
    except FileNotFoundError:
        log.exception("File(s) not found")
        return False


def _replace_video_with_muxed(video_path: Path, temp_output: Path, log: Logger) -> bool:
    """Replace original video with muxed version. Returns True on success."""
    try:
        utils.trash_or_delete_path(video_path)
        temp_output.rename(video_path)
    except OSError:
        log.exception("Failed to replace video file with muxed version")
        if temp_output.exists():
            utils.trash_or_delete_path(temp_output)
        return False
    else:
        log.info(f"Replaced {video_path.name} with muxed version")
        return True


def _update_txt_headers(txt_path: Path, video_path: Path, log: Logger) -> bool:
    """Update txt file headers to reference muxed video. Returns True on success."""
    try:
        if not (txt := SongTxt.try_from_file(txt_path, log)):
            log.error("Unable to update txt.")
            return False

        txt.headers.mp3 = video_path.name
        txt.headers.audio = video_path.name
        txt.headers.video = video_path.name

        encoding = settings.get_encoding()
        newline = settings.get_newline()
        txt.write_to_file(txt_path, encoding.value, newline.value)
    except OSError:
        log.exception("Failed to update txt file")
        return False
    else:
        log.info(f"Updated {txt_path.name} to reference muxed video file")
        return True


def _cleanup_audio_file(audio_path: Path, log: Logger) -> None:
    """Delete the separate audio file."""
    try:
        utils.trash_or_delete_path(audio_path)
        log.info("Deleted separate audio file")
    except OSError:
        log.exception("Could not delete audio file")


# Register the addon to run after each download
hooks.SongLoaderDidFinish.subscribe(on_download_finished)
