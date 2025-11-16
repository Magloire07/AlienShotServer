"""AlienShotServer backend API.

Provides endpoints to ingest photos, manage them from an admin UI, and
share curated selections without authentication via share tokens.
"""

from __future__ import annotations

import io
import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from flask import Flask, abort, current_app, jsonify, request, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


db = SQLAlchemy()


class Photo(db.Model):
    __tablename__ = "photos"

    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "original_name": self.original_name,
            "created_at": self.created_at.isoformat(),
        }


class ShareLink(db.Model):
    __tablename__ = "share_links"

    token = db.Column(db.String(64), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    photos = db.relationship(
        "Photo",
        secondary="share_photos",
        lazy="joined",
        order_by=desc(Photo.created_at),
    )

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "created_at": self.created_at.isoformat(),
            "photos": [photo.to_dict() for photo in self.photos],
        }


class SharePhoto(db.Model):
    __tablename__ = "share_photos"

    share_token = db.Column(
        db.String(64), db.ForeignKey("share_links.token"), primary_key=True
    )
    photo_id = db.Column(db.Integer, db.ForeignKey("photos.id"), primary_key=True)


DEFAULT_MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB per request


def create_app(test_config: Optional[dict] = None) -> Flask:
    """Application factory used by Flask CLI and tests."""

    app = Flask(__name__, instance_relative_config=True)

    default_db_path = os.path.join(app.instance_path, "alienshot.db")
    default_upload_path = os.path.join(app.instance_path, "uploads")

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=int(
            os.getenv("MAX_CONTENT_LENGTH", DEFAULT_MAX_CONTENT_LENGTH)
        ),
        ADMIN_PASSWORD=os.getenv("ADMIN_PASSWORD", "admin"),
        UPLOAD_FOLDER=os.getenv("UPLOAD_FOLDER", default_upload_path),
        SHARE_BASE_URL=os.getenv("SHARE_BASE_URL", "http://localhost:5173"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
    )

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    CORS(
        app,
        resources={
            r"/photos*": {"origins": "*"},
            r"/shares*": {"origins": "*"},
        },
    )

    db.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def register_routes(app: Flask) -> None:
    @app.get("/healthz")
    def healthcheck():
        return {"status": "ok"}

    @app.post("/images/add")
    def upload_photo():
        files = _extract_files(request.files)
        if not files:
            abort(400, "Aucun fichier fourni")

        stored = []
        for file in files:
            stored.append(_store_file(file, app.config["UPLOAD_FOLDER"]))

        db.session.add_all(stored)
        db.session.commit()

        return jsonify([photo.to_dict() for photo in stored]), 201

    @app.get("/photos")
    def list_photos():
        _require_admin()
        photos = Photo.query.order_by(desc(Photo.created_at)).all()
        return jsonify([photo.to_dict() for photo in photos])

    @app.get("/photos/<int:photo_id>/file")
    def download_photo(photo_id: int):
        _require_admin()
        photo = Photo.query.get_or_404(photo_id)
        return _send_photo_file(photo, app.config["UPLOAD_FOLDER"])

    @app.delete("/photos")
    def delete_photos():
        _require_admin()
        body = request.get_json(silent=True) or {}
        photo_ids: List[int] = body.get("photo_ids", [])
        if not photo_ids:
            abort(400, "photo_ids est requis")

        photos = Photo.query.filter(Photo.id.in_(photo_ids)).all()
        if not photos:
            return ("", 204)

        for photo in photos:
            _remove_photo_file(photo, app.config["UPLOAD_FOLDER"])
            db.session.delete(photo)

        db.session.commit()
        return {"deleted": [photo.id for photo in photos]}

    @app.post("/shares")
    def create_share_link():
        _require_admin()
        body = request.get_json(silent=True) or {}
        photo_ids: List[int] = body.get("photo_ids", [])
        if not photo_ids:
            abort(400, "photo_ids est requis")

        photos = Photo.query.filter(Photo.id.in_(photo_ids)).order_by(
            desc(Photo.created_at)
        )
        found = photos.all()
        if not found:
            abort(404, "Aucune photo trouvée")

        token = uuid.uuid4().hex
        share = ShareLink(token=token)
        unique_photos = list({photo.id: photo for photo in found}.values())
        share.photos.extend(unique_photos)

        db.session.add(share)
        db.session.commit()

        share_url = f"{app.config['SHARE_BASE_URL'].rstrip('/')}/share/{token}"
        return {
            "token": token,
            "share_url": share_url,
            "qr_payload": share_url,
            "photos": [photo.to_dict() for photo in unique_photos],
        }, 201

    @app.get("/shares/<string:token>")
    def get_share(token: str):
        share = ShareLink.query.get_or_404(token)
        return share.to_dict()

    @app.get("/shares/<string:token>/files/<int:photo_id>")
    def download_shared_photo(token: str, photo_id: int):
        share = ShareLink.query.get_or_404(token)
        photo = _photo_in_share_or_404(share, photo_id)
        return _send_photo_file(photo, app.config["UPLOAD_FOLDER"])

    @app.post("/shares/<string:token>/download")
    def download_shared_selection(token: str):
        share = ShareLink.query.get_or_404(token)
        body = request.get_json(silent=True) or {}
        requested_ids: List[int] = body.get("photo_ids", [])

        if requested_ids:
            photos = [_photo_in_share_or_404(share, pid) for pid in requested_ids]
        else:
            photos = share.photos

        if not photos:
            abort(404, "Aucune photo disponible")

        archive = _zip_photos(photos, app.config["UPLOAD_FOLDER"])
        filename = f"alienshot_{token}.zip"
        return send_file(
            archive,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename,
        )


def _extract_files(storage) -> List[FileStorage]:
    """Support both single and multi-file uploads."""

    if not storage:
        return []

    files: List[FileStorage] = []
    file_lists = [
        storage.getlist("photos"),
        storage.getlist("photos[]"),
        storage.getlist("files"),
    ]
    for file_list in file_lists:
        files.extend([file for file in file_list if file and file.filename])

    single = storage.get("photo") or storage.get("file")
    if single and single.filename:
        files.append(single)

    return files


def _store_file(file: FileStorage, upload_dir: str) -> Photo:
    filename = secure_filename(file.filename or "photo")
    ext = os.path.splitext(filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target_path = os.path.join(upload_dir, stored_name)
    file.save(target_path)
    return Photo(original_name=filename, stored_name=stored_name)


def _remove_photo_file(photo: Photo, upload_dir: str) -> None:
    path = os.path.join(upload_dir, photo.stored_name)
    if os.path.exists(path):
        os.remove(path)


def _photo_in_share_or_404(share: ShareLink, photo_id: int) -> Photo:
    for photo in share.photos:
        if photo.id == photo_id:
            return photo
    abort(404, "Photo non associée à ce partage")


def _send_photo_file(photo: Photo, upload_dir: str):
    path = os.path.join(upload_dir, photo.stored_name)
    if not os.path.exists(path):
        abort(410, "Fichier manquant sur le serveur")
    return send_file(path, download_name=photo.original_name)


def _zip_photos(photos: Iterable[Photo], upload_dir: str) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for photo in photos:
            path = os.path.join(upload_dir, photo.stored_name)
            if not os.path.exists(path):
                continue
            arcname = photo.original_name or f"photo_{photo.id}"
            archive.write(path, arcname)
    buffer.seek(0)
    return buffer


def _require_admin() -> None:
    password = request.headers.get("X-Admin-Password") or request.args.get("password")
    expected = current_app.config.get("ADMIN_PASSWORD") if request else None
    if not expected or password != expected:
        abort(403, "Mot de passe admin invalide")


# Expose application instance for `flask run`.
app = create_app()
