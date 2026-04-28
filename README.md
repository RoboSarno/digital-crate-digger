# Digital Crate Digger

Pull audio from YouTube/SoundCloud and split it into stems (vocals, drums, bass, other) using Demucs. Built for sampling workflows — find a track, isolate what you want, load it onto a sampler.

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
streamlit run app.py
```

Four pages: **Download**, **Stem Separation**, **Output**, **Logs**

### Batch downloads

You can preload URLs from a `test.json` file using the button on the download page:
```json
{
    "Song Name": "https://www.youtube.com/watch?v=...",
    "Another Song": "https://soundcloud.com/artist/track"
}
```

### Auth

Most YouTube videos work without auth. For age-restricted stuff, try browser cookies or OAuth from the download page.

### Models

`htdemucs` is the default and fastest. `htdemucs_ft` is a step up. The `mdx` models sound better but are slower and need `diffq` installed.

## License

For personal use only. Don't redistribute downloaded or separated audio.
