from __future__ import annotations

import hashlib
import re
from bs4 import BeautifulSoup

from .models import HtmlDocument

_SPACE_RE = re.compile(r"\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def clean_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value).strip()


def split_sentences(text: str) -> list[str]:
    return [clean_text(part) for part in _SENTENCE_RE.split(clean_text(text)) if clean_text(part)]


def parse_html(filename: str, html: str) -> HtmlDocument:
    """Extract a compact wiki-friendly document from uploaded ecommerce HTML."""

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = clean_text(soup.title.get_text(" ")) if soup.title else filename
    canonical = soup.find("link", rel=lambda value: value and "canonical" in value)
    url = canonical.get("href") if canonical and canonical.get("href") else None

    sections: list[dict[str, str]] = []
    current_heading = title or filename
    current_parts: list[str] = []

    body = soup.body or soup
    for node in body.find_all(["h1", "h2", "h3", "h4", "p", "li", "dt", "dd", "td", "th"], recursive=True):
        text = clean_text(node.get_text(" "))
        if not text:
            continue
        if node.name in {"h1", "h2", "h3", "h4"}:
            if current_parts:
                sections.append({"heading": current_heading, "text": clean_text(" ".join(current_parts))})
                current_parts = []
            current_heading = text
        else:
            current_parts.append(text)
    if current_parts:
        sections.append({"heading": current_heading, "text": clean_text(" ".join(current_parts))})

    text = clean_text(body.get_text(" "))
    doc_id = hashlib.sha1(f"{filename}:{text[:1000]}".encode("utf-8")).hexdigest()[:12]
    return HtmlDocument(
        doc_id=doc_id,
        filename=filename,
        title=title or filename,
        url=url,
        text=text,
        sections=sections or [{"heading": title or filename, "text": text}],
        metadata={"characters": len(text), "section_count": len(sections)},
    )
