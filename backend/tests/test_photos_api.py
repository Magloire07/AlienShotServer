import io
import os
import pytest

from app import create_app


@pytest.fixture()
def client(tmp_path):
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "test.db"
    app = create_app(
        {
            "TESTING": True,
            "UPLOAD_FOLDER": str(upload_dir),
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "ADMIN_PASSWORD": "secret",
        }
    )

    with app.test_client() as client:
        yield client


@pytest.fixture()
def admin_headers():
    return {"X-Admin-Password": "secret"}


def _upload_sample(client):
    data = {
        "photo": (io.BytesIO(b"alien-bytes"), "alien.jpg"),
    }
    response = client.post("/images/add", data=data, content_type="multipart/form-data")
    assert response.status_code == 201
    payload = response.get_json()
    return payload[0]["id"], payload[0]["original_name"]


def test_upload_and_list_photos(client, admin_headers):
    _upload_sample(client)

    response = client.get("/photos", headers=admin_headers)
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["original_name"] == "alien.jpg"


def test_create_share_and_download_archive(client, admin_headers, tmp_path):
    first_id, _ = _upload_sample(client)
    second_id, _ = _upload_sample(client)

    response = client.post(
        "/shares",
        json={"photo_ids": [first_id, second_id]},
        headers=admin_headers,
    )
    assert response.status_code == 201
    payload = response.get_json()
    token = payload["token"]

    share_response = client.get(f"/shares/{token}")
    assert share_response.status_code == 200
    assert len(share_response.get_json()["photos"]) == 2

    zip_response = client.post(f"/shares/{token}/download", json={})
    assert zip_response.status_code == 200
    assert zip_response.headers["Content-Type"] == "application/zip"


def test_delete_photos_removes_files(client, admin_headers):
    photo_id, _ = _upload_sample(client)

    upload_dir = client.application.config["UPLOAD_FOLDER"]
    files_before = list(os.listdir(upload_dir))
    assert files_before, "File should exist on disk before deletion"

    response = client.delete("/photos", json={"photo_ids": [photo_id]}, headers=admin_headers)
    assert response.status_code == 200
    assert response.get_json()["deleted"] == [photo_id]

    assert not os.listdir(upload_dir), "Upload folder should be empty after delete"
