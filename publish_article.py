#!/usr/bin/env python3
"""
Auto-publisher for raquel-campos.com
Called by linkedin_weekly_posts.py after generating the weekly posts.
Generates a long-form article, writes HTML to articles/, updates index.json,
and git-pushes so Cloudflare Pages auto-deploys.
"""

import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path

SITE_DIR = Path(__file__).parent


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:80]


def generate_article_html(title: str, date: str, topic: str, tags: list,
                           body_html: str, excerpt: str,
                           linkedin_posts: str) -> str:
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    # Pull first LinkedIn teaser post
    first_post = linkedin_posts.split("---")[1].strip() if "---" in linkedin_posts else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — Raquel Campos</title>
  <meta name="description" content="{excerpt}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{excerpt}">
  <meta property="og:type" content="article">
  <link rel="stylesheet" href="../style.css">
  <link rel="icon" href="../favicon.ico">
</head>
<body>

<nav class="nav">
  <div class="nav-inner">
    <a href="../index.html" class="nav-logo">Raquel <span>Campos</span></a>
    <ul class="nav-links">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../about.html">About</a></li>
      <li><a href="../articles.html" class="active">Articles</a></li>
      <li><a href="../contact.html">Contact</a></li>
    </ul>
  </div>
</nav>

<div class="article-header">
  <div class="article-header-inner">
    <p class="article-meta">{date} &nbsp;·&nbsp; {topic}</p>
    <h1>{title}</h1>
    <p class="deck">{excerpt}</p>
    <div style="margin-top:1.25rem;">{tags_html}</div>
  </div>
</div>

<div class="article-body">
{body_html}
</div>

<div class="article-footer">
  <div class="linkedin-teaser">
    <h4>This week on LinkedIn</h4>
    <p>Three shorter posts expanding on these signals — follow along for the weekly take.</p>
    <a href="https://linkedin.com/in/raquel-camposme" class="btn btn-dark" target="_blank" rel="noopener">Follow on LinkedIn →</a>
  </div>
  <p style="margin-top: 2rem; font-size: 0.9rem; color: var(--text-muted);">
    ← <a href="../articles.html">Back to all articles</a>
  </p>
</div>

<footer class="footer">
  <div class="footer-inner">
    <div class="footer-logo">Raquel <span>Campos</span></div>
    <ul class="footer-links">
      <li><a href="../index.html">Home</a></li>
      <li><a href="../about.html">About</a></li>
      <li><a href="../articles.html">Articles</a></li>
      <li><a href="../contact.html">Contact</a></li>
    </ul>
    <p class="footer-copy">&copy; {datetime.now().year} Raquel Campos</p>
  </div>
</footer>

</body>
</html>
"""


def markdown_to_html(text: str) -> str:
    """Minimal markdown → HTML: headings, bold, paragraphs, blockquotes."""
    lines = text.split("\n")
    html_lines = []
    in_para = False

    for line in lines:
        line = line.rstrip()

        if line.startswith("## "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("> "):
            if in_para: html_lines.append("</p>"); in_para = False
            html_lines.append(f"<blockquote><p>{line[2:]}</p></blockquote>")
        elif line == "":
            if in_para: html_lines.append("</p>"); in_para = False
        else:
            # inline bold
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            if not in_para:
                html_lines.append("<p>")
                in_para = True
            html_lines.append(line)

    if in_para:
        html_lines.append("</p>")

    return "\n".join(html_lines)


def update_index(slug: str, title: str, date: str, topic: str,
                  tags: list, excerpt: str) -> None:
    index_path = SITE_DIR / "articles" / "index.json"
    with open(index_path) as f:
        data = json.load(f)

    # Remove existing entry with same slug (idempotent re-publish)
    data["articles"] = [a for a in data["articles"] if a["slug"] != slug]

    data["articles"].insert(0, {
        "slug": slug,
        "title": title,
        "date": date,
        "topic": topic,
        "tags": tags,
        "excerpt": excerpt,
    })

    with open(index_path, "w") as f:
        json.dump(data, f, indent=2)


def git_push(message: str) -> None:
    cmds = [
        ["git", "-C", str(SITE_DIR), "add", "-A"],
        ["git", "-C", str(SITE_DIR), "commit", "-m", message],
        ["git", "-C", str(SITE_DIR), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  git warning: {result.stderr.strip()}")


def publish(title: str, topic: str, tags: list, body_markdown: str,
             excerpt: str, linkedin_posts: str) -> str:
    """
    Main entry point. Call this from linkedin_weekly_posts.py.
    Returns the URL of the published article.
    """
    date = datetime.now().strftime("%B %d, %Y")
    slug = slugify(title)
    body_html = markdown_to_html(body_markdown)

    html = generate_article_html(
        title=title, date=date, topic=topic, tags=tags,
        body_html=body_html, excerpt=excerpt, linkedin_posts=linkedin_posts
    )

    article_path = SITE_DIR / "articles" / f"{slug}.html"
    with open(article_path, "w") as f:
        f.write(html)

    update_index(slug, title, date, topic, tags, excerpt)

    git_push(f"publish: {title}")

    url = f"https://raquel-campos.com/articles/{slug}.html"
    print(f"  Published: {url}")
    return url


if __name__ == "__main__":
    # Test publish
    publish(
        title="Test Article: How to Read This Site",
        topic="Meta",
        tags=["foresight", "intralogistics"],
        body_markdown="""## Welcome

This is a test article to verify the auto-publishing pipeline works correctly.

## What this site is

Every Monday, a weekly foresight article is published here automatically, alongside three LinkedIn posts linking back.

## Why it matters

Because **connections between domains** are where the real signal lives.""",
        excerpt="A test article to verify the publishing pipeline is working end-to-end.",
        linkedin_posts="---\nTest LinkedIn post content here.\n---"
    )
