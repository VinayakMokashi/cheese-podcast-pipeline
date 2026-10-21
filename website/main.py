"""
Mega Pipeline Viewer: one web page showing every pipeline stage
for one group, read live from the GCS bucket.
"""
import html
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from google.cloud import storage

# Settings come from environment variables, with our values as defaults
BUCKET_NAME = os.environ.get("BUCKET_NAME", "harvard-mlops-mega-pipeline")
GROUP_NAME = os.environ.get("GROUP_NAME", "unemployed")

# One entry per pipeline stage: (column title, bucket folder, kind of file)
STAGES = [
    ("Input audio", "input_audios", "audio"),
    ("Transcribed text", "text_prompts", "text"),
    ("Generated text", "text_paragraphs", "text"),
    ("Synthesised audio (EN)", "text_audios", "audio"),
    ("Translated text", "text_translated", "text"),
    ("Synthesised audio (FR)", "output_audios", "audio"),
    ("Pavlos' voice (FR)", "output_audios_pp", "audio"),
]
FOLDERS = {folder for _, folder, _ in STAGES}

app = FastAPI(title="Mega Pipeline Viewer")
bucket = storage.Client().bucket(BUCKET_NAME)


def list_stage(folder):
    """Return {uuid: blob} for every file one stage has written."""
    # Input audios sit directly in their folder; every other stage
    # writes into a subfolder named after the group.
    if folder == "input_audios":
        prefix = f"{folder}/"
    else:
        prefix = f"{folder}/{GROUP_NAME}/"

    files = {}
    for blob in bucket.list_blobs(prefix=prefix):
        filename = blob.name.rsplit("/", 1)[-1]
        if filename:
            uuid = filename.rsplit(".", 1)[0]
            files[uuid] = blob
    return files


CSS = """
body { font-family: system-ui, sans-serif; margin: 2rem; background: #fafafa; color: #222; }
h1 { color: #a51c30; margin-bottom: 0.2rem; }
table { border-collapse: collapse; width: 100%; background: white; }
th, td { border: 1px solid #ddd; padding: 0.6rem; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
td.pending { color: #999; font-style: italic; }
.text { max-height: 12rem; overflow-y: auto; font-size: 0.9rem; line-height: 1.4; }
audio { width: 220px; }
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """Build the page: one row per input audio, one column per stage."""
    stages = [(title, kind, list_stage(folder)) for title, folder, kind in STAGES]
    uuids = sorted(stages[0][2])

    header = "".join(f"<th>{title}</th>" for title, _, _ in stages)
    rows = ""
    for uuid in uuids:
        cells = ""
        for _, kind, files in stages:
            blob = files.get(uuid)
            if blob is None:
                cells += '<td class="pending">not yet</td>'
            elif kind == "audio":
                cells += f'<td><audio controls preload="none" src="/file/{blob.name}"></audio></td>'
            else:
                text = html.escape(blob.download_as_text())
                cells += f'<td><div class="text">{text}</div></td>'
        rows += f"<tr><th>{uuid}</th>{cells}</tr>"

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Mega Pipeline Viewer</title>
  <style>{CSS}</style>
</head>
<body>
  <h1>Mega Pipeline Viewer</h1>
  <p>Bucket <code>{BUCKET_NAME}</code> &middot; group <code>{GROUP_NAME}</code> &middot; refresh to update</p>
  <table>
    <tr><th>File</th>{header}</tr>
    {rows}
  </table>
</body>
</html>"""


@app.get("/file/{path:path}")
def get_file(path: str):
    """Send one audio file from the bucket to the browser."""
    if path.split("/", 1)[0] not in FOLDERS:
        raise HTTPException(status_code=404)
    blob = bucket.blob(path)
    if not blob.exists():
        raise HTTPException(status_code=404)

    data = blob.download_as_bytes()
    # Text-to-Speech writes WAV data even though the files end in .mp3
    media_type = "audio/wav" if data[:4] == b"RIFF" else "audio/mpeg"
    return Response(content=data, media_type=media_type)
