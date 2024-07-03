import dataclasses
import json
import os
import pathlib
from itertools import count

import flask

app = flask.Flask(__name__)
uploads_path = pathlib.Path(app.static_folder) / "uploads"
uploads_path.mkdir(exist_ok=True, parents=True)


@dataclasses.dataclass(frozen=True)
class UploadedFile:
    name: str
    url: str
    meta: dict
    stat: os.stat_result

    @property
    def ctime(self) -> float:
        return self.stat.st_ctime


def get_uploads():
    for pth in uploads_path.glob("*"):
        if pth.suffix == ".meta":
            continue
        meta_path = uploads_path / f"{pth.name}.meta"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        else:
            meta = {}
        stat = pth.stat()
        yield UploadedFile(
            name=pth.name,
            url=flask.url_for("static", filename=f"uploads/{pth.name}"),
            meta=meta,
            stat=stat,
        )


@app.route("/")
def index():
    uploads = sorted(get_uploads(), key=lambda x: x.ctime, reverse=True)
    return flask.render_template("index.html", uploads=uploads)


@app.route("/upload", methods=["POST"])
def upload():
    file = flask.request.files["file"]
    metadata = {
        key: value for (key, value) in flask.request.form.to_dict() if key and value
    }
    dest_path = find_upload_path(file)
    file.save(dest_path)
    if metadata:
        meta_path = uploads_path / f"{dest_path.name}.meta"
        meta_path.write_text(json.dumps(metadata, default=str))
    return flask.redirect(flask.url_for("index"))


def find_upload_path(file) -> pathlib.Path:
    filename = file.filename
    for counter in count(1):
        dest_name = uploads_path / filename
        # TODO: Mildly TOCTOU-prone
        if not dest_name.exists():
            return dest_name
        filename = f"{counter}_{file.filename}"
