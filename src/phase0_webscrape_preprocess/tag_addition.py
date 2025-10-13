import json
import tqdm
import re
import subprocess

# Paths to your files
BLOG_FILE = "processed_posts.json"   # your JSON file
TAGS_FILE = "tags.txt"         # list of possible tags, one per line
OUTPUT_FILE = "tagged_posts.json"

# Ollama model name
MODEL = "gemma3:12b"  # or whatever model you have (e.g., mistral, gemma, etc.)

def call_ollama(prompt, model=MODEL):
    """Call Ollama CLI with a prompt and return the response text."""
    result = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def extract_tags_from_output(output, valid_tags):
    """
    Try to extract multiple tags from model output.
    Only keep valid tags that exist in the tag list.
    """
    # Lowercase both for comparison
    valid_tags_lower = [t.lower() for t in valid_tags]
    chosen = []
    for tag in valid_tags:
        if tag.lower() in output.lower():
            chosen.append(tag)
    if not chosen:
        # Fallback: try to parse comma-separated list
        guessed = re.findall(r"[A-Za-z0-9\s\-]+", output)
        chosen = [g.strip() for g in guessed if g.strip() in valid_tags]
    return list(set(chosen))

def main():
    # Load blog posts
    with open(BLOG_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    # Load tags
    with open(TAGS_FILE, "r", encoding="utf-8") as f:
        tags = [line.strip() for line in f if line.strip()]

    print(f"Loaded {len(posts)} posts and {len(tags)} candidate tags.")

    # Process posts
    for post in tqdm.tqdm(posts):
        text_sample = post["text"][:1200]  # truncate long text
        prompt = f"""
You are a blog content tagging assistant.
Given the following list of tags, choose all tags that are relevant to this blog post.
Return a comma-separated list of tags, and only include tags from the provided list.

Available tags:
{", ".join(tags)}

Blog post:
Title: {post["title"]}
Excerpt:
{text_sample}

Respond ONLY with a comma-separated list of tags from the list above.
""".strip()
        output = call_ollama(prompt)
        chosen_tags = extract_tags_from_output(output, tags)
        post["tags"] = chosen_tags

    # Save tagged data
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Multi-tagged posts saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()