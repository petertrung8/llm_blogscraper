from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time, os, requests, re, tqdm
from bs4 import BeautifulSoup
from html2text import HTML2Text
from urllib.parse import urlparse, urljoin

# ── 1) configure headless Chrome ─────────────────────────────────────────────
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)

# ── 2) setup converter ───────────────────────────────────────────────────────
converter = HTML2Text()
converter.ignore_images = False
converter.ignore_links = False

# ── 3) helper: extract links from sitemap.xml ─────────────────────────────
def extract_links_from_sitemap(sitemap_url):
    response = requests.get(sitemap_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch sitemap: {response.status_code}")

    soup = BeautifulSoup(response.content, 'xml')
    urls = [url.loc.text for url in soup.find_all('url')]
    return urls


# ── 3) helper: turn URL path into a slug-filename ────────────────────────────
def path_to_slug(url):
    path = urlparse(url).path.lstrip('/')
    if path.startswith('blog/'):
        path = path[len('blog/'):]
    return path.replace('/', '-')

# ── 4) helper: rewrite thejerx links in Markdown ───────────────────────────
def rewrite_jerx_links(md_text):
    pattern = re.compile(
        r'\[([^\]]+)\]\('
        r'(https://www\.thejerx\.com/blog/[0-9]+(?:/[0-9]+){2}/[^\)]+)'
        r'\)'
    )
    def repl(m):
        link_text = m.group(1)
        external_url = m.group(2)
        slug = path_to_slug(external_url)
        return f'[{link_text}]({slug}.md)'
    return pattern.sub(repl, md_text)

# ── 5) prepare output folders ─────────────────────────────────────────────────
base_folder = "saved_articles"
img_folder = os.path.join(base_folder, "images")
os.makedirs(img_folder, exist_ok=True)


# ── 6) your list of URLs ─────────────────────────────────────────────────────
urls = extract_links_from_sitemap("https://www.thejerx.com/sitemap.xml")

err_url = []
for url in tqdm.tqdm(urls):
    if not 'blog/' in url:
        print(f"Skipping non-blog URL: {url}")
        continue
    slug = path_to_slug(url)
    if os.path.exists(os.path.join(base_folder, f"{slug}.md")):
        continue
    # print(f"→ Fetching {url}  → slug: {slug}")
    driver.get(url)
    time.sleep(5)  # wait for JS-rendered content

    # ── 7) grab the article HTML ────────────────────────────────────────────
    try:
        article_el = driver.find_element(By.CSS_SELECTOR, "article")
    except NoSuchElementException:
        err_url.append(url)
        print(f"Error in: {url}")
        continue
    raw_html = article_el.get_attribute("innerHTML")

    # ── 8) parse & download images ───────────────────────────────────────────
    soup = BeautifulSoup(raw_html, "html.parser")

    # ── 9) turn any <iframe> (e.g. YouTube) into markdown links ──────────────
    for i, iframe in enumerate(soup.find_all("iframe"), start=1):
        src = iframe.get("src") or iframe.get("data-src")
        if not src:
            continue
        full_src = urljoin(url, src)
        # create a simple link tag: “[Media 1](https://...)”
        link_tag = soup.new_tag("a", href=full_src)
        link_tag.string = f"External media {i}"
        iframe.replace_with(link_tag)
    
    # ── 10) download & rewrite images ────────────────────────────────────────
    for i, img in enumerate(soup.find_all("img"), start=1):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        src = requests.compat.urljoin(url, src)
        resp = requests.get(src, stream=True)
        if resp.status_code == 200:
            ext = os.path.splitext(src)[1].split("?")[0] or ".jpg"
            local_name = f"{slug}_img{i}{ext}"
            local_path = os.path.join(img_folder, local_name)
            with open(local_path, "wb") as f:
                for chunk in resp.iter_content(1024):
                    f.write(chunk)
            img["src"] = os.path.join("images", local_name)

    # ── 11) convert modified HTML → Markdown ─────────────────────────────────
    markdown_body = converter.handle(str(soup))


    # ── 12) rewrite any thejerx.com/blog links → local .md files ────────────
    markdown_body = rewrite_jerx_links(markdown_body)

    # ── 13) write out the .md file (all in one folder) ──────────────────────
    md_path = os.path.join(base_folder, f"{slug}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        # Optional human-friendly heading:
        f.write(f"# {slug.replace('-', ' ')}\n\n")
        f.write(markdown_body)

if err_url:
    with open('error_links.txt', 'w') as f:
        for line in err_url:
            f.write(line+"\n")
driver.quit()
