from io import BytesIO
from pathlib import Path

from PIL import Image

from app.auth.roles import Role
from app.core.config import get_settings


def test_player_cannot_publish_content(client, make_user) -> None:
    _, token = make_user()
    response = client.post(
        "/api/admin/banlists",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "测试禁卡表", "content_html": "<p>内容</p>"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_publishes_sanitized_versioned_content(client, make_user) -> None:
    _, token = make_user(role=Role.PLATFORM_ADMIN)
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post(
        "/api/admin/banlists",
        headers=headers,
        json={"title": "第一版", "content_html": '<h2>规则</h2><script>alert(1)</script><p>正文</p>'},
    )
    second = client.post(
        "/api/admin/banlists",
        headers=headers,
        json={"title": "第二版", "content_html": "<p>更新</p>"},
    )
    listing = client.get("/api/banlists")

    assert first.status_code == 201
    assert first.json()["version"] == "V1.0"
    assert "<script" not in first.json()["content_html"]
    assert second.json()["version"] == "V1.1"
    assert listing.json()["total"] == 2
    assert listing.json()["items"][0]["version"] == "V1.1"


def test_admin_updates_banlist_without_changing_its_version(client, make_user) -> None:
    _, admin_token = make_user(
        qq_number="12345679", nickname="禁卡表管理员", role=Role.PLATFORM_ADMIN
    )
    _, player_token = make_user(qq_number="12345680", nickname="普通用户")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    created = client.post(
        "/api/admin/banlists",
        headers=admin_headers,
        json={"title": "修改前", "content_html": "<p>旧内容</p>"},
    )
    item_id = created.json()["id"]

    forbidden = client.patch(
        f"/api/admin/banlists/{item_id}",
        headers={"Authorization": f"Bearer {player_token}"},
        json={"title": "越权修改"},
    )
    updated = client.patch(
        f"/api/admin/banlists/{item_id}",
        headers=admin_headers,
        json={
            "title": "修改后",
            "content_html": '<p onclick="bad()">新内容</p><script>alert(1)</script>',
        },
    )
    public = client.get(f"/api/banlists/{item_id}")

    assert forbidden.status_code == 403
    assert updated.status_code == 200
    assert updated.json()["version"] == "V1.0"
    assert updated.json()["title"] == "修改后"
    assert "onclick" not in updated.json()["content_html"]
    assert "script" not in updated.json()["content_html"]
    assert public.json()["title"] == "修改后"
    assert public.json()["content_html"] == updated.json()["content_html"]
    audit = client.get("/api/admin/audit-logs?limit=20", headers=admin_headers)
    assert any(item["action_type"] == "BANLIST_UPDATED" for item in audit.json()["items"])


def test_announcement_publication_and_update_are_sanitized(client, make_user) -> None:
    _, token = make_user(role=Role.PLATFORM_ADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/admin/announcements",
        headers=headers,
        json={"title": "维护通知", "content_html": '<p onclick="bad()">今晚维护</p>', "is_pinned": True},
    )
    item_id = created.json()["id"]
    updated = client.patch(
        f"/api/admin/announcements/{item_id}",
        headers=headers,
        json={"content_html": '<p>维护完成</p><iframe src="bad"></iframe>', "is_pinned": False},
    )
    public = client.get(f"/api/announcements/{item_id}")

    assert created.status_code == 201
    assert "onclick" not in created.json()["content_html"]
    assert updated.status_code == 200
    assert "iframe" not in updated.json()["content_html"]
    assert public.json()["content_html"] == "<p>维护完成</p>"


def test_image_upload_validates_and_reencodes_images(client, make_user) -> None:
    _, token = make_user(role=Role.PLATFORM_ADMIN)
    headers = {"Authorization": f"Bearer {token}"}
    image_buffer = BytesIO()
    Image.new("RGB", (12, 8), color=(141, 61, 45)).save(image_buffer, format="PNG")
    jpeg_buffer = BytesIO()
    Image.new("RGB", (12, 8), color=(141, 61, 45)).save(jpeg_buffer, format="JPEG")
    mpo_buffer = BytesIO()
    Image.new("RGB", (12, 8), color=(141, 61, 45)).save(
        mpo_buffer,
        format="MPO",
        save_all=True,
        append_images=[Image.new("L", (6, 4), color=128)],
    )

    valid = client.post(
        "/api/admin/uploads/images",
        headers=headers,
        files={"image": ("sample.png", image_buffer.getvalue(), "image/png")},
    )
    invalid = client.post(
        "/api/admin/uploads/images",
        headers=headers,
        files={"image": ("attack.png", b"<script>alert(1)</script>", "image/png")},
    )
    jpeg = client.post(
        "/api/admin/uploads/images",
        headers=headers,
        files={"image": ("sample.jpeg", jpeg_buffer.getvalue(), "image/jpeg")},
    )
    mpo = client.post(
        "/api/admin/uploads/images",
        headers=headers,
        files={"image": ("iphone-hdr.jpg", mpo_buffer.getvalue(), "image/jpeg")},
    )
    settings = get_settings()
    too_large = client.post(
        "/api/admin/uploads/images",
        headers=headers,
        files={"image": ("large.png", b"0" * (settings.upload_max_bytes + 1), "image/png")},
    )

    assert valid.status_code == 200
    assert valid.json()["url"].startswith("/uploads/")
    assert valid.json()["width"] == 12
    assert valid.json()["height"] == 8
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_IMAGE"
    assert jpeg.status_code == 200
    assert jpeg.json()["content_type"] == "image/jpeg"
    assert jpeg.json()["url"].endswith(".jpg")
    assert mpo.status_code == 200
    assert mpo.json()["content_type"] == "image/jpeg"
    assert mpo.json()["url"].endswith(".jpg")
    with Image.open(get_settings().upload_dir / Path(mpo.json()["url"]).name) as stored_mpo:
        assert stored_mpo.format == "JPEG"
        assert getattr(stored_mpo, "n_frames", 1) == 1
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "INVALID_IMAGE_SIZE"
    assert too_large.json()["message"] == "图片为空或超过 20MB"
