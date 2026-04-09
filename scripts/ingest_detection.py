"""Automatic ingest-mode detection for local files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from scripts import storage


URL_PATTERN = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
URL_LIST_SUFFIXES = {".list", ".urls", ".urlset"}
URL_LIST_LINE_PREFIX = re.compile(r"^([-*+]\s+|\d+\.\s+)?")
MARKDOWN_HEADING_PATTERN = re.compile(r"^\s{0,3}#\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True)
class IngestPlan:
    source_path: Path
    title: str
    initial_status: str
    is_url_list: bool
    detection_reason: str


def build_ingest_plan(
    *,
    source_type: str,
    content_type: str,
    source_path: Path,
    explicit_title: str | None = None,
    explicit_accept: bool = False,
) -> IngestPlan:
    storage._validate_choice("source_type", source_type, storage.SOURCE_TYPES)
    storage._validate_choice("content_type", content_type, storage.CONTENT_TYPES)
    if explicit_title is not None:
        storage._validate_string("title", explicit_title)

    text_preview = _read_text_preview(source_path)
    is_url_list, detection_reason = detect_url_list(source_path, text_preview)
    initial_status, detection_reason = _initial_status(
        source_type=source_type,
        explicit_accept=explicit_accept,
        default_reason=detection_reason,
    )
    title = derive_title(source_path, explicit_title, text_preview)
    return IngestPlan(
        source_path=source_path,
        title=title,
        initial_status=initial_status,
        is_url_list=is_url_list,
        detection_reason=detection_reason,
    )


def detect_url_list(source_path: Path, text_preview: str | None) -> tuple[bool, str]:
    if text_preview is None:
        return False, "binary_or_non_utf8_input"

    urls = URL_PATTERN.findall(text_preview)
    non_empty_lines = [line.strip() for line in text_preview.splitlines() if line.strip()]
    urlish_lines = 0
    for line in non_empty_lines:
        normalized_line = URL_LIST_LINE_PREFIX.sub("", line).strip()
        if normalized_line and URL_PATTERN.fullmatch(normalized_line):
            urlish_lines += 1

    suffix = source_path.suffix.lower()
    if suffix in URL_LIST_SUFFIXES and urls:
        return True, f"suffix={suffix}"
    if len(urls) >= 2 and non_empty_lines and (urlish_lines / len(non_empty_lines)) >= 0.6:
        return True, "content=url_heavy_list"
    return False, "content=regular_file"


def derive_title(source_path: Path, explicit_title: str | None, text_preview: str | None) -> str:
    if explicit_title is not None:
        return explicit_title

    if text_preview:
        for line in text_preview.splitlines():
            heading_match = MARKDOWN_HEADING_PATTERN.match(line)
            if heading_match:
                return heading_match.group("title").strip()
        for line in text_preview.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            if candidate.startswith("Source URL:"):
                continue
            if URL_PATTERN.fullmatch(URL_LIST_LINE_PREFIX.sub("", candidate).strip()):
                continue
            return candidate[:120]

    stem = source_path.stem.replace("-", " ").replace("_", " ").strip()
    return stem or source_path.name


def _initial_status(
    *,
    source_type: str,
    explicit_accept: bool,
    default_reason: str,
) -> tuple[str, str]:
    if explicit_accept:
        return "accepted", "manual_override=accept"
    return "candidate", f"default_candidate:{default_reason}"


def _read_text_preview(source_path: Path, max_chars: int = 20000) -> str | None:
    try:
        return source_path.read_text(encoding="utf-8")[:max_chars]
    except UnicodeDecodeError:
        return None
