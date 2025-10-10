import os
import re
import json
from bs4 import BeautifulSoup
from markdown import markdown
import datetime

# Directory containing your markdown files
INPUT_DIR = "./saved_articles"   # Change if needed
OUTPUT_FILE = "processed_posts.json"


def extract_metadata_and_text(file_path):
    """Extract metadata and clean text from a TheJerx markdown file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # --- Extract title and URL from first header ---
    header_match = re.search(r"# \[(.*?)\]\((.*?)\)", content)
    title = header_match.group(1).strip() if header_match else "Untitled"
    source_path = header_match.group(2).strip() if header_match else ""
    source_url = f"https://www.thejerx.com{source_path}" if source_path else ""

    # --- Extract date (first [Month Day, Year]) ---
    date_match = re.search(r"\[(\w+ \d{1,2}, \d{4})\]", content)
    date = ""
    if date_match:
        try:
            date_obj = datetime.datetime.strptime(date_match.group(1), "%B %d, %Y")
            date = date_obj.strftime("%Y-%m-%d")
        except ValueError:
            date = date_match.group(1)

    # --- Extract author ---
    author_match = re.search(r"\[([A-Za-z ]+)\]\(/\?author=.*?\)", content)
    author = author_match.group(1).strip() if author_match else "Unknown"

    # --- Remove images (Markdown + HTML) ---
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)  # markdown images
    content = re.sub(r"<img[^>]*>", "", content, flags=re.IGNORECASE)  # html images

    # --- Convert markdown to plain text ---
    html = markdown(content)
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
        cutoff = remain_header[0]+len(author)  # second last "__"
        text = text[cutoff:].lstrip()


    # --- Build ID ---
    slug = os.path.splitext(os.path.basename(file_path))[0]
    post_id = f"{date}-{slug}"

    return {
        "id": post_id,
        "title": title,
        "author": author,
        "date": date,
        "source_url": source_url,
        "text": text,
        "file": os.path.basename(file_path),
    }


def process_all_markdown(input_dir=INPUT_DIR, output_file=OUTPUT_FILE):
    """Process all markdown files in a directory and save to JSON."""
    all_posts = []
    for filename in os.listdir(input_dir):
        if filename.endswith(".md"):
            path = os.path.join(input_dir, filename)
            print(f"Processing {filename}...")
            post_data = extract_metadata_and_text(path)
            all_posts.append(post_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Processed {len(all_posts)} files → {output_file}")


if __name__ == "__main__":
    process_all_markdown()
