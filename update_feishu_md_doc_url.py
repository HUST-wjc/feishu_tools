#!/usr/bin/env python3
"""
Update feishu_md_doc_url — Feishu Open Platform documentation URL index.

The index lives in docs/agents_doc/feishu_md_doc_url_YYYY_MM-DD.json
(relative to this script). The date in the filename indicates when the index was
last refreshed. On each run the old dated file is deleted and a new one is
written with today's date, so the freshness is always visible from the filename
alone.

Agents use this file to quickly locate official .md documentation for any API,
then fetch the content with:  curl -L <md_url>

Strategy:
1. Load the existing docs/agents_doc/feishu_md_doc_url_*.json as the starting
   structure.
2. For each configured section, discover sub-pages by fetching the section's
   .md overview pages and parsing linked doc URLs.
3. Recursively discover pages within the same section path.
4. Check each discovered URL for a .md version (DocumentType vs DirectoryType).
5. Build a tree organised by URL path hierarchy.
6. Delete the old dated file and save the new one with today's date.

Usage:
    python3 update_feishu_md_doc_url.py                 # full update
    python3 update_feishu_md_doc_url.py --max-depth 5   # control crawl depth
    python3 update_feishu_md_doc_url.py --verify-md     # also fill missing md_url
    python3 update_feishu_md_doc_url.py --dry-run       # preview, no file changes
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DOCS_DIR = Path(__file__).parent / "docs" / "agents_doc"
FILE_STEM = "feishu_md_doc_url_"
FILE_SUFFIX = ".json"
BASE_URL = "https://open.feishu.cn"
DOC_PREFIX = "/document/"
DELAY = 0.4          # seconds between requests (be polite)
TIMEOUT = 20         # request timeout
MAX_DEPTH = 6        # default crawl depth

# Known section entry points for deep crawl. Key = section name fragment,
# value = list of seed .md URLs to start discovery from.
SEED_PAGES: dict[str, list[str]] = {
    "多维表格": [
        "https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview.md",
    ],
    "电子表格": [
        "https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet/overview.md",
    ],
    "文档": [
        "https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-overview.md",
    ],
    "云空间": [
        "https://open.feishu.cn/document/server-docs/docs/drive-v1/overview.md",
    ],
    "知识库": [
        "https://open.feishu.cn/document/server-docs/docs/wiki-v2/wiki-overview.md",
    ],
    "获取访问凭证": [
        "https://open.feishu.cn/document/server-docs/authentication-management/access-token/overview.md",
    ],
    "搜索": [
        "https://open.feishu.cn/document/server-docs/docs/search-v2/overview.md",
    ],
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; feishukit-sidebar-updater/1.0; "
        "+https://github.com/HUST-wjc/feishu_tools)"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9",
}


# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _get(url: str, *, timeout: int = TIMEOUT, retries: int = 2) -> str | None:
    """Fetch URL text. Returns None on error."""
    req = urllib.request.Request(url, headers=headers)
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
            if attempt < retries:
                time.sleep(1)
        except Exception:
            if attempt < retries:
                time.sleep(1)
    return None


def _has_md(url: str) -> bool:
    """Return True if {url}.md responds with 200 and non-trivial content."""
    md_url = url.rstrip("/") + ".md"
    content = _get(md_url, retries=1)
    if not content:
        return False
    # Feishu returns "This document is not found" (26 chars) for missing .md
    return len(content) > 100 and "not found" not in content.lower()[:50]


def _make_md_url(url: str) -> str:
    url = url.rstrip("/")
    if url.endswith(".md"):
        return url
    return url + ".md"


# ── URL helpers ───────────────────────────────────────────────────────────────

DOC_LINK_RE = re.compile(
    r"https?://open\.feishu\.cn/document/([a-zA-Z0-9/_-]+?)(?:\.md)?(?:\s|\)|\]|$)"
)


def _extract_doc_links(markdown: str) -> set[str]:
    """Extract all /document/* links from markdown content."""
    links = set()
    for m in DOC_LINK_RE.finditer(markdown):
        path = m.group(1).rstrip("/")
        links.add(f"{BASE_URL}{DOC_PREFIX}{path}")
    return links


def _same_section(url: str, section_root: str) -> bool:
    """Return True if url is under the same path prefix as section_root."""
    parsed = urlparse(url)
    root_parsed = urlparse(section_root)
    return parsed.path.startswith(root_parsed.path)


def _url_depth(url: str) -> int:
    return urlparse(url).path.count("/")


def _url_name(url: str) -> str:
    """Derive a display name from the last path segment."""
    return urlparse(url).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")


# ── Tree building ─────────────────────────────────────────────────────────────

class Node:
    def __init__(self, url: str, name: str = "", *, is_doc: bool = False):
        self.url = url
        self.name = name or _url_name(url)
        self.md_url = _make_md_url(url) if is_doc else ""
        self.type = "DocumentType" if is_doc else "DirectoryType"
        self.children: list[Node] = []

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "url": self.url,
            "md_url": self.md_url,
            "type": self.type,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in sorted(self.children, key=lambda n: n.url)]
        return d


def _build_section_tree(
    seed_urls: list[str],
    section_root: str,
    max_depth: int,
    verbose: bool,
) -> list[Node]:
    """
    Crawl from seed_urls, following links within section_root, up to max_depth.
    Returns a list of Node objects (flat discovered pages organized into a tree).
    """
    visited: set[str] = set()
    # Normalise seed URLs to canonical (no .md suffix)
    queue: list[tuple[str, int]] = []
    for u in seed_urls:
        canonical_seed = u.rstrip("/")
        if canonical_seed.endswith(".md"):
            canonical_seed = canonical_seed[:-3]
        queue.append((canonical_seed, 0))
    discovered: dict[str, Node] = {}  # canonical url → Node

    while queue:
        url, depth = queue.pop(0)
        url = url.rstrip("/")
        # Normalise: strip .md suffix for canonical URL
        if url.endswith(".md"):
            canonical = url[:-3]
            md_url_to_fetch = url
        else:
            canonical = url
            md_url_to_fetch = url + ".md"

        if canonical in visited:
            continue
        visited.add(canonical)

        if verbose:
            print(f"  [depth={depth}] GET {md_url_to_fetch}", file=sys.stderr)
        content = _get(md_url_to_fetch)
        time.sleep(DELAY)

        is_doc = bool(
            content and len(content) > 100
            and "not found" not in content.lower()[:50]
        )

        if canonical not in discovered:
            discovered[canonical] = Node(canonical, is_doc=is_doc)

        if not is_doc or depth >= max_depth:
            continue

        for link in _extract_doc_links(content):
            link = link.rstrip("/")
            if link in visited:
                continue
            if not _same_section(link, section_root):
                continue
            queue.append((link, depth + 1))

    return list(discovered.values())


def _nodes_to_tree(nodes: list[Node], section_root: str) -> list[dict]:
    """
    Given flat list of discovered nodes, organize into a URL-path hierarchy tree.

    Algorithm:
    1. Build a trie-like structure from URL path components relative to section_root.
    2. Create virtual DirectoryType nodes for intermediate path segments.
    3. Return children dicts for insertion under the section entry.
    """
    if not nodes:
        return []

    root_path = urlparse(section_root).path.rstrip("/")

    # Map: relative_path_tuple → Node (real or virtual directory)
    tree: dict[tuple, Node] = {}

    for node in nodes:
        path = urlparse(node.url).path.rstrip("/")
        # Compute path relative to section_root
        if path.startswith(root_path):
            rel = path[len(root_path):].strip("/")
        else:
            # URL uses a different base; use full last 3 segments as relative path
            parts = path.strip("/").split("/")
            rel = "/".join(parts[-3:]) if len(parts) >= 3 else parts[-1]

        rel_parts = tuple(rel.split("/")) if rel else ()
        tree[rel_parts] = node

        # Ensure all parent paths exist as directory nodes
        for i in range(1, len(rel_parts)):
            parent_parts = rel_parts[:i]
            if parent_parts not in tree:
                parent_url = section_root.rstrip("/") + "/" + "/".join(parent_parts)
                tree[parent_parts] = Node(parent_url, is_doc=False)

    # Build the tree by wiring children to parents
    # Sort so parents are always processed before children
    for parts, node in sorted(tree.items(), key=lambda x: len(x[0])):
        if len(parts) <= 1:
            continue
        parent_parts = parts[:-1]
        parent = tree.get(parent_parts)
        if parent and node not in parent.children:
            parent.children.append(node)

    # Return top-level nodes (depth=1 from section_root)
    top_level = [n for parts, n in tree.items() if len(parts) == 1]
    return [n.to_dict() for n in sorted(top_level, key=lambda n: n.url)]


# ── Sidebar update logic ──────────────────────────────────────────────────────

def _find_entry(data: list[dict], name_fragment: str) -> dict | None:
    """Find first entry whose name contains name_fragment (recursive)."""
    for item in data:
        if name_fragment in item.get("name", ""):
            return item
        for child in item.get("children", []):
            if name_fragment in child.get("name", ""):
                return child
    return None


def update_section(
    data: list[dict],
    section_name: str,
    seed_urls: list[str],
    max_depth: int,
    verbose: bool,
) -> bool:
    """Update a section entry in-place. Returns True if changes were made."""
    entry = _find_entry(data, section_name)
    if not entry:
        print(f"[SKIP] Section not found: {section_name!r}", file=sys.stderr)
        return False

    # section_root uses the URL from the sidebar entry (old-style hash URL).
    # Links discovered from .md pages may use either old or new URL format.
    section_root = entry["url"].rstrip("/")
    print(f"[INFO] Updating {section_name!r} (section_root={section_root})", file=sys.stderr)

    nodes = _build_section_tree(seed_urls, section_root, max_depth, verbose)
    if not nodes:
        print(f"[WARN] No pages discovered for {section_name!r}", file=sys.stderr)
        return False

    new_children = _nodes_to_tree(nodes, section_root)
    if not new_children:
        return False

    entry["children"] = new_children
    print(f"[OK]   {section_name!r}: {len(nodes)} pages → {len(new_children)} root children",
          file=sys.stderr)
    return True


def verify_existing_md_urls(data: list[dict], verbose: bool) -> int:
    """
    Walk the existing structure and verify / fill in md_url for DocumentType entries.
    Returns number of entries updated.
    """
    updated = 0

    def walk(items: list[dict]) -> None:
        nonlocal updated
        for item in items:
            if item.get("type") == "DocumentType" and not item.get("md_url"):
                url = item.get("url", "")
                if url and _has_md(url):
                    item["md_url"] = _make_md_url(url)
                    updated += 1
                    if verbose:
                        print(f"  [md] Found: {item['md_url']}", file=sys.stderr)
                    time.sleep(DELAY)
            walk(item.get("children", []))

    walk(data)
    return updated


# ── Main ──────────────────────────────────────────────────────────────────────

def _find_existing_file() -> Path | None:
    """Return the current dated index file, or None if not found."""
    if not DOCS_DIR.exists():
        return None
    matches = sorted(DOCS_DIR.glob(f"{FILE_STEM}*{FILE_SUFFIX}"))
    return matches[-1] if matches else None


def _new_file_path() -> Path:
    """Return the output path for today's dated index file."""
    today = datetime.date.today().strftime("%Y_%m-%d")
    return DOCS_DIR / f"{FILE_STEM}{today}{FILE_SUFFIX}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--max-depth", "-d", type=int, default=MAX_DEPTH,
        help=f"Maximum crawl depth per section (default: {MAX_DEPTH}).",
    )
    parser.add_argument(
        "--verify-md", action="store_true",
        help="Also verify/fill md_url for existing DocumentType entries.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print a preview but do not write or delete any files.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    existing = _find_existing_file()
    if existing is None:
        print("[ERROR] No existing feishu_md_doc_url_*.json found in docs/agents_doc/.", file=sys.stderr)
        sys.exit(1)

    with open(existing, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    changed = False

    for section_name, seed_urls in SEED_PAGES.items():
        changed |= update_section(data, section_name, seed_urls, args.max_depth, args.verbose)

    if args.verify_md:
        n = verify_existing_md_urls(data, args.verbose)
        if n:
            print(f"[OK] Filled in md_url for {n} existing entries.", file=sys.stderr)
            changed = True

    if not changed:
        print("[INFO] No changes detected.", file=sys.stderr)
        return

    if args.dry_run:
        print(json.dumps(data, ensure_ascii=False, indent=2)[:2000], "... [dry-run]")
        return

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    new_path = _new_file_path()
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    # Delete old file only after the new one is successfully written
    if existing != new_path and existing.exists():
        existing.unlink()
        print(f"[OK] Removed old index: {existing.name}", file=sys.stderr)

    print(f"[OK] Saved → {new_path.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
