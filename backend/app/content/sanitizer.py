import bleach

ALLOWED_TAGS = ["p", "h2", "h3", "strong", "ul", "ol", "li", "br", "a", "img"]
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title"],
    "img": ["src", "alt"],
}


def sanitize_rich_text(value: str) -> str:
    cleaned = bleach.clean(
        value.strip(),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https"],
        strip=True,
    )
    return cleaned
