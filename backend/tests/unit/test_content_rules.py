from types import SimpleNamespace

from app.content.sanitizer import sanitize_rich_text
from app.content.service import BanlistService


def test_banlist_version_rolls_over_after_minor_nine() -> None:
    assert BanlistService.next_version(None) == (1, 0)
    assert BanlistService.next_version(SimpleNamespace(major_version=1, minor_version=8)) == (1, 9)
    assert BanlistService.next_version(SimpleNamespace(major_version=1, minor_version=9)) == (2, 0)


def test_rich_text_sanitizer_removes_scripts_and_event_handlers() -> None:
    clean = sanitize_rich_text(
        '<h2>标题</h2><script>alert(1)</script><img src="/uploads/a.png" onerror="alert(2)">'
    )

    assert "<script" not in clean
    assert "onerror" not in clean
    assert "<h2>标题</h2>" in clean
    assert '<img src="/uploads/a.png">' in clean
