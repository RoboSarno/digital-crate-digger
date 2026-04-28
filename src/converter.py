import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Callable

from .utils import get_logger


class YouTubeToMP3Converter:
    """Wraps yt-dlp to download audio as MP3. Tries multiple auth strategies for YouTube."""

    def __init__(
        self,
        output_directory: str = "./output/mp3",
        log_directory: str = "./logs",
        delay_between_downloads: int = 10,
        cookies_from_browser: Optional[str] = None,
        use_oauth: bool = False,
        cookies_file: Optional[str] = None,
    ):
        self.output_directory = Path(output_directory)
        self.delay_between_downloads = delay_between_downloads
        self.cookies_from_browser = cookies_from_browser
        self.use_oauth = use_oauth
        self.cookies_file = cookies_file
        self.logger = get_logger("converter", log_dir=log_directory)

        self.output_directory.mkdir(parents=True, exist_ok=True)

    def _detect_platform(self, url: str) -> str:
        url_lower = url.lower()
        if "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "youtube"
        elif "soundcloud.com" in url_lower:
            return "soundcloud"
        return "other"

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        return re.sub(r'[/\\:<>"|?*]', '-', name).strip(". ")

    def download_audio(self, url: str, filename: str, ffmpeg_location: Optional[str] = None) -> bool:
        """Download a single URL as MP3, cycling through auth strategies until one works."""
        filename = self._sanitize_filename(filename)
        output_path = self.output_directory / f"{filename}.mp3"
        platform = self._detect_platform(url)
        self.logger.info(f"Detected platform: {platform}")

        strategies = self._build_strategies(platform)
        last_error = None

        for strategy_name, extra_args in strategies:
            command = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--output", str(output_path),
                *extra_args,
            ]
            if ffmpeg_location:
                command.extend(["--ffmpeg-location", ffmpeg_location])
            command.append(url)

            try:
                self.logger.info(f"Trying strategy: {strategy_name}")
                subprocess.run(command, check=True, capture_output=True, text=True)
                self.logger.info(f"Downloaded successfully via {strategy_name}")
                return True
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"{strategy_name} failed: {e}")
                if e.stderr:
                    last_error = e.stderr
                    self._log_error_hints(e.stderr)

        self.logger.error(f"All strategies failed for {filename}")
        if last_error:
            self.logger.error(f"Last error:\n{last_error}")
        return False

    def _build_strategies(self, platform: str) -> list:
        if platform == "soundcloud":
            return [("soundcloud direct", [])]

        if platform != "youtube":
            return [("default", [])]

        # YouTube: try authenticated methods first, fall back to unauthenticated
        strategies = []
        if self.use_oauth:
            strategies.append(("oauth login", ["--username", "oauth2", "--password", ""]))
        if self.cookies_file:
            strategies.append(("cookies file", ["--cookies", self.cookies_file]))
        if self.cookies_from_browser:
            strategies.append(("ios with cookies", [
                "--cookies-from-browser", self.cookies_from_browser,
                "--extractor-args", "youtube:player_client=ios",
            ]))
            strategies.append(("web with cookies", [
                "--cookies-from-browser", self.cookies_from_browser,
                "--extractor-args", "youtube:player_client=web",
            ]))
        strategies.append(("android", ["--extractor-args", "youtube:player_client=android"]))
        strategies.append(("default", []))
        return strategies

    def _log_error_hints(self, stderr: str):
        stderr_lower = stderr.lower()
        if "age" in stderr_lower and "restrict" in stderr_lower:
            self.logger.warning("AGE RESTRICTION detected")
        elif "not available" in stderr_lower:
            self.logger.warning("CONTENT NOT AVAILABLE")
        elif "copyright" in stderr_lower:
            self.logger.warning("COPYRIGHT RESTRICTION detected")
        elif "private" in stderr_lower:
            self.logger.warning("PRIVATE VIDEO detected")
        elif "sign in" in stderr_lower:
            self.logger.warning("AUTHENTICATION REQUIRED")

    def convert_songs(
        self,
        songs: Dict[str, str],
        progress_callback=None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, bool]:
        """Download all songs in the dict. Returns {name: True/False} for each."""
        results = {}
        total = len(songs)

        self.logger.info(f"Starting batch download of {total} song(s)")

        for i, (song_name, url) in enumerate(songs.items(), 1):
            if not url or not url.strip():
                self.logger.warning(f"Skipping {song_name}: no URL")
                results[song_name] = False
                continue

            if progress_callback:
                progress_callback(i, total, song_name)

            msg = f"[{i}/{total}] Downloading: {song_name}"
            self.logger.info(msg)
            if status_callback:
                status_callback(msg)

            success = self.download_audio(url, song_name)
            results[song_name] = success

            if not success:
                fail_msg = f"[{i}/{total}] Failed: {song_name}"
                self.logger.warning(fail_msg)
                if status_callback:
                    status_callback(fail_msg)

            # Only rate-limit YouTube requests
            if i < total and self.delay_between_downloads > 0:
                if self._detect_platform(url) == "youtube":
                    self.logger.info(f"Waiting {self.delay_between_downloads}s for rate limit")
                    if status_callback:
                        status_callback(f"Waiting {self.delay_between_downloads}s (YouTube rate limit)...")
                    time.sleep(self.delay_between_downloads)

        successful = sum(1 for s in results.values() if s)
        self.logger.info(f"Finished: {successful}/{total} downloaded successfully")
        return results
