from io import BytesIO

from PIL import Image

from app.auth.roles import Role


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

    assert valid.status_code == 200
    assert valid.json()["url"].startswith("/uploads/")
    assert valid.json()["width"] == 12
    assert valid.json()["height"] == 8
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "INVALID_IMAGE"
