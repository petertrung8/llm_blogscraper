#!/usr/bin/env python3
import re
import json
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from markdown import markdown

DATE_LINK_RE = re.compile(
    r"\[(?P<date>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\]\((?P<url>[^)]+)\)",
    re.IGNORECASE
)

DATE_AUTHOR_LINE_RE = re.compile(
    r"\[(?P<date>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})\]\((?P<url>[^)]+)\)\s*/\s*\[(?P<author>[^\]]+)\]",
    re.IGNORECASE
)

H1_TITLE_RE = re.compile(r"^#\s+(?:\[(?P<link_title>[^\]]+)\]\([^)]+\)|(?P<plain_title>.+))\s*$")

AUTHOR_FALLBACK_RE = re.compile(
    r"^\s*#{1,6}\s*\[(?P<author>[^\]]+)\]\([^)]+author[^)]*\)\s*$",
    re.IGNORECASE | re.MULTILINE
)

LEADING_DATE_IN_TITLE_RE = re.compile(
    r"^\s*(?:\d{4}[-/ ]\d{1,2}[-/ ]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s*\d{4})\s*[-–—:]*\s*",
    re.IGNORECASE
)

def parse_front_matter(text: str):
    fm = {}
    if text.startswith("\ufeff"):
        text = text.lstrip("\ufeff")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, flags=re.DOTALL)
    if not m:
        m = re.match(r"^---\s*\n(.*?)\n---\s*(.*)$", text, flags=re.DOTALL)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    for line in fm_text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip().lower()] = v.strip().strip('"').strip("'")
    return fm, body

def extract_title(body: str, file_stem: str) -> str:
    for line in body.splitlines():
        m = H1_TITLE_RE.match(line.strip())
        if m:
            title = (m.group("link_title") or m.group("plain_title") or file_stem).strip()
            return title
    return file_stem

def extract_date_url_author(body: str):
    date, url, author = "", "", ""

    # First try combined date/url/author pattern on a single line
    m = DATE_AUTHOR_LINE_RE.search(body)
    if m:
        return m.group("date").strip(), m.group("url").strip(), m.group("author").strip()

    # Otherwise, get date+url from first date-link anywhere
    m = DATE_LINK_RE.search(body)
    if m:
        date = m.group("date").strip()
        url = m.group("url").strip()

    # Try to find an "Author" via author header link
    m2 = AUTHOR_FALLBACK_RE.search(body)
    if m2:
        author = m2.group("author").strip()

    # Also try to parse " / [Author]" on any line, even if date was elsewhere
    if not author:
        slash_author = re.search(r"/\s*\[(?P<author>[^\]]+)\]\([^)]+\)", body)
        if slash_author:
            author = slash_author.group("author").strip()

    return date, url, author

def to_iso_date(date_str: str) -> str:
    """Convert 'Month DD, YYYY' or variations to ISO 8601 YYYY-MM-DD, else return original."""
    date_str = date_str.strip()
    # Common formats to try
    fmts = [
        "%B %d, %Y",   # October 02, 2015
        "%b %d, %Y",   # Oct 2, 2015
        "%B %d,%Y",    # October 2,2015 (missing space)
        "%b %d,%Y",    # Oct 2,2015
        "%Y-%m-%d",    # 2015-10-02
        "%Y/%m/%d",    # 2015/10/02
        "%Y %m %d",    # 2015 10 02
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    # Try to fix ordinal day suffixes like "October 2nd, 2015"
    m = re.match(r"^(?P<mon>\w+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th),\s*(?P<year>\d{4})$", date_str, flags=re.IGNORECASE)
    if m:
        try:
            dt = datetime.strptime(f"{m.group('mon')} {m.group('day')}, {m.group('year')}", "%B %d, %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return date_str  # fallback to original if parsing fails

def clean_title(title: str) -> str:
    # Remove leading date patterns
    cleaned = LEADING_DATE_IN_TITLE_RE.sub("", title).strip()
    # De-dub spaces and separators
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -–—:")
    return cleaned if cleaned else title

def body_process(body:str, author) -> str:
    # --- Remove images (Markdown + HTML) ---
    body = re.sub(r"!\[.*?\]\(.*?\)", "", body)  # markdown images
    body = re.sub(r"<img[^>]*>", "", body, flags=re.IGNORECASE)  # html images
    # --- Convert markdown to plain text ---
    html = markdown(body)
    text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    
    # --- Clean up newlines and hyphenations ---
    # 1. Remove hyphen + newline (e.g. "transfor-\nmation" → "transformation")
    text = re.sub(r"-\n", "", text)
    # 2. Replace single newlines with spaces but keep paragraph breaks (\n\n)
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # 3. Normalize excessive blank lines to just one paragraph break
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    underscores = [m.start() for m in re.finditer(r"__", text)]
    if len(underscores) >= 2:
        cutoff = underscores[-2]-1  # second last "__"
        text = text[:cutoff].rstrip()
    
    remain_header = [m.start() for m in re.finditer(author, text)]
    if remain_header:
        cutoff = remain_header[0]+len(author)
        text = text[cutoff:].lstrip()
    return text

def parse_markdown_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, body = parse_front_matter(text)

    # If no front matter, allow simple key: value header section until blank line
    if not meta:
        lines = text.splitlines()
        head_meta = {}
        i = 0
        while i < len(lines):
            if not lines[i].strip():
                i += 1
                break
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                head_meta[k.strip().lower()] = v.strip().strip('"').strip("'")
                i += 1
            else:
                break
        if head_meta:
            meta = head_meta
            body = "\n".join(lines[i:])
        else:
            body = text

    file_stem = path.stem
    title = meta.get("title") or extract_title(body, file_stem)
    title = clean_title(title)

    # Extract date/url/author from body content if not present in meta
    date = meta.get("date", "").strip()
    source_url = meta.get("source_url", "").strip()
    author = meta.get("author", "").strip()

    d,u,a = extract_date_url_author(body)
    if not date and d: date = d
    if not source_url and u: source_url = u
    if not author and a: author = a

    if "\n" in author:
        author = author.replace("\n", " ")

    # Link to actual blog
    source_url = f"https://www.thejerx.com{source_url}" if source_url else ""

    # Normalize date to ISO
    if date:
        date = to_iso_date(date)
    
    body = body_process(body, author)

    return {
        "id": file_stem,
        "title": title,
        "author": author,
        "date": date,
        "source_url": source_url,
        "text": body.strip()
    }

def main(input_dir: str, output_json: str):
    md_paths = list(Path(input_dir).rglob("*.md"))
    articles = []
    for p in sorted(md_paths):
        try:
            parsed = parse_markdown_file(p)
        except Exception as e:
            parsed = {
                "id": p.stem,
                "title": p.stem,
                "author": "",
                "date": "",
                "source_url": "",
                "text": ""
            }
        # Ensure all keys exist
        for key in ["id", "title", "author", "date", "source_url", "text"]:
            parsed.setdefault(key, "")
        articles.append(parsed)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    import sys
    in_dir = "saved_articles"
    out_path = "articles.json"
    main(in_dir, out_path)
