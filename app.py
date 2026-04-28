import json
import streamlit as st
from pathlib import Path

from src.converter import YouTubeToMP3Converter
from src.separator import AudioStemSeparator, AVAILABLE_MODELS
from streamlit_advanced_audio import audix, WaveSurferOptions
from src.config import (
    MP3_DIR, STEMS_DIR, LOGS_DIR, JSON_PATH, AUDIO_EXTENSIONS,
    APP_TITLE, APP_SUBTITLE, PAGE_DESCRIPTIONS, AUTH_OPTIONS, DEVICE_OPTIONS,
)

WAVE_OPTS = WaveSurferOptions(
    wave_color="#333",
    progress_color="#ccc",
    cursor_color="#666",
    height=50,
)
STEM_WAVE_OPTS = WaveSurferOptions(
    wave_color="#222",
    progress_color="#999",
    cursor_color="#555",
    height=40,
)

st.set_page_config(page_title="Digital Crate Digger", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Mono', monospace;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }

    /* sidebar */
    [data-testid="stSidebar"] {
        border-right: 1px solid #222;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.1rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #e0e0e0;
    }
    [data-testid="stSidebar"] .stCaption {
        letter-spacing: 0.08em;
        color: #555;
    }

    /* headers */
    h1, h2, h3 {
        font-family: 'IBM Plex Mono', monospace;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #e0e0e0;
    }
    h2 { font-size: 1.1rem; }

    /* muted descriptions */
    .page-desc {
        color: #555;
        font-size: 0.8rem;
        letter-spacing: 0.04em;
        margin-bottom: 1.5rem;
    }

    /* buttons */
    .stButton > button,
    .stFormSubmitButton > button {
        background-color: #1a1a1a;
        color: #ccc;
        border: 1px solid #333;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }
    .stButton > button:hover,
    .stFormSubmitButton > button:hover {
        background-color: #222;
        border-color: #555;
        color: #fff;
    }

    /* inputs */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        background-color: #0e0e0e;
        border: 1px solid #222;
        color: #ccc;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* metrics */
    [data-testid="stMetricValue"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.8rem;
        color: #e0e0e0;
    }
    [data-testid="stMetricLabel"] {
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #555;
    }

    /* expanders */
    [data-testid="stExpander"] {
        border: 1px solid #1a1a1a;
        border-radius: 0px;
    }

    /* tabs */
    .stTabs [data-baseweb="tab"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    /* alerts */
    [data-testid="stAlert"] {
        border-radius: 0px;
        font-size: 0.82rem;
    }
    /* info alerts — hacker green */
    [data-testid="stAlert"][data-baseweb*="notification"] .st-emotion-cache-1vt4y43,
    [data-testid="stAlert"] [data-testid="stAlertContentInfo"] {
        color: #00ff41;
    }
    div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) {
        background-color: #0a0a0a;
        border: 1px solid #0f3d0f;
        color: #00ff41;
    }
    div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) p,
    div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) span {
        color: #00ff41;
    }
    div[data-testid="stAlert"]:has(svg[data-testid="stIconInfo"]) svg {
        fill: #00ff41;
    }

    /* dividers */
    hr {
        border-color: #1a1a1a;
    }

    /* audio player */
    audio {
        width: 100%;
        filter: grayscale(100%) brightness(0.8);
    }

    /* progress bar */
    .stProgress > div > div {
        background-color: #1a1a1a;
    }
    .stProgress > div > div > div {
        background-color: #00ff41;
    }

    /* radio buttons / checkboxes */
    .stRadio label, .stCheckbox label, .stMultiSelect label {
        font-size: 0.82rem;
    }
</style>
""", unsafe_allow_html=True)


def download_page():
    st.header("Download")
    st.markdown(f'<p class="page-desc">{PAGE_DESCRIPTIONS["download"]}</p>', unsafe_allow_html=True)

    default_text = ""
    if JSON_PATH.exists():
        if st.button("Load from test.json"):
            data = json.loads(JSON_PATH.read_text())
            default_text = "\n".join(f"{name} | {url}" for name, url in data.items())
            st.session_state["url_input"] = default_text

    with st.form("download_form"):
        url_input = st.text_area(
            "URLs",
            height=150,
            value=st.session_state.get("url_input", default_text),
            placeholder="https://www.youtube.com/watch?v=...\nMy Song | https://soundcloud.com/artist/track",
        )

        col1, col2 = st.columns(2)
        with col1:
            delay = st.number_input(
                "Delay between downloads (sec)",
                min_value=0, max_value=60, value=10,
                help="Only applies to YouTube. Helps avoid rate limiting.",
            )
        with col2:
            auth_method = st.selectbox(
                "Authentication",
                AUTH_OPTIONS,
                help="Only needed for age-restricted YouTube videos.",
            )

        cookies_file = None
        cookies_browser = None
        use_oauth = False

        if auth_method == "Cookies File":
            cookies_file = st.text_input("Path to cookies.txt")
        elif auth_method == "Browser Cookies":
            cookies_browser = st.text_input("Browser name (e.g., chrome, firefox, safari)")
        elif auth_method == "OAuth":
            use_oauth = True

        submitted = st.form_submit_button("Start Download", type="primary")

    if submitted and url_input.strip():
        lines = [line.strip() for line in url_input.strip().splitlines() if line.strip()]

        songs = {}
        for line in lines:
            if "|" in line:
                name, url = line.split("|", 1)
                songs[name.strip()] = url.strip()
            else:
                songs[f"track_{len(songs) + 1}"] = line

        converter = YouTubeToMP3Converter(
            output_directory=str(MP3_DIR),
            log_directory=str(LOGS_DIR),
            delay_between_downloads=delay,
            cookies_from_browser=cookies_browser,
            use_oauth=use_oauth,
            cookies_file=cookies_file,
        )

        progress_bar = st.progress(0, text="Starting...")
        status_text = st.empty()
        status_lines = []

        def on_progress(current, total, song_name):
            progress_bar.progress(current / total, text=f"{current}/{total}: {song_name}")

        def on_status(msg):
            status_lines.append(msg)
            status_text.text(msg)

        results = converter.convert_songs(
            songs, progress_callback=on_progress, status_callback=on_status,
        )

        progress_bar.progress(1.0, text="Complete")
        status_text.empty()
        st.divider()

        passed = sum(1 for s in results.values() if s)
        st.metric("Result", f"{passed}/{len(results)} successful")
        for song_name, success in results.items():
            if success:
                st.success(song_name)
            else:
                st.error(f"{song_name} -- failed")

        with st.expander("Activity log"):
            st.code("\n".join(status_lines), language="log")


@st.cache_resource
def _load_separator(model_name: str, device: str):
    device_val = None if device == "Auto" else device
    return AudioStemSeparator(
        model_name=model_name,
        device=device_val,
        log_directory=str(LOGS_DIR),
    )


def separate_page():
    st.header("Stem Separation")
    st.markdown(f'<p class="page-desc">{PAGE_DESCRIPTIONS["separate"]}</p>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        model_name = st.selectbox(
            "Model",
            options=list(AVAILABLE_MODELS.keys()),
            format_func=lambda k: f"{k} -- {AVAILABLE_MODELS[k]}",
        )
    with col2:
        device = st.selectbox("Device", DEVICE_OPTIONS)

    source_option = st.radio(
        "Input source",
        ["Use downloaded MP3s", "Custom directory"],
        horizontal=True,
    )

    input_dir = st.text_input("Input directory path") if source_option == "Custom directory" else str(MP3_DIR)

    input_path = Path(input_dir)
    audio_files = []
    if input_path.exists():
        for ext in AUDIO_EXTENSIONS:
            audio_files.extend(input_path.glob(ext))
        audio_files = sorted(audio_files)

    if audio_files:
        st.info(f"{len(audio_files)} audio file(s) found")

    scope = st.radio("Scope", ["All songs", "Select songs"], horizontal=True)

    selected_files = audio_files
    if scope == "Select songs" and audio_files:
        selected_names = st.multiselect(
            "Choose files",
            options=[f.name for f in audio_files],
            default=[],
        )
        selected_files = [f for f in audio_files if f.name in selected_names]

    if st.button("Start Separation", type="primary"):
        if not input_path.exists():
            st.error(f"Directory not found: {input_dir}")
            return

        if not selected_files:
            st.warning("No audio files selected.")
            return

        progress_bar = st.progress(0, text="Loading model...")
        status_text = st.empty()
        status_lines = []

        def on_status(msg):
            status_lines.append(msg)
            status_text.text(msg)

        separator = _load_separator(model_name, device)
        on_status(f"Model ready: {model_name} on {separator.device}")

        total = len(selected_files)

        results = {"processed": 0, "successful": 0, "failed": 0, "files": []}
        for i, audio_file in enumerate(selected_files, 1):
            progress_bar.progress(i / total, text=f"{i}/{total}: {audio_file.name}")
            on_status(f"[{i}/{total}] {audio_file.name}")

            success = separator.separate_audio_file(str(audio_file), str(STEMS_DIR))
            results["processed"] += 1
            status = "success" if success else "failed"
            results["successful" if success else "failed"] += 1
            results["files"].append({"file": audio_file.name, "status": status})

        progress_bar.progress(1.0, text="Complete")
        status_text.empty()
        st.divider()

        st.metric("Result", f"{results['successful']}/{results['processed']} successful")
        for entry in results["files"]:
            if entry["status"] == "success":
                st.success(entry["file"])
            else:
                st.error(f"{entry['file']} -- failed")

        with st.expander("Activity log"):
            st.code("\n".join(status_lines), language="log")


@st.fragment
def output_page():
    st.header("Output")
    st.markdown(f'<p class="page-desc">{PAGE_DESCRIPTIONS["output"]}</p>', unsafe_allow_html=True)

    tab_mp3, tab_stems = st.tabs(["MP3s", "Stems"])

    with tab_mp3:
        if MP3_DIR.exists():
            mp3_files = sorted(MP3_DIR.glob("*.mp3"))
            if mp3_files:
                st.info(f"{len(mp3_files)} file(s)")
                for mp3 in mp3_files:
                    with st.expander(mp3.stem):
                        audix(str(mp3), wavesurfer_options=WAVE_OPTS)
            else:
                st.info("No MP3 files yet. Download some tracks first.")
        else:
            st.info("Output directory doesn't exist yet.")

    with tab_stems:
        if STEMS_DIR.exists():
            song_dirs = sorted(d for d in STEMS_DIR.iterdir() if d.is_dir())
            if song_dirs:
                st.info(f"{len(song_dirs)} song(s) separated")
                for song_dir in song_dirs:
                    with st.expander(song_dir.name):
                        for stem in sorted(song_dir.glob("*.wav")):
                            st.caption(stem.stem)
                            audix(str(stem), wavesurfer_options=STEM_WAVE_OPTS)
            else:
                st.info("No stems yet. Run separation first.")
        else:
            st.info("No stems yet.")


def logs_page():
    st.header("Logs")

    if not LOGS_DIR.exists():
        st.info("No logs yet.")
        return

    log_files = sorted(LOGS_DIR.glob("*.log"), reverse=True)
    if not log_files:
        st.info("No log files found.")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected_log = st.selectbox("Log file", log_files, format_func=lambda p: p.name)
    with col2:
        level_filter = st.selectbox("Filter by level", ["All", "INFO", "WARNING", "ERROR"])

    if not selected_log:
        return

    for line in selected_log.read_text().strip().splitlines():
        parts = line.split(" - ", 3)
        if len(parts) < 4:
            continue

        timestamp, _, level, message = parts
        level = level.strip()

        if level_filter != "All" and level != level_filter:
            continue

        time_part = timestamp.split(" ")[-1].split(",")[0] if " " in timestamp else timestamp

        if level == "ERROR":
            st.error(f"`{time_part}` {message}")
        elif level == "WARNING":
            st.warning(f"`{time_part}` {message}")
        else:
            st.caption(f"`{time_part}` {message}")

    with st.expander("Raw log"):
        st.code(selected_log.read_text(), language="log")


# page routing
PAGES = {
    "Download": download_page,
    "Stem Separation": separate_page,
    "Output": output_page,
    "Logs": logs_page,
}

st.sidebar.image("img/image.png", width="stretch")
st.sidebar.title(APP_TITLE)
st.sidebar.caption(APP_SUBTITLE)
selection = st.sidebar.radio("Navigate", list(PAGES.keys()))
PAGES[selection]()
