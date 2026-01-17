import json
import tqdm
import re
import subprocess

# Paths to your files
BLOG_FILE = "tagged_posts.json"   # your JSON file
OUTPUT_FILE = "tagged_posts_chunked.json"
TEXT_CHUNK_SIZE = 2000
TEXT_CHUNK_OVERLAP = 1000

def sliding_window(seq, size, step):
    """Simple chunking of article text with overlap. Returns the chunked parts as a list"""
    if size <= 0 or step <= 0:
        raise ValueError("size and step must be positive")

    n = len(seq)
    result = []
    for i in range(0, n, step):
        chunk = seq[i:i+size]
        result.append({'start': i, 'chunk': chunk})
        if i + size >= n:
            break

    return result

def main():
    with open(BLOG_FILE,"r", encoding="utf-8") as f:
        posts = json.load(f)

    print(f"Loaded {len(posts)} posts.")

    chunked_posts = []
    for post in tqdm.tqdm(posts):
        post_copy = post.copy()
        post_text = post_copy.pop("text")
        chunks = sliding_window(post_text, TEXT_CHUNK_SIZE, TEXT_CHUNK_OVERLAP)
        for chunk in chunks:
            chunk.update(post_copy)
        chunked_posts.extend(chunks)

    # Save tagged data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunked_posts, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
