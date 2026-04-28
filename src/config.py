from pathlib import Path

# directories
OUTPUT_DIR = Path("./output")
MP3_DIR = OUTPUT_DIR / "mp3"
STEMS_DIR = OUTPUT_DIR / "stems"
LOGS_DIR = Path("./logs")
JSON_PATH = Path("./test.json")

# audio formats to scan for
AUDIO_EXTENSIONS = ["*.mp3", "*.wav", "*.flac", "*.m4a"]

# UI strings
APP_TITLE = "DIGITAL CRATE DIGGER"
APP_SUBTITLE = "download // separate // sample"

PAGE_DESCRIPTIONS = {
    "download": "Paste one URL per line, or use the format `Song Name | URL` for custom filenames.",
    "separate": "Pick a model below. Higher quality = longer processing.",
    "output": "Browse and play downloaded MP3s and separated stems.",
}

AUTH_OPTIONS = ["None", "Cookies File", "Browser Cookies", "OAuth"]
DEVICE_OPTIONS = ["Auto", "cpu", "mps", "cuda"]
