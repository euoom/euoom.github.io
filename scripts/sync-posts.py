#!/usr/bin/env python3
"""Build euoom.github.io from public Knowledge Base markdown."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

import yaml
from markdown_it import MarkdownIt

SCRIPT_ROOT = Path(__file__).resolve().parent
SITE_ROOT = SCRIPT_ROOT.parent
CONFIG_FILE = SCRIPT_ROOT / "config.json"
POSTS_OUTPUT_DIR = SITE_ROOT / "post"
INDEX_OUTPUT_FILE = SITE_ROOT / "posts.json"
SITE_URL = "https://euoom.github.io"
SITE_TITLE = "euoom — 블로그"
SITE_DESCRIPTION = "만들고, 실험하고, 배운 것을 기록하는 기술 아카이브."

MD = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": False}).enable("table")


def load_source() -> Path:
    """Resolve KB source from explicit overrides, then the shared workspace convention."""
    knowledge_base_root = os.environ.get("KB_ROOT", "").strip()
    if not knowledge_base_root and CONFIG_FILE.is_file():
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        knowledge_base_root = str(config.get("knowledge_base_root") or "").strip()
    if knowledge_base_root:
        return Path(knowledge_base_root).expanduser() / "public" / "post"

    workspace_root = SITE_ROOT.parent.parent
    default_root = workspace_root / "knowledge-base"
    if not default_root.is_dir():
        raise SystemExit(
            f"Knowledge Base not found at workspace default: {default_root}. "
            "Set KB_ROOT or scripts/config.json to override it."
        )
    return default_root / "public" / "post"


def parse_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw.strip()
    parts = raw.split("---", 2)
    if len(parts) != 3:
        raise ValueError("frontmatter closing delimiter (---) is missing")
    metadata = yaml.safe_load(parts[1]) or {}
    if not isinstance(metadata, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return metadata, parts[2].strip()


def normalize_date(value, fallback: date) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value) if value else fallback.isoformat()


def normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise ValueError("tags must be a string or list")


def normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def normalize_url(value) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    markdown_match = re.search(r"https?://[^\s)\\]+", value)
    candidate = markdown_match.group(0) if markdown_match else value
    parsed = urlparse(candidate)
    return candidate if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def build_post(source: Path, source_dir: Path) -> dict:
    meta, body = parse_frontmatter(source.read_text(encoding="utf-8"))
    slug = str(meta.get("slug") or source.stem).strip()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError(f"invalid slug: {slug!r}; use lowercase letters, numbers and hyphens")
    relative = source.relative_to(source_dir)
    parent_parts = relative.parent.parts if relative.parent != Path(".") else ()
    for part in parent_parts:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", part):
            raise ValueError(f"invalid route segment: {part!r}; use lowercase letters, numbers and hyphens")
    route = "/".join((*parent_parts, slug))
    return {
        "slug": slug,
        "route": route,
        "title": str(meta.get("title") or slug.replace("-", " ").title()).strip(),
        "date": normalize_date(meta.get("date"), date.fromtimestamp(source.stat().st_mtime)),
        "tags": normalize_tags(meta.get("tags")),
        "summary": str(meta.get("summary") or "").strip(),
        "icon": str(meta.get("icon") or "✦").strip(),
        "featured": normalize_bool(meta.get("featured", False)),
        "project_url": normalize_url(meta.get("project_url")),
        "content": body,
    }


def render_markdown(source: str) -> str:
    mermaid_blocks: list[str] = []
    youtube_blocks: list[str] = []

    def stash_youtube(match: re.Match) -> str:
        video_id = match.group(1)
        index = len(youtube_blocks)
        youtube_blocks.append(
            '<div class="video-embed"><iframe '
            f'src="https://www.youtube-nocookie.com/embed/{video_id}" '
            'title="YouTube 영상" loading="lazy" '
            'referrerpolicy="strict-origin-when-cross-origin" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'allowfullscreen></iframe></div>'
        )
        return f"\nEUOOMYOUTUBEBLOCK{index}\n"

    # Explicit video directive only; arbitrary HTML/iframes remain disabled.
    source = re.sub(r"(?m)^\[youtube:(?:https?://(?:www\.)?youtube\.com/watch\?v=|https?://youtu\.be/)?([A-Za-z0-9_-]{11})\]\s*$", stash_youtube, source)

    def stash_mermaid(match: re.Match) -> str:
        index = len(mermaid_blocks)
        mermaid_blocks.append(html.escape(match.group(1).strip()))
        return f"\nEUOOMMERMAIDBLOCK{index}\n"

    source = re.sub(r"```mermaid\s*\n(.*?)```", stash_mermaid, source, flags=re.DOTALL)
    rendered = MD.render(source)
    def size_slide_comparison(match: re.Match) -> str:
        table = match.group(0)
        headings = [html.unescape(re.sub(r"<[^>]+>", "", value)).strip()
                    for value in re.findall(r"<th\b[^>]*>(.*?)</th>", table, re.DOTALL)]
        if headings == ["모델", "디버깅 결과"]:
            return table.replace('<table>', '<table class="model-results">', 1)
        if headings != ["구분", "내가 기대한 에이전트의 수준", "만들어진 결과물"]:
            return table
        return table.replace("<table>", '<table class="slide-comparison"><colgroup><col class="comparison-label"><col class="comparison-slide"><col class="comparison-slide"></colgroup>', 1)
    rendered = re.sub(r"<table>.*?</table>", size_slide_comparison, rendered, flags=re.DOTALL)
    for index, diagram in enumerate(mermaid_blocks):
        rendered = rendered.replace(
            f"<p>EUOOMMERMAIDBLOCK{index}</p>",
            f'<div class="mermaid">{diagram}</div>',
        )
    for index, embed in enumerate(youtube_blocks):
        rendered = rendered.replace(f"<p>EUOOMYOUTUBEBLOCK{index}</p>", embed)
    return rendered


def post_page(post: dict) -> str:
    title = html.escape(post["title"])
    summary = html.escape(post["summary"] or SITE_DESCRIPTION)
    canonical = f"{SITE_URL}/post/{post['route']}/"
    tags = " · ".join(html.escape(tag) for tag in post["tags"])
    project = ""
    if post["project_url"]:
        url = html.escape(post["project_url"], quote=True)
        project = f'<a class="project-link" href="{url}" target="_blank" rel="noopener noreferrer">Open project ↗</a>'
    body = render_markdown(post["content"])
    return f'''<!doctype html>
<html lang="ko" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="{summary}" />
  <meta name="author" content="euoom" />
  <meta name="theme-color" content="#0b0d10" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{summary}" />
  <meta property="og:url" content="{canonical}" />
  <meta property="article:published_time" content="{html.escape(post['date'])}" />
  <meta name="twitter:card" content="summary" />
  <link rel="canonical" href="{canonical}" />
  <link rel="alternate" type="application/rss+xml" title="{SITE_TITLE}" href="{SITE_URL}/feed.xml" />
  <title>{title} — euoom</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600&family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css" />
  <link rel="stylesheet" href="/styles.css?v=3" />
  <script defer src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/prism.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/plugins/autoloader/prism-autoloader.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script defer src="/post.js"></script>
</head>
<body>
  <a class="skip-link" href="#main">본문으로 건너뛰기</a>
  <header class="site-header"><div class="shell header-inner"><a class="brand" href="/"><span class="brand-mark" aria-hidden="true">e.</span><span>euoom</span></a><nav class="site-nav" aria-label="주요 메뉴"><a href="/" class="nav-link">블로그</a><a href="https://github.com/euoom" class="nav-link" target="_blank" rel="noopener noreferrer">GitHub</a><button id="theme-toggle" class="theme-toggle" type="button" aria-label="테마 변경">☀</button></nav></div></header>
  <main id="main" class="shell"><section class="post-detail active"><a class="back-link" href="/">← 블로그로 돌아가기</a><article><header><p class="article-kicker">{html.escape(post['icon'])} · {tags}</p><h1 class="article-title">{title}</h1>{f'<p class="article-summary">{summary}</p>' if post['summary'] else ''}<div class="article-meta"><time datetime="{html.escape(post['date'])}">{html.escape(post['date'])}</time>{project}</div></header><div class="markdown-body">{body}</div></article></section></main>
  <footer class="site-footer"><div class="shell footer-inner"><p>© {date.today().year} euoom</p></div></footer>
</body>
</html>
'''


def build_feed(posts: list[dict]) -> str:
    items = []
    kst = timezone(timedelta(hours=9))
    for post in posts:
        url = f"{SITE_URL}/post/{post['route']}/"
        published = datetime.fromisoformat(post["date"]).replace(tzinfo=kst)
        items.append(f'''  <item>
    <title>{xml_escape(post['title'])}</title>
    <link>{url}</link>
    <guid isPermaLink="true">{url}</guid>
    <pubDate>{format_datetime(published)}</pubDate>
    <description>{xml_escape(post['summary'])}</description>
  </item>''')
    return f'''<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel>
  <title>{xml_escape(SITE_TITLE)}</title>
  <link>{SITE_URL}/</link>
  <description>{xml_escape(SITE_DESCRIPTION)}</description>
  <language>ko</language>
{chr(10).join(items)}
</channel></rss>
'''


def build_sitemap(posts: list[dict]) -> str:
    urls = [f"  <url><loc>{SITE_URL}/</loc></url>"]
    urls.extend(f"  <url><loc>{SITE_URL}/post/{post['route']}/</loc><lastmod>{post['date']}</lastmod></url>" for post in posts)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"


def sync(source_dir: Path, clean: bool = True) -> int:
    if not source_dir.is_dir():
        raise SystemExit(f"Source directory not found: {source_dir}")
    POSTS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    posts = []
    for source in sorted(source_dir.rglob("*.md")):
        try:
            post = build_post(source, source_dir)
        except Exception as exc:
            raise SystemExit(f"Failed to parse {source.relative_to(source_dir)}: {exc}") from exc
        route = Path(post["route"])
        json_output = POSTS_OUTPUT_DIR / route.parent / f"{route.name}.json"
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        page_dir = POSTS_OUTPUT_DIR / route
        page_dir.mkdir(parents=True, exist_ok=True)
        (page_dir / "index.html").write_text(post_page(post), encoding="utf-8")
        posts.append({key: value for key, value in post.items() if key != "content"})
    posts.sort(key=lambda item: (item["date"], item["slug"]), reverse=True)
    INDEX_OUTPUT_FILE.write_text(json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (SITE_ROOT / "feed.xml").write_text(build_feed(posts), encoding="utf-8")
    (SITE_ROOT / "sitemap.xml").write_text(build_sitemap(posts), encoding="utf-8")
    (SITE_ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    if clean:
        expected_files = {
            POSTS_OUTPUT_DIR / Path(post["route"]).parent / f"{Path(post['route']).name}.json"
            for post in posts
        }
        expected_files.update(POSTS_OUTPUT_DIR / Path(post["route"]) / "index.html" for post in posts)
        for stale in sorted(POSTS_OUTPUT_DIR.rglob("*"), reverse=True):
            if stale.is_file() and stale not in expected_files:
                stale.unlink()
            elif stale.is_dir() and not any(stale.iterdir()):
                stale.rmdir()
    return len(posts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="override the configured public/post source directory")
    parser.add_argument("--no-clean", action="store_true", help="keep generated post artifacts with no matching source")
    args = parser.parse_args()
    source = (args.source or load_source()).expanduser().resolve()
    count = sync(source, clean=not args.no_clean)
    print(f"Published {count} post(s) from {source} -> {SITE_ROOT}")


if __name__ == "__main__":
    main()
