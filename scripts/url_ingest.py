"""Minimal URL list ingestion into raw stores and workspace records."""

from __future__ import annotations

import html
import logging
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from scripts import storage


LOGGER = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
DEFAULT_TIMEOUT_SECONDS = 20
USER_AGENT = "pkls-url-ingest/0.1"


class UrlIngestError(ValueError):
    """Raised when URL ingestion cannot proceed."""


@dataclass
class FetchedPage:
    url: str
    title: str
    body: str


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.ignored_depth = 0
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "title":
            self.in_title = True
        if normalized_tag in {"script", "style", "noscript"}:
            self.ignored_depth += 1
        if normalized_tag in {"p", "div", "section", "article", "main", "br", "li", "h1", "h2", "h3", "h4"}:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "title":
            self.in_title = False
        if normalized_tag in {"script", "style", "noscript"} and self.ignored_depth > 0:
            self.ignored_depth -= 1
        if normalized_tag in {"p", "div", "section", "article", "main", "li"}:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.ignored_depth > 0:
            return
        stripped = data.strip()
        if stripped:
            self.text_parts.append(stripped)

    def extracted_title(self) -> str:
        return _normalize_whitespace(" ".join(self.title_parts))

    def extracted_text(self) -> str:
        lines = [_normalize_whitespace(part) for part in "".join(self.text_parts).splitlines()]
        non_empty_lines = [line for line in lines if line]
        return "\n\n".join(non_empty_lines)


def ingest_url_list(
    *,
    source_type: str,
    content_type: str,
    url_list_path: Path,
    initial_status: str = "candidate",
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or storage.get_repo_root()
    if not url_list_path.exists() or not url_list_path.is_file():
        raise FileNotFoundError(url_list_path)

    urls = read_url_list(url_list_path)
    if not urls:
        raise UrlIngestError(f"no URLs found in {url_list_path}")

    added_items: list[dict[str, Any]] = []
    duplicate_items: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for url in urls:
        try:
            result = ingest_single_url(
                source_type=source_type,
                content_type=content_type,
                url=url,
                initial_status=initial_status,
                root=base,
            )
            item = result["item"]
            if result["duplicate"]:
                duplicate_items.append(item)
                LOGGER.info("Skipped duplicate URL item: %s -> %s", url, item["id"])
            else:
                added_items.append(item)
                LOGGER.info("Ingested URL as content item: %s -> %s", url, item["id"])
        except Exception as exc:  # pragma: no cover - batch continuation is intentional
            LOGGER.error("Failed to ingest URL %s: %s", url, exc)
            failures.append({"url": url, "error": str(exc)})

    if not added_items and not duplicate_items and failures:
        raise UrlIngestError(f"failed to ingest all URLs from {url_list_path}")

    return {
        "added_items": added_items,
        "duplicate_items": duplicate_items,
        "failures": failures,
    }


def ingest_single_url(
    *,
    source_type: str,
    content_type: str,
    url: str,
    initial_status: str = "candidate",
    root: Path | None = None,
) -> dict[str, Any]:
    base = root or storage.get_repo_root()
    storage._validate_choice("source_type", source_type, storage.SOURCE_TYPES)
    storage._validate_choice("content_type", content_type, storage.CONTENT_TYPES)
    if initial_status not in {"candidate", "accepted"}:
        raise UrlIngestError(f"initial_status must be candidate or accepted, got {initial_status!r}")
    normalized_url = _normalize_url(url)
    existing_item = find_existing_item_by_source_url(normalized_url, base)
    if existing_item is not None:
        return {"item": existing_item, "duplicate": True}

    fetched_page = fetch_url_snapshot(normalized_url)
    doc_id = storage.build_doc_id(fetched_page.title, source_type, base)
    filename = _snapshot_filename(normalized_url, doc_id)
    snapshot_text = render_page_snapshot(fetched_page)

    with tempfile.TemporaryDirectory() as temp_dir:
        snapshot_path = Path(temp_dir) / filename
        snapshot_path.write_text(snapshot_text, encoding="utf-8")
        stored_file_info = storage.ingest_raw_file(doc_id, source_type, snapshot_path, base)

    status = initial_status
    recommendation = "learn" if status == "accepted" else "skim"
    item = storage.create_content_item(
        doc_id=doc_id,
        title=fetched_page.title,
        source_type=source_type,
        content_type=content_type,
        ingest_date=date.today().isoformat(),
        status=status,
        priority=1.0 if source_type == "manual" else 0.5,
        ai_recommendation=recommendation,
        manual_decision=None,
        storage_tier=stored_file_info["storage_tier"],
        full_raw_relpath=stored_file_info["full_raw_relpath"],
        sync_raw_relpath=stored_file_info["sync_raw_relpath"],
        source_filename=stored_file_info["source_filename"],
        source_device=stored_file_info["source_device"],
        content_hash=stored_file_info["content_hash"],
        sync_status=stored_file_info["sync_status"],
    )
    storage.write_content_item(item, base)

    if status == "accepted":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), base)

    return {"item": item, "duplicate": False}


def read_url_list(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    urls: list[str] = []
    seen: set[str] = set()

    for match in URL_PATTERN.findall(text):
        normalized = _normalize_url(match)
        if normalized not in seen:
            urls.append(normalized)
            seen.add(normalized)

    return urls


def fetch_url_snapshot(url: str) -> FetchedPage:
    LOGGER.info("Fetching URL: %s", url)
    request_headers = {"User-Agent": USER_AGENT}
    fetch_request = request.Request(url, headers=request_headers)

    try:
        with request.urlopen(fetch_request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            html_text = response.read().decode(charset, errors="replace")
    except error.URLError as exc:
        raise UrlIngestError(f"failed to fetch URL {url}: {exc}") from exc

    extractor = _HtmlTextExtractor()
    extractor.feed(html_text)
    title = extractor.extracted_title() or _title_from_url(url)
    body = extractor.extracted_text()
    if not body:
        raise UrlIngestError(f"no readable body content extracted from {url}")

    return FetchedPage(url=url, title=title, body=body)


def find_existing_item_by_source_url(url: str, root: Path | None = None) -> dict[str, Any] | None:
    base = root or storage.get_repo_root()
    source_line = f"Source URL: {url}"

    for item in storage.list_content_items(root=base):
        try:
            raw_text = storage.read_raw_text_for_item(item, base)
        except (FileNotFoundError, storage.StorageError):
            continue
        for line in raw_text.splitlines()[:10]:
            if line.strip() == source_line:
                LOGGER.info("Found existing URL content item for %s: %s", url, item["id"])
                return item
    return None


def render_page_snapshot(page: FetchedPage) -> str:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    return (
        f"# {page.title}\n\n"
        f"Source URL: {page.url}\n"
        f"Fetched At (UTC): {fetched_at}\n\n"
        f"{page.body}\n"
    )


def _normalize_url(url: str) -> str:
    cleaned = html.unescape(url.strip())
    parsed = parse.urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UrlIngestError(f"invalid URL: {url}")
    normalized = parsed._replace(fragment="").geturl()
    return normalized.rstrip(".,;")


def _title_from_url(url: str) -> str:
    parsed = parse.urlparse(url)
    path_segment = Path(parsed.path).name.replace("-", " ").replace("_", " ").strip()
    domain = parsed.netloc.replace("www.", "")
    suffix = path_segment.title() if path_segment else "Page"
    return f"{domain} {suffix}".strip()


def _snapshot_filename(url: str, doc_id: str) -> str:
    parsed = parse.urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix not in {".md", ".txt"}:
        suffix = ".md"
    return f"{doc_id}{suffix}"


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
