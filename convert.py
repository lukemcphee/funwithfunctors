import re
from pathlib import Path
import shutil

# -------------------------
# Paths
# -------------------------
src_posts = Path("posts")
docs_dir = Path("docs")
posts_dir = docs_dir / "_posts"
drafts_dir = docs_dir / "_drafts"
assets_dir = docs_dir / "assets/images"
layouts_dir = docs_dir / "_layouts"

# -------------------------
# Create folder structure
# -------------------------
for folder in [docs_dir, posts_dir, drafts_dir, assets_dir, layouts_dir]:
    folder.mkdir(parents=True, exist_ok=True)

# -------------------------
# Move Markdown posts
# -------------------------
for md_file in src_posts.glob("*.md"):
    shutil.move(str(md_file), str(posts_dir / md_file.name))
    print(f"Moved post {md_file.name} → _posts/")

# Move drafts
drafts_src = src_posts / "_drafts"
if drafts_src.exists():
    for draft in drafts_src.glob("*.md"):
        shutil.move(str(draft), str(drafts_dir / draft.name))
        print(f"Moved draft {draft.name} → _drafts/")

# -------------------------
# Move all images to single assets folder
# -------------------------
existing_files = set(f.name for f in assets_dir.glob("*"))

for img_file in src_posts.rglob("*"):
    if img_file.is_file() and img_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".svg"]:
        filename = img_file.name
        # avoid collisions by prefixing with parent folder name
        if filename in existing_files:
            filename = f"{img_file.parent.name}-{filename}"
        shutil.move(str(img_file), assets_dir / filename)
        existing_files.add(filename)
        print(f"Moved image {img_file} → {assets_dir / filename}")

# -------------------------
# Update Markdown image links
# -------------------------
md_image_re = re.compile(r'(!\[.*?\])\((.*?)\)')
html_image_re = re.compile(r'(<img\s+[^>]*src=["\'])(.*?)["\']')

def fix_links(md_path):
    text = md_path.read_text(encoding="utf-8")

    def md_replace(m):
        filename = Path(m.group(2)).name
        return f'{m.group(1)}({{{{ "/assets/images/{filename}" | relative_url }}}})'

    def html_replace(m):
        filename = Path(m.group(2)).name
        return f'{m.group(1)}{{{{ "/assets/images/{filename}" | relative_url }}}}"'

    text = md_image_re.sub(md_replace, text)
    text = html_image_re.sub(html_replace, text)
    md_path.write_text(text, encoding="utf-8")

for md_file in posts_dir.glob("*.md"):
    fix_links(md_file)
for md_file in drafts_dir.glob("*.md"):
    fix_links(md_file)

# -------------------------
# Create _config.yml
# -------------------------
config = """title: Fun with Functors
description: Thoughts on programming, Scala, Spark, and functional ideas
url: "https://lukemcphee.github.io"
baseurl: "/funwithfunctors"

markdown: kramdown
"""

(docs_dir / "_config.yml").write_text(config, encoding="utf-8")
print("Created _config.yml")

# -------------------------
# Create index.md
# -------------------------
index_md = """---
layout: default
title: Fun with Functors
---

# Fun with Functors

Thoughts on programming, Scala, Spark, and functional ideas.

## Posts

{% for post in site.posts %}
- **{{ post.date | date: "%Y-%m-%d" }}** —
  [{{ post.title }}]({{ post.url | relative_url }})
{% endfor %}
"""
(docs_dir / "index.md").write_text(index_md, encoding="utf-8")
print("Created index.md")

# -------------------------
# Create default layout
# -------------------------
default_html = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{{ page.title }} · {{ site.title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
  </head>
  <body>
    <main>
      {{ content }}
    </main>
  </body>
</html>
"""
(layouts_dir / "default.html").write_text(default_html, encoding="utf-8")
print("Created _layouts/default.html")

print("\nSetup complete! Run:\ncd docs && jekyll serve")

